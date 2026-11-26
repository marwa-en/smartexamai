"""
Syntax Repair Module for SmartExamAI (Preprocessing Step)

Applies conservative, deterministic syntax repairs to student code.
NEVER modifies algorithm, variable names, function names, or logic.
Supported: PHP, Python, Java.
"""
import re
from typing import Dict, List, Optional, Any

def detect_language(code: str) -> str:
    code_stripped = code.strip()
    if code_stripped.startswith('<?') or re.search(r'\b(function|foreach|if|echo)\b.*\$', code_stripped):
        return 'php'
    if any(ind in code_stripped for ind in ['public class', 'System.out.', 'String[] args']):
        return 'java'
    return 'python'

def repair_php(code: str) -> Dict[str, Any]:
    repairs: List[str] = []
    repaired_code = code
    
    if not repaired_code.strip().startswith('<?'):
        repaired_code = '<?php\n' + repaired_code
        repairs.append("Added missing '<?php' at the beginning")
        
    if ';;' in repaired_code:
        repaired_code = repaired_code.replace(';;', ';')
        repairs.append("Removed duplicated semicolons ';;'")
        
    open_braces = repaired_code.count('{')
    close_braces = repaired_code.count('}')
    if open_braces > close_braces:
        missing = open_braces - close_braces
        repaired_code = repaired_code.rstrip() + '\n' + '}' * missing
        repairs.append(f"Added {missing} missing closing brace '}}' at the end")
        
    def fix_params(match: re.Match) -> str:
        params_str = match.group(1)
        params = [p.strip() for p in params_str.split(',')]
        new_params = []
        changed = False
        for p in params:
            if not p: 
                new_params.append(p)
                continue
            if re.match(r'^[a-zA-Z_]\w*$', p):
                new_params.append('$' + p)
                changed = True
            else:
                new_params.append(p)
        if changed:
            repairs.append("Added missing '$' to function parameters")
        return f"({', '.join(new_params)})"
    
    repaired_code = re.sub(r'\bfunction\s+\w+\s*\(([^)]*)\)', fix_params, repaired_code)
    
    return {"original_code": code, "repaired_code": repaired_code, "language": "php", "repair_applied": len(repairs) > 0, "repairs": repairs}

def repair_python(code: str) -> Dict[str, Any]:
    repairs: List[str] = []
    lines = code.split('\n')
    repaired_lines = []
    
    for i, line in enumerate(lines):
        new_line = line
        stripped = line.rstrip()
        if re.match(r'^\s*(if|for|while|def|class|elif|else|try|except|finally|with)\b.*$', stripped) and not stripped.endswith(':'):
            new_line = stripped + ':'
            repairs.append(f"Added missing ':' at the end of line {i+1}")
            
        if i > 0 and lines[i-1].rstrip().endswith(':') and new_line.strip() and not new_line.startswith((' ', '\t')):
            if not re.match(r'^\s*(else|elif|except|finally)\b', new_line):
                new_line = '    ' + new_line
                repairs.append(f"Fixed indentation on line {i+1}")
        repaired_lines.append(new_line)
        
    repaired_code = '\n'.join(repaired_lines)
    open_parens = repaired_code.count('(')
    close_parens = repaired_code.count(')')
    if open_parens > close_parens:
        missing = open_parens - close_parens
        repaired_code += '\n' + ')' * missing
        repairs.append(f"Added {missing} missing closing parenthesis ')' at the end")
        
    return {"original_code": code, "repaired_code": repaired_code, "language": "python", "repair_applied": len(repairs) > 0, "repairs": repairs}

def repair_java(code: str) -> Dict[str, Any]:
    repairs: List[str] = []
    repaired_code = code
    
    open_braces = repaired_code.count('{')
    close_braces = repaired_code.count('}')
    if open_braces > close_braces:
        missing = open_braces - close_braces
        repaired_code = repaired_code.rstrip() + '\n' + '}' * missing
        repairs.append(f"Added {missing} missing closing brace '}}' at the end")
        
    return {"original_code": code, "repaired_code": repaired_code, "language": "java", "repair_applied": len(repairs) > 0, "repairs": repairs}

def repair_code(code: str, language: Optional[str] = None) -> Dict[str, Any]:
    lang = (language or detect_language(code)).lower()
    if lang == 'php': return repair_php(code)
    if lang == 'python': return repair_python(code)
    if lang == 'java': return repair_java(code)
    return {"original_code": code, "repaired_code": code, "language": lang, "repair_applied": False, "repairs": []}