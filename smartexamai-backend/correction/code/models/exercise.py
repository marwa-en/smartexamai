"""
Models for representing exam exercises and their components.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class ExerciseType(str, Enum):
    """Enumeration of supported exercise types."""
    FUNCTION = "function"
    PROGRAM = "program"


@dataclass
class TestCase:
    """
    Represents a single test case for an exercise.

    Attributes:
        input_data: The input to be fed to the program (stdin) or parsed for function arguments.
        expected_output: The expected standard output or return value.
        is_hidden: Whether the test case should be hidden from the student's view.
    """
    input_data: str
    expected_output: str
    is_hidden: bool = False


@dataclass
class Exercise:
    """
    Represents a programming exercise.

    Attributes:
        title: Title of the exercise.
        statement: Problem description.
        language: Programming language (e.g., 'python', 'c', 'java', 'php').
        type: Type of exercise (FUNCTION or PROGRAM).
        rubric: Grading rubric with criteria and max scores.
        test_cases: List of test cases to evaluate the submission.
        id: Unique identifier for the exercise.
        reference_solution: Optional correct solution provided by the professor.
        function_name: The name of the function to call (only for FUNCTION type exercises).
        consignes: Optional grading instructions from the professor (tolerances, things to
            emphasize or ignore, etc.), taken into account by the LLM during evaluation.
    """
    title: str
    statement: str
    language: str
    type: ExerciseType
    rubric: Dict[str, Any]
    test_cases: List[TestCase] = field(default_factory=list)
    id: Optional[str] = None
    reference_solution: Optional[str] = None
    function_name: Optional[str] = None  # <--- Crucial for the PythonRunner harness
    consignes: Optional[str] = None  # Consignes de correction fournies par le professeur (prises en compte par le LLM)