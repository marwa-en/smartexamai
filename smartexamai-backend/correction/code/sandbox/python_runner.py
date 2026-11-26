"""
Python-specific Docker runner for SmartExamAI.
Handles execution of Python programs and functions with automated test harnesses.
"""
import json
import re
import logging
from typing import List, Optional

from sandbox.docker_runner import DockerRunner
from sandbox.execution_report import ExecutionReport, TestCaseResult
from models.exercise import Exercise, ExerciseType, TestCase
from configg import settings

logger = logging.getLogger(__name__)


class PythonRunner(DockerRunner):
    """
    Executes Python code inside a secure Docker container.
    Generates a test harness to run professor-defined test cases.
    """

    def __init__(self):
        super().__init__(image=settings.docker_image_python, language="python")

    def _prepare_workspace(self, workspace: str, code: str, exercise: Exercise, test_cases: List[TestCase]) -> None:
        """Writes the student code and generates the test harness."""
        # 1. Write student code
        self._write_file(workspace, "student_code.py", code)
        
        # 2. Generate and write the test harness
        harness_code = self._generate_harness(exercise, test_cases)
        self._write_file(workspace, "harness.py", harness_code)

    def _get_run_command(self, workspace: str) -> str:
        """Returns the command to execute the harness."""
        return "python /workspace/harness.py"

    def _generate_harness(self, exercise: Exercise, test_cases: List[TestCase]) -> str:
        """
        Generates a Python script that runs all test cases and prints 
        structured output for easy parsing.
        """
        # Format test cases as a JSON string to embed in the harness
        tc_data = [
            {"id": i + 1, "input": tc.input_data, "expected": tc.expected_output}
            for i, tc in enumerate(test_cases)
        ]
        tc_json = json.dumps(tc_data)

        if exercise.type == ExerciseType.PROGRAM:
            return self._generate_program_harness(tc_json)
        elif exercise.type == ExerciseType.FUNCTION:
            # Default to 'solution' if no function name is provided in the exercise
            func_name = exercise.function_name or "solution"
            return self._generate_function_harness(tc_json, func_name)
        else:
            raise ValueError(f"Unsupported exercise type: {exercise.type}")

    def _generate_program_harness(self, tc_json: str) -> str:
        """Harness for Program type: feeds stdin and captures stdout."""
        return f"""
import sys
import subprocess
import json

test_cases = json.loads('''{tc_json}''')

for tc in test_cases:
    print(f"[TEST_START] {{tc['id']}}")
    print(f"[EXPECTED] {{repr(tc['expected'])}}")
    
    # Run student code as a subprocess to isolate stdout/stderr per test case
    result = subprocess.run(
        ["python", "/workspace/student_code.py"],
        input=tc['input'],
        capture_output=True,
        text=True,
        timeout=5  # 5-second timeout per individual test case
    )
    
    print(f"[ACTUAL] {{repr(result.stdout)}}")
    if result.returncode != 0:
        print(f"[ERROR] {{result.stderr.strip()}}")
        print(f"[RESULT] FAIL")
    elif result.stdout == tc['expected']:
        print(f"[RESULT] PASS")
    else:
        print(f"[RESULT] FAIL")
    print(f"[TEST_END]")
"""

    def _generate_function_harness(self, tc_json: str, func_name: str) -> str:
        """Harness for Function type: imports code, calls function, compares return value."""
        return f"""
import sys
import json
import traceback

# Load and execute student code in a clean namespace
namespace = {{}}
try:
    with open('/workspace/student_code.py', 'r') as f:
        exec(f.read(), namespace)
except Exception as e:
    print(f"[COMPILATION_ERROR] {{str(e)}}")
    sys.exit(1)

func_name = "{func_name}"
if func_name not in namespace:
    print(f"[COMPILATION_ERROR] Function '{{func_name}}' not found in student code.")
    sys.exit(1)

func = namespace[func_name]
test_cases = json.loads('''{tc_json}''')

for tc in test_cases:
    print(f"[TEST_START] {{tc['id']}}")
    print(f"[EXPECTED] {{repr(tc['expected'])}}")
    
    try:
        # Parse input as JSON list of arguments
        args = json.loads(tc['input'])
        if not isinstance(args, list):
            args = [args]
            
        actual = func(*args)
        print(f"[ACTUAL] {{repr(actual)}}")
        
        # Compare actual with expected
        try:
            expected_val = eval(tc['expected'])
            if actual == expected_val:
                print(f"[RESULT] PASS")
            else:
                print(f"[RESULT] FAIL")
        except Exception:
            # If eval fails, fallback to string representation comparison
            if repr(actual) == tc['expected']:
                print(f"[RESULT] PASS")
            else:
                print(f"[RESULT] FAIL")
                
    except Exception as e:
        print(f"[ACTUAL] ERROR")
        print(f"[ERROR] {{traceback.format_exc()}}")
        print(f"[RESULT] FAIL")
        
    print(f"[TEST_END]")
"""

    def _build_report(
        self, 
        stdout: str, 
        stderr: str, 
        exit_code: int, 
        execution_time_ms: float, 
        timed_out: bool, 
        oom_killed: bool,
        test_cases: List[TestCase]
    ) -> ExecutionReport:
        """
        Parses the structured output from the harness to build the ExecutionReport.
        """
        compiled = True
        executed = True
        
        # Check for syntax errors or missing functions caught by the harness
        if "[COMPILATION_ERROR]" in stdout:
            compiled = False
            executed = False
            stderr = stdout.split("[COMPILATION_ERROR]")[1].strip()
            
        if timed_out:
            executed = False
            stderr = "Error: Global execution timed out."
        elif oom_killed:
            executed = False
            stderr = "Error: Memory limit exceeded."
        elif exit_code != 0 and not compiled:
            executed = False

        passed_tests = 0
        failed_tests = 0
        failed_cases = []
        
        # Parse the [TEST_START] ... [TEST_END] blocks using Regex
        pattern = re.compile(
            r"\[TEST_START\] (\d+)\n"
            r"\[EXPECTED\] (.*?)\n"
            r"\[ACTUAL\] (.*?)\n"
            r"(?:\[ERROR\] (.*?)\n)?"
            r"\[RESULT\] (PASS|FAIL)\n"
            r"\[TEST_END\]",
            re.DOTALL
        )
        
        for match in pattern.finditer(stdout):
            test_id = int(match.group(1))
            expected = match.group(2).strip()
            actual = match.group(3).strip()
            error_msg = match.group(4).strip() if match.group(4) else None
            passed = match.group(5) == "PASS"
            
            # Find the original test case to get the input data
            tc_input = ""
            if 0 < test_id <= len(test_cases):
                tc_input = test_cases[test_id - 1].input_data
                
            if passed:
                passed_tests += 1
            else:
                failed_tests += 1
                failed_cases.append(TestCaseResult(
                    test_id=test_id,
                    input_data=tc_input,
                    expected_output=expected,
                    actual_output=actual,
                    passed=False,
                    error_message=error_msg
                ))

        return ExecutionReport(
            compiled=compiled,
            executed=executed,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            execution_time_ms=execution_time_ms,
            memory_mb=0.0,
            stdout=stdout,
            stderr=stderr,
            failed_cases=failed_cases
        )