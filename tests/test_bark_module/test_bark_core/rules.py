from gitbark.rule import CommitRule, RuleViolation
from gitbark.git import Commit


class AlwaysFailRule(CommitRule):
    def validate(self, commit: Commit) -> None:
        msg = commit.message
        if not "Skip" in msg:
            raise RuleViolation("Violation")


class AlwaysPassRule(CommitRule):
    def validate(self, commit: Commit) -> None:
        pass
