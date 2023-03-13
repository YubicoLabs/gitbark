from gitbark.git.commit import Commit
from gitbark.cache import Cache
from gitbark.rules.rule import Rule

import re


class Rule(Rule):
    def validate(self, commit: Commit, validator: Commit = None, cache: Cache = None) -> bool:
        pattern = self.args["pattern"]
        passes_rule =  file_not_modified(commit, validator, pattern)        

        if not passes_rule:
            self.add_violation(f"Commit modified locked file(s) with pattern {pattern}")

        return passes_rule

def file_not_modified(commit: Commit, validator: Commit, pattern):
    files_modified = commit.get_files_modified(validator)
    file_matches = re.search(pattern, files_modified, flags=re.M)
    
    if file_matches:
        # File was modified
        return False
    else:
        return True