from gitbark.git.commit import Commit
from gitbark.cache import Cache
from gitbark.rules.rule import Rule


class Rule(Rule):
    def validate(self, commit: Commit, validator: Commit = None, cache: Cache = None) -> bool:
        threshold = self.args["threshold"]
        passes_rule, violation  =  validate_number_of_parents(commit, cache, threshold)
        if not passes_rule:
            self.add_violation(violation)
        return passes_rule
    
def validate_number_of_parents(commit: Commit, cache:Cache, threshold):
    parents = commit.get_parents()

    if len(parents) < threshold:
        return False, f"Commit has {len(parents)} parent(s) but expected {threshold}"
    else:
        return True, None