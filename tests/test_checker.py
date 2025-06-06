import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from polygon_env.checker import CheckResultOrError, LocalChecker
from polygon_env.solution import (
    MemoryLimitExceed,
    RunsSolution,
    TimeLimitExceed,
    get_solution_runner,
)

from .test_problems.golden_results import GOLDEN_RESULTS


def collect_problem_dirs(test_problems_path: str) -> list[str]:
    """
    Collect all problem directories from the test problems path.

    Parameters
    ----------
    test_problems_path : str
        Path to the test problems directory

    Returns
    -------
    list[str]
        List of problem directory names
    """
    problems_path = Path(test_problems_path)
    if not problems_path.exists():
        return []

    problem_dirs = []
    for item in problems_path.iterdir():
        if item.is_dir() and item.name.isdigit():
            problem_dirs.append(item.name)

    return sorted(problem_dirs, key=int)


def collect_solutions(problem_dir_path: Path) -> list[str]:
    """
    Collect all solution files from a problem directory.

    Parameters
    ----------
    problem_dir_path : Path
        Path to the problem directory

    Returns
    -------
    list[str]
        List of solution filenames
    """
    solutions_path = problem_dir_path / 'solutions'
    if not solutions_path.exists():
        return []

    solutions = []
    for solution_file in solutions_path.iterdir():
        if solution_file.is_file():
            solutions.append(solution_file.name)

    return sorted(solutions)


def read_test_files(problem_dir_path: Path) -> tuple[list[str], list[str]]:
    """
    Read test input and output files from a problem directory.

    Parameters
    ----------
    problem_dir_path : Path
        Path to the problem directory

    Returns
    -------
    tuple[list[str], list[str]]
        Tuple of (test_inputs, test_outputs)
    """
    tests_path = problem_dir_path / 'tests'
    if not tests_path.exists():
        return [], []

    test_inputs = []
    test_outputs = []

    # Collect test files (assuming numbered pattern like 01, 02, etc.)
    test_files = sorted(
        [f for f in tests_path.iterdir() if f.is_file() and not f.name.endswith('.a')]
    )

    for test_file in test_files:
        # Read input file
        input_content = test_file.read_text()
        test_inputs.append(input_content)

        # Read corresponding output file (.a extension)
        output_file = tests_path / f'{test_file.name}.a'
        if output_file.exists():
            output_content = output_file.read_text()
            test_outputs.append(output_content)
        else:
            raise RuntimeError(f'Test output not specified for test input {test_file}')

    return test_inputs, test_outputs


def load_expected_results(problem_dir: str, solution_name: str) -> list[CheckResultOrError]:
    """
    Load expected test results for a given problem and solution.

    Parameters
    ----------
    problem_dir : str
        Problem directory name
    solution_name : str
        Solution filename

    Returns
    -------
    list[CheckResultOrError]
        Expected results for this solution
    """
    problem_index = int(problem_dir)

    # Check if problem index is within bounds
    if problem_index >= len(GOLDEN_RESULTS):
        raise ValueError(f'Problem directory {problem_dir} not found in golden results')

    problem_results = GOLDEN_RESULTS[problem_index]

    # Check if solution exists in golden results
    if solution_name not in problem_results:
        raise ValueError(
            f'Solution {solution_name} not found in golden results for problem {problem_dir}'
        )

    return problem_results[solution_name]


def create_test_parameters():
    """
    Create test parameters for parametrized testing.

    Returns
    -------
    list[tuple[str, str]]
        List of (problem_dir, solution_name) tuples
    """
    test_problems_path = 'tests/test_problems'
    problem_dirs = collect_problem_dirs(test_problems_path)

    test_params = []
    for problem_dir in problem_dirs:
        problem_path = Path(test_problems_path) / problem_dir
        solutions = collect_solutions(problem_path)

        for solution in solutions:
            test_params.append((problem_dir, solution))

    return test_params


# Generate test parameters
TEST_PARAMETERS = create_test_parameters()


