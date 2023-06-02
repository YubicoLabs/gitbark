import pytest
from .utils.util import Environment, Users
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
    alice = Users("Alice", "alice@test.com", "7DD61D90C0FC215E")
    bob = Users("Bob", "bob@test.com", "3504E1A6A48F7C8E")
    eve = Users("Eve", "eve@test.com", "3D3986BB3558EE24") 

    return [alice, bob, eve]

@pytest.fixture(scope="session")
def env_signed_commits(users:list[Users]):
    env_signed_commits = Environment("env_signed_commits", users)
    os.environ["TEST_WD"] = env_signed_commits.local.wd
    os.environ["GNUPGHOME"] = f"{os.getcwd()}/tests/utils/gpg/.gnupg"

    env_signed_commits.remote.initialize_git()

    env_signed_commits.local.initialize_git()
    env_signed_commits.local.configure_git_user(env_signed_commits.users["Alice"].name,
                                                 env_signed_commits.users["Alice"].email)
    env_signed_commits.local.cmd("git", "remote", "add", "origin", env_signed_commits.remote.wd)
    
    env_signed_commits.external.initialize_git()
    env_signed_commits.external.configure_git_user(env_signed_commits.users["Eve"].name,
                                                   env_signed_commits.users["Eve"].email)
    env_signed_commits.external.cmd("git", "remote", "add", "origin", env_signed_commits.remote.wd)

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
    alice_key = env_signed_commits.users["Alice"].key_id
    env_signed_commits.local.initialize_commit_rules_on_branch(commit_rules_main, pubkeys_main, alice_key)

    commit_rules_branch_rules = {
        "rules": [
            {"rule": "require_signature", "allowed_keys": "(Alice|Bob).asc"}
        ]
    }
    branch_rules = {
        "branches": [
            {"pattern": "main", "validate_from": env_signed_commits.local.get_head(), "allow_force_push": False}
        ]
    }
    env_signed_commits.local.initialize_branch_rules(commit_rules_branch_rules, branch_rules, pubkeys_main, alice_key)

    
    globals.init()

    with replace_stdin(StringIO("yes")):
        install()

    env_signed_commits.local.cmd("git", "push", "origin", "main")
    env_signed_commits.local.cmd("git", "branch", "--set-upstream-to=origin/main", "main")
    env_signed_commits.external.cmd("git", "pull", "origin", "main")
    yield env_signed_commits
    env_signed_commits.clean()

@pytest.fixture(scope="session")
def env_commit_approvals(users:list[Users]):
    env_commit_approvals = Environment("env_commit_approvals", users)
    os.environ["TEST_WD"] = env_commit_approvals.local.wd
    os.environ["GNUPGHOME"] = f"{os.getcwd()}/tests/utils/gpg/.gnupg"

    env_commit_approvals.remote.initialize_git()

    env_commit_approvals.local.initialize_git()
    env_commit_approvals.local.configure_git_user(env_commit_approvals.users["Alice"].name,
                                                 env_commit_approvals.users["Alice"].email)
    env_commit_approvals.local.cmd("git", "remote", "add", "origin", env_commit_approvals.remote.wd)
    
    env_commit_approvals.external.initialize_git()
    env_commit_approvals.external.configure_git_user(env_commit_approvals.users["Eve"].name,
                                                   env_commit_approvals.users["Eve"].email)
    env_commit_approvals.external.cmd("git", "remote", "add", "origin", env_commit_approvals.remote.wd)

    commit_rules_main = {
        "rules": [
            {"rule": "require_signature", "allowed_keys": "(Alice|Bob).asc"},
            {"rule": "require_approval", "allowed_keys": "(Alice|Bob).asc", "threshold": 2},
            {"rule": "disallow_invalid_parents", "exception": "parent_hash_in_merge_message"}
        ]
    }
    pubkeys_main = ["Alice.asc", "Bob.asc"]
    alice_key = env_commit_approvals.users["Alice"].key_id
    env_commit_approvals.local.initialize_commit_rules_on_branch(commit_rules_main, pubkeys_main, alice_key)

    commit_rules_branch_rules = {
        "rules": [
            {"rule": "require_signature", "allowed_keys": "(Alice|Bob).asc"}
        ]
    }
    branch_rules = {
        "branches": [
            {"pattern": "main", "validate_from": env_commit_approvals.local.get_head(), "allow_force_push": False}
        ]
    }
    env_commit_approvals.local.initialize_branch_rules(commit_rules_branch_rules, branch_rules, pubkeys_main, alice_key)

    
    globals.init()

    with replace_stdin(StringIO("yes")):
        install()

    env_commit_approvals.local.cmd("git", "push", "origin", "main")
    env_commit_approvals.local.cmd("git", "branch", "--set-upstream-to=origin/main", "main")
    env_commit_approvals.external.cmd("git", "pull", "origin", "main")
    yield env_commit_approvals
    env_commit_approvals.clean()








