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

from .git import Commit
from .objects import CompositeCommitRuleData, CommitRuleData
from .project import Cache, Project

from abc import ABC, abstractmethod
from pygit2 import Repository
from typing import Union, Any
from importlib.metadata import entry_points


class Rule(ABC):
    def __init__(
        self,
        name: str,
        commit: Commit,
        cache: Cache,
        repo: Repository,
        args: dict[str, Any] = {},
    ) -> None:
        self.name = name
        self.validator = commit
        self.args = args
        self.cache = cache
        self.repo = repo
        self.violation: str = ""

    def add_violation(self, violation: str) -> None:
        self.violation = violation

    def get_violation(self) -> str:
        return self.violation

    @abstractmethod
    def validate(self, commit: Commit) -> bool:
        pass

    def prepare_merge_msg(self, commit_msg_file: str) -> None:
        pass


class CompositeRule(Rule):
    def __init__(self) -> None:
        self.violation: str = ""
        self.sub_rules: list[Rule] = []

    def add_sub_rule(self, rule: Rule):
        self.sub_rules.append(rule)

    def validate(self, commit: Commit) -> bool:
        if not any(rule.validate(commit) for rule in self.sub_rules):
            return False
        return True

    def get_violation(self):
        violations = [rule.get_violation() for rule in self.sub_rules]
        return " and ".join(violations)


def get_rules(commit: Commit, project: Project) -> list[Rule]:
    rules: list[Union[Rule, CompositeRule]] = []

    for rule in commit.get_commit_rules().rules:
        if isinstance(rule, CompositeCommitRuleData):
            composite_rule = CompositeRule()
            for sub_rule in rule.rules:
                composite_rule.add_sub_rule(
                    create_rule(
                        sub_rule,
                        commit,
                        project.cache,
                        project.repo,
                    )
                )
            rules.append(composite_rule)
        else:
            rules.append(create_rule(rule, commit, project.cache, project.repo))
    return rules


def create_rule(
    rule: CommitRuleData,
    commit: Commit,
    cache: Cache,
    repo: Repository,
) -> Rule:
    rule_cls = entry_points(group="bark_rules")[rule.id].load()
    return rule_cls(rule.id, commit, cache, repo, rule.args)
