import sys, os
from io import StringIO
from contextlib import contextmanager

from .utils.util import Environment
from gitbark.bark_core.signatures.commands.approve_cmd import approve_cmd as approve
from gitbark.bark_core.signatures.commands.add_detached_signatures_cmd import get_signatures
from gitbark.git.commit import Commit
from gitbark import globals

@contextmanager
def replace_stdin(target):
    orig = sys.stdin
    sys.stdin = target
    yield
    sys.stdin = orig


def test_pull_no_signature(env_signed_commits:Environment):
    env_signed_commits.external.cmd("echo nonsense >> README.md", shell=True)
    # Creating commit without signature
    env_signed_commits.external.cmd("git", "add", ".")
    env_signed_commits.external.cmd("git", "commit", "-m", "Invalid commit")
    env_signed_commits.external.cmd("git", "push", "origin", "main")

    pre_pull_head = env_signed_commits.local.get_head()
    _, stderr, exit_code = env_signed_commits.local.cmd("git", "pull", "origin", "main")
    post_pull_head = env_signed_commits.local.get_head()

    assert(pre_pull_head == post_pull_head)
    assert (exit_code != 0)

def test_pull_untrusted_signature(env_signed_commits:Environment):
    env_signed_commits.external.cmd("git", "reset", "--hard", "HEAD^")
    env_signed_commits.external.cmd("echo nonsense >> README.md", shell=True)
    env_signed_commits.external.cmd("git", "add", ".")

    # Create commit with untrusted signature
    eves_key = env_signed_commits.users["Eve"].key_id
    env_signed_commits.external.cmd("git", "commit", "-S",
                                    f"--gpg-sign={eves_key}",
                                    "-m", "Invalid commit")
    env_signed_commits.external.cmd("git", "push", "origin", "main", "--force")
    
    pre_pull_head = env_signed_commits.local.get_head()
    _, stderr, exit_code = env_signed_commits.local.cmd("git", "pull", "origin", "main")
    post_pull_head = env_signed_commits.local.get_head()

    assert(pre_pull_head == post_pull_head)
    assert (exit_code != 0)

def test_pull_trusted_signature(env_signed_commits:Environment):
    env_signed_commits.external.cmd("git", "reset", "--hard", "HEAD^")
    env_signed_commits.external.cmd("echo nonsense >> README.md", shell=True)
    env_signed_commits.external.cmd("git", "add", ".")

    # Create commit with untrusted signature
    bobs_key = env_signed_commits.users["Bob"].key_id
    env_signed_commits.external.cmd("git", "commit", "-S",
                                    f"--gpg-sign={bobs_key}",
                                    "-m", "Valid commit")
    env_signed_commits.external.cmd("git", "push", "origin", "main", "--force")
    
    pre_pull_head = env_signed_commits.local.get_head()
    _, stderr, exit_code = env_signed_commits.local.cmd("git", "pull", "origin", "main")
    post_pull_head = env_signed_commits.local.get_head()

    assert(pre_pull_head != post_pull_head)
    assert (exit_code == 0)


def test_pull_unauthorized_modification(env_signed_commits:Environment):
    env_signed_commits.external.cmd("echo unauthorized change > config.json", shell=True)
    env_signed_commits.external.cmd("git", "add", ".")

    # Create commit which is signed by Alice which modifies a file
    # only Bob is allowed to modify
    alice_key = env_signed_commits.users["Alice"].key_id
    env_signed_commits.external.cmd("git", "commit", "-S",
                                    f"--gpg-sign={alice_key}",
                                    "-m", "Invalid commit")
    env_signed_commits.external.cmd("git", "push", "origin", "main", "--force")

    pre_pull_head = env_signed_commits.local.get_head()
    _, stderr, exit_code = env_signed_commits.local.cmd("git", "pull", "origin", "main")
    env_signed_commits.local.cmd("rm", "config.json")
    post_pull_head = env_signed_commits.local.get_head()

    assert(pre_pull_head == post_pull_head)
    assert (exit_code != 0)

def test_pull_authorized_modification(env_signed_commits:Environment):
    env_signed_commits.external.cmd("git", "reset", "--hard", "HEAD^")
    env_signed_commits.external.cmd("echo authorized change > config.json", shell=True)
    env_signed_commits.external.cmd("git", "add", ".")

    # Create commit signed by Bob that modifies a file he is
    # authorized to modify
    bob_key = env_signed_commits.users["Bob"].key_id
    env_signed_commits.external.cmd("git", "commit", "-S",
                                    f"--gpg-sign={bob_key}",
                                    "-m", "Valid commit")
    env_signed_commits.external.cmd("git", "push", "origin", "main", "--force")
    pre_pull_head = env_signed_commits.local.get_head()
    _, stderr, exit_code = env_signed_commits.local.cmd("git", "pull", "origin", "main")
    post_pull_head = env_signed_commits.local.get_head()

    assert(pre_pull_head != post_pull_head)
    assert (exit_code == 0)


