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

import pytest
from .utils.util import Environment, User, KeyType
from gitbark.commands.install import install
import sys
from io import StringIO
from contextlib import contextmanager
import os

from click.testing import CliRunner
from gitbark._cli.__main__ import cli
from gitbark import globals


@contextmanager
def replace_stdin(target):
    orig = sys.stdin
    sys.stdin = target
    yield
    sys.stdin = orig


@pytest.fixture(scope="session")
def bark_cli():
    return _bark_cli


def _bark_cli(*args):
    runner = CliRunner()
    result = runner.invoke(cli, args)
    return result


@pytest.fixture(scope="session")
def users():
    alice = User("Alice", "alice@test.com", "7DD61D90C0FC215E",
                 f"{os.getcwd()}/tests/utils/ssh/.ssh/alice.ssh")
    bob = User("Bob", "bob@test.com", "3504E1A6A48F7C8E",
               f"{os.getcwd()}/tests/utils/ssh/.ssh/bob.ssh")
    eve = User("Eve", "eve@test.com", "3D3986BB3558EE24",
               f"{os.getcwd()}/tests/utils/ssh/.ssh/eve.ssh")

    return [alice, bob, eve]


@pytest.fixture(scope="session")
def env_signed_commits(users: list[User]):
    env_signed_commits = Environment("env_signed_commits", users)
    os.environ["TEST_WD"] = env_signed_commits.local.wd
    os.environ["GNUPGHOME"] = f"{os.getcwd()}/tests/utils/gpg/.gnupg"

    env_signed_commits.remote.initialize_git()

    env_signed_commits.local.initialize_git()
    env_signed_commits.local.configure_git_user(env_signed_commits.users["Alice"].name,
                                                env_signed_commits.users["Alice"].email)
    env_signed_commits.local.cmd(
        "git", "remote", "add", "origin", env_signed_commits.remote.wd)

    env_signed_commits.external.initialize_git()
    env_signed_commits.external.configure_git_user(env_signed_commits.users["Eve"].name,
                                                   env_signed_commits.users["Eve"].email)
    env_signed_commits.external.cmd(
        "git", "remote", "add", "origin", env_signed_commits.remote.wd)

    commit_rules_main = {
        "rules": [
            {"rule": "require_signature", "allowed_keys": "(Alice|Bob).asc"},
            {"any": [
                {"rule": "file_not_modified", "pattern": "config.json"},
                {"rule": "require_signature", "allowed_keys": "Bob.asc"}
            ]
            }
        ]
    }
    pubkeys_main = ["Alice.asc", "Bob.asc"]
    alice_key = env_signed_commits.users["Alice"].gpg_key_id
    env_signed_commits.local.initialize_commit_rules_on_branch(
        commit_rules_main, pubkeys_main, gpg_signing_key=alice_key, key_type=KeyType.GPG)

    commit_rules_branch_rules = {
        "rules": [
            {"rule": "require_signature", "allowed_keys": "(Alice|Bob).asc"}
        ]
    }
    branch_rules = {
        "branches": [
            {"pattern": "main", "validate_from": env_signed_commits.local.get_head(),
             "allow_force_push": False}
        ]
    }
    env_signed_commits.local.initialize_branch_rules(
        commit_rules_branch_rules, branch_rules, pubkeys_main, gpg_signing_key=alice_key, key_type=KeyType.GPG)

    globals.init()

    with replace_stdin(StringIO("yes")):
        install()

    env_signed_commits.local.cmd("git", "push", "origin", "main")
    env_signed_commits.local.cmd(
        "git", "branch", "--set-upstream-to=origin/main", "main")
    env_signed_commits.external.cmd("git", "pull", "origin", "main")
    yield env_signed_commits
    env_signed_commits.clean()


