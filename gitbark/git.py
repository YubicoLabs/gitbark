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

from .objects import CommitRulesData, BarkRules
from gitbark import globals

from dataclasses import dataclass
import yaml
import re


class Commit:
    """Git commit class

    This class serves as a wrapper for a Git commit object
    """

    def __init__(self, hash: str) -> None:
        """Init Commit with commit hash"""
        self.repo = globals.repo
        self.hash = hash
        self.object = self.repo.get(hash)
        self.parents = None
        self.violations: list[str] = []

    def __eq__(self, other) -> bool:
        """Perform equality check on two commits based on their hashes"""
        return self.hash == other.hash

    def __hash__(self) -> int:
        return int(self.hash, base=16)

    def add_rule_violation(self, violation):
        self.violations.append(violation)

    def get_commit_object(self):
        """Return the Git commit object in text"""
        content = self.object.read_raw()
        return content

    def get_commit_message(self):
        return self.object.message

    def get_blob_object(self, path):
        """Return a specific blob object referenced to by the commit"""
        return self.repo.revparse_single(f"{self.hash}:{path}").read_raw().decode()

    def get_parents(self):
        """Return the parents of a commit"""
        parents = [
            Commit(parent_hash.__str__()) for parent_hash in self.object.parent_ids
        ]
        self.parents = parents
        return parents

    def get_commit_rules(self):
        commit_rules = yaml.safe_load(
            self.get_blob_object(".gitbark/commit_rules.yaml")
        )
        return CommitRulesData.parse(commit_rules)

    def get_bark_rules(self) -> "BarkRules":
        """Return the branch rules for a commit"""
        bark_rules_object = yaml.safe_load(
            self.get_blob_object(".gitbark/branch_rules.yaml")
        )
        return BarkRules.parse(bark_rules_object)

    def get_signature(self):
        """Return the signature and commit object (with signature removed)"""
        signature, commit_object = self.object.gpg_signature
        if signature:
            signature = signature.decode()

        if commit_object:
            commit_object = commit_object.decode()

        return signature, commit_object

    def get_public_keys(self, pattern: str):
        """Return the set of trusted public keys reference to by the commit"""
        pubkey_entries = self.repo.revparse_single(f"{self.hash}:.gitbark/.pubkeys")
        pubkeys = []
        for obj in pubkey_entries:
            if re.search(pattern, obj.name):
                pubkey = self.repo.get(obj.id).read_raw().decode().strip()
                pubkeys.append(pubkey)
        return pubkeys

    def get_files_modified(self, validator):
        """Return the set of files changed between validator commit and current commit"""
        diff = self.repo.diff(self.hash, validator.hash)
        files = []
        for delta in diff.deltas:
            files.append(delta.new_file.path)
        return files


@dataclass
class ReferenceUpdate:
    """Git reference update class

    This class serves as a wrapper for a Git reference-update
    """

    old_ref: str
    new_ref: str
    ref_name: str
