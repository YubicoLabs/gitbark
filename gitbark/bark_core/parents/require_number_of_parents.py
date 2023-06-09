# Copyright 2023 Yubico AB

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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