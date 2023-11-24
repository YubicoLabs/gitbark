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

from gitbark.git import Repository

from pytest_gitbark.util import on_dir
import pytest


class TestInstall:
    def verify_install(self, repo: Repository, bark_cli, passes: bool):
        with on_dir(repo._path):
            if not passes:
                with pytest.raises(SystemExit):
                    bark_cli("install", input="y")
            else:
                bark_cli("install", input="y")

    def test_install_without_bark_rules(self, repo: Repository, bark_cli):
        self.verify_install(repo=repo, bark_cli=bark_cli, passes=False)

    def test_install_with_initialized(self, repo_initialized: Repository, bark_cli):
        self.verify_install(repo=repo_initialized, bark_cli=bark_cli, passes=True)
