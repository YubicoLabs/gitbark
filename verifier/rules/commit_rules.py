
import re
import pgpy

from models.commit import Commit
from wrappers.git_wrapper import GitWrapper

import warnings
warnings.filterwarnings("ignore")


def validate_commit_rules(branch_name, branch_rule):
    """Validates commit rules on branch"""

    current_commit, bootstrap_commit = get_head_and_bootstrap(branch_name, branch_rule)

    is_branch_rules_branch = True if branch_name == "branch_rules" else False

    valid_commits = {}

    def is_commit_valid(commit: Commit):
        """Recursively validates a commit by using its parents as validators
        
        Note: The commit is considered valid if it passes the commit rules of all its validator 
        ancestors. The validators are defined in the following way:
            - If the parent of x itself is valid, the parent becomes a validator of x
            - If the parent of x is not valid, x inherits all Validators that the parent has
        """ 

        # Bootstrap commit is explicitly trusted
        if not is_branch_rules_branch and commit.hash == bootstrap_commit.hash:
            valid_commits[commit.hash] = True
            return True
   
        parents = commit.get_parents()

        # If commit rules are evaluated against branch_rules branch,
        # the root commit is the bootstrap commit.
        if is_branch_rules_branch and len(parents) == 0:
            valid_commits[commit.hash] = True
            return True
        
        validators = []
        for parent in parents:
            if is_commit_valid(parent):
                validators.append(parent)
            else:
                nearest_valid_ancestors = find_nearest_valid_ancestors(parent)
                validators.extend(nearest_valid_ancestors)

        
        for validator in validators:
            if not validate_rules(commit, validator, valid_commits):
                return False
        valid_commits[commit.hash] = True
        return True

    def find_nearest_valid_ancestors(commit:Commit, valid_ancestors=[]):
        """Return the nearest valid ancestors"""
        parents = commit.get_parents()
        for parent in parents:
            if parent.hash in valid_commits:
                valid_ancestors.append(parent)
            else:
                nearest_valid_ancestors = find_nearest_valid_ancestors(parent, valid_ancestors)
                valid_ancestors.extend(nearest_valid_ancestors)
        return valid_ancestors
    
    passes_commit_rules = is_commit_valid(current_commit)
    return passes_commit_rules, current_commit.violations

def get_head_and_bootstrap(branch_name, branch_rule):
    git = GitWrapper()
    current_head = git.rev_parse(branch_name).rstrip()
    current_commit = Commit(current_head)
    if branch_name != "branch_rules":
        boostrap_hash = branch_rule["validate_from"]
        boostrap_commit = Commit(boostrap_hash)
        return current_commit, boostrap_commit
    return current_commit, None

def validate_rules(commit:Commit, validator: Commit, valid_commits):
    rules = validator.get_rules()
    rules = rules["rules"]

    passes_rules = True
    any_rule_index = 1
    for rule in rules:
        if "any" in rule:
            sub_rules = rule["any"]
            rule_name = ""
            if "name" in sub_rules:
                rule_name = sub_rules["name"]
            else:
                rule_name = any_rule_index
                any_rule_index += 1
            if not any(validate_rule(commit, validator, sub_rule, valid_commits, rule_name) for sub_rule in sub_rules):
                # If none of the "any" rules are followed, we must give a reason for why that is
                passes_rules = False
        else:
            if not validate_rule(commit, validator, rule, valid_commits):
                passes_rules = False

    return passes_rules

def validate_rule(commit: Commit, validator:Commit, rule, valid_commits, any_clause_name=None):
    rule_name = rule["rule"]

    if rule_name == "require_signature":
        return validate_signatures(commit, validator, rule, any_clause_name)
    if rule_name == "file_not_modified":
        return validate_file_modification(commit, validator, rule, any_clause_name)
    if rule_name == "disallow_invalid_parents":
        return validate_invalid_parents(commit, rule, valid_commits, any_clause_name)
    if rule_name == "require_number_of_parents":
        return validate_number_of_parents(commit, rule, any_clause_name)


    return True



####### SIGNATURES #######

def validate_signatures(commit: Commit, validator: Commit,  rule, any_clause_name):
    signature, commit_object = commit.get_signature()
    if not signature:
        commit.add_rule_violation(f"Commit {commit.hash} is not signed", any_clause_name)
        return False
    signature = pgpy.PGPSignature().from_blob(signature)
    allowed_pgpy_keys = generate_pgp_keys(validator, rule)
    for key in allowed_pgpy_keys:
        try:
            key.verify(commit_object, signature)
            return True
        except:
            continue
    commit.add_rule_violation(f"Commit {commit.hash} was signed by untrusted key", any_clause_name)
    return False

def generate_pgp_keys(validator: Commit, rule):
    allowed_public_keys = validator.get_trusted_public_keys(rule["allowed_keys"])
    keys = []
    for allowed_public_key in allowed_public_keys:
        key = pgpy.PGPKey()
        key.parse(allowed_public_key)
        keys.append(key)

    return keys



###### FILE MODIFICATION #####
def validate_file_modification(commit: Commit, validator: Commit, rule, any_clause_name):
    file_pattern = rule["pattern"]
    files_modified = commit.get_files_modified(validator)
    matches = re.search(file_pattern, files_modified, flags=re.M)
    if matches:
        commit.add_rule_violation(f"Commit {commit.hash} modified a file matching the pattern {file_pattern}", any_clause_name)
        return False
    else:
        return True

##### PARENTS #######
def validate_invalid_parents(commit: Commit, rule, valid_commits, any_clause_name):
    parents = commit.get_parents()
    invalid_parents = []
    for parent in parents:
        if not parent.hash in valid_commits:
            invalid_parents.append(parent)
    if len(invalid_parents) > 0:
        # parents_violations = [parent.violations for parent in invalid_parents]
        commit.add_rule_violation(f"Commit {commit.hash} has invalid parents", any_clause_name)
        return False
    return True

def validate_number_of_parents(commit: Commit, rule):
    expected_nr_parents = rule["required_parents"]
    actual_nr_parent = len(commit.get_parents())
    return expected_nr_parents == actual_nr_parent



