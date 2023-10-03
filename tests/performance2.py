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
    cmd("git", "checkout", commit.hash)
    cmd(f"rsync -aH --delete --exclude={{\'.git\',\'.gitbark\'}} {path} {new_path}", shell=True)
    # parents = commit.get_parents()
    # parent = parents[0]
    # patch_file = "/Users/ebonnici/Github/rev.patch"
    # # print("creating patch for ", commit.hash, " using parent = ", parent.hash)
    # cmd(f"git diff {parent.hash} {commit.hash} > {patch_file}", shell=True)
    # # modified_files, _ = cmd(f"grep '^+++' {patch_file} | sed -e 's#+++ [ab]/##'", shell=True)
    # # print("modified files: ", modified_files)
    # if commit.hash == "dbfed5c79d2aa8b09d0ec0f238e31259ff1662a9":
    #     sys.exit(1)
    # try:
    #     cmd(f"git apply -p1 < {patch_file}", shell=True, cwd=new_path)
    # except Exception as e:
    #     ans = input("Handle apply fail. Make your changes and proceed with enter: ")
    #     # current_branch, _ = cmd("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=new_path)
    #     # print("current branch = ", current_branch)
    #     # print("creating patch for ", commit.hash, " using parent = ", parent.hash)
    #     # print(e)
    #     # exit(1)
    #     pass
    # cmd("git", "apply", patch_file, cwd=new_path)

