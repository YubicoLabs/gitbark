
from models.commit import Commit
from models.reference_update import ReferenceUpdate
from wrappers.git_wrapper import GitWrapper

import re
import yaml


def validate_branch_rules(ref_update:ReferenceUpdate, branch_name, branch_rule):
    """Validates branch rules with respect to ReferenceUpdate
    
    Note: If no reference update, there is no need to evaluate branch_rules 
    """

    exact_branch_name = branch_name.split("/")
    exact_branch_name = exact_branch_name[-1]

    violations = []

    if not ref_update:
        return True, violations

    if not re.search(f"refs/.*/{exact_branch_name}", ref_update.ref_name, re.M):
        # Not evaluating branch rules if branch_name does not match the ref being updated
        return True, violations

    # Checks if allow_force_push is included as a rule in branch_rules
    # TODO: allow_force_push should be renamed to fast-forward-only
    if "allow_force_push" in branch_rule:
        passes_force_push = validate_force_push(ref_update, branch_rule["allow_force_push"])
        if not passes_force_push:
            violations.append(f"Incomming commit {ref_update.new_ref} is not fast-forward")
            return False, violations

    return True, violations


def validate_force_push(ref_update:ReferenceUpdate, allow_force_push):
    if not allow_force_push:
        current = Commit(ref_update.new_ref)
        old = Commit(ref_update.old_ref)
        return is_descendant(current, old)
    return True

def is_descendant(current: Commit, old: Commit):
    """Checks that the current tip is a descendant of the old tip"""

    if current.hash == old.hash:
        return True
    if len(current.get_parents()) == 0:
        return False

    parents = current.get_parents()
    for parent in parents:
        if is_descendant(parent, old):
            return True
    return False

def get_branch_rules():
    """Returns the latest branch_rules"""
    
    git = GitWrapper()
    branch_rules_head = git.rev_parse("branch_rules").rstrip()
    branch_rules_commit = Commit(branch_rules_head)

    branch_rules = branch_rules_commit.get_blob_object("branch_rules.yaml")
    branch_rules = yaml.safe_load(branch_rules)
    branch_rules = branch_rules["branches"]

    # Find matching branches
    for rule in branch_rules:
        pattern = rule["pattern"]
        all_branches = git.get_refs()
        matching_branches = re.findall(f".*{pattern}", all_branches)
        rule["branches"] = [branch.split() for branch in matching_branches]
    
    return branch_rules

