"""Prompt Builder for SmartExamAI Grading Module."""
import json
from typing import List
from models.exercise import Exercise
from sandbox.execution_report import ExecutionReport


def build_grading_prompt(
    exercise: Exercise,
    student_code: str,
    execution_report: ExecutionReport,
    language: str,
    syntax_repairs: List[str]
) -> str:
    
    # Utilise les vrais attributs de ta classe ExecutionReport
    total_tests = execution_report.passed_tests + execution_report.failed_tests

    prompt = f"""You are an experienced programming instructor responsible for grading students' exam answers.
Your task is NOT only to execute code. Your task is to evaluate the student's understanding of the problem exactly as a human teacher would.
You will receive:
1. The programming language.
2. The exercise statement.
3. The student's source code.
4. The sandbox execution report.
5. The grading rubric.
6. Optional grading instructions from the professor.

## Important grading rules
Do NOT assign a zero simply because the code does not compile.
First determine whether the student's algorithm and reasoning are correct.
If the compilation fails only because of small syntax mistakes (missing semicolon, missing `$` in PHP, missing `<?php`, missing colon in Python, indentation, missing braces, etc.), consider these as minor errors and apply only a reasonable penalty.
Differentiate between:
* Syntax errors
* Logical errors
* Algorithmic errors
* Runtime errors
* Missing edge cases
* Poor coding practices
Use the sandbox results to identify failing tests, but explain WHY they failed.
If syntax repairs were applied, evaluate the ORIGINAL student code, not the repaired version.
Do not reward code that was fixed automatically. Use the repaired code only to understand the student's intended algorithm.

## Provided Information
Programming Language: {language}
Exercise Statement:
{exercise.statement}
Student Code:
```{language}
{student_code}
```
"""
    if exercise.reference_solution:
        prompt += f"""
Reference Solution (for grading guidance only, do not reveal to the student):
```{language}
{exercise.reference_solution}
```
"""
    if exercise.rubric:
        prompt += f"""
Grading Rubric:
{json.dumps(exercise.rubric, ensure_ascii=False, indent=2)}
"""
    if exercise.consignes:
        prompt += f"""
Grading Instructions from the Professor (follow these carefully — they take
precedence over your own judgment on tolerances, emphasis, and penalties):
{exercise.consignes}
"""
    if syntax_repairs:
        prompt += f""" ⚠️  IMPORTANT: The system auto-corrected minor syntax errors before execution: {', '.join(syntax_repairs)}.
DO NOT penalize the student for these syntax issues. Grade based strictly on the underlying algorithmic logic, style, and security.
"""

    # Le rapport d'exécution du sandbox doit TOUJOURS être envoyé au LLM,
    # que des réparations de syntaxe aient eu lieu ou non : sans lui, le LLM
    # note à l'aveugle, sans savoir si le code a compilé/exécuté ni combien
    # de tests sont passés.
    prompt += f""" Sandbox Execution Report:

    Compiled Successfully: {execution_report.compiled}
    Executed Successfully: {execution_report.executed}
    Tests Passed: {execution_report.passed_tests} / {total_tests}
    Execution Time: {execution_report.execution_time_ms} ms
    Memory Usage: {execution_report.memory_mb} MB

Test Case Details (Failed Tests):
"""
    if execution_report.failed_cases:
        # Itère sur failed_cases (seulement les tests échoués)
        for tc in execution_report.failed_cases:
            prompt += f"Test {tc.test_id} [❌ FAIL]:\n"
            prompt += f"  Input: {repr(tc.input_data)}\n"
            prompt += f"  Expected: {repr(tc.expected_output)}\n"
            prompt += f"  Actual: {repr(tc.actual_output)}\n"
            if tc.error_message:
                prompt += f"  Error: {tc.error_message}\n"
    else:
        prompt += "Tous les tests ont réussi.\n"

    prompt += """ Produce your answer ONLY as valid JSON in FRENCH.
Use exactly this schema:
{
  "score": 0,
  "max_score": 20,
  "overall_assessment": "",
  "algorithm_correct": true,
  "syntax_errors": [""],
  "logical_errors": [""],
  "runtime_errors": [""],
  "failed_tests_analysis": [
    {
      "test_id": 0,
      "reason": "",
      "recommendation": ""
    }
  ],
  "strengths": [""],
  "weaknesses": [""],
  "feedback": "",
  "suggested_improvements": [""]
}
Evaluation criteria:

    Correct understanding of the problem.
    Correct algorithm.
    Correct implementation.
    Correct handling of edge cases.
    Code quality.
    Syntax quality.
    Sandbox execution results.

Do not invent errors.
Base every observation on the provided code or the sandbox report.
Never produce Markdown.
Never produce explanations outside the JSON.
ALL TEXT FIELDS MUST BE IN FRENCH.
"""
    return prompt