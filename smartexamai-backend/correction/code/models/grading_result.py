"""Pydantic models for SmartExamAI grading output."""
from pydantic import BaseModel, Field
from typing import List

class FailedTestAnalysis(BaseModel):
    test_id: int
    reason: str
    recommendation: str

class GradingResult(BaseModel):
    score: int = Field(..., ge=0)
    max_score: int = Field(..., gt=0)
    overall_assessment: str
    algorithm_correct: bool
    syntax_errors: List[str] = Field(default_factory=list)
    logical_errors: List[str] = Field(default_factory=list)
    runtime_errors: List[str] = Field(default_factory=list)
    failed_tests_analysis: List[FailedTestAnalysis] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    feedback: str
    suggested_improvements: List[str] = Field(default_factory=list)