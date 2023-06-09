# Copyright 2023 Yubico AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import subprocess
import os
import sys

class WorkingDirectory:
    def __init__(self) -> None:
        self.wd = self.get_working_directory()
    def get_working_directory(self):
        try:
            git_repo_root = ""
            if "TEST_WD" in os.environ:
                git_repo_root = os.environ["TEST_WD"]
            else:
                git_repo_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).rstrip()
            git_repo_content = os.listdir(git_repo_root)
            if ".gitbark" in git_repo_content:
                return git_repo_root
            else:
                print("fatal: bark has not been initialized on this repository")
                sys.exit(1)
        except subprocess.CalledProcessError as cpe:
            print(cpe.output)
            sys.exit(1)
