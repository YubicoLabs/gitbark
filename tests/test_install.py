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

from .util import Environment

from unittest.mock import patch

import os


class TestInstall:
    def verify_install(self, env: Environment, bark_cli, passes: bool):
        cwd = os.getcwd()
        os.chdir(env.repo.repo_dir)
        with patch("click.confirm", return_value="y"):
            result = bark_cli("install")
        if passes:
            assert result.exit_code == 0
        else:
            assert result.exit_code != 0
        os.chdir(cwd)

    def test_install_without_bark_rules(self, env_clean: Environment, bark_cli):
        self.verify_install(env=env_clean, bark_cli=bark_cli, passes=False)

    def test_install_with_invalid_bark_rules(
        self, env_bark_rules_invalid: Environment, bark_cli
    ):
        self.verify_install(env=env_bark_rules_invalid, bark_cli=bark_cli, passes=False)

    def test_install_with_initialized(self, env_initialized: Environment, bark_cli):
        self.verify_install(env=env_initialized, bark_cli=bark_cli, passes=True)
