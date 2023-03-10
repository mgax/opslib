from textwrap import dedent

import pytest

from opslib.lazy import Lazy
from opslib.local import run
from opslib.operations import apply
from opslib.props import Prop
from opslib.results import Result
from opslib.things import Stack, Thing


class Task(Thing):
    class Props:
        changed = Prop(bool, default=False)
        failed = Prop(bool, default=False)
        exception = Prop(bool, default=False)

    def deploy(self, dry_run=False):
        if self.props.exception:
            run("bash", "-c", "echo dont panic >&2; false")

        return Result(
            changed=self.props.changed,
            failed=self.props.failed,
        )


def test_print_ok(capsys):
    stack = Stack()
    stack.task = Task(changed=False)

    apply(stack, deploy=True)

    captured = capsys.readouterr()
    assert captured.out == "task Task ...\ntask Task [ok]\n"
    assert captured.err == ""


def test_print_changed(capsys):
    stack = Stack()
    stack.task = Task(changed=True)

    apply(stack, deploy=True)

    captured = capsys.readouterr()
    assert captured.out == "task Task ...\ntask Task [changed]\n"
    assert captured.err == ""


def test_print_failed(capsys):
    stack = Stack()
    stack.task = Task(failed=True)

    apply(stack, deploy=True)

    captured = capsys.readouterr()
    assert captured.out == "task Task ...\ntask Task [failed]\n"
    assert captured.err == ""


def test_print_error(capsys):
    stack = Stack()
    stack.task = Task(exception=True)

    with pytest.raises(SystemExit):
        apply(stack, deploy=True)

    captured = capsys.readouterr()
    assert captured.out == "task Task ...\ntask Task [failed]\ndont panic\n\n"
    assert captured.err == "Operation failed!\n"


def test_print_direct_output(capfd):
    class DirectOutputTask(Thing):
        def deploy(self, dry_run=False):
            return Lazy(run, "echo", "hello lazy", capture_output=False)

    stack = Stack()
    stack.task = DirectOutputTask()
    apply(stack, deploy=True)

    captured = capfd.readouterr()
    assert captured.out == dedent(
        """\
        task DirectOutputTask ...
        hello lazy
        task DirectOutputTask [changed]
        """
    )
