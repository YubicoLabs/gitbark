
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




