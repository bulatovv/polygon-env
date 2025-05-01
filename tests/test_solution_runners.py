from polygon_env.solution import CompiledSolutionRunner


def test_init_with_default_execute_args():
    """Test initialization with default execute arguments."""
    compile_cmd = ['cc', '-o', '{output_file}', '{input_file}']
    runner = CompiledSolutionRunner(compile_cmd)

    assert runner.compile_command == compile_cmd
    assert runner.execute_args == []
    assert runner.executable_name is None


def test_init_with_custom_execute_args():
    """Test initialization with custom execute arguments."""
    compile_cmd = ['cc', '-o', '{output_file}', '{input_file}']
    execute_args = ['--verbose', '--input', 'test.txt']
    runner = CompiledSolutionRunner(compile_cmd, execute_args)

    assert runner.compile_command == compile_cmd
    assert runner.execute_args == execute_args
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

    runner = CompiledSolutionRunner(['cc', '-o', '{output_file}', '{input_file}'])
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

    runner = CompiledSolutionRunner(['cc', '-o', '{output_file}', '{input_file}', '-lm'])
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

    runner = CompiledSolutionRunner(
        ['cc', '-o', '{output_file}', '{input_file}'], ['arg1', 'arg2', 'arg3']
    )
    result = runner.run(c_code)

    lines = result.strip().split('\n')
    assert 'argc = 4' in lines[0]  # program name + 3 args
    assert 'arg1' in result
    assert 'arg2' in result
    assert 'arg3' in result


if __name__ == '__main__':
    # Run tests manually since we're not using unittest.TestCase
    import sys

    # Get all test functions
    test_functions = [
        obj for name, obj in globals().items() if name.startswith('test_') and callable(obj)
    ]

    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            print(f'Running {test_func.__name__}...', end=' ')
            test_func()
            print('PASSED')
            passed += 1
        except Exception as e:
            print(f'FAILED: {e}')
            failed += 1

    print(f'\nResults: {passed} passed, {failed} failed')
    sys.exit(0 if failed == 0 else 1)
