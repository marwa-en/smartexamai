"""
Programming language detection using heuristics.
"""
import re
from typing import Optional


class LanguageDetector:
    """
    Detects the programming language of a given code snippet using heuristics.
    Useful for verifying the provided language hint or inferring it if missing.
    """
    
    # Mapping of language names to their identifying regex patterns
    LANGUAGE_SIGNATURES = {
        "python": [r"^\s*def\s+\w+", r"^\s*class\s+\w+", r"^\s*import\s+", r"print\s*\("],
        "java": [r"public\s+class", r"public\s+static\s+void\s+main", r"System\.out\.print"],
        "c": [r"#include\s*<\w+\.h>", r"int\s+main\s*\(", r"printf\s*\("],
        "cpp": [r"#include\s*<\w+>", r"using\s+namespace\s+std", r"cout\s*<<"],
        "php": [r"<\?php", r"\$\w+\s*=", r"echo\s+"],
        "javascript": [r"console\.log\s*\(", r"const\s+\w+\s*=", r"let\s+\w+\s*="],
        "typescript": [r":\s*(string|number|boolean)\b", r"interface\s+\w+"]
    }

    def detect(self, code: str, hint: Optional[str] = None) -> str:
        """
        Detects the programming language.
        
        Args:
            code: The cleaned source code.
            hint: An optional language hint (e.g., from the input JSON).
            
        Returns:
            The detected or verified language string (lowercase).
        """
        # Normalize hint if provided
        if hint:
            hint = hint.lower().strip()
            # Map common aliases to standard names
            alias_map = {"py": "python", "js": "javascript", "ts": "typescript", "c++": "cpp"}
            hint = alias_map.get(hint, hint)
            
            if hint in self.LANGUAGE_SIGNATURES:
                # Verify the hint against the code signatures
                for pattern in self.LANGUAGE_SIGNATURES[hint]:
                    if re.search(pattern, code, re.MULTILINE):
                        return hint
                # If no signatures match, it might be a very short snippet. 
                # We trust the hint if it's a known language.
                return hint

        # Fallback: Heuristic detection based on signature scoring
        scores = {lang: 0 for lang in self.LANGUAGE_SIGNATURES}
        
        for lang, patterns in self.LANGUAGE_SIGNATURES.items():
            for pattern in patterns:
                if re.search(pattern, code, re.MULTILINE):
                    scores[lang] += 1
                    
        # Special boost for PHP to avoid confusion with C/JS when tags are present
        if "<?php" in code:
            scores["php"] += 5
            
        best_lang = max(scores, key=scores.get)
        
        if scores[best_lang] > 0:
            return best_lang
            
        return "unknown"