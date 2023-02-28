
import sys

from rules.commit_rules import validate_commit_rules
from rules.branch_rules import validate_branch_rules, get_branch_rules
from models.reference_update import ReferenceUpdate


# Only perform verification on the working branch. For instance if you're commiting to
# refs/head/main, verification will be done on that particular branch. If you're pulling from the remote, new changes from all branches
# need to be validated. When pushing, only the working branch needs to be validated.

# Steps:
# 1. Read the trigger type: COMMIT, PUSH, PULL, CHECKOUT, MERGE
# 2. If COMMIT
# 2.1 Give the commit hash as input to verify
# 2.2 If the commit is not valid, refuse changes
# 2.3 Otherwise let them in
# 3. PUSH (same as COMMIT)
# 4. PULL (same as COMMIT)
# 5. CHECKOUT (same as COMMIT)
# 6. MERGE (same as COMMIT) 

def verify(ref_update:ReferenceUpdate = None):
    
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
    passes_branch_rules = validate_branch_rules(ref_update, branch_name, branch_rule)
    if not passes_branch_rules:
        return False
    
    passes_commit_rules = validate_commit_rules(branch_name, branch_rule)
    if not passes_commit_rules:
        return False

    return True


updates_str = sys.argv[1]

updates = updates_str.split(',')



if verify():
    sys.exit(0)
else:
    sys.exit(1)    











