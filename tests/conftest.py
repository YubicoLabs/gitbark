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

from gitbark.objects import BarkRules
from gitbark.core import BARK_RULES_BRANCH
from gitbark.util import cmd
from gitbark.git import Repository

from pytest_gitbark.util import (
    write_bark_rules,
    write_bark_file,
    write_commit_rules,
    dump,
    restore_from_dump,
    on_branch,
    on_dir,
    uninstall_hooks,
)

import pytest
import os


@pytest.fixture(autouse=True, scope="session")
def test_bark_module():
    cwd = os.getcwd()
    return os.path.join(cwd, "tests", "test_bark_module")


@pytest.fixture(scope="session")
def repo_initialized_dump(
    repo_dump: tuple[Repository, str], tmp_path_factory, test_bark_module
):
    repo, _ = repo_dump

    cmd("git", "commit", "-m", "Initial commit", "--allow-empty", cwd=repo._path)

    bootstrap_main = repo.head

    branch_rule = {
        "bootstrap": bootstrap_main.hash.hex(),
        "refs": [{"pattern": "refs/heads/main"}],
    }
    bark_rules = BarkRules([], project=[branch_rule])
    with on_branch(repo, BARK_RULES_BRANCH, True):
        write_bark_rules(repo, bark_rules, test_bark_module)
        cmd("git", "commit", "-m", "Add initial bark rules", cwd=repo._path)

    dump_path = tmp_path_factory.mktemp("dump")
    dump(repo, dump_path)
    return repo, dump_path


@pytest.fixture(scope="session")
def repo_installed_dump(
    repo_initialized_dump: tuple[Repository, str], tmp_path_factory, bark_cli
):
    repo, _ = repo_initialized_dump

    with on_dir(repo._path):
        bark_cli("install", input="y")

    dump_path = tmp_path_factory.mktemp("dump")
    dump(repo, dump_path)
    return repo, dump_path


@pytest.fixture(scope="session")
def repo_bark_rules_invalid_dump(
    repo_installed_dump: tuple[Repository, str], tmp_path_factory
):
    repo, _ = repo_installed_dump

    always_fail_rule = {"rules": [{"always_fail": None}]}
    with on_branch(repo, BARK_RULES_BRANCH, True):
        write_commit_rules(repo, always_fail_rule)
        cmd("git", "commit", "-m", "Invalid bark rules", cwd=repo._path)
        with uninstall_hooks(repo):
            cmd("git", "commit", "-m", "Invalid", "--allow-empty", cwd=repo._path)

    dump_path = tmp_path_factory.mktemp("dump")
    dump(repo, dump_path)
    return repo, dump_path


@pytest.fixture(scope="function")
def repo_initialized(repo_initialized_dump: tuple[Repository, str]):
    repo, dump_path = repo_initialized_dump
    restore_from_dump(repo, dump_path)
    return repo


@pytest.fixture(scope="function")
def repo_installed(repo_installed_dump: tuple[Repository, str]):
    repo, dump_path = repo_installed_dump
    restore_from_dump(repo, dump_path)
    return repo


@pytest.fixture(scope="function")
def repo_bark_rules_invalid(repo_bark_rules_invalid_dump: tuple[Repository, str]):
    repo, dump_path = repo_bark_rules_invalid_dump
    restore_from_dump(repo, dump_path)
    return repo
