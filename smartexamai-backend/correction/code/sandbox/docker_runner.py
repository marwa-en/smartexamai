"""
Base Docker sandbox runner for executing student code securely.
"""
import docker
import os
import tempfile
import time
import logging
import shutil
from typing import Optional, Tuple, List
from docker.errors import DockerException

from configg import settings
from sandbox.execution_report import ExecutionReport
from models.exercise import Exercise, TestCase  # <--- ADDED MISSING IMPORTS

logger = logging.getLogger(__name__)


class DockerRunner:
    """
    Base class for executing code inside a secure Docker container.
    Handles container creation, resource limits, timeouts, and cleanup.
    Language-specific runners must inherit from this class and implement
    the `_prepare_workspace` and `_get_run_command` methods.
    """
    
    def __init__(self, image: str, language: str):
        """
        Initializes the Docker runner.
        
        Args:
            image: The Docker image to use (e.g., 'python:3.11-slim').
            language: The programming language (e.g., 'python', 'c').
        """
        self.image = image
        self.language = language
        try:
            self.client = docker.from_env()
            self.client.ping()  # Verify Docker daemon is running
        except DockerException as e:
            logger.error(f"Failed to connect to Docker daemon: {e}")
            raise RuntimeError("Docker daemon is not running or not accessible.") from e

    def run(
        self, 
        code: str, 
        exercise: Exercise,           # <--- MOVED BEFORE OPTIONAL ARGS
        test_cases: List[TestCase],   # <--- MOVED BEFORE OPTIONAL ARGS
        stdin_data: Optional[str] = None, 
        timeout: Optional[int] = None
    ) -> ExecutionReport:
        """
        Executes the code inside the Docker container.
        
        Args:
            code: The student's source code.
            exercise: The exercise details (type, language, etc.).
            test_cases: List of professor-defined test cases.
            stdin_data: Optional input to feed to the program's stdin.
            timeout: Execution timeout in seconds. Defaults to settings.sandbox_timeout_seconds.
            
        Returns:
            An ExecutionReport object containing the results.
        """
        timeout = timeout or settings.sandbox_timeout_seconds
        workspace = self._create_temp_workspace()
        
        try:
            # 1. Prepare workspace (write code, test harness, etc.)
            self._prepare_workspace(workspace, code, exercise, test_cases)
            
            # 2. Get the command to run inside the container
            command = self._get_run_command(workspace)
            
            # 3. Execute in Docker
            start_time = time.time()
            stdout, stderr, exit_code, timed_out, oom_killed = self._execute_in_docker(
                workspace, command, stdin_data, timeout
            )
            end_time = time.time()
            
            execution_time_ms = (end_time - start_time) * 1000
            
            # 4. Build the report
            return self._build_report(
                stdout=stdout, 
                stderr=stderr, 
                exit_code=exit_code,
                execution_time_ms=execution_time_ms, 
                timed_out=timed_out, 
                oom_killed=oom_killed, 
                test_cases=test_cases
            )
            
        finally:
            # 5. Cleanup workspace
            self._cleanup_workspace(workspace)

    def _create_temp_workspace(self) -> str:
        """Creates a temporary directory for the execution workspace."""
        return tempfile.mkdtemp(prefix="smartexam_")

    def _write_file(self, directory: str, filename: str, content: str) -> str:
        """Writes content to a file in the specified directory."""
        filepath = os.path.join(directory, filename)
        # IMPORTANT: newline='\n' forces LF line endings so Linux containers don't crash
        with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        return filepath

    def _execute_in_docker(
        self, 
        workspace: str, 
        command: str, 
        stdin_data: Optional[str], 
        timeout: int
    ) -> Tuple[str, str, int, bool, bool]:
        """
        Runs the Docker container with security limits and captures output.
        
        Returns:
            Tuple of (stdout, stderr, exit_code, timed_out, oom_killed)
        """
        stdout = ""
        stderr = ""
        exit_code = -1
        timed_out = False
        oom_killed = False
        
        container = None
        try:
            logger.info(f"Starting container with image {self.image} and command: {command}")
            
            # Create and run the container with strict security limits
            container = self.client.containers.run(
                image=self.image,
                command=command,
                working_dir="/workspace",
                volumes={workspace: {'bind': '/workspace', 'mode': 'rw'}},
                stdin_open=bool(stdin_data),
                stdout=True,
                stderr=True,
                detach=True,
                network_disabled=True,          # Security: Disable network access
                mem_limit=settings.sandbox_memory_limit,  # Security: Memory limit
                cpu_quota=int(settings.sandbox_cpu_limit * 100000),  # Security: CPU limit
                pids_limit=100,                 # Security: Prevent fork bombs
                read_only=True,                 # Security: Read-only root filesystem
                tmpfs={'/tmp': 'size=64m'},     # Allow writing to /tmp only
                security_opt=['no-new-privileges']  # Security: Prevent privilege escalation
            )
            
            # Wait for the container to finish with a timeout
            result = container.wait(timeout=timeout)
            exit_code = result.get('StatusCode', -1)
            
            # Check for OOM (Out of Memory)
            inspect_data = container.attrs
            if inspect_data.get('State', {}).get('OOMKilled', False):
                oom_killed = True
                
            # Get logs
            stdout = container.logs(stdout=True, stderr=False).decode('utf-8', errors='replace')
            stderr = container.logs(stdout=False, stderr=True).decode('utf-8', errors='replace')
            
        except Exception as e:
            err_str = str(e).lower()
            if "timeout" in err_str or "read timed out" in err_str:
                timed_out = True
                stderr = f"Execution timed out after {timeout} seconds."
            elif "oom" in err_str or "memory" in err_str:
                oom_killed = True
                stderr = "Execution exceeded memory limit."
            else:
                stderr = f"Docker execution error: {str(e)}"
                
            if container:
                try:
                    stdout = container.logs(stdout=True, stderr=False).decode('utf-8', errors='replace')
                    stderr_logs = container.logs(stdout=False, stderr=True).decode('utf-8', errors='replace')
                    if stderr_logs:
                        stderr += f"\nContainer Logs:\n{stderr_logs}"
                except Exception:
                    pass
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
                    
        return stdout, stderr, exit_code, timed_out, oom_killed

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
        Builds the ExecutionReport based on the raw execution results.
        Subclasses (like PythonRunner) override this to parse test case results.
        """
        compiled = True
        executed = True
        
        if timed_out:
            executed = False
            stderr = "Error: Execution timed out."
        elif oom_killed:
            executed = False
            stderr = "Error: Memory limit exceeded."
        elif exit_code != 0:
            executed = False
            
        return ExecutionReport(
            compiled=compiled,
            executed=executed,
            passed_tests=0,  # Base class doesn't parse tests; subclasses handle this.
            failed_tests=0,
            execution_time_ms=execution_time_ms,
            memory_mb=0.0,
            stdout=stdout,
            stderr=stderr
        )

    def _cleanup_workspace(self, workspace: str) -> None:
        """Removes the temporary workspace directory."""
        try:
            shutil.rmtree(workspace)
        except Exception as e:
            logger.warning(f"Failed to cleanup workspace {workspace}: {e}")

    # --- Abstract Methods for Subclasses ---
    
    def _prepare_workspace(self, workspace: str, code: str, exercise: Exercise, test_cases: List[TestCase]) -> None:
        """
        Prepares the workspace with the necessary files.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement _prepare_workspace")

    def _get_run_command(self, workspace: str) -> str:
        """
        Returns the shell command to execute inside the container.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement _get_run_command")