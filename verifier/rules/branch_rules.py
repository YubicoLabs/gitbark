
from models.commit import Commit
from models.reference_update import ReferenceUpdate
from wrappers.git_wrapper import GitWrapper

import re
import yaml


def validate_branch_rules(ref_update:ReferenceUpdate, branch_name, branch_rule):
    if not ref_update:
        return True

    if not re.search(f"refs/.*/{branch_name}", ref_update.ref_name, re.M):
        return True

    if "allow_force_push" in branch_rule:
        passes_force_push = validate_force_push(ref_update, branch_rule["allow_force_push"])
        if not passes_force_push:
            #report.add_branch_rule_violation(f"Commit {ref_update.new_ref} is not a descendant of {ref_update.old_ref}", branch_name)
            return False

    return True


def validate_force_push(ref_update:ReferenceUpdate, allow_force_push):
    if not allow_force_push:
        current = Commit(ref_update.new_ref)
        old = Commit(ref_update.old_ref)
        return is_descendant(current, old)
    return True

def is_descendant(current: Commit, target: Commit):
    if target == None:
        return True
    if current.hash == target.hash:
        return True
    if len(current.get_parents()) == 0:
        return False

    parents = current.get_parents()
    for parent in parents:
        if is_descendant(parent, target):
            return True
    return False

def get_branch_rules():
    git = GitWrapper()
    branch_rules_head = git.get_ref("branch_rules").rstrip()
    branch_rules_commit = Commit(branch_rules_head)

    branch_rules = branch_rules_commit.get_blob_object("branch_rules.yaml")
    branch_rules = yaml.safe_load(branch_rules)
    branch_rules = branch_rules["branches"]

    # Find matching branches
    for rule in branch_rules:
        pattern = rule["pattern"]
        all_branches = git.get_heads()
        matching_branches = re.findall(f".*{pattern}", all_branches)
        rule["branches"] = [branch.split() for branch in matching_branches]
    
    return branch_rules

