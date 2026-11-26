"""
Data models for execution reports and test case results.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TestCaseResult:
    """
    Represents the result of a single test case execution.
    
    Attributes:
        test_id: Unique identifier for the test case.
        input_data: The input provided to the test.
        expected_output: The expected output defined by the professor.
        actual_output: The actual output produced by the student's code.
        passed: Whether the test case passed.
        error_message: Optional error message if the test crashed or timed out.
    """
    test_id: int
    input_data: str
    expected_output: str
    actual_output: str
    passed: bool
    error_message: Optional[str] = None


@dataclass
class ExecutionReport:
    """
    Represents the complete execution report of a student's code.
    This object is serialized and sent to the LLM for grading.
    
    Attributes:
        compiled: Whether the code compiled successfully (always True for interpreted languages).
        executed: Whether the code executed without fatal runtime errors.
        passed_tests: Number of test cases passed.
        failed_tests: Number of test cases failed.
        execution_time_ms: Total execution time in milliseconds.
        memory_mb: Peak memory usage in megabytes.
        stdout: Captured standard output.
        stderr: Captured standard error.
        failed_cases: List of detailed results for failed test cases.
    """
    compiled: bool
    executed: bool
    passed_tests: int
    failed_tests: int
    execution_time_ms: float
    memory_mb: float
    stdout: str
    stderr: str
    failed_cases: List[TestCaseResult] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """
        Converts the report to a dictionary for JSON serialization.
        Useful for sending the report to the LLM or saving to logs.
        """
        return {
            "compiled": self.compiled,
            "executed": self.executed,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "memory_mb": round(self.memory_mb, 2),
            "stdout": self.stdout,
            "stderr": self.stderr,
            "failed_cases": [
                {
                    "test_id": tc.test_id,
                    "input_data": tc.input_data,
                    "expected_output": tc.expected_output,
                    "actual_output": tc.actual_output,
                    "passed": tc.passed,
                    "error_message": tc.error_message
                } for tc in self.failed_cases
            ]
        }