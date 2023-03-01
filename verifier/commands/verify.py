
import sys

from rules.commit_rules import validate_commit_rules
from rules.branch_rules import validate_branch_rules, get_branch_rules
from models.reference_update import ReferenceUpdate


def verify(ref_update:ReferenceUpdate = None):
    """ Verify Git repository

    Note: This function takes ref_update as an optional parameter. This is to allow running the function from 
    a reference-transaction hook and manually.
    """
    
    # Verify branch_rules
    branch_rules_valid = verify_branch(ref_update, "branch_rules")
    if not branch_rules_valid:
        print("Branch rules is not valid")
        return False

    # Extract branch_rules
    branch_rules = get_branch_rules()

    # Verify branches
    for rule in branch_rules:
        for branch_hash, branch_name in rule["branches"]:
            branch_valid = verify_branch(ref_update, branch_name, rule)
            if not branch_valid:
                print("Commit with hash ", branch_hash, " is invalid")
            else:
                print("Commit with hash ", branch_hash, " is valid")


def verify_branch(ref_update:ReferenceUpdate, branch_name, branch_rule=None):
    """Verify branch against branch rules and commit rules
    
    Branch rules and commit rules are dependent, meaning that if branch rules fails,
    commit rules will never run.
    """
    passes_branch_rules = validate_branch_rules(ref_update, branch_name, branch_rule)
    if not passes_branch_rules:
        return False
    
    passes_commit_rules = validate_commit_rules(branch_name, branch_rule)
    if not passes_commit_rules:
        return False
    return True


# updates_str = ""
# if len(sys.argv) > 1:
#     updates_str = sys.argv[1]

# updates = updates_str.split(',')

# ref_update = None

# if updates:
#     ref_update = ReferenceUpdate(updates)


if verify():
    sys.exit(0)
else:
    sys.exit(1)    











