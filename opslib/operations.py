import logging
import pdb
import sys
from collections import defaultdict

from click import echo, style

from .lazy import Lazy, NotAvailable, evaluate
from .results import OperationError, Result

logger = logging.getLogger(__name__)


class AbortOperation(RuntimeError):
    pass


class Operation:
    """
    The Operation class represents an operation to be performed on a selection
    of :class:`~opslib.components.Component` objects.

    :param dry_run: If ``True``, the operation will not have effects on the
                    target, just show what would change.
    :param deploy: If ``True``, apply changes to the target. May be combined
                   with ``dry_run``.
    :param refresh: If ``True``, inspect the state of the target and save it in
                    local state.
    :param destroy: If ``True``, destroy the target resource.
    """

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
    def __init__(self, component, suffix=""):
        self.component = component
        self.component_str = str(self.component) + suffix
        self.component_type_str = type(self.component).__name__

    def print_component(self, wip=False, failed=False, changed=False):
        if wip:
            component_color = dict(dim=True)
            status_color = dict(dim=True)
            status = "..."

        elif failed:
            component_color = dict(fg="red")
            status_color = dict(fg="red")
            status = "[failed]"

        elif changed:
            component_color = dict(fg="yellow")
            status_color = dict(fg="yellow")
            status = "[changed]"

        else:
            component_color = dict(dim=True)
            status_color = dict(fg="green")
            status = "[ok]"

        bits = [
            style(self.component_str, **component_color),
            style(self.component_type_str, fg="cyan"),
            style(status, **status_color),
        ]
        echo(" ".join(bits))

    def print_result(self, result, overwrite=False):
        if overwrite:
            echo("\033[F", nl=False)

        self.print_component(failed=result.failed, changed=result.changed)

        if result.failed or result.changed:
            result.print_output()


class Runner:
    def __init__(self, component, use_pdb=False, debug=False):
        self.component = component
        self.printer = Printer(component)
        self.use_pdb = use_pdb
        self.debug = debug

    def run(self, func, *args, **kwargs):
        self.printer.print_component(wip=True)

        try:
            result = func(*args, **kwargs)

            if isinstance(result, Lazy):
                overwrite = False
                result = evaluate(result)

            else:
                overwrite = True

            self.printer.print_result(result, overwrite=overwrite)
            return result

        except BaseException as exception:
            if self.debug:
                raise RuntimeError from exception

            if isinstance(exception, NotAvailable):
                result = Result(failed=True, output=exception.args[0])
                self.printer.print_result(result)
                return result

            if isinstance(exception, OperationError):
                logger.warning("Run failed on %s: %r", self.component, exception)

                if self.use_pdb:
                    logger.exception("Command failed")
                    pdb.post_mortem()
                    sys.exit(1)

                try:
                    self.printer.print_result(exception.result)

                except Exception:
                    logger.exception(
                        "Failed to print exception result at %r", self.component
                    )

                echo(style("Operation failed!", fg="red"), file=sys.stderr)
                raise AbortOperation from exception

            raise


def iter_apply(component, op, use_pdb):
    runner = Runner(component, use_pdb)

    logger.debug("Applying %r to %r", op, component)

    children = list(component)
    if op.destroy:
        if hasattr(component, "destroy"):
            yield component, runner.run(component.destroy, dry_run=op.dry_run)

        assert not op.refresh
        assert not op.deploy
        children.reverse()

    for child in children:
        yield from iter_apply(child, op, use_pdb)

    if op.refresh:
        assert not op.dry_run
        if hasattr(component, "refresh"):
            yield component, runner.run(component.refresh)

    if op.deploy:
        if hasattr(component, "deploy"):
            yield component, runner.run(component.deploy, dry_run=op.dry_run)


def apply(component, use_pdb=False, **kwargs):
    """
    Apply the specified operation on ``component``. It will also be applied
    recursively, depth-first, to all child components.

    The order differs depending on the operation. For ``refresh`` and
    ``deploy``, children are processed first. For ``destroy``, the parent
    component is processed first, then its children.

    :param component: The :class:`Component` on which to apply the operation.
    :param kwargs: Keyword arguments are forwarded to :class:`Operation`.
    """

    op = Operation(**kwargs)
    return dict(iter_apply(component, op, use_pdb))


def print_report(results):
    ok_count = len([r for r in results.values() if not (r.changed or r.failed)])
    if ok_count:
        echo(style(f"{ok_count} ok", fg="green"))

    changed_count = len([r for r in results.values() if r.changed])
    failed_count = len([r for r in results.values() if r.failed])
    if changed_count:
        echo(style(f"{changed_count} changed", fg="yellow"))

    if failed_count:
        echo(style(f"{failed_count} failed", fg="red"))

    if changed_count or failed_count:
        by_type = defaultdict(int)
        for component, result in results.items():
            if result.changed or result.failed:
                by_type[type(component)] += 1

        for cls, number in by_type.items():
            echo(style(f"{cls}: {number}", dim=True))
