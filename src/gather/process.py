"""Subprocess wrapper with a typed result and a clear error signal."""

from __future__ import annotations

import shlex
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

from gather.errors import GatherError


@dataclass(frozen=True)
class Result:
    """The outcome of a subprocess run."""

    args: tuple[str, ...]
    code: int
    out: str
    err: str
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.code == 0 and not self.timed_out


class ProcessError(GatherError):
    """A subprocess failed or timed out."""

    def __init__(self, result: Result) -> None:
        self.result = result
        if result.timed_out:
            kind = "timed out"
        else:
            kind = f"exited with code {result.code}"
        detail = result.err or result.out or "<no output>"
        super().__init__(f"`{' '.join(result.args)}` {kind}: {detail}")


def _split(args: Sequence[str]) -> tuple[str, ...]:
    """Accept either one shell-style string or a sequence of argv tokens."""
    if len(args) == 1:
        return tuple(shlex.split(args[0]))
    return tuple(args)


class Process:
    """A single subprocess invocation, optionally with a working dir and timeout."""

    def __init__(
        self,
        *args: str,
        cwd: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.args = _split(args)
        self.cwd = cwd
        self.timeout = timeout

    def run(self) -> Result:
        """Run and return the result, never raising on a non-zero exit."""
        try:
            completed = subprocess.run(
                self.args,
                capture_output=True,
                text=True,
                cwd=self.cwd,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return Result(
                args=self.args,
                code=-1,
                out=exc.stdout.decode() if exc.stdout else "",
                err=exc.stderr.decode() if exc.stderr else "",
                timed_out=True,
            )
        return Result(
            args=self.args,
            code=completed.returncode,
            out=completed.stdout.strip(),
            err=completed.stderr.strip(),
        )

    def checked(self) -> Result:
        """Run and raise :class:`ProcessError` if the command did not succeed."""
        result = self.run()
        if not result.ok:
            raise ProcessError(result)
        return result
