import pytest

from opslib.state import JsonState
from opslib.things import Thing, init_statedir


@pytest.fixture
def Bench(Stack):
    class Box(Thing):
        state = JsonState()

    class Bench(Stack):
        def build(self):
            self.box = Box()

    init_statedir(Bench())
    return Bench


def test_json_state_store_and_retrieve(Bench):
    bench = Bench()
    bench.box.state["hello"] = "world"
    assert bench.box.state["hello"] == "world"


def test_json_state_access_as_dict(Bench):
    bench = Bench()
    bench.box.state["hello"] = "world"
    assert bench.box.state == {"hello": "world"}
    assert dict(bench.box.state) == {"hello": "world"}


def test_json_state_access_with_get(Bench):
    bench = Bench()
    bench.box.state["hello"] = "world"
    assert bench.box.state.get("hello") == "world"
    assert bench.box.state.get("nothing") is None
    assert bench.box.state.get("nothing", "default") == "default"


def test_json_state_overwrite(Bench):
    bench = Bench()
    bench.box.state == {"hello": "world"}
    bench.box.state.save(other=13)
    assert bench.box.state == {"other": 13}


def test_json_state_persist_value(Bench):
    Bench().box.state["hello"] = "world"
    assert Bench().box.state == {"hello": "world"}
