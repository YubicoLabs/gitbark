from tests.utils.util import Environment
from gitbark.bark_core.signatures.commands.approve_cmd import approve_cmd
from gitbark.bark_core.signatures.commands.add_detached_signatures_cmd import get_signatures
from gitbark.git.commit import Commit
from gitbark.commands.install import install
import os
import sys
from io import StringIO
from contextlib import contextmanager

import time


from gitbark import globals

@contextmanager
def replace_stdin(target):
    orig = sys.stdin
    sys.stdin = target
    yield
    sys.stdin = orig

url = "git@github.com:elibon99/gitbark-performance.git"

def create_env():
    environment = Environment("test_performance")
    environment.remote.initialize_git()
    environment.local.initialize_git()
    environment.external.initialize_git()
    environment.local.cmd("git", "remote", "add", "origin", url)
    environment.external.cmd("git", "remote", "add", "origin", url)

    os.environ["TEST_WD"] = environment.local.wd
    os.environ["GNUPGHOME"] = f"{os.getcwd()}/tests/utils/gpg/.gnupg"
    
    environment.local.configure_git_user("User1", "user1@test.com")
    environment.external.configure_git_user("User1", "user1@test.com")
    commit_rules = {
        "rules": [
            {"rule": "require_signature", "allowed_keys": ".*.asc"},
            {"rule": "require_approval", "allowed_keys": ".*.asc", "threshold": 2}
        ]
    }

    initial_commit_hash = environment.local.initialize_commit_rules_on_branch(commit_rules, ["user1.asc", "user2.asc"], environment.user1_key_id)

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
    environment.local.initialize_branch_rules(commit_rules_branch_rules, branch_rules, ["user1.asc"], environment.user1_key_id)

    globals.init()
    return environment

def create_commits(environment:Environment, pr_index):
    branch_name = f"feat-{pr_index}"

    # Create PR commits
    environment.local.cmd("git", "checkout", "-b", branch_name)
    for i in range(4):
        environment.local.cmd("echo nonsense >> README.md", shell=True)
        environment.local.cmd("git", "add", ".")
        environment.local.cmd("git", "commit", "-S", f"--gpg-sign={environment.user1_key_id}" , "-m", f"Add {branch_name} {i}")

    # Add approvals
    pr_commit_hash, _, _ = environment.local.cmd("git", "rev-parse", f"refs/heads/{branch_name}")
    
    approve_cmd(pr_commit_hash, environment.user1_key_id)
    
    approve_cmd(pr_commit_hash, environment.user2_key_id)

    signatures = "\n".join(get_signatures(Commit(pr_commit_hash)))
    environment.local.cmd("git", "checkout", "main")

    # Create merge commit
    message = f"Including commit: {pr_commit_hash}\n{signatures}"
    environment.local.cmd("git", "merge", "-S", f"--gpg-sign={environment.user1_key_id}" ,"--no-ff", "-m", message, branch_name)
    
    environment.local.cmd("git", "update-ref", "-d", f"refs/signatures/{pr_commit_hash}/{environment.user1_key_id}")
    environment.local.cmd("git", "update-ref", "-d", f"refs/signatures/{pr_commit_hash}/{environment.user2_key_id}")
    # Delete feat branch
    environment.local.cmd("git", "branch", "-D", branch_name)
