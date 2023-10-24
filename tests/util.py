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

from gitbark.util import cmd
from gitbark.objects import BarkRules
from gitbark.commands.install import make_executable
from gitbark.core import BARK_RULES, BARK_RULES_BRANCH
from gitbark.git import Commit, BARK_CONFIG, COMMIT_RULES

from typing import Optional
from pygit2 import Repository
from dataclasses import asdict
from contextlib import contextmanager

import random
import string
import shutil
import yaml
import os


def get_test_bark_module():
    cwd = os.getcwd()
    return os.path.join(cwd, "tests", "test_bark_module")


def random_string(length: int = 10):
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for _ in range(length))


class Repo:
    def __init__(self, repo_dir: str, remote_dir: str) -> None:
        self.repo_dir = repo_dir
        if not os.path.exists(self.repo_dir):
            os.mkdir(self.repo_dir)

        self.initialize_git()
        self.set_git_user()
        self.add_remote(remote_dir)
        self._repo = Repository(self.repo_dir)

    @property
    def head(self) -> str:
        return str(self._repo.head.target)

    def initialize_git(self) -> None:
        cmd("git", "init", cwd=self.repo_dir)
        cmd(
            "git", "checkout", "-b", "main", cwd=self.repo_dir
        )  # make init independent of Git version

    def set_git_user(self, name: str = "Test", email: str = "test@test.com") -> None:
        cmd("git", "config", "user.email", email, cwd=self.repo_dir)
        cmd("git", "config", "user.name", name, cwd=self.repo_dir)

    def add_remote(self, remote_dir: str) -> None:
        cmd("git", "remote", "add", "origin", remote_dir, cwd=self.repo_dir)

    def commit(self, message: str = "Default msg.", amend: bool = False) -> Commit:
        cmd("git", "add", ".", cwd=self.repo_dir)
        if amend:
            cmd(
                "git",
                "commit",
                "--amend",
                "--allow-empty",
                "-m",
                message,
                "--no-gpg-sign",
                check=True,
                cwd=self.repo_dir,
            )
        else:
            cmd(
                "git",
                "commit",
                "--allow-empty",
                "-m",
                message,
                "--no-gpg-sign",
                check=True,
                cwd=self.repo_dir,
            )

        return Commit(hash=self._repo.head.target, repo=self._repo)

    def revert(self, rev: str, branch: Optional[str] = None) -> None:
        curr_branch = cmd("git", "symbolic-ref", "--short", "HEAD", cwd=self.repo_dir)[
            0
        ]
        if branch:
            self.checkout(branch)
        cmd("git", "reset", "--hard", rev, check=True, cwd=self.repo_dir)
        self.checkout(curr_branch)

    def checkout(self, branch: str, orphan: bool = False) -> None:
        if not self._repo.lookup_branch(branch):
            if orphan:
                cmd("git", "checkout", "--orphan", branch, cwd=self.repo_dir)
            else:
                cmd("git", "checkout", "-b", branch, cwd=self.repo_dir)
        else:
            cmd("git", "checkout", branch, cwd=self.repo_dir)

    def _add_bark_files(self, file: str, content: str) -> None:
        bark_folder = f"{self.repo_dir}/{BARK_CONFIG}"
        if not os.path.exists(bark_folder):
            os.mkdir(bark_folder)

        with open(file, "w") as f:
            f.write(content)

    def add_bark_rules(self, bark_rules: BarkRules) -> None:
        curr_branch = cmd("git", "symbolic-ref", "--short", "HEAD", cwd=self.repo_dir)[
            0
        ]
        self.checkout(BARK_RULES_BRANCH, orphan=True)
        self._add_bark_files(
            file=f"{self.repo_dir}/{BARK_RULES}",
            content=yaml.safe_dump(asdict(bark_rules), sort_keys=False),
        )
        self.commit("Add bark rules.")
        self.checkout(curr_branch)

    def add_commit_rules(
        self, commit_rules: dict, branch: Optional[str] = None
    ) -> None:
        curr_branch = cmd("git", "symbolic-ref", "--short", "HEAD", cwd=self.repo_dir)[
            0
        ]
        if branch and branch != curr_branch:
            self.checkout(branch)
        self._add_bark_files(
            file=f"{self.repo_dir}/{COMMIT_RULES}",
            content=yaml.safe_dump(commit_rules, sort_keys=False),
        )
        self.commit("Add commit rules.")
        self.checkout(curr_branch)


@contextmanager
def disable_bark(repo: Repo):
    hook_path = os.path.join(repo.repo_dir, ".git", "hooks", "reference-transaction")
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
            make_executable(hook_path)


class Environment:
    def __init__(self) -> None:
        self.env_dir = f"{os.getcwd()}/{random_string()}"
        if not os.path.exists(self.env_dir):
            os.mkdir(self.env_dir)

        self._add_remote()
        self.repo = Repo(f"{self.env_dir}/{random_string()}-local", self.remote_dir)

    def _add_remote(self):
        self.remote_dir = f"{self.env_dir}/{random_string()}"
        if not os.path.exists(self.remote_dir):
            os.mkdir(self.remote_dir)
        cmd("git", "init", "--bare", cwd=self.remote_dir)  # initialize remote

    def clean(self):
        shutil.rmtree(self.env_dir)
