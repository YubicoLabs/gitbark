from gitbark.commands.verify import verify
from .util import Environment

import pytest
import os

environment = Environment()

@pytest.fixture(scope="session", autouse=True)
def set_env():
    wd = os.getcwd()
    os.environ["TEST_WD"] = f"{wd}/tests/clients/local"


def test_no_signature():
    environment.local_repo.cmd("echo nonsense > README.md", shell=True)
    environment.local_repo.cmd('git', 'add', 'README.md')
    environment.local_repo.cmd("git", "commit", "-m", ".")
    current_branch, _ = environment.local_repo.cmd("git", "symbolic-ref", "HEAD")
    report = verify(all=False)
    branch_report = report.get_branch(current_branch)
    environment.local_repo.restore()
    assert(not branch_report == None)
    assert(len(branch_report.commit_rule_violations) == 1)

def test_trusted_signature():
    environment.local_repo.cmd("echo nonsense > README.md", shell=True)
    environment.local_repo.cmd('git', 'add', 'README.md')
    environment.local_repo.cmd("git", "commit", "-S" ,"-m", ".")
    current_branch, _ = environment.local_repo.cmd("git", "symbolic-ref", "HEAD")
    report = verify(all=False)
    branch_report = report.get_branch(current_branch)
    environment.local_repo.restore()
    assert(branch_report == None)

def test_untrusted_signature():
    environment.local_repo.cmd("echo nonsense > README.md", shell=True)
    environment.local_repo.cmd('git', 'add', 'README.md')
    environment.local_repo.cmd("git", "commit", "-S", f"--gpg-sign={environment.untrusted_key_id}" ,"-m", ".")
    current_branch, _ = environment.local_repo.cmd("git", "symbolic-ref", "HEAD")
    report = verify(all=False)
    branch_report = report.get_branch(current_branch)
    environment.local_repo.restore()
    assert(not branch_report == None)
    assert(len(branch_report.commit_rule_violations) == 1)




        