def create_commits_external(environment:Environment, pr_index):
    branch_name = f"feat-{pr_index}"

    # Create PR commits
    environment.external.cmd("git", "checkout", "-b", branch_name)
    for i in range(4):
        environment.external.cmd("echo nonsense >> README.md", shell=True)
        environment.external.cmd("git", "add", ".")
        environment.external.cmd("git", "commit", "-S", f"--gpg-sign={environment.user1_key_id}" , "-m", f"Add {branch_name} {i}")
    # environment.local.cmd("echo nonsense >> README.md", shell=True)
    # environment.local.cmd("git", "add", ".")
    # environment.local.cmd("git", "commit", "-S", f"--gpg-sign={environment.user1_key_id}" , "-m", f"Add {branch_name}")

    # Add approvals
    pr_commit_hash, _, _ = environment.external.cmd("git", "rev-parse", f"refs/heads/{branch_name}")
    
    approve_cmd(pr_commit_hash, environment.user1_key_id)
    
    approve_cmd(pr_commit_hash, environment.user2_key_id)

    

    signatures = "\n".join(get_signatures(Commit(pr_commit_hash)))
    environment.external.cmd("git", "checkout", "main")

    # Create merge commit
    message = f"Including commit: {pr_commit_hash}\n{signatures}"
    environment.external.cmd("git", "merge", "-S", f"--gpg-sign={environment.user1_key_id}" ,"--no-ff", "-m", message, branch_name)
    
    environment.external.cmd("git", "update-ref", "-d", f"refs/signatures/{pr_commit_hash}/{environment.user1_key_id}")
    environment.external.cmd("git", "update-ref", "-d", f"refs/signatures/{pr_commit_hash}/{environment.user2_key_id}")
    # Delete feat branch
    environment.external.cmd("git", "branch", "-D", branch_name)

def create_commits_storage(environment:Environment, pr_index):
    branch_name = f"fix-{pr_index}"

    environment.external.cmd("git", "checkout", "-b", branch_name)
    for i in range(4):
        environment.external.cmd("echo nonsense >> README.md", shell=True)
        environment.external.cmd("git", "add", ".")
        environment.external.cmd("git", "commit", "-S", f"--gpg-sign={environment.user1_key_id}" , "-m", f"Add {branch_name} {i}")

        # Add approvals
    # pr_commit_hash, _, _ = environment.external_repo.cmd("git", "rev-parse", f"refs/heads/{branch_name}")
    
    # approve_cmd(pr_commit_hash, environment.user1_key_id)
    
    # approve_cmd(pr_commit_hash, environment.user2_key_id)
    # signatures = "\n".join(get_signatures(Commit(pr_commit_hash)))
    environment.external.cmd("git", "checkout", "main")

    # Create merge commit
    # message = f"Including commit: {pr_commit_hash}\n{signatures}"
    environment.external.cmd("git", "merge", "-S", f"--gpg-sign={environment.user1_key_id}" ,"--no-ff", "-m", f"Merging {branch_name}", branch_name)
    
    # Delete feat branch
    environment.external.cmd("git", "branch", "-D", branch_name)

def main():


    # environment = Environment("test_performance")

    # os.environ["TEST_WD"] = environment.local_repo.wd
    # os.environ["GNUPGHOME"] = f"{os.getcwd()}/tests/utils/gpg/.gnupg"
    # create_commits_external(environment, 1)
    times = 0
    count = 0

    environment = create_env()
    for index in range(20):
        create_commits(environment, index)
    # with replace_stdin(StringIO("yes")):
    #     install()
    environment.local.cmd("git", "config", "merge.ff", "true")
    environment.local.cmd("git", "push", "origin", "main", "--force")

    for i in range(10):
        os.environ["TEST_WD"] = environment.external.wd

        environment.external.cmd("git", "pull", "origin", "main")
        globals.init()

        for i in range(4):
            create_commits_external(environment, i)
        environment.external.cmd("git", "push", "origin", "main", "--force")

        os.environ["TEST_WD"] = environment.local.wd
        globals.init()

        print("running git pull on local")
        start = time.time()
        environment.local.cmd("git", "pull", "origin", "main")
        end = time.time()

        times = times + (end-start)
        count = count + 1

    # print("Execution times = ", times)
    print("Average execution time = ", times/count)

    environment.clean()
    


    # os.environ["TEST_WD"] = environment.external.wd
    # environment.external.cmd("echo nonsense >> README.md", shell=True)
    # environment.external.cmd("git", "add", ".")
    # environment.external.cmd("git", "commit", "-S", f"--gpg-sign={environment.user1_key_id}" , "-m", f"Initial commit")    
    # for index in range(6000):
    #     create_commits_storage(environment, index)
    # environment.external_repo.cmd("git", "push", "origin", "main")

main()



