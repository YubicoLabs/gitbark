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
from .objects import RuleData
from .project import Cache

from abc import ABC, abstractmethod
from typing import Any, Optional, ClassVar, Callable, Union
from importlib.metadata import entry_points


class RuleViolation(Exception):
    def __init__(
        self, message: str, sub_violations: Optional[list["RuleViolation"]] = None
    ):
        self.message = message
        self.sub_violations = sub_violations or []


class _Rule(ABC):
    setup: ClassVar[Optional[Callable[[], Union[dict, str]]]] = None

    def __init__(
        self,
        name: str,  # TODO: remove?
        commit: Commit,
        cache: Cache,
        args: Any,
    ) -> None:
        self.name = name
        self.validator = commit
        self.repo = commit.repo
        self.cache = cache
        self._parse_args(args)

    def _parse_args(self, args: Any) -> None:
        pass

    @staticmethod
    @abstractmethod
    def load_rule(rule: RuleData, commit: Commit, cache: Cache) -> "_Rule":
        pass


class CommitRule(_Rule):
    @abstractmethod
    def validate(self, commit: Commit) -> None:
        raise RuleViolation(f"{self}.validate is not defined")

    @staticmethod
    def load_rule(rule: RuleData, commit: Commit, cache: Cache) -> "CommitRule":
        rule_cls = entry_points(group="bark_commit_rules")[rule.id].load()
        return rule_cls(rule.id, commit, cache, rule.args)


class RefRule(_Rule):
    @abstractmethod
    def validate(self, commit: Commit, ref: str) -> None:
        raise RuleViolation(f"{self}.validate is not defined")

    @staticmethod
    def load_rule(rule: RuleData, commit: Commit, cache: Cache) -> "RefRule":
        rule_cls = entry_points(group="bark_ref_rules")[rule.id].load()
        return rule_cls(rule.id, commit, cache, rule.args)


class _CompositeRule(_Rule):
    def _parse_args(self, args: Any):
        if all(isinstance(a, _Rule) for a in args):
            self.sub_rules = args
        else:
            self.sub_rules = [
                self.load_rule(
                    RuleData.parse(data),
                    self.validator,
                    self.cache,
                )
                for data in args
            ]
            if len(self.sub_rules) < 2:
                raise ValueError("Composite rule must contain at least 2 child rules!")

    def _validate_children(
        self, commit: Commit, ref: Optional[str]
    ) -> list[RuleViolation]:
        args = (commit, ref) if ref is not None else (commit,)
        violations = []
        for rule in self.sub_rules:
            try:
                rule.validate(*args)
            except RuleViolation as e:
                violations.append(e)
        return violations


class _AllRule(_CompositeRule):
    def validate(self, commit: Commit, ref: Optional[str] = None):
        violations = self._validate_children(commit, ref)
        if violations:
            if len(violations) == 1:
                raise violations[0]
            raise RuleViolation(
                "All of the following conditions must be met:", violations
            )


class AllCommitRule(_AllRule, CommitRule):
    pass


class AllRefRule(_AllRule, RefRule):
    pass


class _AnyRule(_CompositeRule):
    def validate(self, commit: Commit, ref: Optional[str] = None):
        violations = self._validate_children(commit, ref)
        if len(self.sub_rules) - len(violations) <= 0:
            raise RuleViolation(
                "One of the following conditions must be met:", violations
            )


class AnyCommitRule(_AnyRule, CommitRule):
    pass


class AnyRefRule(_AnyRule, RefRule):
    pass


class NoneCommitRule(CommitRule):
    def validate(self, commit: Commit):
        pass


class NoneRefRule(RefRule):
    def validate(self, commit: Commit, ref: Optional[str] = None):
        pass
