import subprocess
from typing import Any
from gitbark.bark_core.signatures.commands.approve_cmd import approve_cmd
from gitbark.git.commit import Commit
from gitbark.bark_core.signatures.commands.add_detached_signatures_cmd import get_signatures
from tests.utils.util import User
from gitbark.rules.commit_rules import add_children

import os
import sys
from gitbark import globals

import yaml

from io import StringIO
from contextlib import contextmanager

@contextmanager
def replace_stdin(target):
    orig = sys.stdin
    sys.stdin = target
    yield
    sys.stdin = orig

def cmd(*cmd: str,  cwd:str=None, env = None, shell:bool=False):
    try: 
        cwd = cwd or globals.working_directory.wd
        result = None
        if env:
            result = subprocess.run(cmd, capture_output=True, check=True, text=True, cwd=cwd, env=env)
        else:
            result = subprocess.run(cmd, capture_output=True, check=True, text=True, shell=shell, cwd=cwd)
        return result.stdout.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        # print(e.stderr, e.stdout)
        raise e
        return e.stdout.strip(), e.returncode
    
def cmd2(*cmd: str,  cwd:str=None, env = None, shell:bool=False):
    try: 
        cwd = cwd or globals.working_directory.wd
        result = None
        if env:
            result = subprocess.run(cmd, capture_output=True, check=True, text=True, cwd=cwd, env=env)
        else:
            result = subprocess.run(cmd, capture_output=True, check=True, text=True, shell=shell, cwd=cwd)
        return result.stdout.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        # print(e.stderr, e.stdout)
        # raise e
        return e.stdout.strip(), e.returncode





alice = User("Alice", "alice@test.com", "1B6859743123CAF9",
            f"{os.getcwd()}/tests/utils/ssh/.ssh/alice.ssh")
bob = User("Bob", "bob@test.com", "BF5770F1F3A3E74C",
        f"{os.getcwd()}/tests/utils/ssh/.ssh/bob.ssh")
eve = User("Eve", "eve@test.com", "3D3986BB3558EE24",
        f"{os.getcwd()}/tests/utils/ssh/.ssh/eve.ssh")

commit_rules = {
    "rules": [
        {"rule": "require_signature", "allowed_keys": ".*.asc"},
        {"rule": "require_approval", "allowed_keys": ".*.asc", "threshold": 2}
    ]
}

def create_patch(commit:Commit, new_path):
    parents = commit.get_parents()
    parent = parents[0]
    patch_file = "/Users/ebonnici/Github/rev.patch"
    # print("creating patch for ", commit.hash)
    cmd(f"git diff {parent.hash} {commit.hash} > {patch_file}", shell=True)
    # modified_files, _ = cmd(f"grep '^+++' {patch_file} | sed -e 's#+++ [ab]/##'", shell=True)
    # print("modified files: ", modified_files)
    if commit.hash == "dbfed5c79d2aa8b09d0ec0f238e31259ff1662a9":
        sys.exit(1)
    try:
        cmd(f"git apply --reject -p1 < {patch_file}", shell=True, cwd=new_path)
    except:
        pass
    # cmd("git", "apply", patch_file, cwd=new_path)

