from gitbark.rule import Rule, RuleViolation
from gitbark.git import Commit


class AlwaysFailRule(Rule):
    def validate(self, commit: Commit) -> None:
        msg = commit.message
        if not "Skip" in msg:
            raise RuleViolation("Violation")


class AlwaysPassRule(Rule):
    def validate(self, commit: Commit) -> None:
        pass
