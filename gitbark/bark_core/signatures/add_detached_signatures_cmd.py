from gitbark.git.commit import Commit
from gitbark.git.git import Git
from gitbark.cache import Cache
from gitbark.rules.commit_rules import is_commit_valid, find_nearest_valid_ancestors
from gitbark.rules.branch_rules import get_branch_rules
from gitbark.navigation import Navigation

import re
import sys

navigation = Navigation()
navigation.get_root_path()
git = Git()

def add_detached_signatures_cmd(commit_msg_filepath):
    
    branch_name = git.symbolic_ref("HEAD")
    branch_bootstrap = get_bootstrap_commit(branch_name)
    if not branch_bootstrap:
        return
    
    head = Commit(git.rev_parse("HEAD"))
    merge_head = None
    try:
        merge_head_hash = git.rev_parse("MERGE_HEAD")
        merge_head = Commit(merge_head_hash)
    except:
        print("error: no ongoing merge was found.")
        return
    
    cache = Cache()
    signature_threshold = get_signature_threshold(head, branch_bootstrap, cache)
    if not signature_threshold:
        return
    
    # Commits that require approvals
    require_approvals = []
    if not is_commit_valid(head, branch_bootstrap, cache):
        require_approvals.append(head)
    if not is_commit_valid(merge_head, branch_bootstrap, cache):
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
    with open(f"{navigation.wd}/{commit_msg_filepath}", "a") as f:
        f.write("\n"*2)
        for commit_hash in commit_to_signatures:
            f.write(f"Including commit: {commit_hash}\n")
            f.write("Approvals:\n")
            for signature in commit_to_signatures[commit_hash]:
                f.write(signature + "\n")


def get_and_fetch_signatures(commit: Commit, threshold):
    signatures = get_signatures(commit)
    if len(signatures) >= threshold:
        return signatures, None
    else:
        git.fetch("origin refs/signatures/*:refs/signatures/*")
        new_signatures = get_signatures(commit)
        if len(new_signatures) >= threshold:
            return new_signatures, None
        else:
            violation = f"Commit has {len(new_signatures)} out of {threshold} valid approvals"
            return new_signatures, violation

def get_signatures(commit:Commit):
    ref_hashes = git.for_each_ref(f"refs/signatures/{commit.hash}").split()
    signatures = []
    for ref_hash in ref_hashes:
        signature = git.get_object(ref_hash)
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

def get_signature_threshold(head:Commit, bootstrap: Commit, cache:Cache):
    threshold = None
    if is_commit_valid(head, bootstrap, cache):
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


    


# commit_msg_filepath = f"{navigation.wd}/{sys.argv[1]}"
# add_detached_signatures_cmd(commit_msg_filepath)
