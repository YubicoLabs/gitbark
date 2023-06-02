from gitbark.git.commit import Commit
from gitbark.git.git import Git
from gitbark import globals

import subprocess

def approve_cmd(commit_hash, key_id):
    git = Git()
    """ Creates a signature over a commit and stores it in ref (refs/signatures/{commit_hash}/{key_id})

    TODO: It should possible for the user to adds its key ID in a config file
    """

    if not key_id:
        print("error: no key ID provided")
        return
    commit_hash = git.repo.revparse_single(commit_hash).id.__str__()  
    commit = Commit(commit_hash)
    commit_obj = commit.get_commit_object()
    approve = input(f"Are you sure you want to approve commit {commit_hash} (yes/no)? ")
    if approve == "yes":
        signature = create_signature(commit_obj, key_id)
        blob_hash = create_signature_blob(signature)
        ref_name = f"refs/signatures/{commit_hash}/{key_id}"
        git.update_ref(ref_name, blob_hash)
        git.push_ref(f'{ref_name}:{ref_name}')
    else:
        print("Aborting approval")
    return


def create_signature(commit_obj, key_id):
    working_directory = globals.working_directory
    gpg_process = subprocess.Popen(["gpg", "-u", key_id ,"--armor", "--detach-sign", "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd=working_directory.wd)
    signature, _ = gpg_process.communicate(input=commit_obj)
    signature_str = signature.decode()

    return signature_str


def create_signature_blob(signature):
    working_directory = globals.working_directory
    git_process = subprocess.Popen(["git", "hash-object", "--stdin", "-w", "-t", "blob"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd=working_directory.wd)
    blob_hash, _ = git_process.communicate(input=signature.encode())
    blob_hash_str = blob_hash.decode()

    return blob_hash_str
