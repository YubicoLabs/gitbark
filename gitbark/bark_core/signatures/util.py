from gitbark.git import Commit

from pgpy import PGPKey, PGPSignature
from paramiko import PKey
from typing import Any, Union

import warnings

warnings.filterwarnings("ignore")


class Pubkey:
    def __init__(self, pubkey: str) -> None:
        self.key, self.fingerprint = self._parse_pubkey(pubkey)

    def _parse_pubkey(self, pubkey: str) -> Union[PGPKey, PKey]:
        try:
            key, _ = PGPKey.from_blob(pubkey)
            fingerprint = str(key.fingerprint)
            return key, fingerprint
        except Exception:
            pass
        try:
            key = PKey(data=pubkey)
            fingerprint = key.fingerprint.split(":")[1]
        except Exception:
            pass
        raise ValueError("Could not parse public key!")

    def verify_signature(self, signature, subject) -> bool:
        if isinstance(self.key, PGPKey):
            return verify_pgp_signature(self.key, signature, subject)
        else:
            return verify_ssh_signature(self.key, signature, subject)


def verify_ssh_signature(pubkey: PKey, signature: Any, subject: Any) -> bool:
    return pubkey.verify_ssh_sig(subject, signature)


def verify_pgp_signature(pubkey: PGPKey, signature: Any, subject: Any) -> bool:
    signature = PGPSignature().from_blob(signature)
    try:
        if pubkey.verify(subject, signature):
            return True
        else:
            return False
    except Exception:
        return False


def verify_signature_bulk(pubkeys: list[Pubkey], signature: Any, subject: Any) -> bool:
    for pubkey in pubkeys:
        if pubkey.verify_signature(signature, subject):
            return True

    return False


def get_authorized_pubkeys(validator: Commit, authorized_keys_pattern: str):
    authorized_pubkey_blobs = validator.get_public_keys(authorized_keys_pattern)
    return [Pubkey(blob) for blob in authorized_pubkey_blobs]
