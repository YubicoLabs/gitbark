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

from .util import Pubkey, get_authorized_pubkeys

import re


class RequireApproval(Rule):
    def validate(self, commit: Commit) -> bool:
        authorized_keys_pattern, threshold = (
            self.args["authorized_keys"],
            self.args["threshold"],
        )
        threshold = int(threshold)
        authorized_pubkeys = get_authorized_pubkeys(
            self.validator, authorized_keys_pattern
        )

        passes_rule, violation = require_approval(commit, threshold, authorized_pubkeys)
        self.add_violation(violation)
        return passes_rule


def require_approval(commit: Commit, threshold: int, authorized_pubkeys: list[Pubkey]):
    """
    Verifies that the parent from the merged branch contains a threshold of approvals.
    These approvals are detached signatures included in the merge commit message.

    Note: The second parent of a merge request will always be the parent
    of the merged branch.
    """
    parents = commit.get_parents()
    violation = ""

    if len(parents) <= 1:
        # Require approval can only be applied on pull requests
        violation = "Commit does not originate from a pull request"
        return False, violation

    # The merge head
    require_approval_for = parents[-1]

    signatures = get_approvals(commit)

    valid_approvals = 0
    approvers = set()

    for signature in signatures:
        for pubkey in authorized_pubkeys:
            if (
                pubkey.verify_signature(
                    signature, require_approval_for.get_commit_object()
                )
                and pubkey.fingerprint not in approvers
            ):
                valid_approvals = valid_approvals + 1
                approvers.add(pubkey.fingerprint)

    if valid_approvals < threshold:
        violation = (
            f"Commit {commit.hash} has {valid_approvals} valid approvals "
            f" but expected {threshold}"
        )
        return False, violation

    return True, violation


def get_approvals(commit: Commit):
    commit_msg = commit.get_commit_message()

    pattern = re.compile(
        r"-----BEGIN (PGP|SSH) SIGNATURE-----(.*?)-----END (PGP|SSH) SIGNATURE-----",
        re.DOTALL,
    )
    signature_blobs = []
    for match in re.finditer(pattern, commit_msg):
        signature_blobs.append(match.group(0))

    return signature_blobs
