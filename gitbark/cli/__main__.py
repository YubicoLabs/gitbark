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
from gitbark.commands.install import install as install_cmd
from gitbark.commands.setup import (
    setup as setup_cmd,
    add_modules_interactive,
    add_branches_interactive,
    add_commit_rules_interactive,
    _confirm_commit,
    checkout_or_orphan,
)

from gitbark.core import BARK_RULES_REF
from gitbark.project import Project
from gitbark.rule import RuleViolation
from gitbark.util import cmd
from gitbark.git import Commit, BRANCH_REF_PREFIX, TAG_REF_PREFIX
from gitbark.logging import init_logging, LOG_LEVEL
from .util import (
    BarkContextObject,
    click_callback,
    CliFail,
    EnumChoice,
    pp_violation,
    get_root,
    _add_subcommands,
)

import click
import logging
import subprocess
import sys
import os

logger = logging.getLogger(__name__)


def ensure_bootstrap_verified(project: Project) -> None:
    root_hash = cmd("git", "rev-list", "--max-parents=0", BARK_RULES_REF)[0]
    root = Commit(bytes.fromhex(root_hash), project.repo)
    if project.bootstrap:
        if project.bootstrap != root:
            raise CliFail(
                "WARNING! The previously trusted bootstrap commit has CHANGED!"
            )
    else:
        click.echo(
            f"The bootstrap commit ({root_hash}) of the bark_rules "
            "branch has not been verified!"
        )
        click.confirm(
            "Do you want to trust this commit as the bootstrap for bark?",
            abort=True,
            err=True,
        )
        project.bootstrap = root


def format_ref(ref: str) -> str:
    if ref.startswith(BRANCH_REF_PREFIX):
        return f"branch {ref[len(BRANCH_REF_PREFIX) :]}"
    if ref.startswith(TAG_REF_PREFIX):
        return f"tag {ref[len(TAG_REF_PREFIX) :]}"
    return ref


@click.group()
@click.pass_context
@click.option(
    "-l",
    "--log-level",
    default=None,
    type=EnumChoice(LOG_LEVEL, hidden=[LOG_LEVEL.NOTSET]),
    help="enable logging at given verbosity level",
)
@click.option(
    "--log-file",
    default=None,
    type=str,
    metavar="FILE",
    help="write log to FILE instead of printing to stderr (requires --log-level)",
)
def cli(ctx, log_level, log_file):
    ctx.obj = BarkContextObject()

    if log_level:
        init_logging(log_level, log_file=log_file)
    elif log_file:
        ctx.fail("--log-file requires specifying --log-level.")

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
        commit_message="Modify commit rules (made by bark)",
        manual_action=(
            "The 'commit_rules.yaml' file has been staged. "
            "Please commit the changes!"
        ),
    )
    logger.info("Commit rules added successfully")


@cli.command()
@click.pass_context
def add_modules(ctx):
    """Add bark modules."""
    project = ctx.obj["project"]
    branch = project.repo.branch
    add_modules_interactive(project)
    _confirm_commit(
        commit_message="Modify bark modules (made by bark)",
        manual_action=(
            "The 'bark_rules.yaml' file has been staged. Please commit the changes!"
        ),
    )
    checkout_or_orphan(project, branch)
    logger.info("Bark modules added successfully")


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
        commit_message="Modify bark modules (made by bark)",
        manual_action=(
            "The 'bark_rules.yaml' file has been staged. Please commit the changes!"
        ),
    )
    checkout_or_orphan(project, branch)
    logger.info(f"'{branch}' added to 'bark_rules'")


@cli.command()
@click.pass_context
def install(ctx):
    """
    Install hooks.

    Install GitBark in Git hooks, so that verification is performed automatically
    on repository changes.
    """
    project = ctx.obj["project"]

    repo = project.repo
    if BARK_RULES_REF not in repo.references:
        raise CliFail('The "bark_rules" branch has not been created!')

    ensure_bootstrap_verified(project)

    try:
        install_cmd(project)
        logger.info("Hooks installed successfully")
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

    if old == new or ref not in project.repo.references:
        # Not a change of a "real" ref
        return

    if new == "00" * 20:
        # Ref deletion
        return

    head = Commit(bytes.fromhex(new), project.repo)
    fail_head = os.path.join(project.bark_directory, "FAIL_HEAD")
    try:
        verify_ref_update(project, ref, head)
        if os.path.exists(fail_head):
            os.remove(fail_head)
        # TODO: Need to enable logging through env variable
        logger.info(f"{ref} is valid")
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
    help="Verify all refs.",
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
    Verify repository or ref.

    \b
    TARGET the commit or ref to verify.
    """
    project = ctx.obj["project"]
    ensure_bootstrap_verified(project)

    try:
        if all:
            verify_all(project)
            logger.info("All references are valid")
        else:
            head, ref = project.repo.resolve(target)
            if ref:
                verify_ref(project, ref, head)
                logger.info(f"{ref} is valid")
            elif not bootstrap:
                raise CliFail(
                    "Verifying a single commit requires specifying a bootstrap with -b"
                )
            else:
                verify_commit(project, head, bootstrap)
                logger.info(f"Commit {head.hash.hex()} is valid")
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


class _ClickHandler(logging.Handler):
    def emit(self, record) -> None:
        click.echo(record.getMessage())


def main():
    handler = _ClickHandler()
    formatter = _DefaultFormatter()
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)
    try:
        _add_subcommands(cli)
        cli(obj={})
    except Exception as e:
        status = 1
        if isinstance(e, CliFail):
            status = e.status
            msg = e.args[0]
        elif isinstance(e, subprocess.CalledProcessError):
            status = e.returncode
            msg = e.stderr.strip()
        else:
            msg = "An unexpected error occured."
            formatter.show_trace = True
        logger.exception(msg)
        sys.exit(status)


if __name__ == "__main__":
    main()