@pytest.fixture(scope="session")
def env_commit_approvals(users: list[User]):
    env_commit_approvals = Environment("env_commit_approvals", users)
    os.environ["TEST_WD"] = env_commit_approvals.local.wd
    os.environ["GNUPGHOME"] = f"{os.getcwd()}/tests/utils/gpg/.gnupg"

    env_commit_approvals.remote.initialize_git()

    env_commit_approvals.local.initialize_git()
    env_commit_approvals.local.configure_git_user(env_commit_approvals.users["Alice"].name,
                                                  env_commit_approvals.users["Alice"].email)
    env_commit_approvals.local.cmd(
        "git", "remote", "add", "origin", env_commit_approvals.remote.wd)

    env_commit_approvals.external.initialize_git()
    env_commit_approvals.external.configure_git_user(env_commit_approvals.users["Eve"].name,
                                                     env_commit_approvals.users["Eve"].email)
    env_commit_approvals.external.cmd(
        "git", "remote", "add", "origin", env_commit_approvals.remote.wd)

    commit_rules_main = {
        "rules": [
            {"rule": "require_signature", "allowed_keys": "(Alice|Bob).asc"},
            {"rule": "require_approval",
                "allowed_keys": "(Alice|Bob).asc", "threshold": 2},
            {"rule": "disallow_invalid_parents",
                "exception": "parent_hash_in_merge_message"}
        ]
    }
    pubkeys_main = ["Alice.asc", "Bob.asc"]
    alice_key = env_commit_approvals.users["Alice"].gpg_key_id
    env_commit_approvals.local.initialize_commit_rules_on_branch(
        commit_rules_main, pubkeys_main, gpg_signing_key=alice_key, key_type=KeyType.GPG)

    commit_rules_branch_rules = {
        "rules": [
            {"rule": "require_signature", "allowed_keys": "(Alice|Bob).asc"}
        ]
    }
    branch_rules = {
        "branches": [
            {"pattern": "main", "validate_from": env_commit_approvals.local.get_head(),
             "allow_force_push": False}
        ]
    }
    env_commit_approvals.local.initialize_branch_rules(
        commit_rules_branch_rules, branch_rules, pubkeys_main, gpg_signing_key=alice_key, key_type=KeyType.GPG)

    globals.init()

    with replace_stdin(StringIO("yes")):
        install()

    env_commit_approvals.local.cmd("git", "push", "origin", "main")
    env_commit_approvals.local.cmd(
        "git", "branch", "--set-upstream-to=origin/main", "main")
    env_commit_approvals.external.cmd("git", "pull", "origin", "main")
    yield env_commit_approvals
    env_commit_approvals.clean()


@pytest.fixture(scope="session")
def env_signed_commits_ssh(users: list[User]):
    env_signed_commits_ssh = Environment("env_signed_commits_ssh", users)

    os.environ["TEST_WD"] = env_signed_commits_ssh.local.wd
    os.environ["GNUPGHOME"] = f"{os.getcwd()}/tests/utils/gpg/.gnupg"

    env_signed_commits_ssh.remote.initialize_git()

    env_signed_commits_ssh.local.initialize_git()
    env_signed_commits_ssh.local.configure_git_user(env_signed_commits_ssh.users["Alice"].name,
                                          env_signed_commits_ssh.users["Alice"].email)
    env_signed_commits_ssh.local.cmd("git", "remote", "add",
                           "origin", env_signed_commits_ssh.remote.wd)
    env_signed_commits_ssh.local.configure_ssh_signing(
        env_signed_commits_ssh.users["Alice"].ssh_key_path)

    env_signed_commits_ssh.external.initialize_git()
    env_signed_commits_ssh.external.configure_git_user(env_signed_commits_ssh.users["Eve"].name,
                                             env_signed_commits_ssh.users["Eve"].email)
    env_signed_commits_ssh.external.cmd("git", "remote", "add",
                              "origin", env_signed_commits_ssh.remote.wd)
    env_signed_commits_ssh.external.configure_ssh_signing(
        env_signed_commits_ssh.users["Eve"].ssh_key_path)

    commit_rules_main = {
        "rules": [
            {"rule": "require_signature",
                "allowed_keys": "(alice.ssh|bob.ssh).pub"},
            {"any": [
                {"rule": "file_not_modified", "pattern": "config.json"},
                {"rule": "require_signature", "allowed_keys": "bob.ssh.pub"}
            ]
            }
        ]
    }
    pubkeys_main = ["alice.ssh.pub", "bob.ssh.pub"]
    alice_key_path = env_signed_commits_ssh.users["Alice"].ssh_key_path
    env_signed_commits_ssh.local.initialize_commit_rules_on_branch(
        commit_rules_main, pubkeys_main, ssh_key_path=alice_key_path, key_type=KeyType.SSH)

    commit_rules_branch_rules = {
        "rules": [
            {"rule": "require_signature",
                "allowed_keys": "(alice.ssh|bob.ssh).pub"}
        ]
    }
    branch_rules = {
        "branches": [
            {"pattern": "main", "validate_from": env_signed_commits_ssh.local.get_head(),
             "allow_force_push": False}
        ]
    }
    env_signed_commits_ssh.local.initialize_branch_rules(
        commit_rules_branch_rules, branch_rules, pubkeys_main, ssh_key_path=alice_key_path, key_type=KeyType.SSH)

    globals.init()

    with replace_stdin(StringIO("yes")):
        install()

    env_signed_commits_ssh.local.cmd("git", "push", "origin", "main")
    env_signed_commits_ssh.local.cmd("git", "branch", "--set-upstream-to=origin/main", "main")
    env_signed_commits_ssh.external.cmd("git", "pull", "origin", "main")
    yield env_signed_commits_ssh
    env_signed_commits_ssh.clean()