def process_repo(path: str, new_path:str):
    head_commit, _ = cmd("git", "rev-parse", "HEAD")
    head_commit = Commit(head_commit)
    root_commit, _ = cmd("git", "rev-list", "--max-parents=0", head_commit.hash)
    root_commit = "5e0dfdac54e509a97483af1f78af09451c03bfbb"
    root_commit = Commit(root_commit)
    children_dict = add_children(head_commit)
    commit_to_branch = {}
    merge_commit_branch = {}
    queue = [root_commit]
    processed = set()
    branch_index = 0
    nr = 1

    def fill_commit_to_branch(main:Commit, feat:Commit, branch_idx):
        main_temp = main
        feat_temp = feat
        feat_branch = f"feat-{branch_idx}"
        
        # print("Main lane: ")
        while len(main_temp.get_parents()) < 2:
            # print(main_temp.hash, " => ", "main")
            commit_to_branch[main_temp.hash] = "main"
            main_children = children_dict[main_temp.hash]
            main_temp = main_children[0]
        # print("Merge ", main_temp.hash, " => ", feat_branch)
        merge_commit_branch[main_temp.hash] = feat_branch

        while len(feat_temp.get_parents()) < 2:
            commit_to_branch[feat_temp.hash] = feat_branch
            feat_children = children_dict[feat_temp.hash]
            feat_temp = feat_children[0]


    while len(queue) > 0:
        current = queue.pop(0)
        if current.hash not in processed:
            parents = current.get_parents()
            # print("processing ", current.hash)
            # print("Nr = ", nr)
            nr = nr + 1
            skip = False
            # print("Len of parens ", len(parents))
            if current.hash == root_commit.hash:
                handle_root(current, path, new_path)
            elif len(parents) <= 1:
                handle_commit(current, path, new_path, commit_to_branch)
            elif len(parents) == 2:
                if len(queue) > 0:
                    next = queue[0]
                    if next.hash in commit_to_branch and current.hash in merge_commit_branch:
                        if commit_to_branch[next.hash] == merge_commit_branch[current.hash]:
                            skip = True
                if not skip:
                    handle_merge(current, path, new_path, merge_commit_branch)
            
            
            children = []
            if current.hash in children_dict:
                children = children_dict[current.hash]
            
            if len(children) == 2:
                # Want to specify what branch each path should have
                # up to the merge commit
                # print("Filling commit to branch from ", current.hash)
                # print("Children = ", [child.hash for child in children])
                fill_commit_to_branch(children[0], children[1], branch_index)
                branch_index = branch_index + 1
                    
            if not skip:
                # print("processing ", current.hash)
                processed.add(current.hash)
                

                for child in reversed(children):
                    queue.append(child)
    
    



def handle_root(commit: Commit, path, new_path):

    cmd("git", "checkout", commit.hash)

    branch_name, _  = cmd("git", "rev-parse", "--abbrev-ref", "HEAD")
    # tmppath = "/Users/ebonnici/Github/temp"
    # os.mkdir(tmppath)

    # cmd(f"cp -a .git {tmppath}", shell=True, cwd=new_path)

    # # cmd(f"cp -a .gitbark {tmppath}", shell=True, cwd=new_path)
    # cmd(f"rm -rf {new_path}", shell=True)

    
    # os.mkdir(new_path)
    # cmd(f"cp -a {path}/. {new_path}", shell=True)
    
    # cmd(f"rm -rf .git", shell=True, cwd=new_path)
    # cmd(f"cp -a {tmppath}/. {new_path}", shell=True)

    # cmd(f"rm -rf {tmppath}", shell=True)

    cmd(f"rsync -aH --delete --exclude \'.git\' {path} {new_path}", shell=True)
    cmd("git", "checkout", "main")
    # cmd("rm -rf *", shell=True, cwd=new_path)
    # cmd(f"cp -a {path}/* {new_path}", shell=True)

    if not os.path.exists(f"{new_path}/.gitbark"):
        os.mkdir(f"{new_path}/.gitbark")
    
    with open(f"{new_path}/.gitbark/commit_rules.yaml", "w") as f:
        yaml.dump(commit_rules, f)

    os.mkdir(f"{new_path}/.gitbark/.pubkeys")

    pubkeys = ["Alice2.asc", "Bob2.asc"]

    pubkeys_path = f"{os.getcwd()}/tests/utils/gpg/.pubkeys"
    for pubkey in pubkeys:
            cmd("cp", f"{pubkeys_path}/{pubkey}", f"{new_path}/.gitbark/.pubkeys", cwd=new_path)

    cmd("git", "add", "-A", cwd=new_path)
    cmd("git", "commit", "-S", f"--gpg-sign={alice.gpg_key_id}", "-m", commit.get_commit_message(), cwd=new_path)

    bootstrap_hash, _ = cmd("git", "rev-parse", "HEAD", cwd=new_path)
    branch_rules = {
        "branches": [
            {"pattern": branch_name, "validate_from": bootstrap_hash,
             "allow_force_push": False}
        ]
    }
    cmd("git", "checkout", "--orphan", "branch_rules", cwd=new_path)
    cmd("rm -rf .gitbark", shell=True, cwd=new_path)

    if not os.path.exists(f"{new_path}/.gitbark"):
            os.mkdir(f"{new_path}/.gitbark")
    with open(f"{new_path}/.gitbark/branch_rules.yaml", "w") as f:
        yaml.dump(branch_rules, f)
    
    cmd("git", "add", ".", cwd=new_path)
    cmd("git", "commit", "-S", f"--gpg-sign={alice.gpg_key_id}", "-m", "Init branch rules", cwd=new_path)
    cmd("git", "checkout", "main", cwd=new_path)






