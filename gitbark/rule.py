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
from typing import Union
import importlib
import inspect


class Rule(ABC):
    def __init__(
        self, name: str, commit: Commit, cache: Cache, args: dict = {}
    ) -> None:
        self.name = name
        self.validator = commit
        self.args = args
        self.cache = cache
        self.sub_rules: list["Rule"] = []
        self.violation = None

    def get_sub_rules(self) -> list["Rule"]:
        return self.sub_rules

    def add_sub_rule(self, rule: "Rule"):
        self.sub_rules.append(rule)

    def add_violation(self, violation):
        self.violation = violation

    def get_violation(self):
        return self.violation

    @abstractmethod
    def validate(self, commit: Commit) -> bool:
        pass


class CompositeRule(Rule):
    def validate(self, commit: Commit) -> bool:
        if not any(rule.validate(commit) for rule in self.get_sub_rules()):
            return False
        return True

    def get_violation(self):
        violations = [rule.get_violation() for rule in self.get_sub_rules()]
        return " and ".join(violations)


def get_rules(commit: Commit, project: Project) -> list[Rule]:
    # TODO should implement a caching mechanism here so that we don't need
    # to import rule modules multiple times.
    cache = project.cache
    rule_to_entrypoint = project.rule_entrypoints
    commit_rules = commit.get_commit_rules()
    rules: list[Union[Rule, CompositeRule]] = []

    for rule in commit_rules.rules:
        if isinstance(rule, CompositeCommitRuleData):
            composite_rule = CompositeRule("any", commit, cache)
            for sub_rule in rule.rules:
                composite_rule.add_sub_rule(
                    create_rule(sub_rule, commit, rule_to_entrypoint, cache)
                )
            rules.append(composite_rule)
        else:
            rules.append(create_rule(rule, commit, rule_to_entrypoint, cache))
    return rules


def load_rule_module(rule_id, rule_to_entrypoint):
    # Need to know from bark_module.yaml the entrypoints
    module_name = rule_to_entrypoint[rule_id]
    module = importlib.import_module(module_name)
    for _, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, Rule):
            return obj


def create_rule(
    rule: CommitRuleData, commit: Commit, rule_to_entrypoint, cache: Cache
) -> Rule:
    rule_module = load_rule_module(rule.id, rule_to_entrypoint)
    return rule_module(rule.id, commit, cache, rule.args)
