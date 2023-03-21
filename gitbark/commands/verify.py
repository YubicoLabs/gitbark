
import sys
import re
from ..rules.commit_rules import validate_commit_rules
from ..rules.branch_rules import validate_branch_rules, get_branch_rules
from ..git.reference_update import ReferenceUpdate
from ..git.git import Git
from ..report import Report
from ..cache import Cache

# Should be able to take as input branch, commit and boostrap
def verify(all:bool=False, ref_update: ReferenceUpdate = None) -> Report: 
    """ Verify Git repository

    Note: This function takes ref_update as an optional parameter. This is to allow running the function from 
    a reference-transaction hook and manually.
    """
    
    cache = Cache()
    report = Report()

    if ref_update:
        return verify_ref_update(ReferenceUpdate(ref_update), cache, report)
    elif all:
        return verify_all(cache, report)
    else:
        return verify_current_branch(cache, report)


def verify_all(cache: Cache, report: Report):
    if not verify_branch("branch_rules", report, cache):
        cache.dump()
        return report
    
    branch_rules = get_branch_rules()

    for rule in branch_rules:
        for _, branch_name in rule["branches"]:
            verify_branch(branch_name, report, cache, branch_rule=rule)
    if ref_exists("refs/remotes/origin/branch_rules"):
        verify_branch("refs/remotes/origin/branch_rules", report, cache)
    
    cache.dump()
    handle_exit(report)
    return report

def verify_ref_update(ref_update: ReferenceUpdate, cache: Cache, report: Report):
    if ref_update.is_ref_deletion():
        return report
    
    if not verify_branch("branch_rules", report, cache, ref_update=ref_update):
        cache.dump()
        return report
    
    branch_rules = get_branch_rules()

    for rule in branch_rules:
        pattern = rule["pattern"]
        short_branch_name = ref_update.ref_name.split("/")
        short_branch_name = short_branch_name[-1]

        if re.search(pattern, short_branch_name):
            verify_branch(ref_update.ref_name, report, cache, ref_update=ref_update, branch_rule=rule)
    
    cache.dump()
    handle_exit(report, ref_update)
    return report

def verify_current_branch(cache:Cache, report: Report):
    if not verify_branch("branch_rules", report, cache):
        cache.dump()
        return report
    
    branch_rules = get_branch_rules()
    git = Git()
    branch_name = git.symbolic_ref("HEAD", short=False)

    for rule in branch_rules:
        branch_names = [entry[1] for entry in rule["branches"]]
        if branch_name in branch_names:
            verify_branch(branch_name, report, cache, branch_rule=rule)
    
    cache.dump()
    handle_exit(report)
    return report

def ref_exists(ref_name):
    git = Git()
    try:
        git.get_ref(ref_name)
        return True
    except:
        return False


def handle_exit(report:Report, ref_update: ReferenceUpdate = None):
    report.print_report()
    if ref_update:
        exit_status = ref_update.exit_status
        if exit_status == 1:
            # If local changes are updated with remote
            git = Git()
            git.restore_files()
        sys.exit(ref_update.exit_status)


def verify_branch(branch_name, report:Report, cache:Cache, ref_update:ReferenceUpdate = None, branch_rule=None):
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














