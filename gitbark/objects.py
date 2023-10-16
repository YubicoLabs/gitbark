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
from typing import Union, Any
from pygit2 import Repository
import re


@dataclass
class CommitRuleData:
    id: str
    args: Any

    @classmethod
    def parse(cls, commit_rule: Union[str, dict]) -> "CommitRuleData":
        if isinstance(commit_rule, str):
            # No args, just the rule name
            return cls(id=commit_rule, args=None)
        try:
            # Rule has args
            rule_id, args = (k := next(iter(commit_rule)), commit_rule.pop(k))
            if commit_rule:  # More keys, only valid if arg is None
                if args is None:
                    args = commit_rule
                else:
                    raise ValueError("Cannot parse commit rule!")
            return cls(id=rule_id, args=args)
        except Exception:
            raise ValueError("Cannot parse commit rule!")


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
        pattern = re.compile(f"{self.pattern}")
        all_branches = list(repo.branches.local)
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
