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

from gitbark.core import BARK_RULES_BRANCH
from gitbark.objects import BarkRules, BranchRule
from gitbark.util import cmd

from .util import (
    get_test_bark_module,
    disable_bark,
    Environment,
    Repo,
)

from typing import Optional, Callable
from unittest.mock import patch

import pytest
import os


@pytest.fixture(autouse=True, scope="module")
def initialize_bark(env: Environment, bark_cli):
    # create the first commit
    bootstrap_main = env.repo.commit("Initial commit.")

    # create bark_rules
    branch_rule = BranchRule(
        pattern="main", bootstrap=bootstrap_main.hash, ff_only=False
    )
    bark_rules = BarkRules(branches=[branch_rule], modules=[get_test_bark_module()])
    env.repo.add_bark_rules(bark_rules)

    cwd = os.getcwd()
    os.chdir(env.repo.repo_dir)
    # bark install
    with patch("click.confirm", return_value="y"):
        bark_cli("install")
    os.chdir(cwd)

class TestVerify:
    def verify_rules(
        self,
        env: Environment,
        passes: bool,
        action: Callable[[Repo], None],
        commit_rules: Optional[dict] = None,
        bark_rules: Optional[dict] = None,
    ):

        curr_branch_head_a = env.repo.head
        curr_bark_rules_head = cmd(
            "git", "rev-parse", "bark_rules", cwd=env.repo.repo_dir
        )[0]

        if commit_rules:
            env.repo.add_commit_rules(commit_rules)

        if bark_rules:
            env.repo.add_bark_rules(bark_rules)

        self.verify_action(env, passes, action)

        # Reset to previous state
        with disable_bark(env.repo) as repo:
            repo.revert(curr_branch_head_a)
            repo.revert(curr_bark_rules_head, BARK_RULES_BRANCH)

    def verify_action(
        self, env: Environment, passes: bool, action: Callable[[Repo], None]
    ) -> None:
        curr_head = env.repo.head

        if passes:
            action(env.repo)
        else:
            with pytest.raises(Exception):
                action(env.repo)

        post_head = env.repo.head

        if passes:
            assert curr_head != post_head
        else:
            assert curr_head == post_head

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
    def test_commit_rule_validation(self, env: Environment, rules):
        action: Callable[[Repo], None] = lambda repo: repo.commit()
        self.verify_rules(
            env=env,
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
    def test_add_broken_commit_rules(self, env: Environment, rules):
        action: Callable[[Repo], None] = lambda repo: repo.add_commit_rules(rules)
        self.verify_rules(env=env, passes=False, action=action)
