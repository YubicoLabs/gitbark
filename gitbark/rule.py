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
from .objects import CommitRuleData
from .project import Cache, Project

from abc import ABC, abstractmethod
from pygit2 import Repository
from typing import Any
from importlib.metadata import entry_points


class Rule(ABC):
    def __init__(
        self,
        name: str,
        commit: Commit,
        cache: Cache,
        repo: Repository,
        args: Any,
    ) -> None:
        self.name = name
        self.validator = commit
        self.cache = cache
        self.repo = repo
        self.violations: list[str] = []
        self._parse_args(args)

    def _parse_args(self, args: Any) -> None:
        pass

    def add_violation(self, violation: str) -> None:
        self.violations.append(violation)

    def get_violations(self) -> list[str]:
        return self.violations

    @abstractmethod
    def validate(self, commit: Commit) -> bool:
        pass

    def prepare_merge_msg(self, commit_msg_file: str) -> None:
        pass


class _CompositeRule(Rule):
    def _parse_args(self, args: Any):
        self.sub_rules = [
            create_rule(
                CommitRuleData.parse(data),
                self.validator,
                self.cache,
                self.repo,
            )
            for data in args
        ]

    def get_violations(self):
        violations = []
        for rule in self.sub_rules:
            violations.extend(rule.get_violations())
        return violations

    def prepare_merge_msg(self, commit_msg_file: str) -> None:
        for rule in self.sub_rules:
            rule.prepare_merge_msg(commit_msg_file)


class AllRule(_CompositeRule):
    def validate(self, commit: Commit) -> bool:
        # N.B. Make sure all rules validate without short-circuit logic.
        return all([rule.validate(commit) for rule in self.sub_rules])


class AnyRule(_CompositeRule):
    def validate(self, commit: Commit) -> bool:
        return any(rule.validate(commit) for rule in self.sub_rules)


def get_rule(commit: Commit, project: Project) -> Rule:
    rule_data = commit.get_commit_rules()
    return create_rule(rule_data, commit, project.cache, project.repo)


def create_rule(
    rule: CommitRuleData,
    commit: Commit,
    cache: Cache,
    repo: Repository,
) -> Rule:
    rule_cls = entry_points(group="bark_rules")[rule.id].load()
    return rule_cls(rule.id, commit, cache, repo, rule.args)
