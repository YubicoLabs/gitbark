
import sys

from rules.commit_rules import validate_commit_rules
from rules.branch_rules import validate_branch_rules, get_branch_rules
from models.reference_update import ReferenceUpdate
from models.report import Report

def verify(ref_update:ReferenceUpdate = None):
    """ Verify Git repository

    Note: This function takes ref_update as an optional parameter. This is to allow running the function from 
    a reference-transaction hook and manually.
    """
    report = Report()
    
    # Verify branch_rules
    branch_rules_valid = verify_branch(ref_update, "branch_rules", report=report)
    if not branch_rules_valid:
        print("Branch rules is not valid")
        return False

    # Extract branch_rules
    branch_rules = get_branch_rules()

    # Verify branches
    for rule in branch_rules:
        for _,branch_name in rule["branches"]:
            verify_branch(ref_update, branch_name, report=report, branch_rule=rule)
    
    # Print integrity report
    report.print_report()

def verify_branch(ref_update:ReferenceUpdate, branch_name, report:Report, branch_rule=None):
    """Verify branch against branch rules and commit rules
    
    Branch rules and commit rules are dependent, meaning that if branch rules fails,
    commit rules will never run.
    """
    passes_branch_rules, branch_rule_violations = validate_branch_rules(ref_update, branch_name, branch_rule)
    if not passes_branch_rules:
        branch_rule_violations_action(branch_rule_violations, branch_name, report, ref_update)
        return False
    
    passes_commit_rules, commit_rule_violations = validate_commit_rules(branch_name, branch_rule)
    if not passes_commit_rules:
        commit_rule_violations_action(commit_rule_violations, branch_name, report, ref_update)
        return False
    return True

def branch_rule_violations_action(violations, branch_name, report:Report, ref_update:ReferenceUpdate):
    if ref_update.is_on_local_branch():
        # If invalid update on local branch, it has to be resetted
        ref_update.reset_update()
        report.add_branch_reference_reset(branch_name, ref_update)
    report.add_branch_rule_violations(branch_name, violations)


def commit_rule_violations_action(violations, branch_name, report:Report, ref_update:ReferenceUpdate):
    if ref_update and ref_update.ref_name == branch_name and ref_update.is_on_local_branch():
        ref_update.reset_update()
        report.add_branch_reference_reset(branch_name, ref_update)
    report.add_commit_rule_violations(branch_name, violations)



def parse_input():
    if len(sys.argv) > 1:
        ref_update_arr = sys.argv[1]
        ref_updates = ref_update_arr.split(',')

        # Updates to HEAD or ORIG_HEAD won't be taken into consideration
        valid_updates = []
        for ref_update in ref_updates:
            _,_,ref_name = ref_update.split()
            if ref_name not in ["HEAD", "ORIG_HEAD"]:
                valid_updates.append(ReferenceUpdate(ref_update))
        if len(valid_updates) > 0:
            return valid_updates[0]
    else:
        return None 


ref_update = parse_input()

verify(ref_update)













