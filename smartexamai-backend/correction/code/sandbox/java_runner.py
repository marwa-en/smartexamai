"""
Java-specific Docker runner for SmartExamAI.
"""
import re
import logging
from typing import List

from sandbox.docker_runner import DockerRunner
from sandbox.execution_report import ExecutionReport
from sandbox.harness_parser import parse_shell_harness_output
from models.exercise import Exercise, ExerciseType, TestCase
from configg import settings

logger = logging.getLogger(__name__)


class JavaRunner(DockerRunner):
    """Executes Java code inside a secure Docker container using the JDK."""

    def __init__(self):
        super().__init__(image=settings.docker_image_java, language="java")

    def _prepare_workspace(self, workspace: str, code: str, exercise: Exercise, test_cases: List[TestCase]) -> None:
        if exercise.type != ExerciseType.PROGRAM:
            raise NotImplementedError("JavaRunner currently only supports ExerciseType.PROGRAM (stdin/stdout).")

        # 1. Extract the public class name to ensure correct compilation
        match = re.search(r'public\s+class\s+(\w+)', code)
        class_name = match.group(1) if match else "Main"
        
        self._write_file(workspace, f"{class_name}.java", code)
        
        # 2. Write test inputs
        for i, tc in enumerate(test_cases):
            self._write_file(workspace, f"input_{i+1}.txt", tc.input_data)
            
        # 3. Generate harness
        harness_code = self._generate_harness(len(test_cases), class_name)
        self._write_file(workspace, "harness.sh", harness_code)

    def _get_run_command(self, workspace: str) -> str:
        return "sh /workspace/harness.sh"

    
    def _generate_harness(self, num_tests: int, class_name: str) -> str:
        return f"""#!/bin/sh
# --- Compilation Step ---
javac {class_name}.java 2> compile_error.txt
if [ $? -ne 0 ]; then
    echo "[COMPILATION_ERROR] $(cat compile_error.txt)"
    exit 1
fi

# --- Execution Step ---
i=1
while [ $i -le {num_tests} ]; do
    echo "[TEST_START] $i"
    
    java {class_name} < input_$i.txt > actual_$i.txt 2> error_$i.txt
    EXIT_CODE=$?
    
    echo "[ACTUAL] $(cat actual_$i.txt)"
    echo "[STDERR] $(cat error_$i.txt)"
    echo "[EXIT_CODE] $EXIT_CODE"
    echo "[TEST_END]"
    
    i=$((i + 1))
done
"""

    def _build_report(self, stdout: str, stderr: str, exit_code: int, execution_time_ms: float, timed_out: bool, oom_killed: bool, test_cases: List[TestCase]) -> ExecutionReport:
        return parse_shell_harness_output(stdout, stderr, exit_code, execution_time_ms, timed_out, oom_killed, test_cases)