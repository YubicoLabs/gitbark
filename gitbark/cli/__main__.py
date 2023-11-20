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

from gitbark.commands.verify import (
    verify_all,
    verify_ref,
    verify_commit,
    verify_ref_update,
)
from gitbark.commands.install import is_installed, install as install_cmd
from gitbark.commands.setup import (
    setup as setup_cmd,
    add_modules_interactive,
    add_branches_interactive,
    add_commit_rules_interactive,
    _confirm_commit,
    checkout_or_orphan,
)

from gitbark.core import BARK_RULES_BRANCH
from gitbark.project import Project
from gitbark.rule import RuleViolation
from gitbark.util import cmd, branch_name
from gitbark.git import Commit
from .util import (
    BarkContextObject,
    click_callback,
    CliFail,
    pp_violation,
    get_root,
    _add_subcommands,
)

import click
import logging
import sys
import os

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def cli(ctx):
    ctx.obj = BarkContextObject()

    toplevel = get_root()
    project = Project(toplevel)

    ctx.obj["project"] = project


@cli.command()
@click.pass_context
def setup(ctx):
    """Setup GitBark in repo."""

    project = ctx.obj["project"]
    setup_cmd(project)


@cli.command()
@click.pass_context
def add_rules(ctx):
    """Add commit rules to a branch."""
    project = ctx.obj["project"]
    add_commit_rules_interactive(project)
    _confirm_commit(
        commit_message="Modify commit rules (made by bark).",
        manual_action=(
            "The 'commit_rules.yaml' file has been staged. "
            "Please commit the changes!"
        ),
    )
    click.echo("Commit rules configuration was committed successfully!")


@cli.command()
@click.pass_context
def add_modules(ctx):
    """Add bark modules."""
    project = ctx.obj["project"]
    branch = project.repo.branch
    add_modules_interactive(project)
    _confirm_commit(
        commit_message="Modify bark modules (made by bark).",
        manual_action=(
            "The 'bark_rules.yaml' file has been staged. Please commit the changes!"
        ),
    )
    checkout_or_orphan(project, branch)
    click.echo("Bark modules configuration was committed successfully!")


@cli.command()
@click.pass_context
def protect(ctx):
    """Protect a branch.

    This will add the branch you are currently on to 'bark_rules'
    so that when changes are made to this branch, they are validated
    automatically.
    """
    project = ctx.obj["project"]
    branch = project.repo.branch
    add_branches_interactive(project, branch)
    _confirm_commit(
        commit_message="Modify bark modules (made by bark).",
        manual_action=(
            "The 'bark_rules.yaml' file has been staged. Please commit the changes!"
        ),
    )
    checkout_or_orphan(project, branch)
    click.echo("Bark modules configuration was committed successfully!")


@cli.command()
@click.pass_context
def install(ctx):
    """
    Install GitBark modules in repo.

    This command assumes GitBark has been configured in the repository. If so,
    it will verify it and install required GitBark modules and hooks.
    """
    project = ctx.obj["project"]

    repo = project.repo
    if BARK_RULES_BRANCH not in repo.branches:
        raise CliFail('The "bark_rules" branch has not been created!')

    root_commit_hash = cmd("git", "rev-list", "--max-parents=0", BARK_RULES_BRANCH)[0]
    root_commit = Commit(bytes.fromhex(root_commit_hash), repo)
    if root_commit != project.bootstrap:
        click.echo(
            f"The bootstrap commit ({root_commit.hash.hex()}) of the branch_rules "
            "branch has not been verified!"
        )
        click.confirm(
            "Do you want to trust this commit as the bootstrap commit?",
            abort=True,
            err=True,
        )
        project.bootstrap = root_commit

    try:
        install_cmd(project)
        click.echo("Installed GitBark successfully!")
    except RuleViolation as e:
        pp_violation(e)
        sys.exit(1)
    finally:
        project.update()


@click_callback()
def click_parse_bootstrap(ctx, param, val):
    project = ctx.obj["project"]
    if val:
        return Commit(bytes.fromhex(val), project.repo)
    return None


@cli.command(hidden=True)
@click.pass_context
@click.argument("old")
@click.argument("new")
@click.argument("ref")
def ref_update(ctx, old, new, ref):
    """Verify ref update"""
    project = ctx.obj["project"]

    if ref not in project.repo.references:
        return

    head = Commit(bytes.fromhex(new), project.repo)

    fail_head = os.path.join(project.bark_directory, "FAIL_HEAD")
    try:
        verify_ref_update(project, ref, head)
        if os.path.exists(fail_head):
            os.remove(fail_head)
    except RuleViolation as e:
        with open(fail_head, "w") as f:
            f.write(head.hash.hex())
        # TODO: Error message here?
        pp_violation(e)
        sys.exit(1)
    finally:
        project.update()


@cli.command()
@click.pass_context
@click.argument("target", default="HEAD")
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
def verify(ctx, target, all, bootstrap):
    """
    Verify repository or branch.

    \b
    TARGET the commit or branch to verify.
    """

    project = ctx.obj["project"]
    if not is_installed(project):
        raise CliFail("Bark is not installed! Run 'bark install' first!")

    try:
        if all:
            verify_all(project)
            click.echo("Repository is in valid state!")
        else:
            head, ref = project.repo.resolve(target)
            if ref:
                verify_ref(project, ref, head)
                click.echo(f"Branch {branch_name(ref)} is in a valid state!")
            elif not bootstrap:
                raise CliFail(
                    "verifying a single commit requires specifying a bootstrap with -b"
                )
            else:
                verify_commit(project, head, bootstrap)
                click.echo(f"Commit {head.hash.hex()} is in a valid state!")
    except RuleViolation as e:
        # TODO: Error message here?
        pp_violation(e)
        sys.exit(1)
    finally:
        project.update()


class _DefaultFormatter(logging.Formatter):
    def __init__(self, show_trace=False):
        self.show_trace = show_trace

    def format(self, record):
        message = f"{record.levelname}: {record.getMessage()}"
        if self.show_trace and record.exc_info:
            message += "\n" + self.formatException(record.exc_info)
        return message


def main():
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = _DefaultFormatter(True)
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    try:
        _add_subcommands(cli)
        cli(obj={})
    except Exception as e:
        status = 1
        if isinstance(e, CliFail):
            status = e.status
            msg = e.args[0]
        else:
            msg = "An unexpected error occured."
            formatter.show_trace = True
        logger.exception(msg)
        sys.exit(status)


if __name__ == "__main__":
    main()
