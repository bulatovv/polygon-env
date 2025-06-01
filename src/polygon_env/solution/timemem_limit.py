import contextlib
import os
import signal
import subprocess
import time

import psutil

LIMIT_256_MB = 256 * 1024 * 1024


class TimeLimitExceed(Exception):
    """Exception raised when solution runs longer than specified timeout"""

    def __init__(self, timeout: int):
        super().__init__(f'Time limit exceeded ({timeout} ms)')
        self.timeout: int = timeout


class MemoryLimitExceed(Exception):
    """Exception raised when solution consumes more memory than specified memory limit"""

    def __init__(self, peak: int, limit: int):
        super().__init__(f'Memory limit exceeded: {peak:,} > {limit:,} bytes')
        self.peak: int = peak
        self.limit: int = limit


class RunnerRuntimeError(Exception):
    """Exception raised when solution exits with non-zero error code"""

    def __init__(self, stderr: str, exit_code: int):
        super().__init__(f'Runtime error, exit code {exit_code}\n{stderr}')
        self.exit_code: int = exit_code
        self.stderr: str = stderr


def timemem_limit_run(
    cmd: list[str],
    cmd_input: str,
    timeout_ms: int,
    max_memory_bytes: int,
    input_file_name: str | None,
    output_file_name: str | None,
    *,
    poll_interval: float = 0.01,  # 10 ms
) -> str:
    """
    Run a command while enforcing wall-clock time and RSS memory limits.

    Parameters
    ----------
    cmd
        Executable command and its arguments.
    cmd_input
        Input data to pass to the running program.
    timeout_ms
        Time limit in milliseconds for wall-clock execution.
    max_memory_bytes
        Maximum allowed resident set size (RSS) in bytes, summed over the entire process tree.
    input_file_name
        If provided, solution_input is written to this file, otherwise passed via stdin.
    output_file_name
        If provided, output is read from this file, otherwise read from stdout.
    poll_interval
        Interval in seconds between limit checks. Default is 0.01.

    Returns
    -------
    str
        Output of the executed command (from file or stdout).

    Raises
    ------
    TimeLimitExceed
        If the command exceeds the specified time limit.
    MemoryLimitExceed
        If memory usage exceeds the allowed limit.
    RunnerRuntimeError
        If the command exits with a non-zero return code.
    """
    start = time.monotonic()

    # Handle input: write to file or prepare for stdin
    if input_file_name:
        with open(input_file_name, 'w') as f:
            f.write(cmd_input)
        proc_input = None
    else:
        proc_input = cmd_input

    # Launch process
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE if proc_input is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=os.setsid,
    )

    # Send input to stdin if not using file
    if proc_input is not None:
        proc.stdin.write(proc_input)  # pyright: ignore
        proc.stdin.close()  # pyright: ignore

    ps_proc = psutil.Process(proc.pid)
    peak_rss = 0
    try:
        while True:
            elapsed_ms = (time.monotonic() - start) * 1000
            if elapsed_ms > timeout_ms:
                _kill_proc_tree(ps_proc)
                raise TimeLimitExceed(timeout_ms)
            try:
                rss_now = _rss_tree(ps_proc)
                peak_rss = max(peak_rss, rss_now)
                if rss_now > max_memory_bytes:
                    _kill_proc_tree(ps_proc)
                    raise MemoryLimitExceed(rss_now, max_memory_bytes)
            except psutil.NoSuchProcess:
                pass
            if proc.poll() is not None:
                break
            time.sleep(poll_interval)

        # Program finished normally - read output manually
        if proc.stdout is not None:
            stdout = proc.stdout.read()
            proc.stdout.close()
        else:
            stdout = ''

        if proc.stderr is not None:
            stderr = proc.stderr.read()
            proc.stderr.close()
        else:
            stderr = ''

        if proc.returncode != 0:
            raise RunnerRuntimeError(stderr, proc.returncode)

        # Handle output from file if specified
        if output_file_name:
            with open(output_file_name) as f:
                result = f.read()
        else:
            result = stdout

        return result

    finally:
        if proc.poll() is None:
            _kill_proc_tree(ps_proc)
        if input_file_name:
            os.remove(input_file_name)
        if output_file_name:
            os.remove(output_file_name)


def _rss_tree(ps_proc: psutil.Process) -> int:
    """
    Return RSS of `ps_proc` **plus all its alive children** recursively.

    The value is in bytes.
    """
    try:
        total = ps_proc.memory_info().rss
    except psutil.NoSuchProcess:
        return 0

    for child in ps_proc.children(recursive=True):
        try:
            total += child.memory_info().rss
        except psutil.NoSuchProcess:
            continue
    return total


def _kill_proc_tree(ps_proc: psutil.Process) -> None:
    """SIGKILL the whole process group of `ps_proc`."""
    with contextlib.suppress(ProcessLookupError):
        os.killpg(ps_proc.pid, signal.SIGKILL)
