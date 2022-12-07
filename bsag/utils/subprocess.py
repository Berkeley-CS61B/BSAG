import os
import subprocess
import threading
from dataclasses import dataclass
from typing import Sequence


@dataclass
class SubprocessResult:
    output: str
    stderr: str | None
    return_code: int
    timed_out: bool


def run_subprocess(
    command: str | Sequence[str | os.PathLike[str]],
    cwd: str | os.PathLike[str] | None = None,
    timeout: int | None = None,
    separate_stderr: bool = False,
) -> SubprocessResult:
    if cwd is None:
        cwd = os.getcwd()

    killed = False

    def kill(p: subprocess.Popen[str]) -> None:
        if p.poll() is None:
            nonlocal killed
            killed = True
            p.kill()

    stderr_dst = subprocess.PIPE if separate_stderr else subprocess.STDOUT
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=stderr_dst,
        cwd=cwd,
        text=True,
    )
    timed_bomb = None
    if timeout:
        timed_bomb = threading.Timer(timeout, kill, [process])
        timed_bomb.start()
    p_stdout, p_stderr = process.communicate()
    return_code = process.returncode
    if timed_bomb is not None:
        timed_bomb.cancel()

    return SubprocessResult(p_stdout, p_stderr, return_code, killed)
