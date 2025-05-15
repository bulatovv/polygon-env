from inspect import cleandoc

import pytest

from polygon_env.solution import (
    get_solution_runner,
    register_solution_runner,
)
from polygon_env.solution.runners import (
    CompilationError,
    LocalCompiledSolutionRunner,
    LocalInterpretedSolutionRunner,
)
from polygon_env.solution.timemem_limit import (
    MemoryLimitExceed,
    RunnerRuntimeError,
    TimeLimitExceed,
)


def test_init_with_default_run_args():
    """Test initialization with default run arguments."""
    compile_cmd = ['cc', '-o', '{output_file}', '{input_file}']
    runner = LocalCompiledSolutionRunner(compile_cmd, source_code_ext='.c')

    assert runner.compiler_command == compile_cmd
    assert runner.run_args == []
    assert runner.executable_name is None


def test_init_with_custom_run_args():
    """Test initialization with custom run arguments."""
    compile_cmd = ['cc', '-o', '{output_file}', '{input_file}']
    run_args = ['--verbose', '--input', 'test.txt']
    runner = LocalCompiledSolutionRunner(compile_cmd, source_code_ext='.c', run_args=run_args)

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

    runner = LocalCompiledSolutionRunner(
        ['cc', '-o', '{output_file}', '{input_file}'], source_code_ext='.c'
    )
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

    runner = LocalCompiledSolutionRunner(
        ['cc', '-o', '{output_file}', '{input_file}', '-lm'], source_code_ext='.c'
    )
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
        ['cc', '-o', '{output_file}', '{input_file}'],
        source_code_ext='.c',
        run_args=['arg1', 'arg2', 'arg3'],
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

    with pytest.raises(RunnerRuntimeError) as exc_info:
        runner.run(python_code)

    assert 'NameError' in exc_info.value.stderr
    assert 'undefined_variable' in exc_info.value.stderr
    assert exc_info.value.exit_code != 0


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

    with pytest.raises(RunnerRuntimeError) as exc_info:
        runner.run(python_code)

    assert 'SyntaxError' in exc_info.value.stderr
    assert exc_info.value.exit_code != 0


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
        lang='java',
        cmd=['javac', '{input_file}'],
        compiled=True,
        aliases=['java-lang'],
        source_code_ext='.java',
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
        source_code_ext='.c',
    )

    # Verify both languages
    c_runner = get_solution_runner('c')
    ansi_runner = get_solution_runner('ansi-c')

    assert c_runner is ansi_runner
    assert isinstance(c_runner, LocalCompiledSolutionRunner)
    assert c_runner.compiler_command == ['gcc', '{input_file}', '-o', '{output_file}']


def test_compilation_error():
    """Compiled runner fails with compilation error on compilation error"""
    runner = LocalCompiledSolutionRunner(
        ['cc', '-o', '{output_file}', '{input_file}'], source_code_ext='.c'
    )

    invalid_code = """
    #include <stdio.h>
    int main() {
        undeclared_function();  // This will cause compilation error
        return 0;
    }
    """

    with pytest.raises(CompilationError) as exc_info:
        runner.run(invalid_code)

    assert exc_info.value.exit_code != 0


def test_time_limit_exceeded_compiled():
    """Compiled solution fails when time limit exceeded"""
    runner = LocalCompiledSolutionRunner(
        ['cc', '-o', '{output_file}', '{input_file}'], source_code_ext='.c'
    )

    # C code with infinite loop
    infinite_loop_code = """
    #include <stdio.h>
    int main() {
        while(1) {
            // Infinite loop
        }
        return 0;
    }
    """

    timeout_ms = 200
    with pytest.raises(TimeLimitExceed) as exc_info:
        runner.run(infinite_loop_code, timeout_ms=timeout_ms)

    # Should timeout
    assert exc_info.value.timeout == timeout_ms


def test_memory_limit_exceeded_compiled():
    """Compiled solution fails when memory limit exceeded"""
    runner = LocalCompiledSolutionRunner(
        ['cc', '-o', '{output_file}', '{input_file}'], source_code_ext='.c'
    )

    # C code that tries to allocate larger than limit amounts of memory
    memory_hungry_code = """
    #include <stdio.h>
    #include <stdlib.h>
    #include <string.h>
    int main() {
        // Try to allocate 25MB of memory
        size_t alloc_size = 25 * 1024 * 1024; 
        char *ptr = malloc(alloc_size);
        if (ptr != NULL) {
            // malloc() reserves virtual memory but
            // doesn't commit physical pages until written to
            memset(ptr, 0, alloc_size);
            printf("Memory allocated successfully\\n");
            free(ptr);
        }
        return 0;
    }
    """

    max_memory_bytes = 1024 * 1024
    with pytest.raises(MemoryLimitExceed) as exc_info:
        runner.run(memory_hungry_code, max_memory_bytes=max_memory_bytes)

    # Should fail due to memory limit
    assert exc_info.value.limit == max_memory_bytes


