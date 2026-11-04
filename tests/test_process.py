"""Tests for the subprocess wrapper."""

from __future__ import annotations

import pytest

from gather.process import Process, ProcessError


def test_run_success() -> None:
    result = Process("echo", "hello").run()
    assert result.ok
    assert result.out == "hello"


def test_run_nonzero_captures_stderr() -> None:
    result = Process("sh", "-c", "echo boom >&2; exit 3").run()
    assert not result.ok
    assert result.code == 3
    assert result.err == "boom"


def test_checked_raises_with_code() -> None:
    with pytest.raises(ProcessError) as excinfo:
        Process("sh", "-c", "exit 7").checked()
    assert excinfo.value.result.code == 7


def test_timeout_signal() -> None:
    result = Process("sleep", "5", timeout=0.1).run()
    assert result.timed_out
    assert not result.ok


def test_checked_raises_on_timeout() -> None:
    with pytest.raises(ProcessError):
        Process("sleep", "5", timeout=0.1).checked()


def test_single_string_is_shell_split() -> None:
    result = Process("echo hello world").run()
    assert result.out == "hello world"
