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
        self.parents = None
        self.violations = []
        self.any_violations = {}
    
    def __eq__(self, other) -> bool:
        """Perform equality check on two commits based on their hashes"""
        return self.hash == other.hash
    
    def add_rule_violation(self, violation):
        self.violations.append(violation)
    
    def get_commit_object(self):
        """Return the Git commit object in text"""
        return self.git.get_object(self.hash)
    
    def get_commit_message(self):
        return self.git.show(f"git show -s --format=%B {self.hash}")

    def get_tree_object(self):
        """Return the tree object referenced to by the commit"""
        tree_hash = self.git.rev_parse(self.hash + "^{tree}").rstrip()
        return self.git.get_object(tree_hash)
    
    def get_blob_object(self, path):
        """Return a specific blob object referenced to by the commit"""
        return self.git.get_object(f"{self.hash}:{path}")
    
    def get_parents(self):
        """Return the parents of a commit"""
        parent_hashes = self.git.rev_parse(f"{self.hash}^@").splitlines()
        parents = [Commit(parent_hash) for parent_hash in parent_hashes]
        # self.parents = parents
        return parents

    def get_rules(self):
        """Return the commit rules to a commit"""
        rules = self.get_blob_object(".gitbark/commit_rules.yaml")
        return yaml.safe_load(rules)

    def get_signature(self):
        """Return the signature and commit object (with signature removed)"""
        commit_object = self.get_commit_object()
        signature = re.search('-----BEGIN PGP SIGNATURE-----\n(\s.*\n)*\s-----END PGP SIGNATURE-----', commit_object)
        if signature:
            signature = signature.group()
            signature = re.sub("^\s", "", signature, flags=re.M)
            commit_object = re.sub('gpgsig -----BEGIN PGP SIGNATURE-----\n(\s.*\n)*\s-----END PGP SIGNATURE-----\n', '', commit_object)

        return signature, commit_object

    def get_trusted_public_keys(self, allowed_keys_regex):
        """Return the set of trusted public keys reference to by the commit"""
        pubkeys_tree = self.git.get_object(f"{self.hash}:.gitbark/.pubkeys")
        key_blob_fields = re.findall(f".*{allowed_keys_regex}", pubkeys_tree, flags=re.M)
        pubkeys = []
        for key_blob_field in key_blob_fields:
            key_blob_hash = key_blob_field.split()[2]
            key = self.git.get_object(key_blob_hash)
            pubkeys.append(key)
        return pubkeys
    
    def get_files_modified(self, validator):
        """Return the set of files changed between validator commit and current commit"""
        return self.git.get_file_diff(self.hash, validator.hash)

        
