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

from .verify import verify, Report
from ..project import Project
from ..util import cmd

import pkg_resources
import os
import stat


def install(project: Project) -> Report:
    """
    Installs GitBark
    """

    # Verify the branch rules branch
    report = verify(project, all=True)

    if not report.is_repo_valid():
        # Do something
        return report

    # If everything goes well, install hooks
    if not hooks_installed(project):
        install_hooks(project)

    return report


def bootstrap_verified(project: Project) -> bool:
    try:
        root_commit = cmd("git", "rev-list", "--max-parents=0", "branch_rules")[0]
    except Exception:
        root_commit = ""
    return root_commit == project.bootstrap


def is_installed(project: Project) -> bool:
    return bootstrap_verified(project) and hooks_installed(project)


def install_hooks(project: Project):
    print("Installing hooks....")
    reference_transaction_data = pkg_resources.resource_string(
        __name__, "hooks/reference_transaction"
    )
    prepare_commit_msg_data = pkg_resources.resource_string(
        __name__, "hooks/prepare-commit-msg"
    )

    hooks_path = f"{project.project_path}/.git/hooks"
    reference_transaction_path = f"{hooks_path}/reference-transaction"
    prepare_commit_msg_path = f"{hooks_path}/prepare-commit-msg"

    with open(reference_transaction_path, "wb") as f:
        f.write(reference_transaction_data)
    make_executable(reference_transaction_path)

    with open(prepare_commit_msg_path, "wb") as f:
        f.write(prepare_commit_msg_data)
    make_executable(prepare_commit_msg_path)

    print(f"Hooks installed in {hooks_path}")


def make_executable(path: str):
    current_permissions = os.stat(path).st_mode

    new_permissions = current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH

    os.chmod(path, new_permissions)


def hooks_installed(project: Project):
    reference_transaction_data = pkg_resources.resource_string(
        __name__, "hooks/reference_transaction"
    ).decode()
    prepare_commit_msg_data = pkg_resources.resource_string(
        __name__, "hooks/prepare-commit-msg"
    ).decode()

    hooks_path = f"{project.path}/.git/hooks"
    reference_transaction_path = f"{hooks_path}/reference-transaction"
    prepare_commit_msg_path = f"{hooks_path}/prepare-commit-msg"

    if not os.path.exists(reference_transaction_path) or not os.path.exists(
        prepare_commit_msg_path
    ):
        return False

    with open(reference_transaction_path, "r") as f:
        if not f.read() == reference_transaction_data:
            return False

    with open(prepare_commit_msg_path, "r") as f:
        if not f.read() == prepare_commit_msg_data:
            return False

    return True
