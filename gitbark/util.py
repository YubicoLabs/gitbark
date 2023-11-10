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

import subprocess
from typing import Any


BRANCH_REF_PREFIX = "refs/heads/"


def cmd(*cmd: str, check: bool = True, **kwargs: Any):
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, **kwargs
        )
        return result.stdout.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        if check:
            raise e
        else:
            return e.stdout, e.returncode


def branch_name(ref: str) -> str:
    if ref.startswith(BRANCH_REF_PREFIX):
        return ref[len(BRANCH_REF_PREFIX) :]
    raise ValueError(f"Ref does not describe a branch: '{ref}'")
