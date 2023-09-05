from collections import OrderedDict
from collections.abc import MutableMapping

from gitbark.store import Project
from gitbark.commands.verify import Report

import functools
import click
import inspect
import sys


class BarkContextObject(MutableMapping):
    def __init__(self):
        self._objects = OrderedDict()

    def __getitem__(self, key):
        return self._objects[key]

    def __setitem__(self, key, value):
        self._objects[key] = value

    def __delitem__(self, key):
        del self._objects[key]

    def __len__(self):
        return len(self._objects)

    def __iter__(self):
        return iter(self._objects)


class CliFail(Exception):
    def __init__(self, message, status=1):
        super().__init__(message)
        self.status = status


def click_prompt(prompt, err=True, **kwargs):
    """Replacement for click.prompt to better work when piping
    input to the command.

    Note that we change the default of err to be True, since
    that's how we typically use it.
    """
    # logger.debug(f"Input requested ({prompt})")
    if not sys.stdin.isatty():  # Piped from stdin, see if there is data
        # logger.debug("TTY detected, reading line from stdin...")
        line = sys.stdin.readline()
        if line:
            return line.rstrip("\n")
        # logger.debug("No data available on stdin")

    # No piped data, use standard prompt
    # logger.debug("Using interactive prompt...")
    return click.prompt(prompt, err=err, **kwargs)


def click_callback(invoke_on_missing=False):
    def wrap(f):
        @functools.wraps(f)
        def inner(ctx, param, val):
            if not invoke_on_missing and not param.required and val is None:
                return None
            try:
                return f(ctx, param, val)
            except ValueError as e:
                ctx.fail(f'Invalid value for "{param.name}": {str(e)}')

        return inner

    return wrap


def options_from_class(cls):
    def decorator(f):
        for par in inspect.signature(cls.main).parameters.values():
            if par.name not in ["self"]:
                click.option("--" + par.name, required=True, type=par.annotation)(f)
        return f

    return decorator


def verify_bootstrap(project: Project):
    repo = project.repo
    if not repo.lookup_branch("branch_rules"):
        raise CliFail('Error: The "branch_rules" branch has not been created!')


def is_local_branch(branch: str):
    return branch.startswith("refs/heads")


def handle_exit(report: Report):
    exit_status = 0
    for branch_report in report.log:
        head = branch_report.head
        branch = branch_report.branch
        if is_local_branch(branch):
            exit_status = 1
        else:
            exit_status = 2

        click.echo(f"ERROR: Commit {head.hash} on {branch} is invalid!")
        for violation in head.violations:
            click.echo("  {0} {1}".format("-", violation))
    exit(exit_status)
