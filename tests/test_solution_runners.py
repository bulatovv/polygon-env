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
        char input[100];
        fgets(input, sizeof(input), stdin);
        printf("Hello from C! Input was: %s", input);
        return 0;
    }
    """

    runner = LocalCompiledSolutionRunner(
        ['cc', '-o', '{output_file}', '{input_file}'], source_code_ext='.c'
    )
    result = runner.run(c_code, solution_input='test input\n')

    assert 'Hello from C! Input was: test input' in result


def test_integration_with_compiler_args():
    """Integration test with compiler arguments."""

    # C program that uses math library and reads input
    c_code = """
    #include <stdio.h>
    #include <math.h>
    int main() {
        double num;
        scanf("%lf", &num);
        printf("sqrt(%.1f) = %.1f\\n", num, sqrt(num));
        return 0;
    }
    """

    runner = LocalCompiledSolutionRunner(
        ['cc', '-o', '{output_file}', '{input_file}', '-lm'], source_code_ext='.c'
    )
    result = runner.run(c_code, solution_input='16.0\n')

    assert result == 'sqrt(16.0) = 4.0\n'


def test_integration_with_runtime_args():
    """Integration test with runtime arguments."""
    # C program that uses command line arguments and reads input
    c_code = """
    #include <stdio.h>
    int main(int argc, char *argv[]) {
        char input[100];
        fgets(input, sizeof(input), stdin);
        printf("argc = %d\\n", argc);
        printf("Input: %s", input);
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
    result = runner.run(c_code, solution_input='test input\n')

    lines = result.strip().split('\n')
    assert lines[0] == 'argc = 4'  # program name + 3 args
    assert 'Input: test input' in lines[1]
    assert 'argv[0] = ' in lines[2]
    assert 'argv[1] = arg1' in lines[3]
    assert 'argv[2] = arg2' in lines[4]
    assert 'argv[3] = arg3' in lines[5]


def test_interpreted_runner_init():
    """Test initialization of interpreted solution runner."""
    run_cmd = ['python', '{input_file}']
    runner = LocalInterpretedSolutionRunner(run_cmd)
    assert runner.run_command == run_cmd


def test_interpreted_runner_simple_output():
    """Test basic Python code execution with input."""
    python_code = cleandoc("""
    import sys
    input_data = sys.stdin.read().strip()
    print(f'Hello World! Input was: {input_data}')
    """)
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])
    result = runner.run(python_code, solution_input='test')
    assert result == 'Hello World! Input was: test\n'


def test_interpreted_runner_multiline_output():
    """Test multi-line output handling with input processing."""
    python_code = cleandoc("""
    import sys
    lines = sys.stdin.read().strip().split()
    for i, line in enumerate(lines):
        print(f"Line {i}: {line}")
    """)
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])
    result = runner.run(python_code, solution_input='hello world test\n')
    assert result == 'Line 0: hello\nLine 1: world\nLine 2: test\n'


def test_interpreted_runner_with_arguments():
    """Test command-line argument handling with input."""
    python_code = cleandoc("""
    import sys
    input_data = sys.stdin.read().strip()
    print("Arguments:", ' '.join(sys.argv[1:]))
    print("Input:", input_data)
    """)
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}', '--option', 'value'])
    result = runner.run(python_code, solution_input='test input')
    assert 'Arguments: --option value\n' in result
    assert 'Input: test input\n' in result


def test_interpreted_runner_error_handling():
    """Test error propagation for invalid code."""
    python_code = 'print(undefined_variable)'
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])

    with pytest.raises(RunnerRuntimeError) as exc_info:
        runner.run(python_code, solution_input='')

    assert 'NameError' in exc_info.value.stderr
    assert 'undefined_variable' in exc_info.value.stderr
    assert exc_info.value.exit_code != 0


