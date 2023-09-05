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
    eves_key = env_signed_commits.users["Eve"].gpg_key_id
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
    bobs_key = env_signed_commits.users["Bob"].gpg_key_id
    env_signed_commits.external.cmd("git", "commit", "-S",
                                    f"--gpg-sign={bobs_key}",
                                    "-m", "Valid commit")
    env_signed_commits.external.cmd("git", "push", "origin", "main", "--force")
    
    pre_pull_head = env_signed_commits.local.get_head()
    _, stderr, exit_code = env_signed_commits.local.cmd("git", "pull", "origin", "main")
    print(stderr)
    post_pull_head = env_signed_commits.local.get_head()

    assert(pre_pull_head != post_pull_head)
    assert (exit_code == 0)


def test_pull_unauthorized_modification(env_signed_commits:Environment):
    env_signed_commits.external.cmd("echo unauthorized change > config.json", shell=True)
    env_signed_commits.external.cmd("git", "add", ".")

    # Create commit which is signed by Alice which modifies a file
    # only Bob is allowed to modify
    alice_key = env_signed_commits.users["Alice"].gpg_key_id
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
    bob_key = env_signed_commits.users["Bob"].gpg_key_id
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
    alice_key = env_signed_commits.users["Alice"].gpg_key_id
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
    bob_key = env_signed_commits.users["Bob"].gpg_key_id
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

    bob_key = env_commit_approvals.users["Bob"].gpg_key_id
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

    bob_key = env_commit_approvals.users["Bob"].gpg_key_id

    
    with replace_stdin(StringIO("yes")):
        os.environ["TEST_WD"] = env_commit_approvals.external.wd
        globals.init()
        approve(commit_hash, gpg_key_id=bob_key)

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

def test_pull_enough_approvals_but_signed(env_commit_approvals:Environment, bark_cli):
    env_commit_approvals.external.cmd("git", "reset", "--hard", "HEAD^")
    env_commit_approvals.external.cmd("git", "checkout", "-b", "feat-sufficient-approvals")
    env_commit_approvals.external.cmd("echo nonsense >> README.md", shell=True)
    env_commit_approvals.external.cmd("git", "add", ".")

    env_commit_approvals.external.cmd("git", "commit", "-m", "Add feat")
    commit_hash = env_commit_approvals.external.get_head()
    env_commit_approvals.external.cmd("git", "checkout", "main")

    bob_key = env_commit_approvals.users["Bob"].gpg_key_id
    alice_key = env_commit_approvals.users["Alice"].gpg_key_id
    
    os.environ["TEST_WD"] = env_commit_approvals.external.wd
    globals.init()
    with replace_stdin(StringIO("yes")):  
        approve(commit_hash, gpg_key_id=bob_key)
    with replace_stdin(StringIO("yes")):  
        approve(commit_hash, gpg_key_id=alice_key)

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

    bob_key = env_commit_approvals.users["Bob"].gpg_key_id
    
    os.environ["TEST_WD"] = env_commit_approvals.external.wd
    globals.init()
    with replace_stdin(StringIO("yes")):  
        approve(commit_hash, gpg_key_id=bob_key)

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


def test_pull_untrusted_signature_ssh(env_signed_commits_ssh:Environment):
    env_signed_commits_ssh.external.cmd("echo nonsense >> README.md", shell=True)
    env_signed_commits_ssh.external.cmd("git", "add", ".")

    # Create commit with untrusted signature from
    env_signed_commits_ssh.external.cmd("git", "commit", "-S",
                                    "-m", "Invalid commit")
    env_signed_commits_ssh.external.cmd("git", "push", "origin", "main", "--force")
    
    pre_pull_head = env_signed_commits_ssh.local.get_head()
    _, stderr, exit_code = env_signed_commits_ssh.local.cmd("git", "pull", "origin", "main")
    post_pull_head = env_signed_commits_ssh.local.get_head()

    assert(pre_pull_head == post_pull_head)
    assert (exit_code != 0)   
    
def test_pull_trusted_signature_ssh(env_signed_commits_ssh:Environment):
    env_signed_commits_ssh.external.cmd("git", "reset", "--hard", "HEAD^")
    env_signed_commits_ssh.external.cmd("echo nonsense >> README.md", shell=True)
    env_signed_commits_ssh.external.cmd("git", "add", ".")

    # Create commit with untrusted signature
    bobs_key_path = env_signed_commits_ssh.users["Bob"].ssh_key_path
    env_signed_commits_ssh.external.configure_git_user(env_signed_commits_ssh.users["Bob"].name, env_signed_commits_ssh.users["Bob"].email)
    env_signed_commits_ssh.external.configure_ssh_signing(bobs_key_path)
    env_signed_commits_ssh.external.cmd("git", "commit", "-S",
                                    "-m", "Valid commit")
    env_signed_commits_ssh.external.cmd("git", "push", "origin", "main", "--force")
    
    pre_pull_head = env_signed_commits_ssh.local.get_head()
    _, stderr, exit_code = env_signed_commits_ssh.local.cmd("git", "pull", "origin", "main")
    post_pull_head = env_signed_commits_ssh.local.get_head()

    assert(pre_pull_head != post_pull_head)
    assert (exit_code == 0)

