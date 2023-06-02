
from gitbark.git.commit import Commit
from gitbark.git.git import Git
from gitbark.cache import Cache, CacheEntry
from gitbark.git.reference_update import ReferenceUpdate
from gitbark import globals
from .import_rules import get_rules


import re


def validate_commit_rules(ref_update:ReferenceUpdate, branch_name, branch_rule, cache:Cache, from_install=False, boostrap=None):
    """Validates commit rules on branch"""
    head_commit, bootstrap_commit = get_head_and_bootstrap(ref_update, branch_name, branch_rule, boostrap)
    passes_commit_rules = False
    if from_install:
        passes_commit_rules = is_commit_valid_without_recursion(head_commit, bootstrap_commit, cache, branch_name)
    else:
        passes_commit_rules = is_commit_valid(head_commit, bootstrap_commit, cache, branch_name)
    return passes_commit_rules, head_commit.violations

def find_nearest_valid_ancestors(commit:Commit, boostrap_commit: Commit, cache: Cache, valid_ancestors=[]) -> list[Commit]:
    """Return the nearest valid ancestors"""
    parents = commit.get_parents()
    for parent in parents:
        if cache.get(parent.hash).valid:
            valid_ancestors.append(parent)
        else:
            nearest_valid_ancestors = find_nearest_valid_ancestors(parent, boostrap_commit, cache, valid_ancestors)
            valid_ancestors.extend(nearest_valid_ancestors)
    return valid_ancestors


def add_children(commit: Commit):
    queue = [commit]
    children = {}
    processed = set()
    while len(queue) > 0:
        current = queue.pop(0)
        if current.hash not in processed:
            processed.add(current.hash)
            parents = current.get_parents()
            for parent in parents:
                if parent.hash in children:
                    children[parent.hash].append(current)
                    queue.append(parent)
                else:
                    children[parent.hash] = [current]
                    queue.append(parent)
    return children

    

def is_commit_valid_without_recursion(commit: Commit, bootstrap_commit: Commit, cache: Cache, branch_name):
    if commit.hash == bootstrap_commit.hash:
        cache.set(commit.hash, CacheEntry(True, commit.violations, branch_name=branch_name))
        return True
    
    if cache.has(commit.hash):
        value = cache.get(commit.hash)
        if value.branch_name == branch_name:
            if value.valid:
                return True
            else:
                commit.violations = value.violations
                return False


    children_map = add_children(commit)

    cache.set(bootstrap_commit.hash, CacheEntry(True, commit.violations, branch_name=branch_name))
    queue = [bootstrap_commit]

    processed = set()
    validated = set()

    while len(queue) > 0:
        current = queue.pop(0)
        if current.hash not in processed:
            processed.add(current.hash)
            children = []
            if current.hash in children_map:
                children = children_map[current.hash]
            # Need to process the children in reversed order
            for child in reversed(children):
                if child.hash in validated:
                    continue
                parents = child.parents
                validators = []
                visited_validators = set()
                for parent in parents:
                    if cache.has(parent.hash):
                        value = cache.get(parent.hash)
                        if value.valid:
                            validators.append(parent)
                            visited_validators.add(parent.hash)
                        else:
                            nearest_validators = find_nearest_valid_ancestors(parent, bootstrap_commit, cache)
                            for validator in nearest_validators:
                                if not validator.hash in visited_validators:
                                    validators.append(validator) 
                                    visited_validators.add(validator.hash)
                passes_rules = True
                for validator in validators:
                    if not validate_rules(child, validator, cache):
                        cache.set(child.hash, CacheEntry(False, child.violations, branch_name=branch_name))
                        passes_rules = False
                if passes_rules:
                    cache.set(child.hash, CacheEntry(True, child.violations, branch_name=branch_name))
                validated.add(child.hash)
                queue.append(child)
    
    if cache.has(commit.hash):
        value = cache.get(commit.hash)
        if value.valid and value.branch_name == branch_name:
            return True
        else:
            return False


        

def is_commit_valid(commit: Commit, bootstrap_commit: Commit, cache: Cache, branch_name):
    """Recursively validates a commit by using its parents as validators
    
    Note: The commit is considered valid if it passes the commit rules of all its validator 
    ancestors. The validators are defined in the following way:
        - If the parent of x itself is valid, the parent becomes a validator of x
        - If the parent of x is not valid, x inherits all Validators that the parent has
    """
    if cache.has(commit.hash):
        value = cache.get(commit.hash)
        if value.branch_name == branch_name:
            if value.valid:
                return True
            else:
                commit.violations = value.violations
                return False
        
    # Bootstrap commit is explicitly trusted
    if commit.hash == bootstrap_commit.hash:
        cache.set(commit.hash, CacheEntry(True, commit.violations, branch_name=branch_name))
        return True

    parents = commit.get_parents()
    validators = []
    for parent in parents:
        if is_commit_valid(parent, bootstrap_commit, cache, branch_name):
            validators.append(parent)
        else:
            nearest_valid_ancestors = find_nearest_valid_ancestors(parent, bootstrap_commit, cache)
            validators.extend(nearest_valid_ancestors)
    for validator in validators:
        if not validate_rules(commit, validator, cache):
            cache.set(commit.hash, CacheEntry(False, commit.violations, branch_name=branch_name))
            return False
        
    cache.set(commit.hash, CacheEntry(True, commit.violations, branch_name=branch_name))
    return True

def get_head_and_bootstrap(ref_update: ReferenceUpdate, branch_name, branch_rule, bootstrap):
    git = Git()
    current_head = ""
    
    short_branch_name = branch_name.split("/")
    short_branch_name = short_branch_name[-1]

    if ref_update and re.search(f"refs/.*/{short_branch_name}", ref_update.ref_name, re.M):
        current_head = ref_update.new_ref
    else:
        current_head = git.repo.revparse_single(branch_name)
        current_head = current_head.id.__str__()
    current_commit = Commit(current_head)

    if bootstrap:
        bootstrap_commit = Commit(bootstrap)
        return current_commit, bootstrap_commit

    if short_branch_name != "branch_rules":
        boostrap_hash = branch_rule["validate_from"]
        boostrap_commit = Commit(boostrap_hash)
        return current_commit, boostrap_commit
    else:
        working_directory = globals.working_directory
        with open(f"{working_directory.wd}/.git/gitbark_data/root_commit", 'r') as f:
            boostrap_hash = f.read()
            bootstrap_commit = Commit(boostrap_hash)
            return current_commit, bootstrap_commit

def validate_rules(commit:Commit, validator: Commit, cache: Cache):
    rules = get_rules(validator)
    passes_rules = True
    for rule in rules:
        if not rule.validate(commit, validator, cache):
            commit.add_rule_violation(rule.get_violation())
            passes_rules = False
    
    return passes_rules







