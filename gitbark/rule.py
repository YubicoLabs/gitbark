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
from typing import Any, Optional
from importlib.metadata import entry_points


class RuleViolation(Exception):
    def __init__(
        self, message: str, sub_violations: Optional[list["RuleViolation"]] = None
    ):
        self.message = message
        self.sub_violations = sub_violations or []


class Rule(ABC):
    def __init__(
        self,
        name: str,  # TODO: remove
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

    @abstractmethod
    def validate(self, commit: Commit) -> None:
        raise RuleViolation(f"{self}.validate is not defined")

    def prepare_merge_msg(self, commit_msg_file: str) -> None:
        pass


_COMPOSITE_SENTINEL = object()


class _CompositeRule(Rule):
    def _parse_args(self, args: Any):
        if args is not _COMPOSITE_SENTINEL:
            self.sub_rules = [
                create_rule(
                    CommitRuleData.parse(data),
                    self.validator,
                    self.cache,
                    self.repo,
                )
                for data in args
            ]
            if len(self.sub_rules) < 2:
                raise ValueError("Composite rule must contain at least 2 child rules!")

    @classmethod
    def of(cls, name, commit, cache, repo, *rules: Rule) -> Rule:
        rule = cls(name, commit, cache, repo, _COMPOSITE_SENTINEL)
        rule.sub_rules = list(rules)
        return rule

    def _validate_children(self, commit: Commit) -> list[RuleViolation]:
        violations = []
        for rule in self.sub_rules:
            try:
                rule.validate(commit)
            except RuleViolation as e:
                violations.append(e)
        return violations

    def prepare_merge_msg(self, commit_msg_file: str) -> None:
        for rule in self.sub_rules:
            rule.prepare_merge_msg(commit_msg_file)


class AllRule(_CompositeRule):
    def validate(self, commit: Commit):
        violations = self._validate_children(commit)
        if violations:
            if len(violations) == 1:
                raise violations[0]
            raise RuleViolation(
                "All of the following conditions must be met:", violations
            )


class AnyRule(_CompositeRule):
    def validate(self, commit: Commit):
        violations = self._validate_children(commit)
        if len(self.sub_rules) - len(violations) <= 0:
            raise RuleViolation(
                "One of the following conditions must be met:", violations
            )


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
