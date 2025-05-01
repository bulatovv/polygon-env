import subprocess
from inspect import cleandoc

import pytest

from polygon_env.solution import (
    get_solution_runner,
    register_solution_runner,
)
from polygon_env.solution.runners import (
    LocalCompiledSolutionRunner,
    LocalInterpretedSolutionRunner,
)


def test_init_with_default_run_args():
    """Test initialization with default run arguments."""
    compile_cmd = ['cc', '-o', '{output_file}', '{input_file}']
    runner = LocalCompiledSolutionRunner(compile_cmd)

    assert runner.compiler_command == compile_cmd
    assert runner.run_args == []
    assert runner.executable_name is None


def test_init_with_custom_run_args():
    """Test initialization with custom run arguments."""
    compile_cmd = ['cc', '-o', '{output_file}', '{input_file}']
    run_args = ['--verbose', '--input', 'test.txt']
    runner = LocalCompiledSolutionRunner(compile_cmd, run_args)

    assert runner.compiler_command == compile_cmd
    assert runner.run_args == run_args
    assert runner.executable_name is None


def test_integration_with_real_cc_compiler():
    """Integration test with actual cc compiler (must be available)."""

    c_code = """
    #include <stdio.h>
    int main() {
        printf("Hello from C!\\n");
        return 0;
    }
    """

    runner = LocalCompiledSolutionRunner(['cc', '-o', '{output_file}', '{input_file}'])
    result = runner.run(c_code)

    assert result == 'Hello from C!\n'


def test_integration_with_compiler_args():
    """Integration test with compiler arguments."""

    # C program that uses math library
    c_code = """
    #include <stdio.h>
    #include <math.h>
    int main() {
        printf("sqrt(16) = %.1f\\n", sqrt(16.0));
        return 0;
    }
    """

    runner = LocalCompiledSolutionRunner(['cc', '-o', '{output_file}', '{input_file}', '-lm'])
    result = runner.run(c_code)

    assert result == 'sqrt(16) = 4.0\n'


def test_integration_with_runtime_args():
    """Integration test with runtime arguments."""
    # C program that uses command line arguments
    c_code = """
    #include <stdio.h>
    int main(int argc, char *argv[]) {
        printf("argc = %d\\n", argc);
        for (int i = 0; i < argc; i++) {
            printf("argv[%d] = %s\\n", i, argv[i]);
        }
        return 0;
    }
    """

    runner = LocalCompiledSolutionRunner(
        ['cc', '-o', '{output_file}', '{input_file}'], ['arg1', 'arg2', 'arg3']
    )
    result = runner.run(c_code)

    lines = result.strip().split('\n')
    assert lines[0] == 'argc = 4'  # program name + 3 args
    assert 'argv[0] = ' in lines[1]
    assert 'argv[1] = arg1' in lines[2]
    assert 'argv[2] = arg2' in lines[3]
    assert 'argv[3] = arg3' in lines[4]


def test_interpreted_runner_init():
    """Test initialization of interpreted solution runner."""
    run_cmd = ['python', '{input_file}']
    runner = LocalInterpretedSolutionRunner(run_cmd)
    assert runner.run_command == run_cmd


def test_interpreted_runner_simple_output():
    """Test basic Python code execution."""
    python_code = "print('Hello World!')"
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])
    result = runner.run(python_code)
    assert result == 'Hello World!\n'


def test_interpreted_runner_multiline_output():
    """Test multi-line output handling."""
    python_code = cleandoc("""
    for i in range(3):
        print(f"Line {i}")
    """)
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])
    result = runner.run(python_code)
    assert result == 'Line 0\nLine 1\nLine 2\n'


def test_interpreted_runner_with_arguments():
    """Test command-line argument handling."""
    python_code = cleandoc("""
    import sys
    print("Arguments:", ' '.join(sys.argv[1:]))
    """)
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}', '--option', 'value'])
    result = runner.run(python_code)
    assert result == 'Arguments: --option value\n'


def test_interpreted_runner_error_handling():
    """Test error propagation for invalid code."""
    python_code = 'print(undefined_variable)'
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])

    with pytest.raises(Exception) as exc_info:
        runner.run(python_code)

    # Verify we got a CalledProcessError
    assert exc_info.type is subprocess.CalledProcessError
    # Verify error contains relevant information
    assert 'NameError' in exc_info.value.stderr
    assert 'undefined_variable' in exc_info.value.stderr
    assert exc_info.value.returncode != 0


def test_interpreted_runner_with_dependencies():
    """Test execution with external dependencies."""
    python_code = cleandoc("""
    import math
    print(f"Pi: {math.pi:.2f}")
    """)
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])
    result = runner.run(python_code)
    assert 'Pi: 3.14' in result


def test_interpreted_runner_syntax_error():
    """Test handling of syntax errors."""
    python_code = "print('Hello world'"
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])

    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        runner.run(python_code)

    assert 'SyntaxError' in exc_info.value.stderr
    assert exc_info.value.returncode != 0


def test_get_default_runners():
    """Test retrieval of default registered runners."""
    # Test compiled runner
    cpp_runner = get_solution_runner('cpp')
    assert isinstance(cpp_runner, LocalCompiledSolutionRunner)
    assert cpp_runner.compiler_command == ['c++', '-o', '{output_file}', '{input_file}']

    # Test interpreted runner
    py_runner = get_solution_runner('python')
    assert isinstance(py_runner, LocalInterpretedSolutionRunner)
    assert py_runner.run_command == ['python', '{input_file}']

    # Test aliases
    assert get_solution_runner('c++') is cpp_runner
    assert get_solution_runner('py') is py_runner


def test_register_and_retrieve_new_runner():
    """Test registering and retrieving a new runner."""
    # Register new JavaScript runner
    register_solution_runner(lang='javascript', cmd=['node', '{input_file}'], aliases=['js'])

    # Retrieve and verify
    js_runner = get_solution_runner('javascript')
    assert isinstance(js_runner, LocalInterpretedSolutionRunner)
    assert js_runner.run_command == ['node', '{input_file}']

    # Verify alias
    assert get_solution_runner('js') is js_runner


def test_register_compiled_runner():
    """Test registering a compiled runner."""
    # Register Java runner
    register_solution_runner(
        lang='java', cmd=['javac', '{input_file}'], compiled=True, aliases=['java-lang']
    )

    # Retrieve and verify
    java_runner = get_solution_runner('java')
    assert isinstance(java_runner, LocalCompiledSolutionRunner)
    assert java_runner.compiler_command == ['javac', '{input_file}']

    # Verify alias
    assert get_solution_runner('java-lang') is java_runner


def test_get_unregistered_language():
    """Test error handling for unregistered languages."""
    with pytest.raises(ValueError):
        get_solution_runner('this-lang-will-never-be-registered-in-this-lib')


def test_register_multiple_languages():
    """Test registering multiple languages with shared runner."""
    # Register for C and ANSI-C
    register_solution_runner(
        lang='c',
        cmd=['gcc', '{input_file}', '-o', '{output_file}'],
        compiled=True,
        aliases=['ansi-c'],
    )

    # Verify both languages
    c_runner = get_solution_runner('c')
    ansi_runner = get_solution_runner('ansi-c')

    assert c_runner is ansi_runner
    assert isinstance(c_runner, LocalCompiledSolutionRunner)
    assert c_runner.compiler_command == ['gcc', '{input_file}', '-o', '{output_file}']