def test_successful_run_with_time_limit_compiled():
    """Compiled solution runs successfully when time limit set but not exceeded"""
    runner = LocalCompiledSolutionRunner(
        ['cc', '-o', '{output_file}', '{input_file}'], source_code_ext='.c'
    )

    fast_code = """
    #include <stdio.h>
    int main() {
        printf("Hello, World!\\n");
        return 0;
    }
    """

    result = runner.run(fast_code, timeout_ms=5000)  # Generous timeout
    assert result == 'Hello, World!\n'


def test_successful_run_with_memory_limit_compiled():
    """Compiled solution runs successfully when memory limit set but not exceeded"""
    runner = LocalCompiledSolutionRunner(
        ['cc', '-o', '{output_file}', '{input_file}'], source_code_ext='.c'
    )

    efficient_code = """
    #include <stdio.h>
    int main() {
        int x = 42;
        printf("Value: %d\\n", x);
        return 0;
    }
    """

    result = runner.run(efficient_code, max_memory_bytes=64 * 1024 * 1024)
    assert result == 'Value: 42\n'


def test_time_limit_exceeded_interpreted():
    """Interpreted solution fails when time limit exceeded"""
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])

    # Python code with infinite loop
    infinite_loop_code = cleandoc("""
        import time
        while True:
            time.sleep(0.001)  # Small sleep to prevent CPU spinning
    """)

    timeout_ms = 100

    with pytest.raises(TimeLimitExceed) as exc_info:
        runner.run(infinite_loop_code, timeout_ms=timeout_ms)

    assert exc_info.value.timeout == timeout_ms


def test_memory_limit_exceeded_interpreted():
    """Interpreted solution fails when memory limit exceeded"""
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])

    # Python code that tries to consume lots of memory
    memory_hungry_code = cleandoc("""
        # Try to allocate a large list
        big_list = [0] * (100 * 1024 * 1024)
        print("Memory allocated")
    """)

    max_memory_bytes = 10 * 1024 * 1024
    with pytest.raises(MemoryLimitExceed) as exc_info:
        runner.run(memory_hungry_code, max_memory_bytes=max_memory_bytes)
    assert exc_info.value.limit == max_memory_bytes


def test_successful_run_with_time_limit_interpreted():
    """Interpreted solution runs successfully when time limit set but not exceeded"""
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])

    fast_code = cleandoc("""
        print("Hello from Python!")
    """)

    result = runner.run(fast_code, timeout_ms=5000)
    assert result == 'Hello from Python!\n'


def test_successful_run_with_memory_limit_interpreted():
    """Interpreted solution runs successfully when memory limit set but not exceeded"""
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])

    efficient_code = cleandoc("""
        x = 42
        y = "hello"
        print(f"x={x}, y={y}")
    """)

    result = runner.run(efficient_code, max_memory_bytes=64 * 1024 * 1024)  # 64MB limit
    assert result == 'x=42, y=hello\n'


def test_compilation_error_with_stderr_info():
    """Test that compilation errors include useful error information"""
    runner = LocalCompiledSolutionRunner(
        ['cc', '-o', '{output_file}', '{input_file}'], source_code_ext='.c'
    )

    # C code with multiple errors
    multi_error_code = """
    #include <stdio.h>
    int main() {
        undefined_function();
        int x = "string";  // Type mismatch
        return 0;
    }
    """

    with pytest.raises(CompilationError) as exc_info:
        runner.run(multi_error_code)
    assert exc_info.value.exit_code != 0


def test_runtime_error_handling_interpreted():
    """Test that runtime errors are properly handled for interpreted code"""
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])

    # Python code that will cause runtime error
    runtime_error_code = cleandoc("""
        print("Starting...")
        x = 1 / 0  # Division by zero
        print("This won't print")
    """)

    with pytest.raises(RunnerRuntimeError) as exc_info:
        runner.run(runtime_error_code)

    assert exc_info.value.exit_code != 0
    assert 'ZeroDivisionError' in exc_info.value.stderr


def test_successful_execution_with_both_limits():
    """Test successful execution with both time and memory limits set"""
    runner = LocalCompiledSolutionRunner(
        ['cc', '-o', '{output_file}', '{input_file}'], source_code_ext='.c'
    )

    # C code that runs quickly and uses minimal memory
    simple_code = cleandoc("""
        #include <stdio.h>
        int main() {
            for(int i = 0; i < 10; i++) {
                printf("%d ", i);
            }
            printf("\\n");
            return 0;
        }
    """)

    result = runner.run(
        simple_code,
        timeout_ms=2000,  # 2 seconds
        max_memory_bytes=32 * 1024 * 1024,  # 32MB
    )
    assert result == '0 1 2 3 4 5 6 7 8 9 \n'


def test_interpreted_with_both_limits():
    """Test interpreted runner with both time and memory limits"""
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])

    # Python code that completes quickly with minimal memory
    simple_code = cleandoc("""
        import math
        result = math.sqrt(16)
        print(f"Result: {result}")
    """)

    result = runner.run(
        simple_code,
        timeout_ms=3000,  # 3 seconds
        max_memory_bytes=32 * 1024 * 1024,  # 32MB
    )
    assert result == 'Result: 4.0\n'
