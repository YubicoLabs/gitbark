# Copyright 2023 Yubico AB

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from gitbark.commands.verify import verify as verify_cmd
from gitbark.commands.install import is_installed, install as install_cmd

from gitbark.store import Store, Project
from gitbark.util import cmd
from gitbark.git import Commit, ReferenceUpdate, get_root
from gitbark.command import _add_subcommands
from gitbark import globals
from .util import (
    BarkContextObject,
    click_callback,
    verify_bootstrap,
    CliFail,
    handle_exit,
)

from typing import Optional
import click
import logging
import sys

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def cli(ctx):
    ctx.obj = BarkContextObject()

    toplevel = get_root()
    store = Store()

    ctx.obj["store"] = store

    project = store.get_project(toplevel)
    if not project:
        project = store.create_project(toplevel)
    ctx.obj["project"] = project

    env = project.env
    env.activate()

    globals.init(toplevel)


_add_subcommands(cli)


@cli.command()
@click.pass_context
def install(ctx):
    """
    Install GitBark in repo.
    """
    project = ctx.obj["project"]
    store = ctx.obj["store"]

    verify_bootstrap(project)

    root_commit = cmd("git", "rev-list", "--max-parents=0", "branch_rules")[0]
    if root_commit != project.root_commit:
        click.echo(
            f"The bootstrap commit ({root_commit}) of the branch_rules "
            "branch has not been verified!"
        )
        click.confirm(
            "Do you want to trust this commit as the bootstrap commit?",
            abort=True,
            err=True,
        )
        project.set_root_commit(root_commit)

    report = install_cmd(project)

    if report.is_repo_valid():
        click.echo("Installed GitBark successfully!")
        store.update_project(project)

    handle_exit(report)


@click_callback()
def click_parse_ref_update(ctx, param, val):
    old_ref, new_ref, ref_name = val
    return ReferenceUpdate(old_ref, new_ref, ref_name)


@click_callback()
def click_parse_bootstrap(ctx, param, val):
    if val:
        return Commit(val)
    return None


@click_callback()
def click_parse_branch(ctx, param, val):
    project = ctx.obj["project"]

    try:
        _, ref = project.repo.resolve_refish(val)
        try:
            branch = ref.name
            return branch
        except Exception:
            raise
    except KeyError:
        raise KeyError(f"{val} is not a valid branch name!")


def _get_head(
    project: Project, branch: str, ref_update: Optional[ReferenceUpdate]
) -> Commit:
    """Retrieve head commit of branch.

    Note: If `ref_update` is provided, the new reference target
    is returned as head.
    """
    if ref_update:
        hash = ref_update.new_ref
    else:
        hash = project.repo.revparse_single(branch).id.__str__()
    return Commit(hash)


@cli.command()
@click.pass_context
@click.option(
    "-B",
    "--branch",
    type=str,
    default="HEAD",
    show_default=True,
    help="The branch to verify.",
    callback=click_parse_branch,
)
@click.option(
    "-r",
    "--ref-update",
    type=(str, str, str),
    help="The reference update.",
    callback=click_parse_ref_update,
)
@click.option(
    "-a",
    "--all",
    is_flag=True,
    show_default=True,
    default=False,
    help="Verify all branches.",
)
@click.option(
    "-b",
    "--bootstrap",
    type=str,
    help="Verify from bootstrap",
    callback=click_parse_bootstrap,
)
def verify(ctx, branch, ref_update, all, bootstrap):
    """
    Verify repository or branch.
    """
    project = ctx.obj["project"]
    if not is_installed(project):
        click.echo('Error: Bark is not installed! Run "bark install" first!')
        exit(1)
    store = ctx.obj["store"]

    head = None
    if not all:
        # Get head commit
        head = _get_head(project, branch, ref_update)
    if ref_update:
        branch = ref_update.ref_name

    report = verify_cmd(project, branch, head, bootstrap, all)

    if report.is_repo_valid():
        if all:
            click.echo("Repository is in valid state!")
        elif not ref_update:
            click.echo(f"{branch} is in a valid state!")

        store.update_project(project)

    handle_exit(report)


class _DefaultFormatter(logging.Formatter):
    def __init__(self, show_trace=False):
        self.show_trace = show_trace

    def format(self, record):
        message = f"{record.levelname}: {record.getMessage()}"
        if self.show_trace and record.exc_info:
            message += self.formatException(record.exc_info)
        return message


def main():
    handler = logging.StreamHandler()
    handler.setLevel(logging.WARNING)
    formatter = _DefaultFormatter()
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)

    try:
        cli(obj={})
    except Exception as e:
        status = 1
        msg = e.args[0]
        if isinstance(e, CliFail):
            status = e.status
            msg = e.args[0]
        logger.exception(msg)
        sys.exit(status)


if __name__ == "__main__":
    main()
