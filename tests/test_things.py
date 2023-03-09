from opslib.things import Stack, Thing


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
