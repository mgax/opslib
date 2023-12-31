import code
import importlib
import logging
import os
import pdb
import sys

import click

from .operations import apply, print_report
from .state import run_gc

logger = logging.getLogger(__name__)


def lookup(component, path):
    for name in path.split("."):
        if name == "-":
            continue

        component = component._children[name]

    return component


def interact(banner=None, local=None):
    try:
        hook = sys.__interactivehook__

    except AttributeError:
        pass

    else:
        hook()

    try:
        import readline
        import rlcompleter

        readline.set_completer(rlcompleter.Completer(local).complete)

    except ImportError:
        pass

    code.interact(banner=banner, local=local)


class ComponentGroup(click.Group):
    def forward_command(self, *args, **kwargs):
        """
        A specialized :meth:`click.Group.command` for commands that invoke
        another command. Any unprocessed arguments are sent as an ``args``
        tuple, to be forwarded to the other command. It's equivalent to the
        following:

        .. code-block:: python

            @cli.command(
                context_settings=dict(
                    ignore_unknown_options=True,
                    allow_interspersed_args=False,
                )
            )
            @click.argument("args", nargs=-1, type=click.UNPROCESSED)
            def foo(args):
                print("foo called with:", args)
        """

        func = None
        if len(args) == 1 and not kwargs and callable(args[0]):
            func = args[0]
            args = ()

        def decorator(func):
            kwargs.setdefault("context_settings", {}).update(
                ignore_unknown_options=True,
                allow_interspersed_args=False,
            )
            command = super(ComponentGroup, self).command(*args, **kwargs)(func)
            command.params.append(
                click.Argument(("args",), nargs=-1, type=click.UNPROCESSED)
            )
            return command

        if func:
            return decorator(func)

        return decorator


def get_cli(component) -> click.Group:
    @click.group(cls=ComponentGroup)
    def cli():
        pass

    @cli.command()
    def id():
        click.echo(repr(component))

    @cli.command()
    def ls():
        for child in component:
            click.echo(f"{child._meta.name}: {child!r}")

    @cli.command()
    def shell():
        return interact(str(component), dict(self=component))

    @cli.command()
    @click.option("-n", "--dry-run", is_flag=True)
    def gc(dry_run):
        run_gc(component, dry_run=dry_run)

    @cli.forward_command("component")
    @click.pass_context
    @click.argument("path")
    def component_(ctx, path, args):
        target = lookup(component, path)
        target_cli = get_cli(target)
        target_cli(obj=ctx.obj, args=args)

    def register_apply_command(name, *decorators, **defaults):
        @click.option("--pdb", "use_pdb", is_flag=True)
        @click.pass_context
        def command(ctx, use_pdb, **kwargs):
            results = apply(component, use_pdb=use_pdb, **defaults, **kwargs)
            print_report(results)

        for decorator in decorators:
            command = decorator(command)

        cli.command(name)(command)

    register_apply_command(
        "deploy",
        click.option("-n", "--dry-run", is_flag=True),
        deploy=True,
    )

    register_apply_command("diff", deploy=True, dry_run=True)

    register_apply_command("refresh", refresh=True)

    register_apply_command(
        "destroy",
        click.option("-n", "--dry-run", is_flag=True),
        destroy=True,
    )

    @cli.command()
    def check():
        component._check()

    component.add_commands(cli)

    return cli


def get_main_cli(get_stack) -> click.Command:
    """
    Create a :class:`click.Command` for the given stack.

    :param get_stack: Callable that returns a :class:`~opslib.components.Stack`.
    """

    def complete(ctx, param, incomplete):
        component = get_stack()
        prefix = ""

        while "." in incomplete:
            next, incomplete = incomplete.split(".", 1)
            component = component._children[next]
            prefix = f"{prefix}{next}."

        return [
            f"{prefix}{name}"
            for name in component._children
            if name.startswith(incomplete)
        ]

    @click.command(
        context_settings=dict(
            ignore_unknown_options=True,
            allow_interspersed_args=False,
        )
    )
    @click.option("-d", "--debug", is_flag=True)
    @click.option("--pdb", "use_pdb", is_flag=True)
    @click.argument("args", nargs=-1, type=click.UNPROCESSED, shell_complete=complete)
    @click.pass_context
    def cli(ctx: click.Context, debug, use_pdb, args):
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
        ctx.obj["debug"] = debug

        try:
            stack = get_stack()
            return get_cli(stack)(obj=ctx.obj, args=["component", *args])

        except Exception:
            if use_pdb:
                logger.exception("Command failed")
                pdb.post_mortem()
                sys.exit(1)

            raise

    return cli


def get_stack():
    sys.path.append(os.getcwd())
    module = importlib.import_module(os.environ.get("OPSLIB_STACK", "stack"))
    return module.stack


def main():
    """
    Main entry point for the ``opslib`` CLI command. It tries to run ``import
    stack`` and expects to find a stack named ``stack.stack``, which it sends
    to :func:`get_main_cli`.

    The ``OPSLIB_STACK`` environment variable can be set to import something
    other than ``stack``.
    """

    cli = get_main_cli(get_stack)
    cli(obj={})
