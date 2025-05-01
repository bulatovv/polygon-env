# TODO: support execution on remote hosts (ssh, firecracker VM)
import os
import subprocess
from tempfile import NamedTemporaryFile
from typing import Protocol, final, override

from polygon_env.utils import format_list


class SolutionRunner(Protocol):
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


@final
class CompiledSolutionRunner(SolutionRunner):
    """
    Solution runner that compiles code before execution.

    Attributes
    ----------
    compile_command
        Command used to compile the source code.
        File names should be specified using placeholders: {input_file} for the input source file
        and {output_file} for the compiled executable output.
    execute_args
        Arguments to pass to the compiled executable.
    executable_name : str
        Path to the compiled executable.
    """

    def __init__(self, compile_command: list[str], execute_args: list[str] | None = None):
        self.compile_command = compile_command
        self.execute_args = execute_args or []
        self.executable_name = None

    def _compile(self, code: str):
        with NamedTemporaryFile(mode='r+', suffix='.c') as source_file:
            source_file.write(code)
            source_file.flush()

            with NamedTemporaryFile(mode='wb', delete=False) as executable_file:  # noqa: SIM115
                result = subprocess.run(
                    format_list(
                        self.compile_command,
                        input_file=source_file.name,
                        output_file=executable_file.name,
                    ),
                    capture_output=True,
                    text=True,
                )

                if result.returncode != 0:
                    raise subprocess.CalledProcessError(
                        result.returncode,
                        self.compile_command,
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

        Raises
        ------
        subprocess.CalledProcessError
            If compilation fails.
        AssertionError
            If executable name is not set after compilation.

        Examples
        --------
        >>> runner = CompiledSolutionRunner(
        ...     compile_command=["gcc", "{input_file}", "-o", "{output_file}"],
        ...     execute_args=[]
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
        binary_output = subprocess.check_output([self.executable_name] + self.execute_args)
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
