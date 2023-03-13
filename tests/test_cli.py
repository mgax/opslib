import pytest
from click import echo
from click.testing import CliRunner

from opslib.cli import get_cli, get_main_cli
from opslib.results import Result
from opslib.things import Stack, Thing


@pytest.mark.parametrize(
    "args,expected",
    [
        (["refresh"], ["refresh"]),
        (["diff"], ["deploy:dry_run"]),
        (["deploy"], ["deploy"]),
        (["deploy", "--dry-run"], ["deploy:dry_run"]),
        (["destroy"], ["destroy"]),
        (["destroy", "--dry-run"], ["destroy:dry_run"]),
    ],
)
def test_operation(args, expected):
    log = []

    class Target(Thing):
        def refresh(self):
            log.append("refresh")
            return Result()

        def deploy(self, dry_run=False):
            log.append("deploy:dry_run" if dry_run else "deploy")
            return Result()

        def destroy(self, dry_run=False):
            log.append("destroy:dry_run" if dry_run else "destroy")
            return Result()

    stack = Stack()
    stack.target = Target()
    cli = get_cli(stack)
    CliRunner().invoke(cli, args, catch_exceptions=False)

    assert log == expected


def test_id():
    stack = Stack()
    result = CliRunner().invoke(get_cli(stack), ["id"], catch_exceptions=False)
    assert result.output == "<Stack __root__>\n"


@pytest.mark.parametrize(
    "path,expected",
    [
        ("-", "<Stack __root__>"),
        ("a", "<Thing a>"),
        ("a.b", "<Thing a.b>"),
        ("a.b.c", KeyError("c")),
    ],
)
def test_thing_lookup(path, expected):
    stack = Stack()
    stack.a = Thing()
    stack.a.b = Thing()

    def run():
        return CliRunner().invoke(
            get_cli(stack), ["thing", path, "id"], catch_exceptions=False
        )

    if isinstance(expected, str):
        assert run().output.strip() == expected

    else:
        with pytest.raises(type(expected)) as error:
            run()

        assert error.value.args == expected.args


def test_main_cli():
    stack = Stack()
    stack.a = Thing()
    cli = get_main_cli(lambda: stack)
    result = CliRunner().invoke(cli, ["a", "id"], catch_exceptions=False)
    assert result.output == "<Thing a>\n"


def test_thing_add_cli():
    class CommandingThing(Thing):
        def add_commands(self, cli):
            @cli.command()
            def speak():
                echo(f"Hello from {self!r}")

    stack = Stack()
    stack.a = CommandingThing()
    cli = get_main_cli(lambda: stack)
    result = CliRunner().invoke(cli, ["a", "speak"], catch_exceptions=False)
    assert result.output == "Hello from <CommandingThing a>\n"


def test_ls():
    stack = Stack()
    stack.a = Thing()
    stack.b = Thing()
    cli = get_main_cli(lambda: stack)
    result = CliRunner().invoke(cli, ["-", "ls"], catch_exceptions=False)
    assert result.output == "a: <Thing a>\nb: <Thing b>\n"
