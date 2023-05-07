import pytest
from click import echo
from click.testing import CliRunner

from opslib.cli import get_cli, get_main_cli
from opslib.components import Component
from opslib.results import Result


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
def test_operation(args, expected, stack):
    log = []

    class Target(Component):
        def refresh(self):
            log.append("refresh")
            return Result()

        def deploy(self, dry_run=False):
            log.append("deploy:dry_run" if dry_run else "deploy")
            return Result()

        def destroy(self, dry_run=False):
            log.append("destroy:dry_run" if dry_run else "destroy")
            return Result()

    stack.target = Target()
    cli = get_cli(stack)
    CliRunner().invoke(cli, args, catch_exceptions=False)

    assert log == expected


def test_id(stack):
    result = CliRunner().invoke(get_cli(stack), ["id"], catch_exceptions=False)
    assert result.output == "<TestingStack __root__>\n"


@pytest.mark.parametrize(
    "path,expected",
    [
        ("-", "<TestingStack __root__>"),
        ("a", "<Component a>"),
        ("a.b", "<Component a.b>"),
        ("a.b.c", KeyError("c")),
    ],
)
def test_component_lookup(path, expected, stack):
    stack.a = Component()
    stack.a.b = Component()

    def run():
        return CliRunner().invoke(
            get_cli(stack), ["component", path, "id"], catch_exceptions=False
        )

    if isinstance(expected, str):
        assert run().output.strip() == expected

    else:
        with pytest.raises(type(expected)) as error:
            run()

        assert error.value.args == expected.args


def test_main_cli(stack):
    stack.a = Component()
    cli = get_main_cli(lambda: stack)
    result = CliRunner().invoke(cli, ["a", "id"], catch_exceptions=False)
    assert result.output == "<Component a>\n"


def test_add_commands(stack):
    class CommandingComponent(Component):
        def add_commands(self, cli):
            @cli.command()
            def speak():
                echo(f"Hello from {self!r}")

    stack.a = CommandingComponent()
    cli = get_main_cli(lambda: stack)
    result = CliRunner().invoke(cli, ["a", "speak"], catch_exceptions=False)
    assert result.output == "Hello from <CommandingComponent a>\n"


def test_ls(stack):
    stack.a = Component()
    stack.b = Component()
    cli = get_main_cli(lambda: stack)
    result = CliRunner().invoke(cli, ["-", "ls"], catch_exceptions=False)
    assert result.output == "a: <Component a>\nb: <Component b>\n"


def test_show_subcommands(stack):
    cli = get_main_cli(lambda: stack)
    result = CliRunner().invoke(cli, ["-", "--help"], catch_exceptions=False)
    assert "Commands:" in result.output
