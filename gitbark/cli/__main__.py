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
from gitbark.commands.prepare_merge_msg import (
    prepare_merge_msg as prepare_merge_msg_cmd,
)
from gitbark.commands.setup import (
    setup as setup_cmd,
    add_modules_interactive,
    add_branches_interactive,
    add_rules_interactive,
    _confirm_commit,
    checkout_or_orphan,
)

from gitbark.core import BARK_RULES_BRANCH
from gitbark.project import Project
from gitbark.rule import RuleViolation
from gitbark.util import cmd
from gitbark.git import Commit, ReferenceUpdate
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
from pygit2 import Branch

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
    add_rules_interactive(project)
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
    curr_branch = cmd("git", "symbolic-ref", "--short", "HEAD")[0]
    add_modules_interactive(project)
    _confirm_commit(
        commit_message="Modify bark modules (made by bark).",
        manual_action=(
            "The 'bark_rules.yaml' file has been staged. " "Please commit the changes!"
        ),
    )
    checkout_or_orphan(project, curr_branch)
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
    curr_branch = cmd("git", "symbolic-ref", "--short", "HEAD")[0]
    add_branches_interactive(project, curr_branch)
    _confirm_commit(
        commit_message="Modify bark modules (made by bark).",
        manual_action=(
            "The 'bark_rules.yaml' file has been staged. " "Please commit the changes!"
        ),
    )
    checkout_or_orphan(project, curr_branch)
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
    if not repo.lookup_branch(BARK_RULES_BRANCH):
        raise CliFail('Error: The "bark_rules" branch has not been created!')

    root_commit = cmd("git", "rev-list", "--max-parents=0", BARK_RULES_BRANCH)[0]
    if root_commit != project.bootstrap:
        click.echo(
            f"The bootstrap commit ({root_commit}) of the branch_rules "
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
def click_parse_commit_or_branch(ctx, param, val):
    project = ctx.obj["project"]

    try:
        commit, ref = project.repo.resolve_refish(val)
        if commit and not ref:  # val is commit
            return commit
        else:
            return project.repo.branches[ref.shorthand]  # val is a branch

    except KeyError:
        raise CliFail(f"{val} is not a valid commit or branch!")


@click_callback()
def click_parse_bootstrap(ctx, param, val):
    project = ctx.obj["project"]
    if val:
        return Commit(val, project.repo)
    return None


@click_callback()
def click_parse_ref_update(ctx, param, val):
    old_ref, new_ref, ref_name = val
    return ReferenceUpdate(old_ref, new_ref, ref_name)


@cli.command()
@click.pass_context
@click.argument("target", callback=click_parse_commit_or_branch, default="HEAD")
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
@click.option(
    "-r",
    "--ref-update",
    type=(str, str, str),
    hidden=True,
    callback=click_parse_ref_update,
)
def verify(ctx, target, all, bootstrap, ref_update):
    """
    Verify repository or branch.

    \b
    TARGET the commit or branch to verify.
    """

    project = ctx.obj["project"]
    if not is_installed(project):
        raise CliFail("Bark is not installed! Run 'bark install' first!")

    branch = None
    if ref_update:
        if ref_update.ref_name in project.repo.references:
            branch = project.repo.references[ref_update.ref_name].shorthand
            head = Commit(ref_update.new_ref, project.repo)
        else:
            return
    elif isinstance(target, Branch):
        branch = target.shorthand
        head = Commit(target.target, project.repo)
    else:
        if not bootstrap:
            ctx.fail(
                "verifying a single commit requires specifying a bootstrap with -b"
            )
        head = Commit(target.id, project.repo)

    try:
        verify_cmd(project, branch, head, bootstrap, all)
        if all:
            click.echo("Repository is in valid state!")
        elif not ref_update:
            click.echo(f"{branch} is in a valid state!")
    except RuleViolation as e:
        # TODO: Error message here?
        pp_violation(e)
        sys.exit(1)
    finally:
        project.update()


@cli.command(hidden=True)
@click.pass_context
@click.argument("commit_msg_file")
def prepare_merge_msg(ctx, commit_msg_file):
    """Run merge hooks."""

    project = ctx.obj["project"]
    repo = project.repo

    head = Commit(repo.head.target, repo)

    prepare_merge_msg_cmd(head, project, commit_msg_file)


class _DefaultFormatter(logging.Formatter):
    def __init__(self, show_trace=False):
        self.show_trace = show_trace

    def format(self, record):
        message = f"{record.levelname}: {record.getMessage()}"
        if self.show_trace and record.exc_info:
            message += self.formatException(record.exc_info)
        return message


def should_add_subcommands(argv: list[str]) -> bool:
    if len(argv) > 1:
        cmd = argv[1]
        if cmd in ["verify", "install"]:
            return False
        else:
            return True
    return True


def main():
    handler = logging.StreamHandler()
    handler.setLevel(logging.WARNING)
    formatter = _DefaultFormatter()
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    try:
        if should_add_subcommands(sys.argv):
            _add_subcommands(cli)
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
