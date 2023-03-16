from pathlib import Path

import pytest
from click.testing import CliRunner

from opslib.cli import get_main_cli
from opslib.things import Stack, Thing, init_statedir


def test_init_statedir(Stack, tmp_path):
    bench = Stack()
    bench.box = Thing()
    init_statedir(bench)
    assert bench.box._meta.statedir.path == tmp_path / "statedir" / "box" / "_statedir"
    assert bench.box._meta.statedir.path.exists()


def test_cli_init(Stack, tmp_path):
    bench = Stack()
    bench.box = Thing()
    cli = get_main_cli(lambda: bench)
    CliRunner().invoke(cli, ["-", "init"], catch_exceptions=False)
    assert bench.box._meta.statedir.path.exists()


def test_statedir_check(Stack):
    bench = Stack()
    bench.box = Thing()
    with pytest.raises(AssertionError) as error:
        bench.box._meta.statedir.path

    expected = "State directory for <Thing box> missing, please run `init`."
    assert error.value.args == (expected,)


def test_default_state_prefix():
    class Bench(Stack):
        pass

    assert Bench().get_state_directory() == Path(__file__).parent / ".opslib"


def test_guard_statedir_outside_tmp():
    with pytest.raises(AssertionError) as error:
        init_statedir(Stack())

    assert "No statedir outside tmp" in error.value.args[0]
