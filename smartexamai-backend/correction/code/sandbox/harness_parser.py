"""
Shared parsing logic for shell-based test harnesses (C, Java, PHP).
"""
import re
from typing import List

from models.exercise import TestCase
from sandbox.execution_report import ExecutionReport, TestCaseResult


def parse_shell_harness_output(
    stdout: str, 
    stderr: str, 
    exit_code: int, 
    execution_time_ms: float, 
    timed_out: bool, 
    oom_killed: bool, 
    test_cases: List[TestCase]
) -> ExecutionReport:
    """
    Parses the standard shell harness output format used by C, Java, and PHP runners.
    """
    compiled = True
    executed = True
    
    # Check for compilation errors flagged by the harness
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
    
    # Regex to parse the structured output blocks
    pattern = re.compile(
        r"\[TEST_START\] (\d+)\n"
        r"\[ACTUAL\] (.*?)\n"
        r"\[STDERR\] (.*?)\n"
        r"\[EXIT_CODE\] (\d+)\n"
        r"\[TEST_END\]",
        re.DOTALL
    )
    
    for match in pattern.finditer(stdout):
        test_id = int(match.group(1))
        actual = match.group(2).strip()
        tc_stderr = match.group(3).strip()
        tc_exit_code = int(match.group(4))
        
        # Retrieve expected output and input from the test_cases list
        expected = ""
        tc_input = ""
        if 0 < test_id <= len(test_cases):
            expected = test_cases[test_id - 1].expected_output
            tc_input = test_cases[test_id - 1].input_data
            
        # Determine if the test passed (Exit code 0 and output matches)
        # We strip trailing newlines to avoid false negatives from print statements
        passed = (tc_exit_code == 0) and (actual.strip() == expected.strip())
        
        if passed:
            passed_tests += 1
        else:
            failed_tests += 1
            error_msg = tc_stderr if tc_stderr else None
            if tc_exit_code != 0:
                error_msg = f"Runtime error (Exit code: {tc_exit_code}). {tc_stderr}"
            elif actual.strip() != expected.strip():
                error_msg = "Wrong answer"
                
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