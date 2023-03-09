from typing import Optional

import pytest

from opslib.lazy import evaluate, Lazy
from opslib.props import InstanceProps, Prop


class Bench:
    class Props:
        name = Prop(str)
        color = Prop(str, default="black")
        size = Prop(Optional[int])
        material = Prop(str, default="", lazy=True)

    def __init__(self, **kwargs):
        self.props = InstanceProps(type(self), kwargs)


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

    assert error.value.args == (
        "'surprise' is an invalid prop for <class 'test_props.Bench'>",
    )


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

    assert error.value.args == ("Lazy prop 'material': 13 is not <class 'str'>",)
