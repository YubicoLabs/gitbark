from gitbark.commands.verify import verify
from gitbark.commands.install import install
from gitbark.bark_core.signatures.approve_cmd import approve_cmd
from gitbark.bark_core.signatures.add_detached_signatures_cmd import get_signatures
from .utils.util import Environment
from gitbark.git.commit import Commit
import pytest
import os
import sys
from io import StringIO
from contextlib import contextmanager

@contextmanager
def replace_stdin(target):
    orig = sys.stdin
    sys.stdin = target
    yield
    sys.stdin = orig

@pytest.fixture(autouse=True)
def set_env(environment:Environment):
    os.environ["TEST_WD"] = environment.local_repo.wd
    os.environ["GNUPGHOME"] = f"{os.getcwd()}/tests/utils/gpg/.gnupg"

@pytest.fixture(scope="session")
def bark_in_environment(git_in_environment:Environment):
    git_in_environment.local_repo.configure_git_user("User1", "user1@test.com")
    commit_rules= {
        "rules": [
            {"rule": "require_signature","allowed_keys": ".*.asc"}
        ]
    }
    initial_commit_hash = git_in_environment.local_repo.initialize_commit_rules_on_branch(commit_rules, ["user1.asc"], git_in_environment.user1_key_id)
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
    git_in_environment.local_repo.initialize_branch_rules(commit_rules_branch_rules, branch_rules, ["user1.asc"], git_in_environment.user1_key_id)

    return git_in_environment    

@pytest.fixture(scope="session")
def bark_installed(bark_in_environment:Environment):
    with replace_stdin(StringIO("yes")):
        install()
    return bark_in_environment


def test_no_git_repo(environment):
    with pytest.raises(SystemExit) as e:
        verify()
    assert e.type == SystemExit
    assert e.value.code == 1    

def test_git_repo_no_bark(git_in_environment):
    with pytest.raises(SystemExit) as e:
        verify()
    assert e.type == SystemExit
    assert e.value.code == 1

def test_no_signature(bark_installed:Environment):
    bark_installed.local_repo.cmd("echo nonsense > README.md", shell=True)
    bark_installed.local_repo.cmd("git", "add", ".")
    bark_installed.local_repo.cmd("git", "commit", "-m", "Invalid commit")

    report = verify()
    branch_report = report.get_branch("refs/heads/main")
    bark_installed.local_repo.reset_to_previous_commit()
    assert(branch_report != None)
    assert(len(branch_report.commit_rule_violations) == 1)

def test_trusted_signature(bark_installed:Environment):
    bark_installed.local_repo.cmd("echo nonsense > README.md", shell=True)
    bark_installed.local_repo.cmd("git", "add", ".")
    bark_installed.local_repo.cmd("git", "commit", "-S", f"--gpg-sign={bark_installed.user1_key_id}", "-m", "Valid commit")

    report = verify()
    branch_report = report.get_branch("refs/heads/main")
    bark_installed.local_repo.reset_to_previous_commit()
    assert(branch_report == None)

def test_untrusted_signature(bark_installed:Environment):
    bark_installed.local_repo.cmd("echo nonsense > README.md", shell=True)
    bark_installed.local_repo.cmd("git", "add", ".")
    bark_installed.local_repo.cmd("git", "commit", "-S", f"--gpg-sign={bark_installed.user2_key_id}", "-m", "Invalid commit")

    report = verify()
    branch_report = report.get_branch("refs/heads/main")
    bark_installed.local_repo.reset_to_previous_commit()
    assert(branch_report != None)
    assert(len(branch_report.commit_rule_violations) == 1)

@pytest.fixture(scope="session")
def bark_with_locked_file(bark_installed:Environment):
    commit_rule = {
        "any": [
            {"rule":"file_not_modified", "pattern": "config.json"},
            {"rule":"require_signature", "allowed_keys":"user2.asc"}
        ]
    }
    bark_installed.local_repo.add_commit_rule(commit_rule)
    bark_installed.local_repo.cmd("echo sensitive_stuff > config.json", shell=True)
    bark_installed.local_repo.add_pubkey("user2.asc")
    bark_installed.local_repo.cmd("git", "add", ".")
    bark_installed.local_repo.cmd("git", "commit", "-S", f"--gpg-sign={bark_installed.user1_key_id}", "-m", "Add file modification tracking")
    
    return bark_installed

def test_change_locked_file_no_signature(bark_with_locked_file:Environment):
    bark_with_locked_file.local_repo.cmd("echo untrusted_content >> config.json", shell=True)
    bark_with_locked_file.local_repo.cmd("git", "add", ".")
    bark_with_locked_file.local_repo.cmd("git", "commit", "-m", "Invalid commit")

    report = verify()
    branch_report = report.get_branch("refs/heads/main")
    bark_with_locked_file.local_repo.reset_to_previous_commit()
    assert(branch_report != None)
    assert(len(branch_report.commit_rule_violations) == 2)


