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
from gitbark.rule import Rule

import re


class FileNotModified(Rule):
    def validate(self, commit: Commit) -> bool:
        pattern = self.args["pattern"]

        passes_rule, violation = validate_file_not_modified(
            commit, self.validator, pattern
        )
        self.add_violation(violation)
        return passes_rule


def validate_file_not_modified(commit: Commit, validator: Commit, pattern: str):
    files_modified = commit.get_files_modified(validator)
    file_matches = list(filter(lambda f: re.match(pattern, f), files_modified))

    if len(file_matches) > 0:
        # Commit modifies locked file
        files = ", ".join(file_matches)
        violation = f"Commit modified locked file(s): {files}"
        return False, violation

    return True, None
