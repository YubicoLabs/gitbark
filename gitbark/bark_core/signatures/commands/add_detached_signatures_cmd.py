from gitbark.git.commit import Commit
from gitbark.git.git import Git
from gitbark.cache import Cache
from gitbark.rules.commit_rules import is_commit_valid, find_nearest_valid_ancestors
from gitbark.rules.branch_rules import get_branch_rules
from gitbark.wd import WorkingDirectory

import re
import sys

def add_detached_signatures_cmd(commit_msg_filepath):
    git = Git()
    branch_name = git.symbolic_ref("HEAD")
    branch_bootstrap = get_bootstrap_commit(branch_name)
    if not branch_bootstrap:
        return
    
    head_hash = git.repo.revparse_single("HEAD").id.__str__()
    head = Commit(head_hash)
    merge_head = None
    try:
        merge_head_hash = git.repo.revparse_single("MERGE_HEAD").id.__str__()
        merge_head = Commit(merge_head_hash)
    except:
        print("error: no ongoing merge was found.")
        return
    
    cache = Cache()
    signature_threshold = get_signature_threshold(head, branch_bootstrap, cache, branch_name)
    if not signature_threshold:
        return
    
    # Commits that require approvals
    require_approvals = []
 
    require_approvals.append(merge_head)

    commit_to_signatures = {}
    violations = []

    for commit in require_approvals:
        signatures, violation = get_and_fetch_signatures(commit, signature_threshold)
        if violation:
            violations.append(violation)
        else:
            commit_to_signatures[commit.hash] = signatures

    if len(violations) > 0:
        commit_hashes = [commit.hash for commit in require_approvals]
        commit_hashes_str = " and ".join(commit_hashes)
        print(f"Error: incoming commits {commit_hashes_str} are missing valid approvals")
        for violation in violations:
            print("  -", violation)
        print("\nAborting merge commit")
        sys.exit(1)
        return
    else:
        commit_hashes = commit_to_signatures.keys()
        commit_hashes_str = " and ".join(commit_hashes)
        print(f"Valid approvals were found for commit {commit_hashes_str}.")
        sys.stdin = open("/dev/tty", "r")

        accept = input("Do you want to include them in the commit message (yes/no)? ")
        if accept == "yes":
            write_to_commit_message(commit_to_signatures, commit_msg_filepath)
        else:
            sys.exit(1) 


def write_to_commit_message(commit_to_signatures, commit_msg_filepath):
    working_directory = WorkingDirectory()
    with open(f"{working_directory.wd}/{commit_msg_filepath}", "w") as f:
        f.write("\n"*2)
        for commit_hash in commit_to_signatures:
            f.write(f"Including commit: {commit_hash}\n")
            f.write("Approvals:\n")
            for signature in commit_to_signatures[commit_hash]:
                f.write(signature + "\n")


def get_and_fetch_signatures(commit: Commit, threshold):
    git = Git()
    signatures = get_signatures(commit)
    if len(signatures) >= threshold:
        return signatures, None
    else:
        try:
            git.fetch("origin refs/signatures/*:refs/signatures/*")
        except:
            pass
        new_signatures = get_signatures(commit)
        if len(new_signatures) >= threshold:
            return new_signatures, None
        else:
            violation = f"Commit has {len(new_signatures)} out of {threshold} valid approvals"
            return new_signatures, violation

def get_signatures(commit:Commit):
    git = Git()
    signature_refs = git.get_refs(f"refs/signatures/{commit.hash}/*")

    signatures = []
    for ref in signature_refs:
        signature = git.get_object(ref.target.__str__()).read_raw().decode()
        signatures.append(signature)
    return signatures


def get_bootstrap_commit(branch_name):
    branch_rules = get_branch_rules()
    for branch_rule in branch_rules:
        pattern = branch_rule["pattern"]
        if re.search(pattern, branch_name):
            boostrap_hash = branch_rule["validate_from"]
            bootstrap_commit = Commit(boostrap_hash)
            return bootstrap_commit
    return None

def get_signature_threshold(head:Commit, bootstrap: Commit, cache:Cache, branch_name):
    threshold = None
    if is_commit_valid(head, bootstrap, cache, branch_name):
        commit_rules = head.get_rules()["rules"]
        for rule in commit_rules:
            if "rule" in rule and rule["rule"] == "require_approval":
                threshold = rule["threshold"]
                break
    else:
        nearest_valid_ancestors = find_nearest_valid_ancestors(head, bootstrap, cache)
        for ancestor in nearest_valid_ancestors:
            commit_rules = ancestor.get_rules()["rules"]
            for rule in commit_rules:
                if "rule" in rule and rule["rule"] == "require_approval":
                    if not threshold:
                        threshold = rule["threshold"]
                    elif rule["threshold"] > threshold:
                        threshold = rule["threshold"]

    return threshold