from collections import OrderedDict
from collections.abc import MutableMapping

from gitbark.project import Project
from gitbark.rule import RuleViolation
from gitbark.util import cmd

from importlib.metadata import entry_points
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


class EnumChoice(click.Choice):
    """
    Use an enum's member names as the definition for a choice option.

    Enum member names MUST be all uppercase. Options are not case sensitive.
    Underscores in enum names are translated to dashes in the option choice.
    """

    def __init__(self, choices_enum, hidden=[]):
        self.choices_names = [
            v.name.replace("_", "-") for v in choices_enum if v not in hidden
        ]
        super().__init__(
            self.choices_names,
            case_sensitive=False,
        )
        self.hidden = hidden
        self.choices_enum = choices_enum

    def convert(self, value, param, ctx):
        if isinstance(value, self.choices_enum):
            return value

        try:
            # Allow aliases
            self.choices = [
                k.replace("_", "-")
                for k, v in self.choices_enum.__members__.items()
                if v not in self.hidden
            ]
            name = super().convert(value, param, ctx).replace("-", "_")
        finally:
            self.choices = self.choices_names

        return self.choices_enum[name]


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

        # Check if a project exists
        if Project.exists(toplevel):
            Project(
                toplevel
            )  # Initializing the project loads modules which can contain subcommands
    except Exception:
        return

    for ep in entry_points(group="bark_commands"):
        group.add_command(ep.load())


def is_local_branch(branch: str):
    return branch.startswith("refs/heads")


def is_remote_branch(branch: str):
    return branch.startswith("refs/remotes")


def restore_incoming_changes():
    try:
        cmd("git", "restore", "--staged", ".")
        cmd("git", "restore", ".")
    except Exception:
        pass


def pp_violation(violation: RuleViolation, indent: int = 0) -> None:
    if indent:
        click.echo(("  " * (indent - 1)) + " - " + violation.message)
    else:
        click.echo(violation.message)
    for sub in violation.sub_violations:
        pp_violation(sub, indent + 1)
