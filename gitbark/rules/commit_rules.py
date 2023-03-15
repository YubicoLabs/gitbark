
from gitbark.git.commit import Commit
from gitbark.git.git import Git
from gitbark.cache import Cache, CacheEntry
from gitbark.git.reference_update import ReferenceUpdate
from gitbark.navigation import Navigation
from .import_rules import get_rules    



def validate_commit_rules(ref_update:ReferenceUpdate, branch_name, branch_rule, cache:Cache):
    """Validates commit rules on branch"""
    current_commit, bootstrap_commit = get_head_and_bootstrap(ref_update, branch_name, branch_rule)

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
        if commit.hash == bootstrap_commit.hash:
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
    git = Git()
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
    rules = get_rules(validator)

    passes_rules = True
    for rule in rules:
        if not rule.validate(commit, validator, cache):
            commit.add_rule_violation(rule.violation)
            passes_rules = False
    
    return passes_rules







