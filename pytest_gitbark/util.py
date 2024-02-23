from gitbark.util import cmd
from gitbark.core import BARK_RULES, BARK_RULES_BRANCH, BARK_REQUIREMENTS
from gitbark.git import BARK_CONFIG, COMMIT_RULES, Repository

from typing import Callable, Optional
from dataclasses import asdict
from contextlib import contextmanager

import os
import shutil
import stat
import yaml
import pytest

MAIN_BRANCH = "main"


def write_bark_file(repo: Repository, file: str, content: str) -> None:
    """Write and stage a bark file."""
    bark_folder = f"{repo._path}/{BARK_CONFIG}"
    if not os.path.exists(bark_folder):
        os.mkdir(bark_folder)

    with open(file, "w") as f:
        f.write(content)

    cmd("git", "add", file, cwd=repo._path)


def write_bark_rules(
    repo: Repository, bark_rules: dict, requirements: Optional[str] = None
) -> None:
    """Write and stage bark rules."""
    write_bark_file(
        repo=repo,
        file=f"{repo._path}/{BARK_RULES}",
        content=yaml.safe_dump(asdict(bark_rules), sort_keys=False),
    )
    if requirements:
        write_bark_file(
            repo=repo,
            file=f"{repo._path}/{BARK_REQUIREMENTS}",
            content=requirements,
        )


def write_commit_rules(repo: Repository, commit_rules: dict) -> None:
    """Write and stage commit rules."""
    write_bark_file(
        repo=repo,
        file=f"{repo._path}/{COMMIT_RULES}",
        content=yaml.safe_dump(commit_rules, sort_keys=False),
    )


def dump(repo: Repository, dump_path: str) -> None:
    shutil.copytree(repo._path, dump_path, dirs_exist_ok=True)


def restore_from_dump(repo: Repository, dump_path: str) -> None:
    # Recreating the folders to ensure all files and folders are copied.
    shutil.rmtree(repo._path)
    shutil.copytree(dump_path, repo._path)


@contextmanager
def on_branch(repo: Repository, branch: str, orhpan: bool = False):
    curr_branch = repo.branch
    if branch not in repo.branches:
        if orhpan:
            cmd("git", "checkout", "--orphan", branch, cwd=repo._path)
        else:
            cmd("git", "checkout", "-b", branch, cwd=repo._path)
    else:
        cmd("git", "checkout", branch, cwd=repo._path)
    try:
        yield
    finally:
        if curr_branch:
            cmd("git", "checkout", curr_branch, cwd=repo._path)


@contextmanager
def uninstall_hooks(repo: Repository):
    hook_path = os.path.join(repo._path, ".git", "hooks", "reference-transaction")
    hook_content = None
    if os.path.exists(hook_path):
        with open(hook_path, "r") as f:
            hook_content = f.read()
        os.remove(hook_path)
    try:
        yield repo
    finally:
        if hook_content:
            with open(hook_path, "w") as f:
                f.write(hook_content)

            # Update permissions
            current_permissions = os.stat(hook_path).st_mode
            new_permissions = (
                current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )
            os.chmod(hook_path, new_permissions)


@contextmanager
def on_dir(dir: str):
    curr_dir = os.getcwd()
    os.chdir(dir)
    try:
        yield
    finally:
        os.chdir(curr_dir)


def verify_rules(
    repo: Repository,
    passes: bool,
    action: Callable[[Repository], None],
    commit_rules: Optional[dict] = None,
    bark_rules: Optional[dict] = None,
) -> None:

    if commit_rules:
        write_commit_rules(repo, commit_rules)
        cmd("git", "commit", "-m", "Add commit rules", cwd=repo._path)

    if bark_rules:
        with on_branch(repo, BARK_RULES_BRANCH, True):
            write_bark_rules(repo, bark_rules)
            cmd("git", "commit", "-m", "Add bark rules", cwd=repo._path)

    verify_action(repo, passes, action)


def verify_action(
    repo: Repository, passes: bool, action: Callable[[Repository], None]
) -> None:
    curr_head = repo.head

    if passes:
        action(repo)
    else:
        with pytest.raises(Exception):
            action(repo)

    post_head = repo.head

    if passes:
        assert curr_head != post_head
    else:
        assert curr_head == post_head
