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

from ..commands.verify import verify
from ..git.git import Git
from gitbark import globals
import pkg_resources

import os
import stat
import sys

def install(hooks=True):
    """
    Installs GitBark
    """
    
    if is_installed():
        print("Bark already installed!")
        return
    
    verify_bootstrap()

    if hooks:
        install_hooks()

    print("Installed bark successfully!")

def verify_bootstrap():
    git = Git()

    branch_rules_head_hash = git.repo.revparse_single("branch_rules").id.__str__()
    branch_rules_root_hash, _  = git.cmd("git", "rev-list", "--max-parents=0", branch_rules_head_hash)

    if not bootstrap_verified(branch_rules_root_hash):
        print("The bootstrap commit of the branch_rules branch has not been verified")
        print(f"The SHA hash of the root commit is {branch_rules_root_hash}.")
        answer = input("Are you sure you want to continue with this as the bootstrap commit (yes/no)? ")

        if answer == "yes":
            save_bootstrap(branch_rules_root_hash)
            print("Verifying repository....")
            report = verify(all=True, from_install=True)

            if not report.is_repo_valid():
                clear_bootstrap()
                print("Aborting installation!")
                sys.exit(1)
        else:
            sys.exit(0)
            

def bootstrap_verified(bootstrap_hash):
    working_directory = globals.working_directory
    bootstrap_commit_path = f"{working_directory.wd}/.git/gitbark_data/root_commit"
    if os.path.exists(bootstrap_commit_path):
        with open(bootstrap_commit_path, 'r') as f:
            commit_hash = f.read()
            if commit_hash == bootstrap_hash:
                return True
            else:
                return False

def save_bootstrap(bootstrap_hash):
    working_directory = globals.working_directory
    gitbark_path = f"{working_directory.wd}/.git/gitbark_data"
    bootstrap_commit_path = f"{gitbark_path}/root_commit"
    if not os.path.exists(gitbark_path):
        os.mkdir(gitbark_path)
    
    with open(bootstrap_commit_path, 'w') as f:
        f.write(bootstrap_hash)

def clear_bootstrap():
    working_directory = globals.working_directory
    gitbark_path = f"{working_directory.wd}/.git/gitbark_data"
    bootstrap_commit_path = f"{gitbark_path}/root_commit"
    with open(bootstrap_commit_path, 'r+') as f:
        f.truncate(0)

def install_hooks():
    print("Installing hooks....")
    reference_transaction_data = pkg_resources.resource_string(__name__, 'hooks/reference_transaction')
    prepare_commit_msg_data = pkg_resources.resource_string(__name__, 'hooks/prepare-commit-msg')

    working_directory = globals.working_directory
    hooks_path = f"{working_directory.wd}/.git/hooks"
    reference_transaction_path = f"{hooks_path}/reference-transaction"
    prepare_commit_msg_path = f"{hooks_path}/prepare-commit-msg"

    with open(reference_transaction_path, 'wb') as f:
        f.write(reference_transaction_data)
    make_executable(reference_transaction_path)

    with open(prepare_commit_msg_path, 'wb') as f:
        f.write(prepare_commit_msg_data)
    make_executable(prepare_commit_msg_path)

    print(f"Hooks installed in {hooks_path}")



def make_executable(path):
    current_permissions = os.stat(path).st_mode
    
    new_permissions = current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH

    os.chmod(path, new_permissions)

def hooks_installed():
    reference_transaction_data = pkg_resources.resource_string(__name__, 'hooks/reference_transaction').decode()
    prepare_commit_msg_data = pkg_resources.resource_string(__name__, 'hooks/prepare-commit-msg').decode()

    working_directory = globals.working_directory
    hooks_path = f"{working_directory.wd}/.git/hooks"
    reference_transaction_path = f"{hooks_path}/reference-transaction"
    prepare_commit_msg_path = f"{hooks_path}/prepare-commit-msg"

    if not os.path.exists(reference_transaction_path) or not os.path.exists(prepare_commit_msg_path):
        return False
    
    with open(reference_transaction_path, "r") as f:
        if not f.read() == reference_transaction_data:
            return False
    
    with open(prepare_commit_msg_path, "r") as f:
        if not f.read() == prepare_commit_msg_data:
            return False
        
    return True

def is_installed():
    git = Git()
    branch_rules_head_hash = git.repo.revparse_single("branch_rules").id.__str__()
    branch_rules_root_hash, _  = git.cmd("git", "rev-list", "--max-parents=0", branch_rules_head_hash)

    if bootstrap_verified(branch_rules_root_hash) and hooks_installed():
        return True
    else:
        return False



    


