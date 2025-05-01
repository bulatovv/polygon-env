# TODO: support execution on remote hosts (ssh, firecracker VM)
import os
import subprocess
from tempfile import NamedTemporaryFile
from typing import Protocol, override

from polygon_env.utils import format_list


class RunsSolution(Protocol):
    """Protocol defining interface for solution runners."""

    def run(self, code: str) -> str:
        """
        Run soution code and get it's output

        Parameters
        ----------
        code
            The source code to be executed.

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
    def run(self, code: str) -> str:
        """
        Execute the provided source code

        Parameters
        ----------
        code
            The source code to run.

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

            result = subprocess.run(
                format_list(
                    self.run_command,
                    input_file=source_file.name,
                ),
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode,
                    self.run_command,
                    output=result.stdout,
                    stderr=result.stderr,
                )

            return result.stdout


class LocalCompiledSolutionRunner(RunsSolution):
    """Solution runner that compiles code before execution on local machine."""

    def __init__(self, compiler_command: list[str], run_args: list[str] | None = None):
        self.compiler_command: list[str] = compiler_command
        self.run_args: list[str] = run_args or []
        self.executable_name: str | None = None

    def _compile(self, code: str):
        with NamedTemporaryFile(mode='r+', suffix='.c') as source_file:
            source_file.write(code)
            source_file.flush()

            with NamedTemporaryFile(mode='wb', delete=False) as executable_file:  # noqa: SIM115
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
                    raise subprocess.CalledProcessError(
                        result.returncode,
                        self.compiler_command,
                        output=result.stdout,
                        stderr=result.stderr,
                    )

                os.chmod(executable_file.name, 0o700)
                self.executable_name = executable_file.name

    @override
    def run(self, code: str) -> str:
        """
        Compile and execute the provided source code.

        Parameters
        ----------
        code
            The source code to compile and run.

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

        if self.executable_name is None:
            self._compile(code)

        assert self.executable_name
        binary_output = subprocess.check_output([self.executable_name] + self.run_args)
        return binary_output.decode()

    def __del__(self):
        """
        Clean up by removing the compiled executable file.

        Notes
        -----
        This is called when the object is garbage collected.
        """
        if self.executable_name:
            os.remove(self.executable_name)
