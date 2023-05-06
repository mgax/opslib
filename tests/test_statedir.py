from pathlib import Path

import pytest

from opslib.components import Component, Stack


def test_init_statedir(Stack, tmp_path):
    bench = Stack()
    bench.box = Component()
    bench.box._meta.statedir.init()
    assert bench.box._meta.statedir.path == tmp_path / "statedir" / "box" / "_statedir"
    assert bench.box._meta.statedir.path.exists()


def test_default_state_prefix():
    class Bench(Stack):
        pass

    assert Bench().get_state_directory() == Path(__file__).parent / ".opslib"


def test_guard_statedir_outside_tmp():
    with pytest.raises(AssertionError) as error:
        Stack()._meta.statedir.init()

    assert "No statedir outside tmp" in error.value.args[0]
