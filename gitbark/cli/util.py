from collections import OrderedDict
from collections.abc import MutableMapping

from gitbark.core import get_bark_rules
from gitbark.project import Project
from gitbark.commands.verify import Report
from gitbark.commands.install import is_installed
from gitbark.util import cmd
from gitbark import globals


from pkg_resources import EntryPoint
import functools
import click
import sys
import os


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

def get_root() -> str:
    try:
        root = os.path.abspath(cmd("git", "rev-parse", "--show-toplevel")[0])
    except Exception:
        raise CliFail(
            "Failed to find Git repository! Make sure "
            "you are not inside the .git directory."
        )
    
    return root

def _add_subcommands(group: click.Group):
    try:
        toplevel = get_root()
        project = Project(toplevel)
        if not is_installed(project):
            return
    except:
        return
    globals.init(toplevel)
    bark_rules = get_bark_rules(project)
    subcommand_entrypoints = project.get_subcommand_entrypoints(bark_rules)
    for entrypoint in subcommand_entrypoints:
        try:
            ep_string = f"x={entrypoint}"
            ep = EntryPoint.parse(ep_string)
            group.add_command(ep.resolve())
        except Exception as e:
            raise e
        
            
def verify_bootstrap(project: Project):
    repo = project.repo
    if not repo.lookup_branch("branch_rules"):
        raise CliFail('Error: The "branch_rules" branch has not been created!')

def is_local_branch(branch: str):
    return branch.startswith("refs/heads")

def restore_incoming_changes():
    try:
        cmd("git", "restore", "--staged", ".")
        cmd("git", "restore", ".")
    except:
        pass
    

def handle_exit(report: Report):
    exit_status = 0
    for branch_report in report.log:
        head = branch_report.head
        branch = branch_report.branch
        error_type = "WARNING"
        if is_local_branch(branch):
            exit_status = 1
            error_type = "ERROR"
            restore_incoming_changes()
        click.echo(f"{error_type}: Commit {head.hash} on {branch} is invalid!")
        for violation in head.violations:
            click.echo("  {0} {1}".format("-", violation))
    exit(exit_status)