def test_merge_unauthorized_modification(env_signed_commits:Environment):
    env_signed_commits.external.cmd("git", "checkout", "-b", "feat")
    env_signed_commits.external.cmd("echo unauthorized change >> config.json", shell=True)
    env_signed_commits.external.cmd("git", "add", ".")

    # Create commit that modifes file only Bob is allowed to modify
    env_signed_commits.external.cmd("git", "commit", "-m", "Invalid commit")
    env_signed_commits.external.cmd("git", "push", "origin", "feat")

    pre_merge_head = env_signed_commits.local.get_head()
    env_signed_commits.local.cmd("git", "fetch" , "origin")
    alice_key = env_signed_commits.users["Alice"].key_id
    stdout, stderr, exit_code = env_signed_commits.local.cmd("git", "merge", "-S",
                                                        f"--gpg-sign={alice_key}",
                                                        "--no-ff", "-m", "Merge feat",
                                                        "refs/remotes/origin/feat")
    env_signed_commits.local.cmd("git", "merge", "--abort")
    post_merge_head = env_signed_commits.local.get_head()
    assert(pre_merge_head == post_merge_head)
    assert (exit_code != 0)

def test_merge_authorized_modification(env_signed_commits:Environment):
    env_signed_commits.external.cmd("git", "checkout", "main")
    env_signed_commits.external.cmd("git", "checkout", "-b", "feat-valid")
    env_signed_commits.external.cmd("echo unauthorized change > config.json", shell=True)
    env_signed_commits.external.cmd("git", "add", ".")

    # Create commit that modifes file only Bob is allowed to modify
    env_signed_commits.external.cmd("git", "commit", "-m", "Invalid commit")
    env_signed_commits.external.cmd("git", "push", "origin", "feat-valid")

    pre_merge_head = env_signed_commits.local.get_head()
    env_signed_commits.local.cmd("git", "fetch" , "origin")
    bob_key = env_signed_commits.users["Bob"].key_id
    _, stderr, exit_code = env_signed_commits.local.cmd("git", "merge", "-S",
                                                        f"--gpg-sign={bob_key}",
                                                        "--no-ff", "-m", "Merge feat",
                                                        "refs/remotes/origin/feat-valid")
    post_merge_head = env_signed_commits.local.get_head()
    assert(pre_merge_head != post_merge_head)
    assert (exit_code == 0)

def test_pull_no_approvals_but_signed(env_commit_approvals:Environment):
    env_commit_approvals.external.cmd("git", "checkout", "-b", "feat-no-approvals")
    env_commit_approvals.external.cmd("echo nonsense >> README.md", shell=True)
    env_commit_approvals.external.cmd("git", "add", ".")

    env_commit_approvals.external.cmd("git", "commit", "-m", "Add feat")
    env_commit_approvals.external.cmd("git", "checkout", "main")

    bob_key = env_commit_approvals.users["Bob"].key_id
    # Merge commit with trusted signature but no approvals
    env_commit_approvals.external.cmd("git", "merge", "-S",
                                                        f"--gpg-sign={bob_key}",
                                                        "--no-ff", "-m", "Merge feat",
                                                        "feat-no-approvals")
    env_commit_approvals.external.cmd("git", "push", "origin", "main", "--force")

    pre_pull_head = env_commit_approvals.local.get_head()
    _, stderr, exit_code = env_commit_approvals.local.cmd("git", "pull", "origin", "main")
    post_pull_head = env_commit_approvals.local.get_head()

    assert(pre_pull_head == post_pull_head)
    assert(exit_code != 0)

