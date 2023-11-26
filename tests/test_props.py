from typing import Optional

import pytest

from opslib.lazy import Lazy, evaluate
from opslib.props import Prop, get_instance_props


class Bench:
    _props_dataclass = None

    class Props:
        name = Prop(str)
        color = Prop(str, default="black")
        size = Prop(Optional[int])
        material = Prop(str, default="", lazy=True)

    def __init__(self, **kwargs):
        self.props = get_instance_props(self, kwargs)


def test_value():
    bench = Bench(name="bar")
    assert bench.props.name == "bar"


def test_default():
    bench = Bench(name="bar")
    assert bench.props.color == "black"


def test_optional():
    bench = Bench(name="bar")
    assert bench.props.size is None


def test_wrong_type():
    with pytest.raises(TypeError) as error:
        Bench(name=13)

    assert error.value.args == ("Prop 'name': 13 is not <class 'str'>",)


def test_missing():
    with pytest.raises(TypeError) as error:
        Bench()

    assert error.value.args == ("Required prop 'name' is missing",)


def test_unexpected():
    with pytest.raises(TypeError) as error:
        Bench(name="bar", surprise="boom")

    assert (
        "'surprise' is an invalid prop for <test_props.Bench object "
    ) in error.value.args[0]


def test_lazy_property():
    bench = Bench(name="bar", material=Lazy(str.title, "wood"))
    assert evaluate(bench.props.material) == "Wood"


def test_lazy_property_not_lazy_value():
    bench = Bench(name="bar", material="wood")
    assert evaluate(bench.props.material) == "wood"


def test_lazy_property_wrong_type():
    bench = Bench(name="bar", material=Lazy(lambda: 13))
    with pytest.raises(TypeError) as error:
        evaluate(bench.props.material)

    assert "Lazy prop 'material' for <test_props.Bench object " in error.value.args[0]
    assert "13 is not <class 'str'>" in error.value.args[0]


def test_remainder():
    class Bench:
        _props_dataclass = None

        class Props:
            a = Prop(int)
            b = Prop(int)
            z = Prop.remainder

        def __init__(self, **kwargs):
            self.props = get_instance_props(type(self), kwargs)

    bench = Bench(a=1, b=2, c=3, d=4)
    assert bench.props.a == 1
    assert bench.props.b == 2
    assert bench.props.z == dict(c=3, d=4)

    with pytest.raises(TypeError) as error:
        evaluate(Bench(a=1))

    assert error.value.args == ("Required prop 'b' is missing",)
