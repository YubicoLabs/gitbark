
import re
import pgpy

from gitbark.commit import Commit
from gitbark.git_api import GitApi
from gitbark.cache import Cache, CacheEntry
from gitbark.reference_update import ReferenceUpdate
from gitbark.navigation import Navigation
from gitbark.report import Violation    

import warnings
warnings.filterwarnings("ignore")


def validate_commit_rules(ref_update:ReferenceUpdate, branch_name, branch_rule, cache:Cache):
    """Validates commit rules on branch"""
    current_commit, bootstrap_commit = get_head_and_bootstrap(ref_update, branch_name, branch_rule)
    is_branch_rules_branch = True if branch_name == "branch_rules" else False

    def is_commit_valid(commit: Commit):
        """Recursively validates a commit by using its parents as validators
        
        Note: The commit is considered valid if it passes the commit rules of all its validator 
        ancestors. The validators are defined in the following way:
            - If the parent of x itself is valid, the parent becomes a validator of x
            - If the parent of x is not valid, x inherits all Validators that the parent has
        """
        if cache.has(commit.hash):
            value = cache.get(commit.hash)
            if value.valid:
                return True
            else:
                commit.violations = value.violations
                return False
            
        # Bootstrap commit is explicitly trusted
        if not is_branch_rules_branch and commit.hash == bootstrap_commit.hash:
            cache.set(commit.hash, CacheEntry(True, commit.violations))
            return True
   
        parents = commit.get_parents()
        
        validators = []
        for parent in parents:
            if is_commit_valid(parent):
                validators.append(parent)
            else:
                nearest_valid_ancestors = find_nearest_valid_ancestors(parent)
                validators.extend(nearest_valid_ancestors)

        for validator in validators:
            if not validate_rules(commit, validator, cache):
                cache.set(commit.hash, CacheEntry(False, commit.violations))
                return False
            
        cache.set(commit.hash, CacheEntry(True, commit.violations))
        return True

    def find_nearest_valid_ancestors(commit:Commit, valid_ancestors=[]):
        """Return the nearest valid ancestors"""
        parents = commit.get_parents()
        for parent in parents:
            if is_commit_valid(parent):
                valid_ancestors.append(parent)
            else:
                nearest_valid_ancestors = find_nearest_valid_ancestors(parent, valid_ancestors)
                valid_ancestors.extend(nearest_valid_ancestors)
        return valid_ancestors
    
    passes_commit_rules = is_commit_valid(current_commit)
    return passes_commit_rules, current_commit.violations

def get_head_and_bootstrap(ref_update: ReferenceUpdate, branch_name, branch_rule):
    git = GitApi()
    current_head = ""
    if ref_update and ref_update.ref_name == branch_name:
        current_head = ref_update.new_ref
    else:
        current_head = git.rev_parse(branch_name).rstrip()
    current_commit = Commit(current_head)
    if branch_name != "branch_rules":
        boostrap_hash = branch_rule["validate_from"]
        boostrap_commit = Commit(boostrap_hash)
        return current_commit, boostrap_commit
    elif branch_name == "branch_rules":
        navigation = Navigation()
        navigation.get_root_path()
        with open(f"{navigation.wd}/.git/gitbark_data/root_commit", 'r') as f:
            boostrap_hash = f.read()
            bootstrap_commit = Commit(boostrap_hash)
            return current_commit, bootstrap_commit
    else:
        return current_commit, None

def validate_rules(commit:Commit, validator: Commit, cache: Cache):
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
            if not any(validate_rule(commit, validator, sub_rule, cache, rule_name) for sub_rule in sub_rules):
                # If none of the "any" rules are followed, we must give a reason for why that is
                passes_rules = False
                name = ""
                if not type(rule_name) == str:
                    violation = Violation("Any clause", violations=commit.any_violations[rule_name])
                    commit.add_rule_violation(violation, None)
        else:
            if not validate_rule(commit, validator, rule, cache):
                passes_rules = False

    return passes_rules

def validate_rule(commit: Commit, validator:Commit, rule, cache:Cache, any_clause_name=None):
    rule_name = rule["rule"]

    if rule_name == "require_signature":
        return validate_signatures(commit, validator, rule, any_clause_name)
    if rule_name == "file_not_modified":
        return validate_file_modification(commit, validator, rule, any_clause_name)
    if rule_name == "disallow_invalid_parents":
        return validate_invalid_parents(commit, rule, cache, any_clause_name)
    if rule_name == "require_number_of_parents":
        return validate_number_of_parents(commit, rule, any_clause_name)


    return True



####### SIGNATURES #######

def validate_signatures(commit: Commit, validator: Commit,  rule, any_clause_name):
    signature, commit_object = commit.get_signature()
    if not signature:
        violation = Violation("Require signature", "Commit is not signed")
        commit.add_rule_violation(violation, any_clause_name)
        return False
    signature = pgpy.PGPSignature().from_blob(signature)
    allowed_pgpy_keys = generate_pgp_keys(validator, rule)
    for key in allowed_pgpy_keys:
        try:
            key.verify(commit_object, signature)
            return True
        except:
            continue
    violation = Violation("Require signature", "Commit was signed by untrusted key", any_clause_name)
    commit.add_rule_violation(violation, any_clause_name)
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
        violation = Violation("Sensitive file modified", f"Commit modified a file matching the pattern {file_pattern}")
        commit.add_rule_violation(violation, any_clause_name)
        return False
    else:
        return True

##### PARENTS #######
def validate_invalid_parents(commit: Commit, rule, cache: Cache, any_clause_name):
    parents = commit.get_parents()
    invalid_parents = []
    for parent in parents:
        if not cache.has(parent.hash):
            invalid_parents.append(parent)
        else:
            if not cache.get(parent.hash).valid:
                invalid_parents.append(parent)

   
    if len(invalid_parents) > 0:
        parents_hashes = [parent.hash for parent in invalid_parents]
        if "exception" in rule:
            commit_msg = commit.get_commit_message().strip()
            for hash in parents_hashes:
                if not hash in commit_msg:
                    violation = Violation("Invalid parents", "Commit has invalid parents")
                    commit.add_rule_violation(violation, any_clause_name)
                    return False
            return True
        else:
            violation = Violation("Invalid parents", "Commit has invalid parents")
            commit.add_rule_violation(violation, any_clause_name)
        return False
    return True

def validate_number_of_parents(commit: Commit, rule):
    expected_nr_parents = rule["required_parents"]
    actual_nr_parent = len(commit.get_parents())
    return expected_nr_parents == actual_nr_parent