def process_repo(path: str, new_path:str):
    head_commit, _ = cmd("git", "rev-parse", "HEAD")
    head_commit = Commit(head_commit)
    root_commit, _ = cmd("git", "rev-list", "--max-parents=0", head_commit.hash)
    # root_commit = "eb81782cdbdc68aaebe4fa561b5fbb73ef866611"
    # root_commit = "5e0dfdac54e509a97483af1f78af09451c03bfbb"
    # root_commit = "5e0dfdac54e509a97483af1f78af09451c03bfbb"
    root_commit = Commit(root_commit)
    children_dict = add_children(head_commit)
    commit_to_branch = {}
    real_commit_to_commit = {}
    from_commit = {}
    merge_commit_branch = {}
    merge_to_branch = {}
    queue = [root_commit]
    processed = set()
    branch_index = 0
    nr = 1

    def fill_commit_to_branch(main:Commit, feat:Commit, branch_idx, parent_hash):
        main_temp = main
        feat_temp = feat
        feat_branch = f"feat-{branch_idx}"

        current_branch, _ = cmd("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=new_path)
        if main_temp.hash == "3dfa677ede716cb7dd7026f47dc764fcabe1c823":
            current_branch = "main"
            feat_branch = f"feat-{branch_idx-1}"

        # Go until we find the commit which has main_temp and feat_temp as parents

        merge_temp = main

        while len(main_temp.get_parents()) < 2: 
            commit_to_branch[main_temp.hash] = current_branch
            print("Commit ", main_temp.hash, " on ", current_branch)
            main_children = children_dict[main_temp.hash]
            # print("Children = ", [c.hash for c in main_children])
            main_temp = main_children[0]
            # if len(main_children) == 2:
            #     main_temp = main_children[1]
            # else:
            #     main_temp = main_children[0]

        print("Merge ", main_temp.hash, " => ", feat_branch)
        merge_to_branch[main_temp.hash] = current_branch
        merge_commit_branch[main_temp.hash] = feat_branch

        merge_parents = [c.hash for c in main_temp.get_parents()]

        # print("Setting checkout from for", feat_temp.hash, " = ", parent_hash)
        from_commit[feat_temp.hash] = parent_hash

        prev_feat = feat_temp
        while len(feat_temp.get_parents()) < 2:
            commit_to_branch[feat_temp.hash] = feat_branch
            print("Commit ", feat_temp.hash, " on ", feat_branch)
            
            feat_children = children_dict[feat_temp.hash]
            # print("Children = ", [c.hash for c in feat_children])
            prev_feat = feat_temp

            if feat_temp.hash in merge_parents:
                break
            # feat_temp = feat_children[0]
            if len(feat_children) == 2:
                feat_temp = feat_children[1]
            else:
                feat_temp = feat_children[0]
        
        print("Stopped at ", feat_temp.hash)
        merge_commit_branch[main_temp.hash] = prev_feat.hash
        
        
        print("reach merge commit ", feat_temp.hash)

    most_recent_commit = None
    while len(queue) > 0:
        current = queue.pop(0)
        if current.hash not in processed:
            parents = current.get_parents()
            print("processing ", current.hash)
            print("Nr = ", nr)
            nr = nr + 1

            children = []
            if current.hash in children_dict:
                children = children_dict[current.hash]
            
            

            if current.hash == root_commit.hash:
                most_recent_commit = handle_root(current, path, new_path, real_commit_to_commit)
            elif len(parents) <= 1:
                most_recent_commit = handle_commit(current, path, new_path, commit_to_branch, from_commit, real_commit_to_commit)
            elif len(parents) == 2:
                most_recent_commit = handle_merge(current, path, new_path, merge_commit_branch, merge_to_branch, real_commit_to_commit)


            # if len(children) == 2:
            #     # Want to specify what branch each path should have
            #     # up to the merge commit
                
            #     print("Filling commit to merge from ", current.hash)
            #     branch_index = branch_index + 1
            #     if is_merge_commit(children[1]):
            #         new_child = children_dict[children[1].hash][0]
            #         fill_commit_to_branch(new_child, children[0], branch_index, most_recent_commit)
            #     elif is_merge_commit(children[0]):
            #         new_child = children_dict[children[0].hash][0]
            #         fill_commit_to_branch(children[1], new_child, branch_index, most_recent_commit)
            #     else:
            #         # print("Children = ", [child.hash for child in children])
            #         fill_commit_to_branch(children[1], children[0], branch_index, most_recent_commit)
                

            for child in reversed(children):
                if is_merge_commit(child):
                    # If the merge commit has 1 out of 2 processed we append
                    merge_commit_parents = child.get_parents()
                    nr_of_procssed = 0
                    not_processed = []
                    for p in merge_commit_parents:
                        if p.hash in processed:
                            nr_of_procssed = nr_of_procssed + 1
                        if p.hash not in processed:
                            not_processed.append(p)
                    # If a child of the merge commit has not been processed it must be the next thing we do
                    # so we push that to the front of the queue and add the merge commit right after

                    if nr_of_procssed >= 1:
                        queue.append(child)
                else:
                    queue.append(child)
            
            processed.add(current.hash)
            # print("State of the queue: ")
            # for c in queue:
            #     print(c.hash)
    
    

def is_merge_commit(commit: Commit):
    parents = commit.get_parents()
    return len(parents) >= 2


def handle_root(commit: Commit, path, new_path, real_commit_to_commit):

    cmd("git", "checkout", commit.hash)

    branch_name, _  = cmd("git", "rev-parse", "--abbrev-ref", "HEAD")

    branch_name = "master"
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
    cmd("git", "checkout", branch_name)
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
            {"pattern": "main", "validate_from": bootstrap_hash,
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

    os.environ["TEST_WD"] = new_path
    globals.init()

    real_bootstrap = Commit(bootstrap_hash)
    real_commit_to_commit[commit.hash] = real_bootstrap

    os.environ["TEST_WD"] = path
    globals.init()

    return real_bootstrap



def handle_merge(commit: Commit,  path, new_path, merge_commit_branch, merge_to_branch, real_commit_to_commit):

    parents = commit.get_parents()

    real_parents = [real_commit_to_commit[p.hash] for p in parents]

    first_parent, second_parent = real_parents

    # ans = input(f"Should I merge {parents[0].hash} with {parents[1].hash}, using {commit.hash}: y/n?")
    # if ans == "n":
    #     exit(1)
    # print(f"Should I merge {parents[0].hash} with {parents[1].hash}, using {commit.hash}: y/n?")

    # Checkout the first parent
    cmd("git", "checkout", first_parent.hash, cwd=new_path)

    # Handle merge head
    os.environ["TEST_WD"] = new_path
    globals.init()

    merge_head = Commit(second_parent.hash)

    approve_cmd(merge_head.hash, alice.gpg_key_id)
    approve_cmd(merge_head.hash, bob.gpg_key_id)
    signatures = "\n".join(get_signatures(merge_head))
    
    message = f"{commit.get_commit_message()}Including commit: {merge_head.hash}\n{signatures}"

    os.environ["TEST_WD"] = path
    globals.init()

    try:
        cmd("git", "merge", "-S", f"--gpg-sign={alice.gpg_key_id}", "--no-ff", "-m", message, second_parent.hash, cwd=new_path)
    except Exception as e:
        # raise e
        # create_patch(commit, new_path)
        cmd("git", "add", "-A", cwd=new_path)
        cmd("git", "commit", "-S", f"--gpg-sign={alice.gpg_key_id}", "-m", message, cwd=new_path)

    
    merge_hash, _ = cmd("git", "rev-parse", "HEAD", cwd=new_path)

    os.environ["TEST_WD"] = new_path
    globals.init()
    merge_commit = Commit(merge_hash)

    os.environ["TEST_WD"] = path
    globals.init()

    real_commit_to_commit[commit.hash] = merge_commit
    return merge_commit




    if commit.hash in merge_to_branch:
        merge_to = merge_to_branch[commit.hash]

    cmd("git", "checkout", merge_to, cwd=new_path)

    # create_patch(commit, new_path)
    try:
        merge_head_hash = merge_commit_branch[commit.hash]
        merge_head_hash = real_commit_to_commit[merge_head_hash]
        # branch_name = merge_commit_branch[commit.hash]
        # merge_head_hash, _ = cmd("git", "rev-parse", branch_name, cwd=new_path)

        
    except Exception as e:
        print("Exception on merge!!!!!!!!")
        branch_name = "tmp_branch"

        cmd("git", "checkout", "-b", branch_name, cwd=new_path)
        cmd("git", "checkout", "main", cwd=new_path)

        cmd("git", "reset", "--hard", "HEAD^", cwd=new_path)
        # print(merge_commit_branch)
        # raise e
        merge_head_hash, _ = cmd("git", "rev-parse", branch_name, cwd=new_path)
    
    # print()
    ans = input(f"Should I merge {merge_head_hash} to {merge_to}, using {commit.hash}: y/n?")
    if ans == "n":
        exit(1)


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
        cmd("git", "merge", "-S", f"--gpg-sign={alice.gpg_key_id}", "--no-ff", "-m", message, merge_head_hash, cwd=new_path)
        
    except Exception as e:
        # raise e
        # create_patch(commit, new_path)
        cmd("git", "add", "-A", cwd=new_path)
        cmd("git", "commit", "-S", f"--gpg-sign={alice.gpg_key_id}", "-m", message, cwd=new_path)
    merge_hash, _ = cmd("git", "rev-parse", "HEAD", cwd=new_path)
    # cmd("git", "branch", "-D", branch_name, cwd=new_path)
    print("Commiting merge", commit.hash, " => ", merge_hash, " with branch = ", merge_head_hash, " to ", merge_to)
    # print("The merge hash = ", merge_hash)

    current_branch, _ = cmd("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=new_path)
    print("current branch after merge = ", current_branch)
    return merge_hash


def branch_exists(branch_name, new_path):
    _, retcode = cmd2("git", "show-ref", "-q", "--heads", branch_name, cwd=new_path)
    if retcode == 0:
        return True
    else:
        return False

def handle_commit(commit: Commit, path, new_path, commit_to_branch, from_commit, real_commit_to_commit):
    # print("Handling ", commit.hash)

    parents = commit.get_parents()
    parent = parents[0]
    real_parent = real_commit_to_commit[parent.hash]

    # Checkout to parent
    # ans = input(f"Should I checkout out to {real_parent.hash}, using {commit.hash}: y/n?")
    # print(f"Should I checkout out to {real_parent.hash}, using {commit.hash}")
    # if ans == "n":
    #     exit(1)
    
    cmd("git", "checkout", real_parent.hash, cwd=new_path)

    # Create the patch
    create_patch(commit, new_path)

    cmd("git", "add", "-A", cwd=new_path)
    cmd("git", "commit", "-S", f"--gpg-sign={alice.gpg_key_id}", "--allow-empty" , "-m", commit.get_commit_message(), cwd=new_path)

    commit_hash, _ = cmd("git", "rev-parse", "HEAD", cwd=new_path)

    os.environ["TEST_WD"] = new_path
    globals.init()
    real_commit = Commit(commit_hash)

    os.environ["TEST_WD"] = path
    globals.init()

    real_commit_to_commit[commit.hash] = real_commit

    return real_commit



    branch_name, _ = cmd("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=new_path)
    # print(branch_name)
    if commit.hash in commit_to_branch:
        branch_name = commit_to_branch[commit.hash]

    checkout_from = None    
    if commit.hash in from_commit:
        checkout_from = from_commit[commit.hash]
        
    
    curr_branch, _  = cmd("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=new_path)
    # print("The current branch = ", curr_branch)

    if branch_name != curr_branch:
        # print("branch name = ", branch_name)
        # print("current branch = ", curr_branch)
        ans = input(f"Should I checkout out to {branch_name}, using {commit.hash}: y/n?")
        if ans == "n":
            exit(1)
        if branch_exists(branch_name, new_path):
            cmd("git", "checkout", branch_name, cwd=new_path)
        else:
            print("Checking out to ", branch_name)
            if checkout_from:
                cmd("git", "checkout", "-b", branch_name, checkout_from, cwd=new_path)
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
    cmd("git", "commit", "-S", f"--gpg-sign={alice.gpg_key_id}", "--allow-empty" , "-m", commit.get_commit_message(), cwd=new_path)

    commit_hash, _ = cmd("git", "rev-parse", "HEAD", cwd=new_path)

    curr_branch, _  = cmd("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=new_path)
    print("Comitting ", commit.hash, " => ", commit_hash, " on ", curr_branch)

    real_commit_to_commit[commit.hash] = commit_hash

    return commit_hash

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
    



path = sys.argv[1]
new_path = sys.argv[2]
os.environ["GNUPGHOME"] = f"{os.getcwd()}/tests/utils/gpg/.gnupg"
os.environ["TEST_WD"] = path
globals.init()
cmd("git", "init", cwd=new_path)
process_repo(path, new_path)

