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

from gitbark.git.commit import Commit
from gitbark.cache import Cache
from abc import ABC, abstractmethod


class Rule(ABC):
    def __init__(self, name, args=None) -> None:
        self.name = name
        self.args = args
        self.sub_rules = []
        self.violation = None

    def get_sub_rules(self) -> list["Rule"]:
        return self.sub_rules

    def add_sub_rule(self, rule):
        self.sub_rules.append(rule)

    def add_violation(self, violation):
        self.violation = violation

    def get_violation(self):
        return self.violation

    @abstractmethod    
    def validate(self, commit:Commit, validator:Commit=None, cache:Cache=None) -> bool:
        pass

class CompositeRule(Rule):
    def validate(self, commit: Commit, validator: Commit = None, cache: Cache = None) -> bool:
        if not any(rule.validate(commit, validator, cache) for rule in self.get_sub_rules()):
            return False
        return True
    
    def get_violation(self):
        violations = [rule.get_violation() for rule in self.get_sub_rules()]
        return " and ".join(violations)
        