def handle_merge(commit: Commit,  path, new_path, merge_commit_branch):
    # print("Handling merge")
    # parents = commit.get_parents()

    cmd("git", "checkout", "main", cwd=new_path)

    # create_patch(commit, new_path)
    try:
        branch_name = merge_commit_branch[commit.hash]
        merge_head_hash, _ = cmd("git", "rev-parse", branch_name, cwd=new_path)

    except Exception as e:
        branch_name = "tmp_branch"

        cmd("git", "checkout", "-b", branch_name, cwd=new_path)
        cmd("git", "checkout", "main", cwd=new_path)

        cmd("git", "reset", "--hard", "HEAD^", cwd=new_path)
        # print(merge_commit_branch)
        # raise e
        merge_head_hash, _ = cmd("git", "rev-parse", branch_name, cwd=new_path)
    
    
    merge_head = Commit(merge_head_hash)
    
    os.environ["TEST_WD"] = new_path
    globals.init()

    # with replace_stdin(StringIO("yes")): 
    approve_cmd(merge_head.hash, alice.gpg_key_id)
    # with replace_stdin(StringIO("yes")): 
    approve_cmd(merge_head.hash, bob.gpg_key_id)
    signatures = "\n".join(get_signatures(merge_head))
    # print("Approved")
    
    message = f"{commit.get_commit_message()}Including commit: {merge_head.hash}\n{signatures}"

    os.environ["TEST_WD"] = path
    globals.init()
    # cmd("git", "add", ".", cwd=new_path)
    try:
        cmd("git", "merge", "-S", f"--gpg-sign={alice.gpg_key_id}", "--no-ff", "-m", message, branch_name, cwd=new_path)
    except Exception as e:
        # raise e
        # create_patch(commit, new_path)
        cmd("git", "add", "-A", cwd=new_path)
        cmd("git", "commit", "-S", f"--gpg-sign={alice.gpg_key_id}", "-m", message, cwd=new_path)
    cmd("git", "branch", "-d", branch_name, cwd=new_path)


def branch_exists(branch_name, new_path):
    _, retcode = cmd2("git", "show-ref", "-q", "--heads", branch_name, cwd=new_path)
    if retcode == 0:
        return True
    else:
        return False

