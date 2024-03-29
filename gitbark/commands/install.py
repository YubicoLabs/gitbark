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

from ..project import Project

import pkg_resources
import os
import stat
import logging

logger = logging.getLogger(__name__)


def install(project: Project) -> None:
    """
    Installs GitBark
    """
    if not hooks_installed(project):
        install_hooks(project)


def install_hooks(project: Project):
    logger.debug("Installing hooks...")
    reference_transaction_data = pkg_resources.resource_string(
        __name__, "hooks/reference_transaction"
    )

    hooks_path = f"{project.path}/.git/hooks"
    reference_transaction_path = f"{hooks_path}/reference-transaction"

    with open(reference_transaction_path, "wb") as f:
        f.write(reference_transaction_data)
    make_executable(reference_transaction_path)

    logger.info(f"Hooks installed in {hooks_path}")


def make_executable(path: str):
    current_permissions = os.stat(path).st_mode

    new_permissions = current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH

    os.chmod(path, new_permissions)


def hooks_installed(project: Project):
    reference_transaction_data = pkg_resources.resource_string(
        __name__, "hooks/reference_transaction"
    ).decode()

    hooks_path = f"{project.path}/.git/hooks"
    reference_transaction_path = f"{hooks_path}/reference-transaction"

    if not os.path.exists(reference_transaction_path):
        return False

    with open(reference_transaction_path, "r") as f:
        if not f.read() == reference_transaction_data:
            return False

    return True
