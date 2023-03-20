
from gitbark.git.commit import Commit
from gitbark.rules.rule import Rule
from gitbark.cache import Cache

import pgpy
from pgpy.types import SignatureVerification
import re

class Rule(Rule):
    def validate(self, commit: Commit, validator: Commit = None, cache: Cache = None) -> bool:
        allowed_keys = self.args["allowed_keys"]
        threshold = self.args["threshold"]
        passes_rule, violation = require_approval(commit, validator, allowed_keys, threshold, cache)
        self.add_violation(violation)
        return passes_rule
    

def require_approval(commit: Commit, validator: Commit, allowed_keys, threshold, cache:Cache):
    """
    Verifies that the parent from the merged branch contains a threshold of approvals. These approvals are detached signatures
    included in the merge commit message. 

    Note: The second parent of a merge request will always be the parent of the merged branch. 
    """
    parents = commit.get_parents()

    require_approval = parents[1:]
    violation = ""


    detached_signatures = get_detached_signatures(commit)
 
    pubkey_blobs = validator.get_trusted_public_keys(allowed_keys)
    pgpy_pubkeys = generate_pgpy_pubkeys(pubkey_blobs)

    ## Need to check that each invalid parent has been signed by threshold of developers and that the signature is included in the commit

    for parent in require_approval:
        ## For each parent check that threshold signatures of it is present i detached
        number_of_signatures = check_number_of_signatures(parent, pgpy_pubkeys, detached_signatures)
        if number_of_signatures < threshold:
            violation = f"Commit {parent.hash} has {number_of_signatures} valid approvals but expected {threshold}"
            return False, violation
    return True, None        

def check_number_of_signatures(commit: Commit, pgpy_pubkeys, signatures):
    number_of_signatures = 0
    fingerprints_used = {}
    for signature in signatures:
        for pubkey in pgpy_pubkeys:
            try:
                signature_verification = pubkey.verify(commit.get_commit_object(), signature)
                fingerprint = None
                if signature_verification.good_signatures:
                    sigsubj = next(signature_verification.good_signatures)
                    key = sigsubj.by
                    fingerprint = str(key.fingerprint)
                if signature_verification and not fingerprint in fingerprints_used:
                    number_of_signatures += 1
                if fingerprint:
                    fingerprints_used[fingerprint] = True
            except:
                continue
    return number_of_signatures

def get_detached_signatures(commit:Commit):
    commit_msg = commit.get_commit_message()

    pattern = re.compile(r'-----BEGIN PGP SIGNATURE-----(.*?)-----END PGP SIGNATURE-----', re.DOTALL)
    signature_blobs = []
    for match in re.finditer(pattern, commit_msg):
        signature_blobs.append(match.group(0))
    
    pgpy_signatures = []
    for signature_blob in signature_blobs:
        try:
            pgpy_signature = pgpy.PGPSignature().from_blob(signature_blob)
            pgpy_signatures.append(pgpy_signature)
        except:
            continue
    return pgpy_signatures
    
def generate_pgpy_pubkeys(pubkey_blobs):
    pgpy_pubkeys = []
    for pubkey_blob in pubkey_blobs:
        pgpy_pubkey = pgpy.PGPKey()
        pgpy_pubkey.parse(pubkey_blob)
        pgpy_pubkeys.append(pgpy_pubkey)
    return pgpy_pubkeys