def handle_commit(commit: Commit, path, new_path, commit_to_branch):
    # print("Handling ", commit.hash)

    branch_name = "main"
    if commit.hash in commit_to_branch:
        branch_name = commit_to_branch[commit.hash]
    
    curr_branch, _  = cmd("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=new_path)

    if branch_name != curr_branch:
        if branch_exists(branch_name, new_path):
            cmd("git", "checkout", branch_name, cwd=new_path)
        else:
            cmd("git", "checkout", "-b", branch_name, cwd=new_path)
    
    create_patch(commit, new_path)

    # branch_name = "main"
    # if commit.hash in commit_to_branch:
    #     branch_name = commit_to_branch[commit.hash]
    
    # curr_branch, _  = cmd("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=new_path)

    # if branch_name != curr_branch:
    #     if branch_exists(branch_name, new_path):
    #         cmd("git", "checkout", branch_name, cwd=new_path)
    #     else:
    #         cmd("git", "checkout", "-b", branch_name, cwd=new_path)

    # Am I the child of a commit with two children.
    # If yes, then am I the second child, branch out
    # If not, commit on main

    # branch_name, _ = cmd(f"git log --branches --remotes --source | grep {commit.hash}", shell=True).split()[-1:]
    # curr_branch, _  = cmd("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=new_path)


         

    # branch_name = "feat-branche"
    # curr_branch, _  = cmd("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=new_path)

    # parents = commit.get_parents()
    # parent = parents[0]

    # children_of_parent = children[parent.hash]

    # if len(children_of_parent) > 1:
    #     second_child = children_of_parent[1]
    #     if commit.hash == second_child.hash and curr_branch != branch_name:
    #         cmd("git", "checkout", "-b", branch_name, cwd=new_path)
    #     else:
    #         cmd("git", "checkout", "main", cwd=new_path)

    # else:
        
    #     cmd("git", "checkout", "main", cwd=new_path)



    
    
    # if new_branch and curr_branch != branch_name:
    #     print("Went here")
    #     cmd("git", "checkout", "-b", branch_name, cwd=new_path)
    # except:
    #     cmd(f"rsync -aH --delete --exclude \'.git\' --exclude \'.gitbark\' {path} {new_path}", shell=True)

    # cmd("git", "checkout", commit.hash)


    # tmppath = "/Users/ebonnici/Github/temp"
    # os.mkdir(tmppath)

    # cmd(f"cp -a .git {tmppath}", shell=True, cwd=new_path)
    # cmd(f"cp -a .gitbark {tmppath}", shell=True, cwd=new_path)
    # cmd(f"rm -rf {new_path}", shell=True)

    
    # os.mkdir(new_path)
    # cmd(f"cp -a {path}/. {new_path}", shell=True)
    # cmd(f"rm -rf .git", shell=True, cwd=new_path)
    # cmd(f"cp -a {tmppath}/. {new_path}", shell=True)

    # cmd(f"rm -rf {tmppath}", shell=True)


    # cmd(f"rsync -aH --delete --exclude \'.git\' --exclude \'.gitbark\' {path} {new_path}", shell=True)
    # try:
    #     with replace_stdin(StringIO("y")): 
    #         cmd("rm -rf *", shell=True, cwd=new_path)
    # except:
    #      with replace_stdin(StringIO("y")): 
    #         cmd("rm *", shell=True, cwd=new_path)
    # cmd(f"cp -a {path}/* {new_path}", shell=True)

    cmd("git", "add", "-A", cwd=new_path)
    cmd("git", "commit", "-S", f"--gpg-sign={alice.gpg_key_id}","--allow-empty" , "-m", commit.get_commit_message(), cwd=new_path)

    # curr_branch, _ = cmd("git", "rev-parse", "--abbrev-ref", "HEAD")
    # tmp_branch = "tmp_branch"
    # cmd("git", "checkout", commit.hash, "-b", tmp_branch)
    # cmd("git", "commit", "-S", f"--gpg-sign={alice.gpg_key_id}", "--amend", "--no-edit")
    # _, retcode = cmd("git", "rebase", "--onto", tmp_branch, "HEAD", curr_branch)
    
    # if retcode:
    #     cont = True
    #     while cont:
    #         cmd("git", "add", ".")
            
    #         res, retcode2 = cmd("git", "rebase", "--continue", env=dict(os.environ, GIT_EDITOR='true'))
    #         print(res)
    #         print("Return code = ", retcode2)
    #         if retcode2 == 0:
    #             cont = False

    # cmd("git", "branch", "-d", tmp_branch)
    # print("Deleted ", tmp_branch)

def load_all_commits() -> list[Commit]:
    hashes, _  = cmd("git", "rev-list", "HEAD")
    hash_list = hashes.split()
    commits = []
    for hash in hash_list:
        commit = Commit(hash)
        commits.append(commit)

    return commits

def load_all_merge_commits() -> list[Commit]:
    hashes, _ = cmd("git", "rev-list")



path = sys.argv[1]
# new_path = sys.argv[2]
os.environ["GNUPGHOME"] = f"{os.getcwd()}/tests/utils/gpg/.gnupg"
os.environ["TEST_WD"] = path
globals.init()

load_all_commits()
# cmd("git", "init", cwd=new_path)
# process_repo(path, new_path)

