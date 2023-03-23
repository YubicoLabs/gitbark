import pytest
import os
from .utils.util import Environment
from gitbark.commands.install import install
import sys
from io import StringIO
from contextlib import contextmanager

@contextmanager
def replace_stdin(target):
    orig = sys.stdin
    sys.stdin = target
    yield
    sys.stdin = orig

@pytest.fixture(scope="session", autouse=True)
def set_env_hooks(environment_with_hooks:Environment):
    os.environ["TEST_WD"] = environment_with_hooks.local_repo.wd
    os.environ["GNUPGHOME"] = f"{os.getcwd()}/tests/utils/gpg/.gnupg"

@pytest.fixture(scope="session")
def bark_installed_environment(environment_with_hooks:Environment):
    environment_with_hooks.local_repo.configure_git_user("User1", "user1@test.com")
    environment_with_hooks.external_repo.configure_git_user("User2", "user2@test.com")
    commit_rules= {
        "rules": [
            {"rule": "require_signature","allowed_keys": ".*.asc"}
        ]
    }
    initial_commit_hash = environment_with_hooks.local_repo.initialize_commit_rules_on_branch(commit_rules, ["user1.asc"], environment_with_hooks.user1_key_id)
    branch_rules = {
        "branches": [
            {"pattern": "main","validate_from": initial_commit_hash,"allow_force_push": False}
        ]
    }
    commit_rules_branch_rules = {
        "rules": [
            {"rule": "require_signature","allowed_keys": "user1.asc"}
        ]
    }
    environment_with_hooks.local_repo.initialize_branch_rules(commit_rules_branch_rules, branch_rules, ["user1.asc"], environment_with_hooks.user1_key_id)

    with replace_stdin(StringIO("yes")):
        install()

    environment_with_hooks.local_repo.install_hooks()

    
    environment_with_hooks.local_repo.cmd("git", "push", "origin", "main")
    environment_with_hooks.local_repo.cmd("git", "branch", "--set-upstream-to=origin/main", "main")

    return environment_with_hooks

def test_no_signature_reject(bark_installed_environment:Environment):
    current_head, _, _ = bark_installed_environment.local_repo.cmd("git", "rev-parse", "HEAD")
    bark_installed_environment.local_repo.cmd("echo nonsense > README.md", shell=True)
    bark_installed_environment.local_repo.cmd("git", "add", ".")
    bark_installed_environment.local_repo.cmd("git", "commit", "-m", "Invalid commit")
    staged_files, _, _ = bark_installed_environment.local_repo.cmd("git", "diff", "--name-only", "--cached")
    new_head, _, _ = bark_installed_environment.local_repo.cmd("git", "rev-parse", "HEAD")

    assert(new_head == current_head)
    assert(staged_files == "README.md")
    bark_installed_environment.local_repo.cmd("git", "restore", "--staged", ".")
    bark_installed_environment.local_repo.cmd("git", "restore", ".")
    
def test_trusted_signature_no_reject(bark_installed_environment:Environment):
    current_head, _, _ = bark_installed_environment.local_repo.cmd("git", "rev-parse", "HEAD")
    bark_installed_environment.local_repo.cmd("echo nonsense > README.md", shell=True)
    bark_installed_environment.local_repo.cmd("git", "add", ".")
    bark_installed_environment.local_repo.cmd("git", "commit", "-S", f"--gpg-sign={bark_installed_environment.user1_key_id}", "-m", "Valid commit")
    new_head, _, _ = bark_installed_environment.local_repo.cmd("git", "rev-parse", "HEAD")
    assert(new_head != current_head)
    bark_installed_environment.local_repo.reset_to_previous_commit(hooks=True)

@pytest.fixture(scope="session")
def untrusted_changes_on_remote(bark_installed_environment:Environment):
    bark_installed_environment.external_repo.cmd("git", "pull", "origin", "main")
    bark_installed_environment.external_repo.cmd("echo nonsense > README.md", shell=True)
    bark_installed_environment.external_repo.cmd("git", "add", ".")
    bark_installed_environment.external_repo.cmd("git", "commit", "-m", "Invalid commit")
    bark_installed_environment.external_repo.cmd("git", "push", "origin", "main")
    return bark_installed_environment

def test_fetch_untrsuted_changes(untrusted_changes_on_remote:Environment):
    stdout, stderr , _ = untrusted_changes_on_remote.local_repo.cmd("git", "fetch", "origin")
    assert f"refs/remotes/origin/main is invalid" in stderr

def test_pull_untrusted_changes(untrusted_changes_on_remote:Environment):
    current_head, _, _ = untrusted_changes_on_remote.local_repo.cmd("git", "rev-parse", "HEAD")
    stdout, stderr , _ = untrusted_changes_on_remote.local_repo.cmd("git", "pull")
    new_head, _, _ = untrusted_changes_on_remote.local_repo.cmd("git", "rev-parse", "HEAD")
    staged_files, _, _ = untrusted_changes_on_remote.local_repo.cmd("git", "diff", "--name-only", "--cached")
    untrusted_changes_on_remote.local_repo.cmd("git", "merge", "--abort")
    untrusted_changes_on_remote.local_repo.cmd("git", "clean", "-f", "-x")
    assert(current_head == new_head)
    assert(f"refs/heads/main is invalid" in stderr)
    assert(staged_files == "")

@pytest.fixture(scope="session")
def rollback_changes_on_remote(bark_installed_environment:Environment):
    bark_installed_environment.local_repo.cmd("echo nonsense > README.md", shell=True)
    bark_installed_environment.local_repo.cmd("git", "add", ".")
    bark_installed_environment.local_repo.cmd("git", "commit", "-S", f"--gpg-sign={bark_installed_environment.user1_key_id}", "-m", "Valid commit")
    bark_installed_environment.local_repo.cmd("git", "push", "origin", "main", "--force")

    bark_installed_environment.external_repo.cmd("git", "fetch", "origin")
    bark_installed_environment.external_repo.cmd("git", "reset", "--hard", "origin/main")
    bark_installed_environment.external_repo.cmd("git", "reset", "--hard", "HEAD^")
    bark_installed_environment.external_repo.cmd("git", "push", "origin", "main", "--force")
    return bark_installed_environment

def test_fetch_rollback(rollback_changes_on_remote:Environment):
    stdout, stderr, _ =  rollback_changes_on_remote.local_repo.cmd("git", "fetch", "origin")
    assert f"refs/remotes/origin/main is invalid" in stderr
    assert "Commit is not fast-forward" in stderr

def test_pull_rollback(rollback_changes_on_remote:Environment):
    current_head, _, _  = rollback_changes_on_remote.local_repo.cmd("git", "rev-parse", "HEAD")
    stdout, stderr, _ = rollback_changes_on_remote.local_repo.cmd("git", "reset", "--hard", "origin/main")
    new_head, _, _  = rollback_changes_on_remote.local_repo.cmd("git", "rev-parse", "HEAD")
    staged_files, _, _  = rollback_changes_on_remote.local_repo.cmd("git", "diff", "--name-only", "--cached")
    rollback_changes_on_remote.local_repo.cmd("git", "merge", "--abort")
    rollback_changes_on_remote.local_repo.cmd("git", "clean", "-f", "-x")
    assert(current_head == new_head)
    assert("refs/heads/main is invalid" in stderr)
    assert("Commit is not fast-forward" in stderr)
    assert(staged_files == "")

    





