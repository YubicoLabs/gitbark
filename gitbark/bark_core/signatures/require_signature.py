
from gitbark.git.commit import Commit
from gitbark.rules.rule import Rule
from gitbark.cache import Cache
import pgpy
import subprocess
import os
import shutil

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

    pubkey_blobs = validator.get_trusted_public_keys(allowed_keys)
    if len(pubkey_blobs) == 0:
        # No pubkeys specified
        violation = "No public keys registered"
        return False, violation
    
    if validate_signature(pubkey_blobs, signature_blob, commit_object):
        return True,None
    else:
        violation = "Commit was signed by untrusted key"
        return False, violation

def validate_signature(allowed_pubkeys, signature, commit_object):

    for pubkey in allowed_pubkeys:
        if is_gpg(pubkey, signature):
            if validate_gpg_signature(pubkey, signature, commit_object):
                return True
        else:
            if validate_ssh_signature(pubkey, signature, commit_object):
                return True
            
    return False

def is_gpg(key, signature):
    if "-----BEGIN PGP PUBLIC KEY BLOCK-----" in key and "-----BEGIN PGP SIGNATURE-----" in signature:
        return True
    else:
        return False


def validate_gpg_signature(pubkey, signature, commit_object):
    pgpy_signature = pgpy.PGPSignature().from_blob(signature)
    pgpy_pubkey = pgpy.PGPKey()
    pgpy_pubkey.parse(pubkey)
    try:
        valid = pgpy_pubkey.verify(commit_object, pgpy_signature)
        if valid:
            return True
        else:
            return False
    except:
        return False

def validate_ssh_signature(allowed_signers, signature, commit_object):
    signer_identities = []
    try:
        for allowed_signer in allowed_signers.split("\n\n"):
            signer_identities.append(allowed_signer.split()[0])
    except:
        return False
        
    os.mkdir("tmp")
    with open("tmp/allowed_signers", "w") as f:
        f.write(allowed_signers)
    with open("tmp/sig", "w") as f:
        f.write(signature)
    with open("tmp/commit", "w") as f:
        f.write(commit_object)

    for signer_identity in signer_identities:
        p = subprocess.Popen(["ssh-keygen", "-Y", "verify", "-f", "tmp/allowed_signers", "-I", signer_identity, "-n", "git", "-s", "tmp/sig"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout_data = p.communicate(input=commit_object.encode())
        print(stdout_data)
        rc = p.returncode
        if rc == 0:
            shutil.rmtree("tmp")
            return True
    shutil.rmtree("tmp")
    return False
