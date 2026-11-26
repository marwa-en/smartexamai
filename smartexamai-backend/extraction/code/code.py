import os
import re
import json
import base64
import tempfile
import subprocess
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from dotenv import load_dotenv
from mistralai.client import Mistral
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from security.llm_guard import detect_prompt_injection, sanitize_llm_text, log_llm_call
load_dotenv()


class PixtralClient:
    def __init__(self, api_key: str = None, model: str = "mistral-medium-latest"):
        self.api_key = api_key or os.environ.get("API_KEY")
        if not self.api_key:
            raise ValueError("Clé API manquante. Définis MISTRAL_API_KEY ou passe-la en paramètre.")
        self.client = Mistral(api_key=self.api_key)
        self.model = model

    @staticmethod
    def encode_image(image_path: str) -> str:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image introuvable : {image_path}")

        mime = {'.jpg': 'jpeg', '.jpeg': 'jpeg', '.png': 'png',
                '.webp': 'webp', '.bmp': 'bmp'}.get(path.suffix.lower(), 'jpeg')

        with open(path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode()
        return f"data:image/{mime};base64,{b64}"

    def generate(self, prompt: str, image_path: str) -> str:
        response = self.client.chat.complete(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": self.encode_image(image_path)}},
                ],
            }],
            temperature=0.0,
            max_tokens=4096,
        )
        return response.choices[0].message.content




CODE_PROMPT = """Tu es un système d'extraction de code manuscrit.

RÈGLES :
- Extraire fidèlement le code visible, sans corriger ni interpréter
- Conserver indentation, sauts de ligne et structure exacts
- Si un caractère est illisible, écrire [ILLISIBLE]
- Ne rien ajouter (pas de code, pas de commentaires invisibles)

SORTIE : UNIQUEMENT un JSON :
{"code": "le code extrait ici"}
"""


def build_code_prompt(teacher_input: Dict[str, Any]) -> str:
    lang = teacher_input.get('language', 'python')
    return f"""{CODE_PROMPT}

CONTEXTE :
- Matière : {teacher_input.get('subject', 'Informatique')}
- Type : {teacher_input.get('exam_type', 'Examen')}
- Langage : {lang}

Extrais uniquement le code {lang} manuscrit visible."""


def extract_code_from_response(response: str) -> str:
    # 1. JSON direct
    try:
        data = json.loads(response)
        if "code" in data:
            return data["code"]
    except json.JSONDecodeError:
        pass

    # 2. JSON partiel
    m = re.search(r'\{[\s\S]*?"code"\s*:\s*"([\s\S]*?)"[\s\S]*?\}', response)
    if m:
        code = m.group(1)
        for old, new in [('\\n', '\n'), ('\\t', '\t'), ('\\"', '"'), ('\\\\', '\\')]:
            code = code.replace(old, new)
        return code

    # 3. Bloc markdown
    m = re.search(r'```(?:\w+)?\s*\n([\s\S]*?)```', response)
    if m:
        return m.group(1).strip()

    return response.strip()


def clean_code(code: str, indent_size: int = 4) -> str:
    if not code:
        return ""
    lines = [line.rstrip() for line in code.split("\n")]
    # Supprimer lignes vides en début/fin
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    # Normaliser indentation
    return "\n".join(line.replace("\t", " " * indent_size) for line in lines)


class CodeSyntaxChecker:
    ALIASES = {'javascript': 'js', 'typescript': 'js', 'c++': 'c', 'cpp': 'c'}
    SUPPORTED = {'python', 'c', 'php', 'js', 'java'}

    @classmethod
    def check(cls, code: str, language: str) -> Tuple[bool, Optional[str]]:
        lang = cls.ALIASES.get(language.lower().strip(), language.lower().strip())
        if lang not in cls.SUPPORTED:
            return False, f"Langage non supporté : {lang}"
        if not code or not code.strip():
            return False, "Code vide"
        return getattr(cls, f"_check_{lang}")(code)

    @classmethod
    def _check_python(cls, code: str) -> Tuple[bool, Optional[str]]:
        try:
            compile(code, "<student>", "exec")
            return True, None
        except SyntaxError as e:
            return False, f"Ligne {e.lineno} : {e.msg}"

    @classmethod
    def _run_compiler(cls, code: str, suffix: str, cmd: list) -> Tuple[bool, Optional[str]]:
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
            f.write(code)
            tmp = f.name
        try:
            r = subprocess.run(cmd + [tmp], capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                return True, None
            err = (r.stderr or r.stdout or "Erreur inconnue").strip().split('\n')[0]
            return False, err
        except FileNotFoundError:
            return False, f"{cmd[0]} non installé"
        except subprocess.TimeoutExpired:
            return False, "Timeout"
        finally:
            os.unlink(tmp)

    @classmethod
    def _check_c(cls, code):   return cls._run_compiler(code, '.c',   ['gcc', '-fsyntax-only', '-w'])
    @classmethod
    def _check_php(cls, code):
        if not code.strip().startswith('<?php'): code = "<?php\n" + code
        if not code.strip().endswith('?>'):      code = code + "\n?>"
        return cls._run_compiler(code, '.php', ['php', '-l'])
    @classmethod
    def _check_js(cls, code):  return cls._run_compiler(code, '.js',  ['node', '--check'])

    @classmethod
    def _check_java(cls, code: str) -> Tuple[bool, Optional[str]]:
        m = re.search(r'public\s+class\s+(\w+)', code)
        name = m.group(1) if m else "Main"
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / f"{name}.java"
            path.write_text(code, encoding='utf-8')
            try:
                r = subprocess.run(['javac', str(path)], capture_output=True, text=True, timeout=15)
                if r.returncode == 0:
                    return True, None
                err = re.sub(r'[/\\\w]+\.java:\d+:\s*', '', r.stderr.strip())
                return False, err.split('\n')[0] if err else "Erreur inconnue"
            except FileNotFoundError:
                return False, "javac non installé"
            except subprocess.TimeoutExpired:
                return False, "Timeout"


def extract_code(image_path: str, teacher_input: Dict[str, Any], api_key: str = None) -> Dict[str, Any]:
    language = teacher_input.get('language', 'python').lower()

    pixtral = PixtralClient(api_key=api_key)
    raw_code = extract_code_from_response(pixtral.generate(build_code_prompt(teacher_input), image_path))
    cleaned = clean_code(raw_code)
    # ✅ NOUVEAU : Détecter les tentatives d'injection dans le code extrait
    injection_flags = detect_prompt_injection(cleaned)

    # ✅ NOUVEAU : Sanitiser le code
    cleaned = sanitize_llm_text(cleaned, max_length=50_000)


    # Balises PHP automatiques
    final_code = cleaned
    if language == 'php':
        if not cleaned.strip().startswith('<?php'): final_code = "<?php\n" + final_code
        if not final_code.strip().endswith('?>'):   final_code = final_code + "\n?>"

    is_valid, error = CodeSyntaxChecker.check(final_code, language)

    result = {
        'code': final_code,
        'language': language,
        'injection_flags': injection_flags,
        'requires_human_review': len(injection_flags) > 0,
       
    }
    log_llm_call(
        section="code_extraction",
        injection_flags=injection_flags,
        output_valid=is_valid,
        error=error if not is_valid else None,
    )


    with open("code.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    result['file_path'] = "code.json"
    return result


 