@pytest.mark.parametrize('problem_dir,solution_name', TEST_PARAMETERS)
def test_solution_checker(problem_dir: str, solution_name: str):
    """
    Test solution checker for a specific problem and solution.

    Parameters
    ----------
    problem_dir : str
        Problem directory name (e.g., "0", "1", etc.)
    solution_name : str
        Solution filename (e.g., "main_1.cpp", "wrong_1.cpp", etc.)
    """
    # Setup paths
    test_problems_path = Path('tests/test_problems')
    problem_path = test_problems_path / problem_dir

    # Read required files
    checker_code_path = problem_path / 'check.cpp'
    solution_path = problem_path / 'solutions' / solution_name

    # Ensure files exist
    assert checker_code_path.exists(), f'Checker code not found: {checker_code_path}'
    assert solution_path.exists(), f'Solution not found: {solution_path}'

    # Read file contents
    checker_code = checker_code_path.read_text()
    solution_code = solution_path.read_text()

    # Read test inputs and outputs
    test_inputs, test_outputs = read_test_files(problem_path)

    # Skip if no test files found
    if not test_inputs or not test_outputs:
        pytest.skip(f'No test files found for problem {problem_dir}')

    # Load expected results
    expected_results = load_expected_results(problem_dir, solution_name)

    runner = get_solution_runner('cpp')

    # Create checker instance
    checker = LocalChecker(
        checker_code=checker_code, test_inputs=test_inputs, test_outputs=test_outputs
    )

    # Run the check
    actual_results = checker.check(
        runner=runner,
        solution=solution_code,
        max_memory_bytes=256 * 1024 * 1024,  # 256MB
        timeout_ms=2000,  # 2 seconds
    )

    # Compare results
    assert len(actual_results) == len(expected_results), (
        f'Result count mismatch for {problem_dir}/{solution_name}: '
        f'expected {len(expected_results)}, got {len(actual_results)}'
    )

    for i, (actual, expected) in enumerate(zip(actual_results, expected_results, strict=False)):
        assert actual == expected, (
            f'Result mismatch for {problem_dir}/{solution_name} test case {i}: '
            f'expected {expected}, got {actual}'
        )


def test_checker_compilation_error():
    """Test that checker compilation errors are properly handled."""
    invalid_checker_code = "invalid c++ code that won't compile"

    with pytest.raises(subprocess.CalledProcessError):
        LocalChecker(
            checker_code=invalid_checker_code,
            test_inputs=['test input'],
            test_outputs=['test output'],
        )


def test_empty_test_cases():
    """Test checker behavior with empty test cases."""
    checker_code = """
    #include "testlib.h"
    int main(int argc, char* argv[]) {
        registerTestlibCmd(argc, argv);
        quit(_ok, "");
    }
    """

    checker = LocalChecker(checker_code=checker_code, test_inputs=[], test_outputs=[])

    mock_runner = Mock(spec=RunsSolution)

    results = checker.check(
        runner=mock_runner,
        solution='// empty solution',
        max_memory_bytes=256 * 1024 * 1024,
        timeout_ms=2000,
    )

    assert results == []


def test_memory_limit_exceed():
    """Test handling of memory limit exceeded scenarios."""
    checker_code = """
    #include "testlib.h"
    int main(int argc, char* argv[]) {
        registerTestlibCmd(argc, argv);
        quit(_ok, "");
    }
    """

    checker = LocalChecker(checker_code=checker_code, test_inputs=['1'], test_outputs=['1'])

    mock_runner = Mock(spec=RunsSolution)

    mock_runner.run.side_effect = MemoryLimitExceed(peak=0, limit=0)

    results = checker.check(
        runner=mock_runner,
        solution='// memory-intensive solution',
        max_memory_bytes=1024,
        timeout_ms=2000,
    )

    expected = [{'outcome': 'memory-limit-exceed', 'limit': 1024}]
    assert results == expected


def test_time_limit_exceed():
    """Test handling of time limit exceeded scenarios."""
    checker_code = """
    #include "testlib.h"
    int main(int argc, char* argv[]) {
        registerTestlibCmd(argc, argv);
        quit(_ok, "");
    }
    """

    checker = LocalChecker(checker_code=checker_code, test_inputs=['1'], test_outputs=['1'])

    mock_runner = Mock(spec=RunsSolution)
    mock_runner.run.side_effect = TimeLimitExceed(timeout=0)

    results = checker.check(
        runner=mock_runner,
        solution='// time-intensive solution',
        max_memory_bytes=256 * 1024 * 1024,
        timeout_ms=1000,
        input_file_name='input.txt',
        output_file_name='output.txt',
    )

    expected = [{'outcome': 'time-limit-exceed', 'limit': 1000}]
    assert results == expected
