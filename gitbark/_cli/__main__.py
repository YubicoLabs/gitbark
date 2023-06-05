from gitbark.commands.verify import verify as verify_cmd
from gitbark.commands.install import install as install_cmd, is_installed
from gitbark.bark_core.signatures.commands.approve_cmd import approve_cmd
from gitbark.bark_core.signatures.commands.add_detached_signatures_cmd import add_detached_signatures_cmd
from gitbark.wd import WorkingDirectory
import click

import sys

from gitbark import globals

@click.group()
def cli():
    globals.init()
    pass

@cli.command()
def install():
    install_cmd()


@cli.command()
@click.option('-r', '--ref-update', type=(str, str, str))
@click.option("--all", is_flag=True, show_default=True, default=False, help="Verify all branches")
@click.option("-b", "--bootstrap", type=str, help="Verify from bootstrap")
def verify(ref_update, all, bootstrap):
    if not is_installed():
        print("Error: Bark is not properly installed! Run \"bark install\" first!")
        sys.exit(1)
    verify_cmd(all, ref_update, bootstrap)
    

# TODO: Add these commands dynamically
@cli.command()
@click.argument("commit")
@click.option('--gpg-sign', type=str)
@click.option('--ssh-key-path', type=str)
def approve(commit, gpg_sign, ssh_key_path):
    approve_cmd(commit, gpg_sign, ssh_key_path)

@cli.command(name="add-detached-signatures")
@click.argument("commit-msg-file", type=str)
def add_detached_signatures(commit_msg_file):
    add_detached_signatures_cmd(commit_msg_file)



if __name__ == "__main__":
    cli()
