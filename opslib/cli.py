import click

from .operations import apply


def get_cli(thing):
    @click.group()
    def cli():
        pass

    def register_apply_command(name, *decorators, **defaults):
        @click.pass_context
        def command(ctx, **kwargs):
            apply(thing, **defaults, **kwargs)

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

    return cli
