from opslib.components import Component
from opslib.lazy import Lazy, NotAvailable
from opslib.operations import apply
from opslib.props import Prop
from opslib.results import Result


def test_call_deploy(stack):
    class Task(Component):
        class Props:
            data = Prop(str)

        def deploy(self, dry_run=False):
            assert not dry_run
            return Result(changed=True, output=self.props.data)

    stack.one = Task(data="one")
    stack.one.a = Task(data="one.a")
    stack.two = Task(data="two")

    results = apply(stack, deploy=True)

    assert list(results) == [stack.one.a, stack.one, stack.two]
    assert results[stack.one.a].output == "one.a"
    assert results[stack.one].output == "one"
    assert results[stack.two].output == "two"


def test_call_diff(stack):
    class Task(Component):
        class Props:
            data = Prop(str)

        def deploy(self, dry_run=False):
            assert dry_run
            return Result(changed=True, output=self.props.data)

    stack.one = Task(data="one")
    stack.one.a = Task(data="one.a")
    stack.two = Task(data="two")

    results = apply(stack, deploy=True, dry_run=True)

    assert list(results) == [stack.one.a, stack.one, stack.two]
    assert results[stack.one.a].output == "one.a"
    assert results[stack.one].output == "one"
    assert results[stack.two].output == "two"


def test_call_refresh(stack):
    class Task(Component):
        class Props:
            data = Prop(str)

        def refresh(self):
            return Result(changed=True, output=self.props.data)

    stack.one = Task(data="one")
    stack.one.a = Task(data="one.a")
    stack.two = Task(data="two")

    results = apply(stack, refresh=True)

    assert list(results) == [stack.one.a, stack.one, stack.two]
    assert results[stack.one.a].output == "one.a"
    assert results[stack.one].output == "one"
    assert results[stack.two].output == "two"


def test_call_destroy(stack):
    class Task(Component):
        class Props:
            data = Prop(str)

        def destroy(self, dry_run=False):
            assert not dry_run
            return Result(changed=True, output=self.props.data)

    stack.one = Task(data="one")
    stack.one.a = Task(data="one.a")
    stack.two = Task(data="two")

    results = apply(stack, destroy=True)

    assert list(results) == [stack.two, stack.one, stack.one.a]
    assert results[stack.two].output == "two"
    assert results[stack.one].output == "one"
    assert results[stack.one.a].output == "one.a"


def test_call_destroy_dry_run(stack):
    class Task(Component):
        class Props:
            data = Prop(str)

        def destroy(self, dry_run=False):
            assert dry_run
            return Result(changed=True, output=self.props.data)

    stack.one = Task(data="one")
    stack.one.a = Task(data="one.a")
    stack.two = Task(data="two")

    results = apply(stack, destroy=True, dry_run=True)

    assert list(results) == [stack.two, stack.one, stack.one.a]
    assert results[stack.two].output == "two"
    assert results[stack.one].output == "one"
    assert results[stack.one.a].output == "one.a"


def test_evaluate_lazy_result(stack):
    called = False

    class Task(Component):
        def deploy(self, dry_run=False):
            def get_result():
                nonlocal called
                called = True
                return Result(output="lay-z")

            return Lazy(get_result)

    stack.one = Task()
    results = apply(stack, deploy=True)
    assert called
    assert results[stack.one].output == "lay-z"


def test_not_available(capsys, stack):
    class Task(Component):
        def deploy(self, dry_run=False):
            raise NotAvailable("Something is not quite ready yet")

    stack.one = Task()
    results = apply(stack, deploy=True)
    assert results[stack.one].failed
    captured = capsys.readouterr()
    assert "one Task [failed]\nSomething is not quite ready yet\n" in captured.out
