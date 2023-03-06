from gitbark.commands.verify import verify as verify_cmd
from gitbark.commands.install import install as install_cmd
import click

@click.group()
def cli():
    pass

@cli.command()
@click.option('-r', '--ref-update', type=(str, str, str))
def verify(ref_update):
    if not install_cmd():
        return False
    verify_cmd(ref_update)

@cli.command()
def install():
    install_cmd()



if __name__ == "__main__":
    cli()
