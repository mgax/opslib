import pytest

from opslib.props import Prop
from opslib.things import Stack, Thing


def test_thing_props():
    class Bench(Thing):
        class Props:
            name = Prop(str)

    bench = Bench(name="thingie")
    assert bench.props.name == "thingie"


def test_stack_calls_build():
    class Bench(Stack):
        def build(self):
            self.build_called = True

    bench = Bench()
    assert bench.build_called


def test_setattr_attaches_child_and_calls_build():
    class Child(Thing):
        build_called = False

        def build(self):
            self.build_called = True

    class Bench(Stack):
        def build(self):
            self.child = Child()

    bench = Bench()
    assert bench.child.build_called
    assert bench._children["child"] is bench.child


def test_setattr_skips_underscore_names():
    class Child(Thing):
        build_called = False

        def build(self):
            self.build_called = True

    class Bench(Stack):
        def build(self):
            self._child = Child()

    bench = Bench()
    assert not bench._child.build_called


def test_meta_fields():
    stack = Stack()
    stack.child = Thing()
    assert stack.child._meta.thing is stack.child
    assert stack.child._meta.name == "child"
    assert stack.child._meta.parent is stack


def test_str():
    stack = Stack()
    stack.a = Thing()
    stack.a.b = Thing()
    assert str(stack.a.b) == "a.b"


def test_repr():
    stack = Stack()
    stack.a = Thing()
    stack.a.b = Thing()
    assert repr(stack.a.b) == "<Thing a.b>"


def test_double_attach_fails():
    stack = Stack()
    stack.child = Thing()

    with pytest.raises(ValueError) as error:
        stack.alias = stack.child

    assert error.value.args == (
        "Cannot attach <Thing child> to <Stack __root__> because it's already attached",
    )


def test_iter():
    stack = Stack()
    stack.a = Thing()
    stack.b = Thing()
    assert list(stack) == [stack.a, stack.b]
