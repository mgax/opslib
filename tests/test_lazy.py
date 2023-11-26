from opslib.lazy import Lazy, evaluate, lazy_property


def func(*args, **kwargs):
    return dict(args=args, kwargs=kwargs)


def test_no_arguments():
    lazy = Lazy(func)
    assert evaluate(lazy) == dict(args=(), kwargs={})


def test_arguments():
    lazy = Lazy(func, 1, 2, a=3, b=4)
    assert evaluate(lazy) == dict(args=(1, 2), kwargs={"a": 3, "b": 4})


def test_list():
    lazy = [Lazy(func, 1)]
    assert evaluate(lazy) == [dict(args=(1,), kwargs={})]


def test_dict():
    lazy = {0: Lazy(func, 1)}
    assert evaluate(lazy) == {0: dict(args=(1,), kwargs={})}


def test_not_lazy():
    lazy = 13
    assert evaluate(lazy) == 13


def test_lazy_only_evaluated_once():
    calls = 0

    def func():
        nonlocal calls
        calls += 1

    lazy = Lazy(func)
    evaluate(lazy)
    evaluate(lazy)
    assert calls == 1


def test_lazy_property():
    class Bench:
        called = 0

        @lazy_property
        def foo(self):
            self.called += 1
            return "bar"

    bench = Bench()
    assert not bench.called
    assert isinstance(bench.foo, Lazy)
    assert evaluate(bench.foo) == "bar"
    assert bench.called == 1
    evaluate(bench.foo)
    evaluate(bench.foo)
    assert bench.called == 1
