from gitbark.git.commit import Commit
from gitbark.cache import Cache
from gitbark.rules.rule import Rule


class Rule(Rule):
    def validate(self, commit: Commit, validator: Commit = None, cache: Cache = None) -> bool:
        threshold = self.args["threshold"]
        passes_rule, violation  =  require_number_of_parents(commit, cache, threshold)
        if not passes_rule:
            self.add_violation(violation)
        return passes_rule
def require_number_of_parents(commit: Commit, cache:Cache, threshold):
    parents = commit.get_parents()
    number_of_parents = len(parents)

    if number_of_parents < threshold:
        return False, f"Commit has {number_of_parents} parent(s) but expected {threshold}"
    else:
        return True, None
            

# def check_hashes_in_commit_message(commit:Commit, hashes):
#     commit_msg = commit.get_commit_message()
#     for hash in hashes:
#         if not hash in commit_msg:
#             return False

#     return True
