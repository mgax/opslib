import importlib
import logging
import os
import sys

import click

from .operations import apply, print_report
from .things import init_statedir


def lookup(thing, path):
    for name in path.split("."):
        if name == "-":
            continue

        thing = thing._children[name]

    return thing


def get_cli(thing):
    @click.group()
    def cli():
        pass

    @cli.command("init")
    def init():
        init_statedir(thing)

    @cli.command()
    def id():
        click.echo(repr(thing))

    @cli.command()
    def ls():
        for child in thing:
            click.echo(f"{child._meta.name}: {child!r}")

    @cli.command(
        "thing",
        context_settings=dict(
            ignore_unknown_options=True,
            allow_interspersed_args=False,
        ),
    )
    @click.pass_context
    @click.argument("path")
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def thing_(ctx, path, args):
        target = lookup(thing, path)
        target_cli = get_cli(target)
        target_cli(obj=ctx.obj, args=args)

    def register_apply_command(name, *decorators, **defaults):
        @click.pass_context
        def command(ctx, **kwargs):
            results = apply(thing, **defaults, **kwargs)
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

    thing.add_commands(cli)

    return cli


def get_main_cli(get_stack):
    @click.command(
        context_settings=dict(
            ignore_unknown_options=True,
            allow_interspersed_args=False,
        )
    )
    @click.option("-d", "--debug", is_flag=True)
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def cli(debug, args):
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
        stack = get_stack()
        return get_cli(stack)(args=["thing", *args])

    return cli


def main():
    sys.path.append(os.getcwd())
    module = importlib.import_module(os.environ.get("OPSLIB_STACK", "stack"))
    cli = get_main_cli(module.get_stack)
    cli()
