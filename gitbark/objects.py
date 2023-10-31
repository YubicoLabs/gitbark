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
class RuleData:
    id: str
    args: Any

    @classmethod
    def parse(cls, data: Union[str, dict]) -> "RuleData":
        if isinstance(data, str):
            # No args, just the rule name
            return cls(id=data, args=None)

        try:
            # Rule has args
            rule_id, args = (k := next(iter(data)), data.pop(k))
            if data:  # More keys, only valid if arg is None
                if args is None:
                    args = data
                else:
                    raise ValueError("Cannot parse commit rule!")
            return cls(id=rule_id, args=args)
        except Exception:
            raise ValueError("Cannot parse commit rule!")

    @classmethod
    def parse_list(cls, data: list) -> "RuleData":
        # List of rules, combine with "all" if multiple, "none" if empty
        if len(data) > 1:
            args: dict[str, Any] = {"all": data}
        elif len(data) == 1:
            args = data[0]
        else:
            args = {"none": None}
        return cls.parse(args)


@dataclass
class BranchRuleData:
    pattern: str
    bootstrap: str
    rules: list

    @classmethod
    def parse(cls, branch_rule: dict) -> "BranchRuleData":
        try:
            pattern = branch_rule["pattern"]
            bootstrap = branch_rule["bootstrap"]
            rules = branch_rule.get("rules", [])
        except Exception:
            raise ValueError("Cannot parse branch rule!")

        return cls(
            pattern=pattern,
            bootstrap=bootstrap,
            rules=rules,
        )

    @classmethod
    def get_default(cls, pattern: str, bootstrap: str) -> "BranchRuleData":
        return cls(pattern=pattern, bootstrap=bootstrap, rules=[])

    def branches(self, repo: Repository) -> list[str]:
        pattern = re.compile(self.pattern)
        return [branch for branch in list(repo.branches.local) if pattern.match(branch)]


@dataclass
class BarkRules:
    branches: list[BranchRuleData]
    modules: list[str]

    @classmethod
    def parse(cls, bark_rules: dict) -> "BarkRules":
        try:
            branches = [BranchRuleData.parse(rule) for rule in bark_rules["branches"]]
            modules = bark_rules.get("modules", [])
        except Exception:
            raise ValueError("Cannot parse bark_modules.yaml!")

        return cls(branches=branches, modules=modules)
