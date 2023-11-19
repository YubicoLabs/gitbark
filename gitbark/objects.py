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
from typing import Union, Any, Optional
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
class RefRules:
    pattern: str
    rules: list

    @classmethod
    def parse(cls, data: dict) -> "RefRules":
        return cls(
            pattern=data["pattern"],
            rules=data.get("rules", []),
        )


@dataclass
class BootstrapEntry:
    bootstrap: str
    refs: list[RefRules]

    @classmethod
    def parse(cls, data: dict) -> "BootstrapEntry":
        return cls(
            bootstrap=data["bootstrap"],
            refs=[RefRules.parse(d) for d in data.get("refs", [])],
        )


@dataclass
class RefRuleData:
    bootstrap: bytes
    pattern: re.Pattern
    rule_data: RuleData


@dataclass
class BarkRules:
    bark_rules: list
    project: list

    def __post_init__(self):
        # Make sure data parses correctly
        self.get_bark_rules(b"")
        self.get_ref_rules()

    @classmethod
    def parse(cls, bark_rules: dict) -> "BarkRules":
        return cls(bark_rules.get("bark_rules", []), bark_rules.get("project", []))

    def get_bark_rules(self, bootstrap: bytes) -> RefRuleData:
        return RefRuleData(
            bootstrap,
            re.compile(r"refs/heads/bark_rules"),
            RuleData.parse_list(self.bark_rules or []),
        )

    def get_ref_rules(self, ref: Optional[str] = None) -> list[RefRuleData]:
        rules = [
            RefRuleData(
                bytes.fromhex(e["bootstrap"]),
                re.compile(r["pattern"]),
                RuleData.parse_list(r.get("rules", [])),
            )
            for e in self.project or []
            for r in e["refs"]
        ]
        if ref:
            return [r for r in rules if r.pattern.match(ref)]
        return rules
