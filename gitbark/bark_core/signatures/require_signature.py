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

from .util import Pubkey, get_authorized_pubkeys, verify_signature_bulk


class RequireSignature(Rule):
    def validate(self, commit: Commit) -> bool:
        authorized_keys_pattern = self.args["authorized_keys"]
        authorized_pubkeys = get_authorized_pubkeys(
            self.validator, authorized_keys_pattern
        )

        passes_rule, violation = require_signature(commit, authorized_pubkeys)
        self.add_violation(violation)
        return passes_rule


def require_signature(commit: Commit, authorized_pubkeys: list[Pubkey]):
    signature, commit_object = commit.get_signature()
    violation = ""

    if not signature:
        # No signature
        violation = "Commit was not signed"
        return False, violation

    if len(authorized_pubkeys) == 0:
        # No pubkeys specified
        violation = "No public keys registered"
        return False, violation

    if verify_signature_bulk(authorized_pubkeys, signature, commit_object):
        return True, None
    else:
        violation = "Commit was signed by untrusted key"
        return False, violation