@pytest.fixture(scope="session")
def env_commit_approvals_ssh(users: list[User]):
    env_commit_approvals_ssh = Environment("env_commit_approvals_ssh", users)
    os.environ["TEST_WD"] = env_commit_approvals_ssh.local.wd
    os.environ["GNUPGHOME"] = f"{os.getcwd()}/tests/utils/gpg/.gnupg"

    env_commit_approvals_ssh.remote.initialize_git()

    env_commit_approvals_ssh.local.initialize_git()
    env_commit_approvals_ssh.local.configure_git_user(env_commit_approvals_ssh.users["Alice"].name,
                                                  env_commit_approvals_ssh.users["Alice"].email)
    env_commit_approvals_ssh.local.cmd(
        "git", "remote", "add", "origin", env_commit_approvals_ssh.remote.wd)
    env_commit_approvals_ssh.local.configure_ssh_signing(
        env_commit_approvals_ssh.users["Alice"].ssh_key_path)

    env_commit_approvals_ssh.external.initialize_git()
    env_commit_approvals_ssh.external.configure_git_user(env_commit_approvals_ssh.users["Eve"].name,
                                                     env_commit_approvals_ssh.users["Eve"].email)
    env_commit_approvals_ssh.external.cmd(
        "git", "remote", "add", "origin", env_commit_approvals_ssh.remote.wd)

    commit_rules_main = {
        "rules": [
            {"rule": "require_signature", "allowed_keys": "(alice.ssh|bob.ssh).pub"},
            {"rule": "require_approval",
                "allowed_keys": "(alice.ssh|bob.ssh).asc", "threshold": 2},
            {"rule": "disallow_invalid_parents",
                "exception": "parent_hash_in_merge_message"}
        ]
    }
    pubkeys_main = ["alice.ssh.pub", "bob.ssh.pub"]
    alice_key_path = env_commit_approvals_ssh.users["Alice"].ssh_key_path
    env_commit_approvals_ssh.local.initialize_commit_rules_on_branch(
        commit_rules_main, pubkeys_main, ssh_key_path=alice_key_path, key_type=KeyType.SSH)

    commit_rules_branch_rules = {
        "rules": [
            {"rule": "require_signature", "allowed_keys": "(Alice|Bob).asc"}
        ]
    }
    branch_rules = {
        "branches": [
            {"pattern": "main", "validate_from": env_commit_approvals_ssh.local.get_head(),
             "allow_force_push": False}
        ]
    }
    env_commit_approvals_ssh.local.initialize_branch_rules(
        commit_rules_branch_rules, branch_rules, pubkeys_main, ssh_key_path=alice_key_path, key_type=KeyType.SSH)

    globals.init()

    with replace_stdin(StringIO("yes")):
        install()

    env_commit_approvals_ssh.local.cmd("git", "push", "origin", "main")
    env_commit_approvals_ssh.local.cmd(
        "git", "branch", "--set-upstream-to=origin/main", "main")
    env_commit_approvals_ssh.external.cmd("git", "pull", "origin", "main")
    yield env_commit_approvals_ssh
    env_commit_approvals_ssh.clean()
