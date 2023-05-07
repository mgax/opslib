from pathlib import Path

import pytest

from opslib.components import Component, Stack, get_stateroot
from opslib.lazy import evaluate


def test_init_statedir(stack, tmp_path):
    stack.box = Component()
    path = evaluate(stack.box._meta.statedir.path)
    assert path == tmp_path / "statedir" / "box" / "_statedir"
    assert path.exists()


def test_default_state_prefix():
    assert get_stateroot(__name__) == Path(__file__).parent / ".opslib"


def test_guard_statedir_outside_tmp():
    vagrant = Stack(__name__)

    with pytest.raises(AssertionError) as error:
        evaluate(vagrant._meta.statedir.path)

    assert "No statedir outside tmp" in error.value.args[0]