def test_interpreted_runner_with_dependencies():
    """Test execution with external dependencies and input."""
    python_code = cleandoc("""
    import math
    import sys
    number = float(sys.stdin.read().strip())
    print(f"Pi: {math.pi:.2f}, Input sqrt: {math.sqrt(number):.2f}")
    """)
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])
    result = runner.run(python_code, solution_input='16.0')
    assert 'Pi: 3.14' in result
    assert 'Input sqrt: 4.00' in result


def test_interpreted_runner_syntax_error():
    """Test handling of syntax errors."""
    python_code = "print('Hello world'"
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])

    with pytest.raises(RunnerRuntimeError) as exc_info:
        runner.run(python_code, solution_input='')

    assert 'SyntaxError' in exc_info.value.stderr
    assert exc_info.value.exit_code != 0


def test_file_based_io_compiled():
    """Test file-based I/O for compiled solutions."""
    c_code = """
    #include <stdio.h>
    int main() {
        FILE *input_file = fopen("input.txt", "r");
        FILE *output_file = fopen("output.txt", "w");
        
        char buffer[100];
        if (input_file && output_file) {
            fgets(buffer, sizeof(buffer), input_file);
            fprintf(output_file, "Processed: %s", buffer);
            fclose(input_file);
            fclose(output_file);
        }
        return 0;
    }
    """

    runner = LocalCompiledSolutionRunner(
        ['cc', '-o', '{output_file}', '{input_file}'], source_code_ext='.c'
    )
    result = runner.run(
        c_code,
        solution_input='file input data\n',
        input_file_name='input.txt',
        output_file_name='output.txt',
    )

    assert 'Processed: file input data' in result


def test_file_based_io_interpreted():
    """Test file-based I/O for interpreted solutions."""
    python_code = cleandoc("""
    with open('input.txt', 'r') as f:
        data = f.read().strip()
    
    with open('output.txt', 'w') as f:
        f.write(f"Processed: {data.upper()}")
    """)

    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])
    result = runner.run(
        python_code,
        solution_input='hello world',
        input_file_name='input.txt',
        output_file_name='output.txt',
    )

    assert 'Processed: HELLO WORLD' in result


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
        runner.run(invalid_code, solution_input='')

    assert exc_info.value.exit_code != 0