def test_change_locked_file_untrusted_signature(bark_with_locked_file:Environment):
    bark_with_locked_file.local_repo.cmd("echo untrusted_content >> config.json", shell=True)
    bark_with_locked_file.local_repo.cmd("git", "add", ".")
    bark_with_locked_file.local_repo.cmd("git", "commit", "-S", f"--gpg-sign={bark_with_locked_file.user1_key_id}" ,"-m", "Invalid commit")

    report = verify()
    branch_report = report.get_branch("refs/heads/main")
    bark_with_locked_file.local_repo.reset_to_previous_commit()
    assert(branch_report != None)
    assert(len(branch_report.commit_rule_violations) == 1)

def test_change_locked_file_trusted_signature(bark_with_locked_file:Environment):
    bark_with_locked_file.local_repo.cmd("echo untrusted_content >> config.json", shell=True)
    bark_with_locked_file.local_repo.cmd("git", "add", ".")
    bark_with_locked_file.local_repo.cmd("git", "commit", "-S", f"--gpg-sign={bark_with_locked_file.user2_key_id}" ,"-m", "Invalid commit")

    report = verify()
    branch_report = report.get_branch("refs/heads/main")
    bark_with_locked_file.local_repo.reset_to_previous_commit()
    assert(branch_report == None)

@pytest.fixture(scope="session")
def bark_with_disallow_invalid_parents(bark_installed:Environment):
    commit_rule = {"rule": "disallow_invalid_parents", "exception": "parent_hash_in_merge_message"}
    bark_installed.local_repo.add_commit_rule(commit_rule)
    bark_installed.local_repo.cmd("git", "add", ".")
    bark_installed.local_repo.cmd("git", "commit", "-S", f"--gpg-sign={bark_installed.user1_key_id}", "-m", "Add invalid parents")
    return bark_installed        

def test_invalid_parents_not_included(bark_with_disallow_invalid_parents:Environment):
    bark_with_disallow_invalid_parents.local_repo.cmd("echo nonsense > README.md", shell=True)
    bark_with_disallow_invalid_parents.local_repo.cmd("git", "add", ".")
    bark_with_disallow_invalid_parents.local_repo.cmd("git", "commit", "-m", "Invalid commit")

    report_invalid = verify()
    branch_report_invalid = report_invalid.get_branch("refs/heads/main")
    assert(branch_report_invalid != None)
    assert(len(branch_report_invalid.commit_rule_violations) == 1)

    bark_with_disallow_invalid_parents.local_repo.cmd("echo nonsense >> README.md", shell=True)
    bark_with_disallow_invalid_parents.local_repo.cmd("git", "add", ".")
    bark_with_disallow_invalid_parents.local_repo.cmd("git", "commit", "-S", f"--gpg-sign={bark_with_disallow_invalid_parents.user1_key_id}", "-m", ".")

    report = verify()
    branch_report = report.get_branch("refs/heads/main")
    bark_with_disallow_invalid_parents.local_repo.cmd("git", "reset", "--hard", "HEAD^^")
    assert(branch_report != None)
    assert(len(branch_report.commit_rule_violations) == 1)

def test_invalid_parents_included(bark_with_disallow_invalid_parents:Environment):
    bark_with_disallow_invalid_parents.local_repo.cmd("echo nonsense > README.md", shell=True)
    bark_with_disallow_invalid_parents.local_repo.cmd("git", "add", ".")
    bark_with_disallow_invalid_parents.local_repo.cmd("git", "commit", "-m", "Invalid commit")

    report_invalid = verify()
    branch_report_invalid = report_invalid.get_branch("refs/heads/main")
    assert(branch_report_invalid != None)
    assert(len(branch_report_invalid.commit_rule_violations) == 1)

    head_commit, _, _ = bark_with_disallow_invalid_parents.local_repo.cmd("git","rev-parse", "HEAD")
    bark_with_disallow_invalid_parents.local_repo.cmd("echo nonsense >> README.md", shell=True)
    bark_with_disallow_invalid_parents.local_repo.cmd("git", "add", ".")
    bark_with_disallow_invalid_parents.local_repo.cmd("git", "commit", "-S", f"--gpg-sign={bark_with_disallow_invalid_parents.user1_key_id}", "-m", head_commit)

    report = verify()
    branch_report = report.get_branch("refs/heads/main")
    bark_with_disallow_invalid_parents.local_repo.cmd("git", "reset", "--hard", "HEAD^^")
    assert(branch_report == None)

