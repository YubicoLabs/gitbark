
import sys

from ..rules.commit_rules import validate_commit_rules
from ..rules.branch_rules import validate_branch_rules, get_branch_rules
from ..git.reference_update import ReferenceUpdate
from ..git.git import Git
from ..report import Report
from ..cache import Cache


def verify(ref_update: ReferenceUpdate = None):
    """ Verify Git repository

    Note: This function takes ref_update as an optional parameter. This is to allow running the function from 
    a reference-transaction hook and manually.
    """

    if ref_update:
        ref_update = ReferenceUpdate(ref_update)

    cache = Cache()
    report = Report()


    # Verify branch_rules
    branch_rules_valid = verify_branch(ref_update, "branch_rules", report=report, cache=cache)
    if not branch_rules_valid:
        # If branch_rules is invalid we wont be able to trustfully verify branches
        # Local branch_rules can never be invalid
        return 
        

    # Extract branch_rules
    branch_rules = get_branch_rules()

    if ref_update:
        relevant_refs = get_relevant_refs(branch_rules)
        if not ref_update.ref_name in relevant_refs:
            return

    
    # If reference_update, only check specific ref
    if ref_update:
        for rule in branch_rules:
            branch_names = [entry[1] for entry in rule["branches"]]
            if ref_update.ref_name in branch_names:
                verify_branch(ref_update, ref_update.ref_name, report=report, cache=cache, branch_rule=rule)
    
    else:
        # Verify all branches defined in branch_rules
        for rule in branch_rules:
            for _,branch_name in rule["branches"]:
                verify_branch(ref_update, branch_name, report=report, cache=cache, branch_rule=rule)
        
    cache.dump()
    # Print integrity report
    report.print_report()

    # Abort reference transaction
    if ref_update:
        exit_status = ref_update.exit_status
        if exit_status == 1:
            # If local changes are updated with remote
            git = Git()
            git.restore_files()
        sys.exit(ref_update.exit_status)


def verify_branch(ref_update:ReferenceUpdate, branch_name, report:Report, cache:Cache, branch_rule=None):
    """Verify branch against branch rules and commit rules
    
    Branch rules and commit rules are dependent, meaning that if branch rules fails,
    commit rules will never run.
    """

    # If ref_update and it matches branch_name, then validate_branch_rules
    passes_branch_rules, branch_rule_violations = validate_branch_rules(ref_update, branch_name, branch_rule)
    if not passes_branch_rules:
        branch_rule_violations_action(branch_rule_violations, branch_name, report, ref_update)
        return False
    
    # If ref_update and it matches branch_name, send ref_update to commit_rules, else not
    passes_commit_rules, commit_rule_violations = validate_commit_rules(ref_update, branch_name, branch_rule, cache)
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


def should_evaluate_branch_rules(ref_update: ReferenceUpdate, branch_name):
    if not ref_update:
        return False
    if not ref_update.ref_name == branch_name:
        return False
    return True


def get_relevant_refs(branch_rules):
    relevant_refs = []
    for rule in branch_rules:
        branch_names = [entry[1] for entry in rule["branches"]]
        relevant_refs.extend(branch_names)
    return relevant_refs



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














