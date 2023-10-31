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

from .util import (
    Environment,
    Repo,
)

from typing import Optional, Callable

import pytest


class TestVerify:
    def verify_rules(
        self,
        env: Environment,
        passes: bool,
        action: Callable[[Repo], None],
        commit_rules: Optional[dict] = None,
        bark_rules: Optional[dict] = None,
    ):
        if commit_rules:
            env.repo.add_commit_rules(commit_rules)

        if bark_rules:
            env.repo.add_bark_rules(bark_rules)

        self.verify_action(env, passes, action)

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
    def test_commit_rule_validation(self, env_installed: Environment, rules):
        action: Callable[[Repo], None] = lambda repo: repo.commit()
        self.verify_rules(
            env=env_installed,
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
    def test_add_broken_commit_rules(self, env_installed: Environment, rules):
        action: Callable[[Repo], None] = lambda repo: repo.add_commit_rules(rules)
        self.verify_rules(env=env_installed, passes=False, action=action)

    def test_commit_with_invalid_bark_rules(self, env_bark_rules_invalid: Environment):
        action: Callable[[Repo], None] = lambda repo: repo.commit()
        self.verify_rules(env=env_bark_rules_invalid, passes=False, action=action)
