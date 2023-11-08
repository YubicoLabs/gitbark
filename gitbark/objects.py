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

from .util import branch_name
from dataclasses import dataclass
from typing import Union, Any
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
            raise
            raise ValueError("Cannot parse branch rule!")

        return cls(
            pattern=pattern,
            bootstrap=bootstrap,
            rules=rules,
        )

    @classmethod
    def get_default(cls, pattern: str, bootstrap: bytes) -> "BranchRuleData":
        return cls(pattern=pattern, bootstrap=bootstrap.hex(), rules=[])


@dataclass
class BarkRules:
    branches: list[BranchRuleData]

    @classmethod
    def parse(cls, bark_rules: dict) -> "BarkRules":
        try:
            branches = [BranchRuleData.parse(rule) for rule in bark_rules["branches"]]
        except Exception:
            raise ValueError("Cannot parse bark_modules.yaml!")

        return cls(branches=branches)

    def get_branch_rules(self, ref: str) -> list[BranchRuleData]:
        branch = branch_name(ref)
        rules = []
        for data in self.branches:
            pattern = re.compile(data.pattern)
            if pattern.match(branch):
                rules.append(data)
        return rules
