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
from gitbark.cli.util import click_prompt, CliFail, click_callback

from enum import Enum
from pygit2 import Repository
from dataclasses import dataclass
import subprocess
import os
import click


class KeyType(Enum):
    GPG = 1
    SSH = 2


@dataclass
class Key:
    identifier: str
    type: KeyType


@click_callback()
def click_parse_commit(ctx, param, val):
    project = ctx.obj["project"]
    repo = project.repo

    try:
        object = repo.revparse_single(val)
        return Commit(object.id)
    except Exception:
        raise CliFail(f"{val} is not a valid commit object!")


@click.command()
@click.pass_context
@click.argument("commit", default="HEAD", callback=click_parse_commit)
@click.option("--gpg-key-id", type=str, default="", help="The GPG key ID.")
@click.option(
    "--ssh-key-path",
    type=str,
    default="",
    help="The path to your private SSH key.",
)
def approve(ctx, commit, gpg_key_id, ssh_key_path):
    """Add your signature to a commit.

    This will create a signature over a given commit object, that
    is stored under `refs/signatures`.

    \b
    COMMIT the commit to sign.
    """

    project = ctx.obj["project"]
    repo = project.repo

    if not gpg_key_id and not ssh_key_path:
        key = get_key_from_git(repo)

    if gpg_key_id:
        key = Key(gpg_key_id, KeyType.GPG)

    if ssh_key_path:
        key = Key(ssh_key_path, KeyType.SSH)

    if not key:
        identifier = click_prompt(
            prompt="Enter key identifier (GPG key id or SSH key path)"
        )
        if is_hex(identifier):
            key = Key(identifier, KeyType.GPG)
        elif os.path.exists(identifier):
            key = Key(identifier, KeyType.SSH)
        else:
            raise CliFail("Invalid key identifier!")

    sig, key_id = sign_commit(commit, key)

    blob_id = repo.create_blob(sig)
    repo.references.create(f"refs/signatures/{commit.hash}/{key_id}", blob_id)


def get_key_from_git(repo: Repository):
    config = repo.config
    if "gpg.format" in config and "user.signingkey" in config:
        identifier = config["user.signingkey"]
        signature_type = config["gpg.format"]

        if signature_type == "openpgp":
            return Key(identifier, KeyType.GPG)
        elif signature_type == "ssh":
            return Key(identifier, KeyType.SSH)
        else:
            return None
    return None


def is_hex(s):
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


def sign_commit(commit: Commit, key: Key):
    commit_obj = commit.get_commit_object()
    if key.type == KeyType.GPG:
        gpg_process = subprocess.Popen(
            ["gpg", "-u", key.identifier, "--armor", "--detach-sign", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        sig, _ = gpg_process.communicate(input=commit_obj)
        return sig, key.identifier
    else:
        ssh_process = subprocess.Popen(
            ["ssh-keygen", "-Y", "sign", "-f", key.identifier, "-n", "git"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        sig, _ = ssh_process.communicate(input=commit_obj)
        return sig, get_ssh_key_id(key.identifier)


def get_ssh_key_id(ssh_key_path):
    output = subprocess.check_output(
        ["ssh-keygen", "-l", "-f", ssh_key_path], text=True
    ).rstrip()
    key_id = output.split(":")[1].split()[0]
    return key_id
