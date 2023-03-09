from typing import Optional

import pytest

from opslib.props import InstanceProps, Prop


class Bench:
    class Props:
        name = Prop(str)
        color = Prop(str, default="black")
        size = Prop(Optional[int])

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
