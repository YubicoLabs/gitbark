
from gitbark.git.commit import Commit
from gitbark.rules.rule import Rule
from gitbark.cache import Cache
import pgpy

import warnings
warnings.filterwarnings("ignore")
# Validate that a commit has a trusted signature

class Rule(Rule):
    def validate(self, commit: Commit, validator: Commit = None, cache:Cache=None) -> bool:
        allowed_keys = self.args["allowed_keys"]
        passes_rule, violation = require_signature(commit, validator, allowed_keys)
        self.add_violation(violation)
        return passes_rule

def require_signature(commit:Commit, validator:Commit, allowed_keys):
    signature_blob, commit_object = commit.get_signature()
    violation = ""

    if not signature_blob:
        # No signature
        violation = f"Commit was not signed"
        return False, violation
    
    pgpy_signature = pgpy.PGPSignature().from_blob(signature_blob)

    pubkey_blobs = validator.get_trusted_public_keys(allowed_keys)
    if len(pubkey_blobs) == 0:
        # No pubkeys specified
        violation = "No public keys registered"
        return False, violation

    pgpy_pubkeys = generate_pgpy_pubkeys(pubkey_blobs)
        
    for pubkey in pgpy_pubkeys:
        try:
            valid = pubkey.verify(commit_object, pgpy_signature)
            if valid:
                return True, None
        except:
            continue
    violation = "Commit was signed by untrusted key"
    return False, violation


def generate_pgpy_pubkeys(pubkey_blobs):
    pgpy_pubkeys = []
    for pubkey_blob in pubkey_blobs:
        pgpy_pubkey = pgpy.PGPKey()
        pgpy_pubkey.parse(pubkey_blob)
        pgpy_pubkeys.append(pgpy_pubkey)
    return pgpy_pubkeys
    