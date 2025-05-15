# TODO: support execution on remote hosts (ssh, firecracker VM)
import os
import subprocess
from tempfile import NamedTemporaryFile
from typing import Protocol, override

from polygon_env.solution.timemem_limit import LIMIT_256_MB, timemem_limit_run
from polygon_env.utils import format_list


class CompilationError(Exception):
    """Exception raised when runner fails to compile solution"""

    def __init__(self, stderr: str, exit_code: int):
        super().__init__(f'Compilation error, exit code {exit_code}\n{stderr}')
        self.exit_code: int = exit_code
        self.stderr: str = stderr


class RunsSolution(Protocol):
    """Protocol defining interface for solution runners."""

    def run(self, code: str, timeout_ms: int, max_memory_bytes: int) -> str:
        """
        Run soution code and get it's output

        Parameters
        ----------
        code
            The source code to be executed.
        timeout_ms
            Max amount of time solution is allowed to run (in milliseconds)
        max_memory_bytes
            Max amount of memory solution is allowed to use (in bytes)

        Returns
        -------
        str
            The output produced by running the code.
        """
        ...


class LocalInterpretedSolutionRunner(RunsSolution):
    """
    Solution runner for solutions which runs on interpreter.

    Runs solution on local machine.
    """

    def __init__(self, run_command: list[str]):
        self.run_command: list[str] = run_command

    @override
    def run(
        self, code: str, timeout_ms: int = 1000, max_memory_bytes: int = LIMIT_256_MB
    ) -> str:
        """
        Execute the provided source code

        Parameters
        ----------
        code
            The source code to run.
        timeout_ms
            Max amount of time solution is allowed to run (in milliseconds)
        max_memory_bytes
            Max amount of memory solution is allowed to use (in bytes)

        Returns
        -------
        str
            The output produced by executing the code.

        Examples
        --------
        >>> runner = LocalInterpretedSolutionRunner(
        ...     run_command=["python", "{input_file}"]
        ... )
        >>> output = runner.run("print('Hello, World!')")
        >>> print(output)
        Hello, World!
        """
        with NamedTemporaryFile(mode='r+') as source_file:
            source_file.write(code)
            source_file.flush()

            result = timemem_limit_run(
                format_list(
                    self.run_command,
                    input_file=source_file.name,
                ),
                timeout_ms=timeout_ms,
                max_memory_bytes=max_memory_bytes,
            )

            return result


class LocalCompiledSolutionRunner(RunsSolution):
    """Solution runner that compiles code before execution on local machine."""

    def __init__(
        self,
        compiler_command: list[str],
        source_code_ext: str,
        run_args: list[str] | None = None,
    ):
        self.compiler_command: list[str] = compiler_command
        self.run_args: list[str] = run_args or []
        self.executable_name: str | None = None
        self.source_code_ext: str = source_code_ext

    def _compile(self, code: str):
        with NamedTemporaryFile(mode='r+', suffix=self.source_code_ext) as source_file:
            source_file.write(code)
            source_file.flush()

            with NamedTemporaryFile(mode='wb', delete=False) as executable_file:
                result = subprocess.run(
                    format_list(
                        self.compiler_command,
                        input_file=source_file.name,
                        output_file=executable_file.name,
                    ),
                    capture_output=True,
                    text=True,
                )

                if result.returncode != 0:
                    raise CompilationError(result.stderr, result.returncode)

                os.chmod(executable_file.name, 0o700)
                self.executable_name = executable_file.name

    @override
    def run(
        self, code: str, timeout_ms: int = 1000, max_memory_bytes: int = LIMIT_256_MB
    ) -> str:
        """
        Compile and execute the provided source code.

        Parameters
        ----------
        code
            The source code to compile and run.
        timeout_ms
            Max amount of time solution is allowed to run (in milliseconds)
        max_memory_bytes
            Max amount of memory solution is allowed to use (in bytes)

        Returns
        -------
        str
            The output produced by executing the code.

        Examples
        --------
        >>> runner = CompiledSolutionRunner(
        ...     compiler_command=["gcc", "{input_file}", "-o", "{output_file}"],
        ...     run_args=[]
        ... )
        >>> output = runner.run('''
        ... #include <stdio.h>
        ... int main() {
        ...     printf("Hello, World!");
        ...     return 0;
        ... }
        ... ''')
        >>> print(output)
        Hello, World!
        """

        self._compile(code)

        assert self.executable_name
        result = timemem_limit_run(
            [self.executable_name] + self.run_args,
            timeout_ms=timeout_ms,
            max_memory_bytes=max_memory_bytes,
        )

        # cleanup
        os.remove(self.executable_name)
        self.executable_name = None

        return result
