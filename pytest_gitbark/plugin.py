from gitbark.cli.__main__ import cli, _DefaultFormatter
from gitbark.cli.util import CliFail, _add_subcommands
from gitbark.git import Repository
from gitbark.util import cmd

from .util import dump, restore_from_dump, MAIN_BRANCH

from click.testing import CliRunner

import logging
import pytest


@pytest.fixture(scope="session")
def bark_cli():
    return _bark_cli


def _bark_cli(*argv, **kwargs):
    handler = logging.StreamHandler()
    handler.setLevel(logging.WARNING)
    handler.setFormatter(_DefaultFormatter())
    logging.getLogger().addHandler(handler)

    runner = CliRunner(mix_stderr=True)
    _add_subcommands(cli)
    result = runner.invoke(cli, argv, obj={}, **kwargs)
    if result.exit_code != 0:
        if isinstance(result.exception, CliFail):
            raise SystemExit()
        raise result.exception
    return result


@pytest.fixture(scope="session")
def repo_dump(tmp_path_factory):
    repo_path = tmp_path_factory.mktemp("repo")
    dump_path = tmp_path_factory.mktemp("dump")

    # Init repo
    cmd("git", "init", cwd=repo_path)
    cmd("git", "checkout", "-b", MAIN_BRANCH, cwd=repo_path)

    repo = Repository(repo_path)

    # Init config
    cmd("git", "config", "commit.gpgsign", "false", cwd=repo._path)
    cmd("git", "config", "user.name", "Test", cwd=repo._path)
    cmd("git", "config", "user.email", "test@test.com", cwd=repo._path)

    dump(repo, dump_path)
    return repo, dump_path


@pytest.fixture(scope="function")
def repo(repo_dump: tuple[Repository, str]):
    repo, dump_path = repo_dump
    restore_from_dump(repo, dump_path)
    return repo
