import contextlib
import os
import subprocess
import xml.etree.ElementTree as ET
from tempfile import NamedTemporaryFile
from typing import Protocol, override

from polygon_env.solution.runners import RunsSolution
from polygon_env.solution.timemem_limit import MemoryLimitExceed, TimeLimitExceed
from polygon_env.testlib import testlib_dir

from .results import CheckResult, CheckResultOrError


class ChecksSolution(Protocol):
    """Protocol defining interface for solution checkers."""

    def check(
        self,
        runner: RunsSolution,
        solution: str,
        max_memory_bytes: int,
        timeout_ms: int,
    ) -> list[CheckResultOrError]:
        """
        Check solution against test cases using provided runner.

        Parameters
        ----------
        runner
            Solution runner that executes the solution
        solution
            Source code of the solution to check
        max_memory_bytes
            Maximum memory allowed for solution execution (bytes)
        timeout_ms
            Maximum execution time allowed (milliseconds)

        Returns
        -------
        list[CheckResultOrError]
            List of check results for each test case
        """
        ...


class LocalChecker(ChecksSolution):
    """
    Solution checker that compiles and runs checkers locally.

    Compiles checker code to binary and uses it to verify solution outputs
    against reference outputs.

    Parameters
    ----------
    checker_code
        Source code of the testlib checker program
    test_inputs
        List of input test cases as strings
    test_outputs
        List of the corresponding reference outputs as strings
    """

    def __init__(self, checker_code: str, test_inputs: list[str], test_outputs: list[str]):
        self.test_inputs: list[str] = test_inputs
        self.test_outputs: list[str] = test_outputs
        self.checker_executable: bytes = self._compile_checker(checker_code)

    def _compile_checker(self, checker_code: str) -> bytes:
        with NamedTemporaryFile(mode='w') as checker_source:
            checker_source.write(checker_code)
            checker_source.flush()

            compiler_command = ['c++', '-I', testlib_dir, '-o', '-', checker_source.name]
            result = subprocess.run(compiler_command)
            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode,
                    compiler_command,
                    output=result.stdout,
                    stderr=result.stderr,
                )

            return result.stdout

    @override
    def check(
        self, runner: RunsSolution, solution: str, max_memory_bytes: int, timeout_ms: int
    ) -> list[CheckResultOrError]:
        """Execute solution checking against all test cases.

        Parameters
        ----------
        runner
            Solution runner that executes the solution
        solution
            Source code of the solution to check
        max_memory_bytes
            Maximum memory allowed for solution execution (bytes)
        timeout_ms
            Maximum execution time allowed (milliseconds)

        Returns
        -------
        list[CheckResultOrError]
            List of check results for each test case, including:
            - Various verdicts (accepted/wrong-answer/etc)
            - Resource limit exceedances
            - Execution errors
        """
        check_results = []
        for test_input, test_output in zip(self.test_inputs, self.test_outputs, strict=True):
            try:
                solution_output = runner.run(
                    solution, max_memory_bytes=max_memory_bytes, timeout_ms=timeout_ms
                )
            except MemoryLimitExceed:
                check_results.append(
                    {'outcome': 'memory-limit-exceed', 'limit': max_memory_bytes}
                )
                continue
            except TimeLimitExceed:
                check_results.append(
                    {
                        'outcome': 'time-limit-exceed',
                        'limit': timeout_ms,
                    }
                )
                continue

            check_results.append(
                self._run_check(
                    test_input=test_input,
                    solution_output=solution_output,
                    test_output=test_output,
                )
            )

        return check_results

    def _run_check(
        self, test_input: str, solution_output: str, test_output: str
    ) -> CheckResult:
        with (
            self._temp_checker_executable() as checker_executable_filename,
            self._temp_test_files(
                test_input=test_input,
                test_output=test_output,
            ) as (test_input_filename, test_output_filename),
            self._temp_solution_output_file(solution_output) as output_filename,
            self._temp_report_file() as report_filename,
        ):
            # <input-file> <output-file> <answer-file> [<report-file> [<-appes>]]
            check_command = [
                checker_executable_filename,
                test_input_filename,
                output_filename,
                test_output_filename,
                report_filename,
                '-appes',
            ]
            result = subprocess.run(check_command)
            # some error happened inside the checker itself
            # exit code can differ based on testlib configuration
            # should be 3 by deafult
            if result.returncode == 3:
                raise subprocess.CalledProcessError(
                    result.returncode,
                    check_command,
                    output=result.stdout,
                    stderr=result.stderr,
                )

            return self._parse_report_xml(report_filename)

    def _parse_report_xml(self, report_filename: str) -> CheckResult:
        tree = ET.parse(report_filename)
        root = tree.getroot()

        outcome = root.attrib['outcome']
        text_content = root.text.strip() if root.text else ''

        if outcome == 'accepted':
            return {'outcome': 'accepted', 'message': text_content}
        elif outcome == 'wrong-answer':
            return {'outcome': 'wrong-answer', 'message': text_content}
        elif outcome == 'presentation-error':
            return {'outcome': 'presentation-error', 'message': text_content}
        elif outcome == 'points':
            points = float(root.attrib['points'])
            return {'outcome': 'points', 'points': points, 'message': text_content}
        elif outcome == 'partially-correct':
            pctype = int(root.attrib['pctype'])
            return {'outcome': 'partially-correct', 'type': pctype}
        else:
            raise ValueError(f'Unknown outcome in report: {outcome}')

    # store tests on disk only during check execution,
    # so LLM cannot peek into test results during solution submission
    @contextlib.contextmanager
    def _temp_test_files(self, test_input: str, test_output: str):
        with (
            NamedTemporaryFile(mode='w') as test_input_file,
            NamedTemporaryFile(mode='w') as test_output_file,
        ):
            test_input_file.write(test_input)
            test_input_file.flush()

            test_output_file.write(test_output)
            test_output_file.flush()

            yield test_input_file.name, test_output_file.name

    # store checker binary only during check execution for same reason as above
    # theoretically LLM can reverse-engineer checker binary and gain some unfair advantage
    @contextlib.contextmanager
    def _temp_checker_executable(self):
        with NamedTemporaryFile(mode='wb') as checker_executable_file:
            checker_executable_file.write(self.checker_executable)
            checker_executable_file.flush()
            os.chmod(checker_executable_file.name, 0o700)
            yield checker_executable_file.name

    @contextlib.contextmanager
    def _temp_report_file(self):
        with NamedTemporaryFile() as report_file:
            yield report_file.name

    @contextlib.contextmanager
    def _temp_solution_output_file(self, solution_output: str):
        with NamedTemporaryFile('w') as solution_output_file:
            solution_output_file.write(solution_output)
            solution_output_file.flush()
            yield solution_output_file.name
