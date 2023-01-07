"""Create Database for User Logins"""
# pylint: disable=R0902, R0912, R0913, R0914, R0915, E1101, E0611, E0611, E1120

from flask.cli import FlaskGroup
import click
from frontend import create_app


@click.group(cls=FlaskGroup, create_app=create_app)
@click.pass_context
def cli(ctx):
    """Management script for the Wiki application."""
    if ctx.parent:
        click.echo(ctx.parent.get_help())


if __name__ == "__main__":
    cli()
