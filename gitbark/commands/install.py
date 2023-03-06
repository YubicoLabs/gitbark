
from ..commit import Commit
from ..commands.verify import verify_branch
from ..git_api import GitApi
from ..cache import Cache
from ..report import Report

import os

WD = "/Users/ebonnici/Github/MasterProject/test-repo"

def install():
    git = GitApi()
    branch_rules_head = git.rev_parse("branch_rules").rstrip()
    branch_rules_commit = Commit(branch_rules_head)
    root  = get_root_commit(branch_rules_commit)
    # print("Installing bark!")

    if is_installed(root):
        # print("Already installed")
        return True
    else:
        print("Looks like you have not confirmed the root commit of the branch_rules branch")
        print(f"The SHA hash of root commit is {root.hash}.")
        answer = input("Are you sure you want to continue (yes/no)? ")

        if answer == "no":
            return False
        else:
            cache = Cache()
            report = Report()
            branch_rules_valid = verify_branch(None, "branch_rules", report, cache)
            if branch_rules_valid:
                # print("Installed successfully")
                write_root_hash(root)
                return True
            else:
                report.print_report()
                return False




def write_root_hash(root:Commit):
    gitbark_path = f"{WD}/.git/.gitbark"
    root_commit_path = f"{gitbark_path}/root_commit"
    if not os.path.exists(gitbark_path):
        os.mkdir(gitbark_path)
    
    with open(root_commit_path, 'w') as f:
        f.write(root.hash)


def is_installed(root: Commit):
    root_path = f"{WD}/.git/.gitbark/root_commit"
    if os.path.exists(root_path):
        with open(root_path, 'r') as f:
            root_hash = f.read()
            if root.hash == root_hash:
                return True
            else:
                return False

    else:
        return False


def get_root_commit(head: Commit):
    parents = head.get_parents()
    if len(parents) == 0:
        return head
    
    for parent in parents:
        return get_root_commit(parent)

    