@pytest.fixture(scope="session")
def bark_with_require_approvals(bark_installed:Environment):
    commit_rule = {"rule":"require_approval", "allowed_keys": ".*.asc", "threshold": 2}
    bark_installed.local_repo.add_commit_rule(commit_rule)
    bark_installed.local_repo.cmd("git", "add", ".")
    bark_installed.local_repo.cmd("git", "commit", "-S", f"--gpg-sign={bark_installed.user1_key_id}", "-m", "Add require approval")
    bark_installed.local_repo.cmd("git", "checkout", "-b", "feat")
    bark_installed.local_repo.cmd("echo nonsense > README.md", shell=True)
    bark_installed.local_repo.cmd("git", "add", ".")
    bark_installed.local_repo.cmd("git", "commit", "-m", "Invalid commit")
    bark_installed.local_repo.cmd("git", "checkout", "main")
    return bark_installed

def test_require_approval_below_threshold(bark_with_require_approvals:Environment):
    commit_hash, _, _ = bark_with_require_approvals.local_repo.cmd("git", "rev-parse", "refs/heads/feat")

    with replace_stdin(StringIO("yes")):
        approve_cmd(commit_hash, bark_with_require_approvals.user1_key_id)
    
    signatures = "\n".join(get_signatures(Commit(commit_hash)))
    bark_with_require_approvals.local_repo.cmd("git", "checkout", "main")

    message = f"Including commit: {commit_hash}\n{signatures}"

    bark_with_require_approvals.local_repo.cmd("git", "merge", "-S", f"--gpg-sign={bark_with_require_approvals.user1_key_id}" ,"--no-ff", "-m", message, "feat")

    report = verify()
    branch_report = report.get_branch("refs/heads/main")
    bark_with_require_approvals.local_repo.cmd("git", "reset", "--hard", "HEAD~1")
    assert(branch_report != None)
    assert(len(branch_report.commit_rule_violations) == 1)

def test_require_approval_above_threshold(bark_with_require_approvals:Environment):
    commit_hash, _, _ = bark_with_require_approvals.local_repo.cmd("git", "rev-parse", "refs/heads/feat")

    with replace_stdin(StringIO("yes")):
        approve_cmd(commit_hash, bark_with_require_approvals.user1_key_id)
    
    with replace_stdin(StringIO("yes")):
        approve_cmd(commit_hash, bark_with_require_approvals.user2_key_id)
    
    signatures = "\n".join(get_signatures(Commit(commit_hash)))
    bark_with_require_approvals.local_repo.cmd("git", "checkout", "main")

    message = f"Including commit: {commit_hash}\n{signatures}\nHey mate"
    bark_with_require_approvals.local_repo.cmd("git", "merge", "-S", f"--gpg-sign={bark_with_require_approvals.user1_key_id}" ,"--no-ff", "-m", message, "feat")

    report = verify()
    branch_report = report.get_branch("refs/heads/main")
    bark_with_require_approvals.local_repo.cmd("git", "reset", "--hard", "HEAD~1")
    bark_with_require_approvals.local_repo.cmd("git", "update-ref", "-d", f"refs/signatures/{commit_hash}/{bark_with_require_approvals.user1_key_id}")
    bark_with_require_approvals.local_repo.cmd("git", "update-ref", "-d", f"refs/signatures/{commit_hash}/{bark_with_require_approvals.user2_key_id}")

    assert(branch_report == None)

def test_require_approval_same_key(bark_with_require_approvals:Environment):
    commit_hash, _, _ = bark_with_require_approvals.local_repo.cmd("git", "rev-parse", "refs/heads/feat")

    with replace_stdin(StringIO("yes")):
        approve_cmd(commit_hash, bark_with_require_approvals.user1_key_id)
    
    with replace_stdin(StringIO("yes")):
        approve_cmd(commit_hash, bark_with_require_approvals.user1_key_fingerprint)
    
    signatures = "\n".join(get_signatures(Commit(commit_hash)))
    bark_with_require_approvals.local_repo.cmd("git", "checkout", "main")

    message = f"Including commit: {commit_hash}\n{signatures}"
    bark_with_require_approvals.local_repo.cmd("git", "merge", "-S", f"--gpg-sign={bark_with_require_approvals.user1_key_id}" ,"--no-ff", "-m", message, "feat")

    report = verify()
    branch_report = report.get_branch("refs/heads/main")
    bark_with_require_approvals.local_repo.cmd("git", "reset", "--hard", "HEAD~1")
    bark_with_require_approvals.local_repo.cmd("git", "update-ref", "-d", f"refs/signatures/{commit_hash}/{bark_with_require_approvals.user1_key_id}")
    bark_with_require_approvals.local_repo.cmd("git", "update-ref", "-d", f"refs/signatures/{commit_hash}/{bark_with_require_approvals.user1_key_fingerprint}")
    assert(branch_report != None)
    assert(len(branch_report.commit_rule_violations) == 1)

    
    
    

