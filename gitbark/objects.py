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

from dataclasses import dataclass
from typing import Union
from pygit2 import Repository
import re


@dataclass
class CommitRuleData:
    id: str
    args: dict

    @classmethod
    def parse(cls, commit_rule: dict) -> "CommitRuleData":
        try:
            id = commit_rule["rule"]
            args = cls.parse_args(commit_rule["args"])
        except Exception:
            raise ValueError("Cannot parse commit rule!")

        return cls(id=id, args=args)

    @staticmethod
    def parse_args(args: list[str]) -> dict:
        args_new = {}
        for arg in args:
            name, val = arg.split("=")
            args_new[name] = val

        return args_new


@dataclass
class CompositeCommitRuleData:
    rules: list[CommitRuleData]

    @classmethod
    def parse(cls, commit_rules: list[dict]) -> "CompositeCommitRuleData":
        rules = []
        for rule in commit_rules:
            rules.append(CommitRuleData.parse(rule))

        return cls(rules=rules)


@dataclass
class CommitRulesData:
    rules: list[Union[CommitRuleData, CompositeCommitRuleData]]

    @classmethod
    def parse(cls, commit_rules: dict) -> "CommitRulesData":
        rules: list[Union[CommitRuleData, CompositeCommitRuleData]] = []
        try:
            for rule in commit_rules["rules"]:
                if "any" in rule:
                    composite_commit_rule = CompositeCommitRuleData.parse(rule["any"])
                    rules.append(composite_commit_rule)
                else:
                    commit_rule = CommitRuleData.parse(rule)
                    rules.append(commit_rule)

        except Exception as e:
            raise e

        return cls(rules=rules)


@dataclass
class BranchRule:
    pattern: str
    bootstrap: str
    ff_only: bool

    @classmethod
    def parse(cls, branch_rule: dict) -> "BranchRule":
        try:
            pattern = branch_rule["pattern"]
            bootstrap = branch_rule["bootstrap"]
            ff_only = branch_rule["ff_only"]
        except Exception:
            raise ValueError("Cannot parse branch rule!")

        return cls(
            pattern=pattern,
            bootstrap=bootstrap,
            ff_only=ff_only,
        )

    @classmethod
    def get_default(cls, pattern: str, bootstrap: str) -> "BranchRule":
        return cls(pattern=pattern, bootstrap=bootstrap, ff_only=True)

    def branches(self, repo: Repository) -> list[str]:
        pattern = re.compile(f".*{self.pattern}")
        all_branches = list(repo.references)
        return [branch for branch in all_branches if pattern.match(branch)]


@dataclass
class BarkRules:
    branches: list[BranchRule]
    modules: list[str]

    @classmethod
    def parse(cls, bark_rules: dict) -> "BarkRules":
        try:
            branches = [BranchRule.parse(rule) for rule in bark_rules["branches"]]
            if "modules" not in bark_rules:
                modules = []
            else:
                modules = bark_rules["modules"]
        except Exception:
            raise ValueError("Cannot parse bark_modules.yaml!")

        return cls(branches=branches, modules=modules)
