"""
PHP-specific Docker runner for SmartExamAI.
"""
import logging
from typing import List

from sandbox.docker_runner import DockerRunner
from sandbox.execution_report import ExecutionReport
from sandbox.harness_parser import parse_shell_harness_output
from models.exercise import Exercise, ExerciseType, TestCase
from configg import settings

logger = logging.getLogger(__name__)

class PhpRunner(DockerRunner):
    """Executes PHP code inside a secure Docker container using the PHP CLI."""

    def __init__(self):
        super().__init__(image=settings.docker_image_php, language="php")

    def _prepare_workspace(self, workspace: str, code: str, exercise: Exercise, test_cases: List[TestCase]) -> None:
        self._write_file(workspace, "student_code.php", code)
        run_cmd = "php student_code.php"
        
        if exercise.type == ExerciseType.FUNCTION:
            func_name = exercise.function_name or "sanitizeInput"
            wrapper_code = f"""<?php
include 'student_code.php';
$input = file_get_contents('php://stdin');
$func = "{func_name}";

if (!function_exists($func)) {{
    fwrite(STDERR, "Function $func not found in student code.");
    exit(1);
}}

$result = $func($input);
echo $result;
?>"""
            self._write_file(workspace, "wrapper.php", wrapper_code)
            run_cmd = "php wrapper.php"
            
        for i, tc in enumerate(test_cases):
            self._write_file(workspace, f"input_{i+1}.txt", tc.input_data)
            
        harness_code = self._generate_harness(len(test_cases), run_cmd)
        self._write_file(workspace, "harness.sh", harness_code)

    def _get_run_command(self, workspace: str) -> str:
        return "sh /workspace/harness.sh"

    def _generate_harness(self, num_tests: int, run_cmd: str) -> str:
    # Les fichiers temporaires vont dans /tmp (seul répertoire inscriptible)
     return f"""#!/bin/sh
# --- Execution Step ---
i=1
while [ $i -le {num_tests} ]; do
    echo "[TEST_START] $i"
    
    {run_cmd} < /workspace/input_$i.txt > /tmp/actual_$i.txt 2> /tmp/error_$i.txt
    EXIT_CODE=$?
    
    echo "[ACTUAL] $(cat /tmp/actual_$i.txt 2>/dev/null || echo '')"
    echo "[STDERR] $(cat /tmp/error_$i.txt 2>/dev/null || echo '')"
    echo "[EXIT_CODE] $EXIT_CODE"
    echo "[TEST_END]"
    
    # Nettoyage
    rm -f /tmp/actual_$i.txt /tmp/error_$i.txt
    
    i=$((i + 1))
done
"""

    def _build_report(self, stdout: str, stderr: str, exit_code: int, execution_time_ms: float, timed_out: bool, oom_killed: bool, test_cases: List[TestCase]) -> ExecutionReport:
        return parse_shell_harness_output(stdout, stderr, exit_code, execution_time_ms, timed_out, oom_killed, test_cases)