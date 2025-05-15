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
    timeout_ms: int,
    max_memory_bytes: int,
    *,
    poll_interval: float = 0.01,  # 10 ms
) -> str:
    """
    Run a command while enforcing wall-clock time and RSS memory limits.

    Parameters
    ----------
    cmd
        Executable command and its arguments.
    timeout_ms
        Time limit in milliseconds for wall-clock execution.
    max_memory_bytes
        Maximum allowed resident set size (RSS) in bytes, summed over the entire process tree.
    poll_interval
        Interval in seconds between limit checks. Default is 0.01.

    Returns
    -------
    str
        Standard output of the executed command.

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

    # launch the user program in its own process group so we can SIGKILL it
    # together with any children it might spawn
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=os.setsid,  # new process group on Unix
    )

    ps_proc = psutil.Process(proc.pid)
    peak_rss = 0

    try:
        while True:
            elapsed_ms = (time.monotonic() - start) * 1000
            if elapsed_ms > timeout_ms:
                _kill_proc_tree(ps_proc)
                raise TimeLimitExceed(timeout_ms)

            try:
                # rss for the whole tree (process + children)
                rss_now = _rss_tree(ps_proc)
                peak_rss = max(peak_rss, rss_now)
                if rss_now > max_memory_bytes:
                    _kill_proc_tree(ps_proc)
                    raise MemoryLimitExceed(rss_now, max_memory_bytes)
            except psutil.NoSuchProcess:  # already terminated
                pass

            # did the program finish?
            if proc.poll() is not None:
                break  # out of monitoring loop

            time.sleep(poll_interval)

        # program finished normally
        stdout, stderr = proc.communicate()

        if proc.returncode != 0:
            raise RunnerRuntimeError(stderr, proc.returncode)

        return stdout

    finally:  # make absolutely sure no zombie remains
        if proc.poll() is None:
            _kill_proc_tree(ps_proc)


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
