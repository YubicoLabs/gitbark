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

from gitbark.util import cmd
from gitbark.git import Repository

from pytest_gitbark.util import verify_rules, write_commit_rules

from typing import Callable
import pytest


@pytest.mark.parametrize(
    "rules",
    [
        {"cr_rules": {"rules": [{"always_pass": None}]}, "passes": True},
        {"cr_rules": {"rules": [{"always_fail": None}]}, "passes": False},
        {
            "cr_rules": {
                "rules": [{"any": [{"always_pass": None}, {"always_fail": None}]}]
            },
            "passes": True,
        },
        {
            "cr_rules": {
                "rules": [{"any": [{"always_fail": None}, {"always_fail": None}]}]
            },
            "passes": False,
        },
        {
            "cr_rules": {
                "rules": [
                    {"always_pass": None},
                    {"any": [{"always_pass": None}, {"always_fail": None}]},
                ]
            },
            "passes": True,
        },
    ],
)
def test_commit_rule_validation(repo_installed: Repository, rules):
    action: Callable[[Repository], None] = lambda repo: cmd(
        "git", "commit", "-m", "Test action", "--allow-empty", cwd=repo._path
    )
    verify_rules(
        repo=repo_installed,
        passes=rules["passes"],
        action=action,
        commit_rules=rules["cr_rules"],
    )


@pytest.mark.parametrize(
    "rules",
    [
        {"ruless": None},
        {"rules": {"always_fail": None}},
        {"always_fail": None},
        {"rules": [{"not_exists_rule": None}]},
        {
            "rules": [
                {
                    "any": [
                        {"always_fail": None},
                    ]
                }
            ]
        },
    ],
)
def test_add_broken_commit_rules(repo_installed: Repository, rules):
    def action(repo: Repository):
        write_commit_rules(repo, rules)
        cmd("git", "commit", "-m", "Broken rule", cwd=repo._path)

    verify_rules(repo=repo_installed, passes=False, action=action)


def test_commit_with_invalid_bark_rules(repo_bark_rules_invalid: Repository):
    action: Callable[[Repository], None] = lambda repo: cmd(
        "git", "commit", "-m", "Invalid", "--allow-empty", cwd=repo._path
    )
    verify_rules(repo=repo_bark_rules_invalid, passes=False, action=action)
