import pytest

from opslib.components import Component, Meta
from opslib.props import Prop


def test_component_props():
    class Bench(Component):
        class Props:
            name = Prop(str)

    bench = Bench(name="thingie")
    assert bench.props.name == "thingie"


def test_stack_calls_build(TestingStack):
    class Bench(TestingStack):
        def build(self):
            self.build_called = True

    bench = Bench()
    assert bench.build_called


def test_setattr_attaches_child_and_calls_build(TestingStack):
    class Child(Component):
        build_called = False

        def build(self):
            self.build_called = True

    class Bench(TestingStack):
        def build(self):
            self.child = Child()

    bench = Bench()
    assert bench.child.build_called
    assert bench._children["child"] is bench.child


def test_setattr_skips_underscore_names(TestingStack):
    class Child(Component):
        build_called = False

        def build(self):
            self.build_called = True

    class Bench(TestingStack):
        def build(self):
            self._child = Child()

    bench = Bench()
    assert not bench._child.build_called


def test_setattr_warns_against_overriding_the_api(stack):
    with pytest.raises(AttributeError) as error:
        stack.build = Component()

    assert error.value.args == (
        "<TestingStack __root__> already has attribute 'build'",
    )


def test_meta_fields(stack):
    stack.child = Component()
    assert stack.child._meta.component is stack.child
    assert stack.child._meta.name == "child"
    assert stack.child._meta.parent is stack


def test_str(stack):
    stack.a = Component()
    stack.a.b = Component()
    assert str(stack.a.b) == "a.b"


def test_repr(stack):
    stack.a = Component()
    stack.a.b = Component()
    assert repr(stack.a.b) == "<Component a.b>"


def test_double_attach_fails(stack):
    stack.child = Component()

    with pytest.raises(ValueError) as error:
        stack.alias = stack.child

    assert error.value.args == (
        "Cannot attach <Component child> to <TestingStack __root__> "
        "because it's already attached",
    )


def test_iter(stack):
    stack.a = Component()
    stack.b = Component()
    assert list(stack) == [stack.a, stack.b]


def test_custom_meta_class(TestingStack):
    class CustomMeta(Meta):
        pass

    class CustomStack(TestingStack):
        Meta = CustomMeta

    class CustomComponent(Component):
        Meta = CustomMeta

    stack = CustomStack()
    stack.child = CustomComponent()
    assert isinstance(stack._meta, CustomMeta)
    assert isinstance(stack.child._meta, CustomMeta)
