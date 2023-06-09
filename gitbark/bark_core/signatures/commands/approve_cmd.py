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

from gitbark.git.commit import Commit
from gitbark.git.git import Git
from gitbark import globals

import subprocess
from enum import Enum

class KeyType(Enum):
    GPG = 1
    SSH = 2

def approve_cmd(commit_hash, gpg_key_id="", ssh_key_path=""):
    git = Git()
    """ Creates a signature over a commit and stores it in ref (refs/signatures/{commit_hash}/{key_id})

    TODO: It should possible for the user to adds its key ID in a config file
    """

    if not gpg_key_id and not ssh_key_path:
        print("error: no key ID provided")
        return
    commit_hash = git.repo.revparse_single(commit_hash).id.__str__()  
    commit = Commit(commit_hash)
    commit_obj = commit.get_commit_object()
    approve = input(f"Are you sure you want to approve commit {commit_hash} (yes/no)? ")

    key_type = KeyType.GPG if gpg_key_id else KeyType.SSH

    if approve == "yes":
        signature = ""
        ref_name = ""
        if key_type == KeyType.GPG:
            signature = create_gpg_signature(commit_obj, gpg_key_id)
            ref_name = f"refs/signatures/{commit_hash}/{gpg_key_id}"
        else:
            signature = create_ssh_signature(commit_obj, ssh_key_path)
            ssh_key_id = get_ssh_key_id(ssh_key_path)
            ref_name = f"refs/signatures/{commit_hash}/{ssh_key_id}"
        
        blob_hash = create_signature_blob(signature)
        git.update_ref(ref_name, blob_hash)
        git.push_ref(f'{ref_name}:{ref_name}')
    else:
        print("Aborting approval")
    return


def create_gpg_signature(commit_obj, gpg_key_id):
    working_directory = globals.working_directory
    gpg_process = subprocess.Popen(["gpg", "-u", gpg_key_id ,"--armor", "--detach-sign", "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd=working_directory.wd)
    signature, _ = gpg_process.communicate(input=commit_obj)
    signature_str = signature.decode()

    return signature_str

def create_ssh_signature(commit_obj, ssh_key_path):
    working_directory = globals.working_directory
    ssh_process = subprocess.Popen(["ssh-keygen", "-Y", "sign", "-f", ssh_key_path, "-n", "git"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd=working_directory.wd)
    signature, _ = ssh_process.communicate(input=commit_obj)
    signature_str = signature.decode()

    return signature_str

def get_ssh_key_id(ssh_key_path):
    output = subprocess.check_output(["ssh-keygen", "-l", "-f", ssh_key_path], text=True).rstrip()
    key_id = output.split(":")[1].split()[0]
    return key_id

def create_signature_blob(signature):
    working_directory = globals.working_directory
    git_process = subprocess.Popen(["git", "hash-object", "--stdin", "-w", "-t", "blob"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd=working_directory.wd)
    blob_hash, _ = git_process.communicate(input=signature.encode())
    blob_hash_str = blob_hash.decode()

    return blob_hash_str
