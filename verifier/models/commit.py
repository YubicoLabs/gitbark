from wrappers.git_wrapper import GitWrapper
import yaml
import re


class Commit:
    def __init__(self, hash) -> None:
        self.git = GitWrapper()
        self.hash = hash
    
    def __eq__(self, other) -> bool:
        return self.hash == other.hash
    
    def get_commit_object(self):
        return self.git.get_object(self.hash)

    def get_tree_object(self):
        tree_hash = self.git.rev_parse(self.hash + "^{tree}").rstrip()
        return self.git.get_object(tree_hash)
    
    def get_blob_object(self, path):
        return self.git.get_object(f"{self.hash}:{path}")
    
    def get_parents(self):
        parent_hashes = self.git.rev_parse(f"{self.hash}^@").splitlines()
        return [Commit(parent_hash) for parent_hash in parent_hashes]

    def get_rules(self):
        rules = self.get_blob_object("commit_rules.yaml")
        return yaml.safe_load(rules)

    def get_signature(self):
        commit_object = self.get_commit_object()
        signature = re.search('-----BEGIN PGP SIGNATURE-----\n(\s.*\n)*\s-----END PGP SIGNATURE-----', commit_object)
        if signature:
            signature = signature.group()
            signature = re.sub("^\s", "", signature, flags=re.M)
            commit_object = re.sub('gpgsig -----BEGIN PGP SIGNATURE-----\n(\s.*\n)*\s-----END PGP SIGNATURE-----\n', '', commit_object)

        return signature, commit_object

    def get_allowed_public_keys(self, allowed_keys_regex):
        pubkeys_tree = self.git.get_object(f"{self.hash}:.pubkeys")
        key_blob_fields = re.findall(allowed_keys_regex, pubkeys_tree, flags=re.M)
        pubkeys = []
        for key_blob_field in key_blob_fields:
            key_blob_hash = key_blob_field.split()[2]
            key = self.git.get_object(key_blob_hash)
            pubkeys.append(key)
        return pubkeys
    
    def get_files_modified(self, validator):
        return self.git.get_file_diff(self.hash, validator.hash)

        

        

# .pubkeys/*.pub


# x = "100644 blob 12e7c9d6f606da3ca1dcbf17118f706a8a52ef75 elias.asc"

# match = re.findall(".*.asc", x)
# print(match)

# commit1 = Commit("02b143c4edfedd188d5b61f9ec897478fc78a5dd")
# print(commit1.get_blob_object("commit_rules.yaml"))

# commit1 = Commit("885975515e5fc387acd50b18a2b8a69cc1709a00")
# parents =  commit1.get_parents()
# for parent in parents:
#     print(parent.get_commit_object())
        