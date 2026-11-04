import os
import shlex
import typing
from subprocess import PIPE, Popen, TimeoutExpired


class Result(typing.NamedTuple):
    out: str
    err: str
    code: int


type ProcArg = str | bytes | os.PathLike[str] | os.PathLike[bytes]


class Process:
    args: tuple[ProcArg, ...]

    def __init__(
        self, arg: str, *args: ProcArg, timeout=15, cwd: ProcArg | None = None
    ):
        self.args = tuple(shlex.split(arg)) if len(args) == 0 else (arg,) + args
        self.timeout = timeout
        self.cwd = cwd

    def run(self) -> Result:
        process = Popen(self.args, stdout=PIPE, stderr=PIPE, cwd=self.cwd)
        try:
            stdout, stderr = process.communicate(timeout=self.timeout)
        except TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
        return Result(
            out=stdout.decode().strip(),
            err=stderr.decode().strip(),
            code=process.returncode,
        )

    def try_run(self) -> str:
        r = self.run()
        if r.code != 0:
            raise RuntimeError(f"stdout: {r.out}; stderr: {r.err}")
        return r.out
