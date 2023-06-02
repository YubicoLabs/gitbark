from gitbark.git.commit import Commit
from gitbark.cache import Cache
from gitbark.rules.rule import Rule


class Rule(Rule):
    def validate(self, commit: Commit, validator: Commit = None, cache: Cache = None) -> bool:
        allow_explicit_approval = True if "exception" in self.args else False
        passes_rule =  validate_disallow_invalid_parents(commit, cache, allow_explicit_approval)
        if not passes_rule:
            self.add_violation("Commit has invalid parents")
        return passes_rule

def validate_disallow_invalid_parents(commit: Commit, cache:Cache, allow_explicit_approval:bool):
    parents = commit.get_parents()
    invalid_parents = []

    for parent in parents:
        if not cache.get(parent.hash).valid:
            invalid_parents.append(parent)
    
    if len(invalid_parents) > 0:
        invalid_parent_hashes = [parent.hash for parent in invalid_parents]

        if allow_explicit_approval:
            return invalid_hashes_included(commit, invalid_parent_hashes)
        else:
            return False
    return True


def invalid_hashes_included(commit:Commit, invalid_hashes):
    commit_msg = commit.get_commit_message()
    for hash in invalid_hashes:
        if not hash in commit_msg:
            return False

    return True
