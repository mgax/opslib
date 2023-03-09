import logging

logger = logging.getLogger(__name__)


class Operation:
    FLAGS = [
        "dry_run",
        "deploy",
        "refresh",
        "destroy",
    ]

    def __init__(self, **kwargs):
        self.results = {}
        for flag in self.FLAGS:
            setattr(self, flag, kwargs.pop(flag, False))
        assert not kwargs

    def __str__(self):
        return ", ".join(
            f"{flag}={value}"
            for flag, value in ((flag, getattr(self, flag)) for flag in self.FLAGS)
            if value
        )

    def __repr__(self):
        return f"<Operation {self}>"


class Runner:
    def __init__(self, thing):
        self.thing = thing

    def run(self, func, *args, **kwargs):
        return func(*args, **kwargs)


def iter_apply(thing, op):
    runner = Runner(thing)

    logger.debug("Applying %r to %r", op, thing)

    children = list(thing)
    if op.destroy:
        if hasattr(thing, "destroy"):
            yield thing, runner.run(thing.destroy, dry_run=op.dry_run)

        assert not op.refresh
        assert not op.deploy
        children.reverse()

    for child in children:
        yield from iter_apply(child, op)

    if op.refresh:
        assert not op.dry_run
        if hasattr(thing, "refresh"):
            yield thing, runner.run(thing.refresh)

    if op.deploy:
        if hasattr(thing, "deploy"):
            yield thing, runner.run(thing.deploy, dry_run=op.dry_run)


def apply(thing, **kwargs):
    op = Operation(**kwargs)
    return dict(iter_apply(thing, op))