def test_pull_too_few_approvals_but_signed(env_commit_approvals:Environment, bark_cli):
    env_commit_approvals.external.cmd("git", "reset", "--hard", "HEAD^")
    env_commit_approvals.external.cmd("git", "checkout", "-b", "feat-insufficient-approvals")
    env_commit_approvals.external.cmd("echo nonsense >> README.md", shell=True)
    env_commit_approvals.external.cmd("git", "add", ".")

    env_commit_approvals.external.cmd("git", "commit", "-m", "Add feat")
    commit_hash = env_commit_approvals.external.get_head()
    env_commit_approvals.external.cmd("git", "checkout", "main")

    bob_key = env_commit_approvals.users["Bob"].key_id

    
    with replace_stdin(StringIO("yes")):
        os.environ["TEST_WD"] = env_commit_approvals.external.wd
        globals.init()
        approve(commit_hash, bob_key)

    signatures = "\n".join(get_signatures(Commit(commit_hash)))
    message = f"Including commit: {commit_hash}\n{signatures}"
    # Merge commit with trusted signature but only 1 approval
    env_commit_approvals.external.cmd("git", "merge", "-S",
                                                        f"--gpg-sign={bob_key}",
                                                        "--no-ff", "-m", message,
                                                        "feat-insufficient-approvals")
    env_commit_approvals.external.cmd("git", "push", "origin", "main", "--force")
    os.environ["TEST_WD"] = env_commit_approvals.local.wd
    pre_pull_head = env_commit_approvals.local.get_head()
    _, stderr, exit_code = env_commit_approvals.local.cmd("git", "pull", "origin", "main")
    post_pull_head = env_commit_approvals.local.get_head()

    assert(pre_pull_head == post_pull_head)
    assert(exit_code != 0)

def test_pull_too_enough_approvals_but_signed(env_commit_approvals:Environment, bark_cli):
    env_commit_approvals.external.cmd("git", "reset", "--hard", "HEAD^")
    env_commit_approvals.external.cmd("git", "checkout", "-b", "feat-sufficient-approvals")
    env_commit_approvals.external.cmd("echo nonsense >> README.md", shell=True)
    env_commit_approvals.external.cmd("git", "add", ".")

    env_commit_approvals.external.cmd("git", "commit", "-m", "Add feat")
    commit_hash = env_commit_approvals.external.get_head()
    env_commit_approvals.external.cmd("git", "checkout", "main")

    bob_key = env_commit_approvals.users["Bob"].key_id
    alice_key = env_commit_approvals.users["Alice"].key_id
    
    os.environ["TEST_WD"] = env_commit_approvals.external.wd
    globals.init()
    with replace_stdin(StringIO("yes")):  
        approve(commit_hash, bob_key)
    with replace_stdin(StringIO("yes")):  
        approve(commit_hash, alice_key)

    signatures = "\n".join(get_signatures(Commit(commit_hash)))
    message = f"Including commit: {commit_hash}\n{signatures}"
    # Merge commit with trusted signature and 2 authorized approvals
    env_commit_approvals.external.cmd("git", "merge", "-S",
                                                        f"--gpg-sign={bob_key}",
                                                        "--no-ff", "-m", message,
                                                        "feat-sufficient-approvals")
    env_commit_approvals.external.cmd("git", "push", "origin", "main", "--force")
    os.environ["TEST_WD"] = env_commit_approvals.local.wd
    pre_pull_head = env_commit_approvals.local.get_head()
    _, stderr, exit_code = env_commit_approvals.local.cmd("git", "pull", "origin", "main")
    post_pull_head = env_commit_approvals.local.get_head()

    assert(pre_pull_head != post_pull_head)
    assert(exit_code == 0)

def test_pull_duplicate_approvals_but_signed(env_commit_approvals:Environment, bark_cli):
    env_commit_approvals.external.cmd("git", "checkout", "-b", "feat-same-approvals")
    env_commit_approvals.external.cmd("echo nonsense >> README.md", shell=True)
    env_commit_approvals.external.cmd("git", "add", ".")

    env_commit_approvals.external.cmd("git", "commit", "-m", "Add feat")
    commit_hash = env_commit_approvals.external.get_head()
    env_commit_approvals.external.cmd("git", "checkout", "main")

    bob_key = env_commit_approvals.users["Bob"].key_id
    
    os.environ["TEST_WD"] = env_commit_approvals.external.wd
    globals.init()
    with replace_stdin(StringIO("yes")):  
        approve(commit_hash, bob_key)

    signatures = "\n".join(get_signatures(Commit(commit_hash)))
    message = f"Including commit: {commit_hash}\n{signatures}\n{signatures}"
    # Merge commit with trusted signature but 2 duplicate approvals
    env_commit_approvals.external.cmd("git", "merge", "-S",
                                                        f"--gpg-sign={bob_key}",
                                                        "--no-ff", "-m", message,
                                                        "feat-same-approvals")
    env_commit_approvals.external.cmd("git", "push", "origin", "main", "--force")
    os.environ["TEST_WD"] = env_commit_approvals.local.wd
    pre_pull_head = env_commit_approvals.local.get_head()
    _, stderr, exit_code = env_commit_approvals.local.cmd("git", "pull", "origin", "main")
    post_pull_head = env_commit_approvals.local.get_head()

    assert(pre_pull_head == post_pull_head)
    assert(exit_code != 0)








    





 