def test_pull_trusted_signature_ssh(env_signed_commits_ssh:Environment):
    env_signed_commits_ssh.external.cmd("git", "reset", "--hard", "HEAD^")
    env_signed_commits_ssh.external.cmd("echo nonsense >> README.md", shell=True)
    env_signed_commits_ssh.external.cmd("git", "add", ".")

    # Create commit with untrusted signature
    bobs_key_path = env_signed_commits_ssh.users["Bob"].ssh_key_path
    env_signed_commits_ssh.external.configure_git_user(env_signed_commits_ssh.users["Bob"].name, env_signed_commits_ssh.users["Bob"].email)
    env_signed_commits_ssh.external.configure_ssh_signing(bobs_key_path)
    env_signed_commits_ssh.external.cmd("git", "commit", "-S",
                                    "-m", "Valid commit")
    env_signed_commits_ssh.external.cmd("git", "push", "origin", "main", "--force")
    
    pre_pull_head = env_signed_commits_ssh.local.get_head()
    _, stderr, exit_code = env_signed_commits_ssh.local.cmd("git", "pull", "origin", "main")
    post_pull_head = env_signed_commits_ssh.local.get_head()

    assert(pre_pull_head != post_pull_head)
    assert (exit_code == 0)


def test_pull_too_few_approvals_but_signed_ssh(env_commit_approvals_ssh:Environment, bark_cli):
    env_commit_approvals_ssh.external.cmd("git", "reset", "--hard", "HEAD^")
    env_commit_approvals_ssh.external.cmd("git", "checkout", "-b", "feat-insufficient-approvals")
    env_commit_approvals_ssh.external.cmd("echo nonsense >> README.md", shell=True)
    env_commit_approvals_ssh.external.cmd("git", "add", ".")

    env_commit_approvals_ssh.external.cmd("git", "commit", "-m", "Add feat")
    commit_hash = env_commit_approvals_ssh.external.get_head()
    env_commit_approvals_ssh.external.cmd("git", "checkout", "main")

    bob_key_path = env_commit_approvals_ssh.users["Bob"].ssh_key_path
    env_commit_approvals_ssh.external.configure_ssh_signing(bob_key_path)
    
    with replace_stdin(StringIO("yes")):
        os.environ["TEST_WD"] = env_commit_approvals_ssh.external.wd
        globals.init()
        approve(commit_hash, ssh_key_path=bob_key_path)

    signatures = "\n".join(get_signatures(Commit(commit_hash)))
    message = f"Including commit: {commit_hash}\n{signatures}"
    # Merge commit with trusted signature but only 1 approval
    env_commit_approvals_ssh.external.cmd("git", "merge", 
                                          "-S", "--no-ff", "-m", 
                                          message, "feat-insufficient-approvals")
    env_commit_approvals_ssh.external.cmd("git", "push", "origin", "main", "--force")
    os.environ["TEST_WD"] = env_commit_approvals_ssh.local.wd
    pre_pull_head = env_commit_approvals_ssh.local.get_head()
    _, stderr, exit_code = env_commit_approvals_ssh.local.cmd("git", "pull", "origin", "main")
    post_pull_head = env_commit_approvals_ssh.local.get_head()

    assert(pre_pull_head == post_pull_head)
    assert(exit_code != 0)

def test_pull_enough_approvals_ssh(env_commit_approvals_ssh:Environment, bark_cli):
    env_commit_approvals_ssh.external.cmd("git", "reset", "--hard", "HEAD^")
    env_commit_approvals_ssh.external.cmd("git", "checkout", "-b", "feat-sufficient-approvals")
    env_commit_approvals_ssh.external.cmd("echo nonsense >> README.md", shell=True)
    env_commit_approvals_ssh.external.cmd("git", "add", ".")

    env_commit_approvals_ssh.external.cmd("git", "commit", "-m", "Add feat")
    commit_hash = env_commit_approvals_ssh.external.get_head()
    env_commit_approvals_ssh.external.cmd("git", "checkout", "main")

    bob_key_path = env_commit_approvals_ssh.users["Bob"].ssh_key_path
    alice_key_path = env_commit_approvals_ssh.users["Alice"].ssh_key_path
    env_commit_approvals_ssh.external.configure_ssh_signing(bob_key_path)
    os.environ["TEST_WD"] = env_commit_approvals_ssh.external.wd
    globals.init()
    with replace_stdin(StringIO("yes")):
        approve(commit_hash, ssh_key_path=bob_key_path)
    with replace_stdin(StringIO("yes")):
        approve(commit_hash, ssh_key_path=alice_key_path)

    signatures = "\n".join(get_signatures(Commit(commit_hash)))
    message = f"Including commit: {commit_hash}\n{signatures}"
    # Merge commit with trusted signature but only 1 approval
    env_commit_approvals_ssh.external.cmd("git", "merge", 
                                          "-S", "--no-ff", "-m", 
                                          message, "feat-sufficient-approvals")
    env_commit_approvals_ssh.external.cmd("git", "push", "origin", "main", "--force")
    os.environ["TEST_WD"] = env_commit_approvals_ssh.local.wd
    pre_pull_head = env_commit_approvals_ssh.local.get_head()
    _, stderr, exit_code = env_commit_approvals_ssh.local.cmd("git", "pull", "origin", "main")
    post_pull_head = env_commit_approvals_ssh.local.get_head()

    assert(pre_pull_head == post_pull_head)
    assert(exit_code != 0)




    





 

