import logging
import sys
from collections import defaultdict

from click import echo, style

from .lazy import evaluate, is_lazy
from .results import OperationError

logger = logging.getLogger(__name__)


class AbortOperation(RuntimeError):
    pass


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
        assert not kwargs, f"Unknown flags: {list(kwargs)}"

    def __str__(self):
        return ", ".join(
            f"{flag}={value}"
            for flag, value in ((flag, getattr(self, flag)) for flag in self.FLAGS)
            if value
        )

    def __repr__(self):
        return f"<Operation {self}>"


class Printer:
    def __init__(self, thing):
        self.thing = thing
        self.thing_str = str(self.thing)
        self.thing_type_str = type(self.thing).__name__

    def print_thing(self, wip=False, failed=False, changed=False):
        if wip:
            thing_color = dict(dim=True)
            status_color = dict(dim=True)
            status = "..."

        elif failed:
            thing_color = dict(fg="red")
            status_color = dict(fg="red")
            status = "[failed]"

        elif changed:
            thing_color = dict(fg="yellow")
            status_color = dict(fg="yellow")
            status = "[changed]"

        else:
            thing_color = dict(dim=True)
            status_color = dict(fg="green")
            status = "[ok]"

        bits = [
            style(self.thing_str, **thing_color),
            style(self.thing_type_str, fg="cyan"),
            style(status, **status_color),
        ]
        echo(" ".join(bits))

    def print_result(self, result, overwrite=False):
        if overwrite:
            echo("\033[F", nl=False)

        self.print_thing(failed=result.failed, changed=result.changed)

        if result.failed or result.changed:
            result.print_output()


class Runner:
    def __init__(self, thing):
        self.thing = thing
        self.printer = Printer(thing)

    def run(self, func, *args, **kwargs):
        self.printer.print_thing(wip=True)

        try:
            result = func(*args, **kwargs)

            if is_lazy(result):
                overwrite = False
                result = evaluate(result)

            else:
                overwrite = True

            self.printer.print_result(result, overwrite=overwrite)
            return result

        except Exception as error:
            if isinstance(error, OperationError):
                logger.warning("Run failed on %s: %r", self.thing, error)

                try:
                    self.printer.print_result(error.result)

                except Exception:
                    logger.exception(
                        "Failed to print exception result at %r", self.thing
                    )

                echo(style("Operation failed!", fg="red"), file=sys.stderr)
                raise AbortOperation()

            raise


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


def print_report(results):
    ok_count = len([r for r in results.values() if not r.changed])
    if ok_count:
        echo(style(f"{ok_count} ok", fg="green"))

    changed_count = len([r for r in results.values() if r.changed])
    if changed_count:
        echo(style(f"{changed_count} changed", fg="yellow"))

        by_type = defaultdict(int)
        for thing, result in results.items():
            if result.changed:
                by_type[type(thing)] += 1

        for cls, number in by_type.items():
            echo(style(f"{cls}: {number}", dim=True))
