from gitbark.commands.verify import verify as verify_cmd
from gitbark.commands.install import install as install_cmd
from gitbark.bark_core.signatures.approve_cmd import approve_cmd
from gitbark.bark_core.signatures.add_detached_signatures_cmd import add_detached_signatures_cmd
from gitbark.wd import WorkingDirectory
import click

@click.group()
def cli():
    pass

@cli.command()
def install():
    install_cmd()


@cli.command()
@click.option('-r', '--ref-update', type=(str, str, str))
@click.option("--all", is_flag=True, show_default=True, default=False, help="Verify all branches")
@click.option("-b", "--bootstrap", type=str, help="Verify from bootstrap")
def verify(ref_update, all, bootstrap):
    verify_cmd(all, ref_update, bootstrap)
    

# TODO: Add these commands dynamically
@cli.command()
@click.argument("commit")
@click.option('--key-id', type=str)
def approve(commit, key_id):
    approve_cmd(commit, key_id)

@cli.command(name="add-detached-signatures")
@click.argument("commit-msg-file", type=str)
def add_detached_signatures(commit_msg_file):
    add_detached_signatures_cmd(commit_msg_file)



if __name__ == "__main__":
    # Will fail if bark has not been initialized on this repository
    WorkingDirectory()
    cli()
