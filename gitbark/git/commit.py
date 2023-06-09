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

from .git import Git
import yaml
import re

class Commit:
    """Git commit class

    This class serves as a wrapper for a Git commit object
    """
    def __init__(self, hash) -> None:
        """Init Commit with commit hash"""
        self.git = Git()
        self.hash = hash
        self.object = self.git.repo.get(hash)
        self.parents = None
        self.children = []
        self.violations = []
        self.any_violations = {}
    
    def __eq__(self, other) -> bool:
        """Perform equality check on two commits based on their hashes"""
        return self.hash == other.hash
    
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
        return self.git.repo.revparse_single(f"{self.hash}:{path}").read_raw().decode()
    
    def get_parents(self):
        """Return the parents of a commit"""
        parents = [Commit(parent_hash.__str__()) for parent_hash in self.object.parent_ids]
        self.parents = parents
        return parents

    def get_rules(self):
        """Return the commit rules to a commit"""
        rules = self.get_blob_object(".gitbark/commit_rules.yaml")
        return yaml.safe_load(rules)

    def get_signature(self):
        """Return the signature and commit object (with signature removed)"""    
        signature, commit_object = self.object.gpg_signature

        if signature:
            signature = signature.decode()
        
        if commit_object:
            commit_object = commit_object.decode()

        return signature, commit_object

    def get_trusted_public_keys(self, allowed_keys_regex):
        """Return the set of trusted public keys reference to by the commit"""
        pubkey_entries = self.git.repo.revparse_single(f"{self.hash}:.gitbark/.pubkeys")
        trusted_pubkeys = []
        for obj in pubkey_entries:
            if re.search(allowed_keys_regex, obj.name):
                pubkey = self.git.repo.get(obj.id).read_raw().decode().strip()
                trusted_pubkeys.append(pubkey)

        return trusted_pubkeys
    
    def get_files_modified(self, validator):
        """Return the set of files changed between validator commit and current commit"""
        return self.git.get_file_diff(self.hash, validator.hash)

        
