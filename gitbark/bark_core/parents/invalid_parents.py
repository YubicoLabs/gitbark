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

from gitbark.git import Commit
from gitbark.project import Cache
from gitbark.rule import Rule


class InvalidParents(Rule):
    def validate(self, commit: Commit) -> bool:
        cache = self.cache
        if "allow" in self.args:
            allow = self.args["allow"]
        else:
            allow = True  # Non-valid commits are allowed per default
        if "require_explicit_inclusion" in self.args:
            require_explicit_inclusion = self.args["require_explicit_inclusion"]
        else:
            require_explicit_inclusion = False

        passes_rule = validate_invalid_parents(
            commit, cache, allow, require_explicit_inclusion
        )
        if not passes_rule:
            self.add_violation("Commit has invalid parents")
        return passes_rule


def validate_invalid_parents(
    commit: Commit, cache: Cache, allow: bool, require_explicit_inclusion: bool
):
    if not allow:
        return False

    if not require_explicit_inclusion:
        return True

    parents = commit.get_parents()
    invalid_parents = []

    for parent in parents:
        value = cache.get(parent.hash)
        if value and not value.valid:
            invalid_parents.append(parent)

    if len(invalid_parents) == 0:
        return True

    invalid_parent_hashes = [parent.hash for parent in invalid_parents]
    commit_msg = commit.get_commit_message()
    for hash in invalid_parent_hashes:
        if hash not in commit_msg:
            return False
    return True
