import pytest

from opslib.local import run
from opslib.results import OperationError


def test_stdout():
    result = run("echo", "hello", "world")
    assert result.stdout == "hello world\n"
    assert result.stderr == ""
    assert result.output == "hello world\n"


def test_stderr():
    result = run("bash", "-c", "echo foo >&2")
    assert result.stdout == ""
    assert result.stderr == "foo\n"
    assert result.output == "foo\n"


def test_bytes_output():
    result = run("echo", "hello", "world", encoding=None)
    assert result.stdout == b"hello world\n"
    assert result.stderr == b""
    assert result.output == b"hello world\n"


def test_no_capture(capfd):
    result = run("echo", "hello", "world", capture_output=False)
    assert result.stdout == ""
    assert result.stderr == ""
    assert result.output == ""
    captured = capfd.readouterr()
    assert captured.out == "hello world\n"


def test_success():
    result = run("true")
    assert result.changed
    assert not result.failed
    assert result.completed.args == ("true",)
    assert result.completed.returncode == 0


def test_failed():
    with pytest.raises(OperationError) as error:
        run("false")

    assert error.value.args == ("Local command failed",)
    assert error.value.result.failed
    assert error.value.result.completed.returncode == 1


def test_exit():
    with pytest.raises(SystemExit) as error:
        run("false", exit=True)

    assert error.value.code == 1


def test_input():
    result = run("cat", input="hello world\n")
    assert result.output == "hello world\n"