def test_time_limit_exceeded_compiled():
    """Compiled solution fails when time limit exceeded"""
    runner = LocalCompiledSolutionRunner(
        ['cc', '-o', '{output_file}', '{input_file}'], source_code_ext='.c'
    )

    # C code with infinite loop that still reads input
    infinite_loop_code = """
    #include <stdio.h>
    int main() {
        char buffer[100];
        fgets(buffer, sizeof(buffer), stdin);  // Read input first
        while(1) {
            // Infinite loop
        }
        return 0;
    }
    """

    timeout_ms = 200
    with pytest.raises(TimeLimitExceed) as exc_info:
        runner.run(infinite_loop_code, solution_input='test input\n', timeout_ms=timeout_ms)

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
        char buffer[100];
        fgets(buffer, sizeof(buffer), stdin);  // Read input first
        
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
        runner.run(
            memory_hungry_code, solution_input='test\n', max_memory_bytes=max_memory_bytes
        )

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
        char input[100];
        fgets(input, sizeof(input), stdin);
        printf("Hello, World! Input: %s", input);
        return 0;
    }
    """

    result = runner.run(fast_code, solution_input='test\n', timeout_ms=5000)  # Generous timeout
    assert 'Hello, World! Input: test' in result


def test_successful_run_with_memory_limit_compiled():
    """Compiled solution runs successfully when memory limit set but not exceeded"""
    runner = LocalCompiledSolutionRunner(
        ['cc', '-o', '{output_file}', '{input_file}'], source_code_ext='.c'
    )

    efficient_code = """
    #include <stdio.h>
    int main() {
        int x = 42;
        char input[100];
        fgets(input, sizeof(input), stdin);
        printf("Value: %d, Input: %s", x, input);
        return 0;
    }
    """

    result = runner.run(
        efficient_code, solution_input='hello\n', max_memory_bytes=64 * 1024 * 1024
    )
    assert 'Value: 42, Input: hello' in result


def test_time_limit_exceeded_interpreted():
    """Interpreted solution fails when time limit exceeded"""
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])

    # Python code with infinite loop
    infinite_loop_code = cleandoc("""
        import sys
        import time
        input_data = sys.stdin.read()  # Read input first
        while True:
            time.sleep(0.001)  # Small sleep to prevent CPU spinning
    """)

    timeout_ms = 100

    with pytest.raises(TimeLimitExceed) as exc_info:
        runner.run(infinite_loop_code, solution_input='test', timeout_ms=timeout_ms)

    assert exc_info.value.timeout == timeout_ms


def test_memory_limit_exceeded_interpreted():
    """Interpreted solution fails when memory limit exceeded"""
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])

    # Python code that tries to consume lots of memory
    memory_hungry_code = cleandoc("""
        import sys
        input_data = sys.stdin.read()  # Read input first
        # Try to allocate a large list
        big_list = [0] * (100 * 1024 * 1024)
        print("Memory allocated")
    """)

    max_memory_bytes = 10 * 1024 * 1024
    with pytest.raises(MemoryLimitExceed) as exc_info:
        runner.run(memory_hungry_code, solution_input='test', max_memory_bytes=max_memory_bytes)
    assert exc_info.value.limit == max_memory_bytes


def test_successful_run_with_time_limit_interpreted():
    """Interpreted solution runs successfully when time limit set but not exceeded"""
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])

    fast_code = cleandoc("""
    import sys
    input_data = sys.stdin.read().strip()
    print(f"Hello from Python! Input: {input_data}")
    """)

    result = runner.run(fast_code, solution_input='test input', timeout_ms=5000)
    assert 'Hello from Python! Input: test input' in result


def test_successful_run_with_memory_limit_interpreted():
    """Interpreted solution runs successfully when memory limit set but not exceeded"""
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])

    efficient_code = cleandoc("""
    import sys
    input_data = sys.stdin.read().strip()
    x = 42
    y = "hello"
    print(f"x={x}, y={y}, input={input_data}")
    """)

    result = runner.run(
        efficient_code, solution_input='world', max_memory_bytes=64 * 1024 * 1024
    )  # 64MB limit
    assert 'x=42, y=hello, input=world' in result


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
        runner.run(multi_error_code, solution_input='')
    assert exc_info.value.exit_code != 0


def test_runtime_error_handling_interpreted():
    """Test that runtime errors are properly handled for interpreted code"""
    runner = LocalInterpretedSolutionRunner(['python', '{input_file}'])

    # Python code that will cause runtime error
    runtime_error_code = cleandoc("""
    import sys
    input_data = sys.stdin.read()
    print("Starting...")
    x = 1 / 0  # Division by zero
    print("This won't print")
    """)

    with pytest.raises(RunnerRuntimeError) as exc_info:
        runner.run(runtime_error_code, solution_input='test')

    assert exc_info.value.exit_code != 0
    assert 'ZeroDivisionError' in exc_info.value.stderr


def test_successful_execution_with_both_limits():
    """Test successful execution with both time and memory limits set"""
    runner = LocalCompiledSolutionRunner(
        ['cc', '-o', '{output_file}', '{input_file}'], source_code_ext='.c'
    )

    # C code that runs quickly and uses minimal memory
    simple_code = """
    #include <stdio.h>
    int main() {
        int n;
        scanf("%d", &n);
        for(int i = 0; i < n; i++) {
            printf("%d ", i);
        }
        printf("\\n");
        return 0;
    }
    """

    result = runner.run(
        simple_code,
        solution_input='10\n',
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
    import sys
    number = float(sys.stdin.read().strip())
    result = math.sqrt(number)
    print(f"Result: {result}")
    """)

    result = runner.run(
        simple_code,
        solution_input='16.0',
        timeout_ms=3000,  # 3 seconds
        max_memory_bytes=32 * 1024 * 1024,  # 32MB
    )
    assert result == 'Result: 4.0\n'
