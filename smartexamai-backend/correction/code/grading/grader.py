"""Grader Orchestrator for SmartExamAI."""
from models.exercise import Exercise
from sandbox.execution_report import ExecutionReport
from models.grading_result import GradingResult
from grading.prompt_builder import build_grading_prompt
from grading.llm_client import LLMClient
from grading.parser import parse_grading_response
from typing import List

class CodeGrader:
    def __init__(self, api_key: str = None):
        self.llm_client = LLMClient(api_key=api_key)

    def grade(
        self, 
        exercise: Exercise, 
        student_code: str, 
        execution_report: ExecutionReport, 
        language: str, 
        syntax_repairs: List[str]
    ) -> GradingResult:
        prompt = build_grading_prompt(
            exercise=exercise,
            student_code=student_code,
            execution_report=execution_report,
            language=language,
            syntax_repairs=syntax_repairs
        )
        
        raw_response = self.llm_client.grade_submission(prompt)
        return parse_grading_response(raw_response)