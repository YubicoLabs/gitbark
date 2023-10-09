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

from ..core import (
    validate_commit_rules,
    validate_branch_rules,
    get_bark_rules,
    BARK_RULES_BRANCH,
)
from ..objects import BranchRule
from ..git import Commit
from ..project import Project

from typing import Optional
from dataclasses import dataclass


@dataclass
class BranchReport:
    branch: str
    head: Commit
    violations: list[str]


class Report:
    def __init__(self) -> None:
        self.log: list[BranchReport] = []

    def is_repo_valid(self):
        return len(self.log) == 0

    def add_violations(self, branch: str, head: Commit):
        branch_report = BranchReport(
            branch=branch, head=head, violations=head.violations
        )
        self.log.append(branch_report)


def verify_bark_rules(
    project: Project,
    report: Report,
):
    """Verifies the bark_rules branch."""
    bootstrap = Commit(project.bootstrap)
    head = Commit(project.repo.references[BARK_RULES_BRANCH].target)
    return verify_branch(
        project=project,
        branch=BARK_RULES_BRANCH,
        head=head,
        bootstrap=bootstrap,
        report=report,
    )


def get_branch_rule(
    project: Project, branch: str, rules: list[BranchRule]
) -> Optional[BranchRule]:
    if branch == BARK_RULES_BRANCH:
        return BranchRule.get_default(BARK_RULES_BRANCH, project.bootstrap)

    for rule in rules:
        if branch in rule.branches(project.repo):
            return rule
    return None


def verify(
    project: Project,
    branch: Optional[str] = None,
    head: Optional[Commit] = None,
    bootstrap: Optional[Commit] = None,
    all: bool = False,
) -> Report:
    """Verifies a branch or the entire repository.

    If `all` is set, the entire repository will be validated. Otherwise
    `branch` will be validated.
    """
    report = Report()

    if not verify_bark_rules(project, report):
        return report

    bark_rules = get_bark_rules(project)
    project.load_rule_entrypoints()
    branch_rules = bark_rules.branches

    if all:
        # Verify all branches matching branch_rules
        verify_all(project, report, branch_rules)
    elif branch and head:
        # Verify target branch
        branch_rule = get_branch_rule(project, branch, branch_rules)
        if branch_rule:
            bootstrap = Commit(branch_rule.bootstrap)
        if bootstrap:
            verify_branch(
                project=project,
                branch=branch,
                head=head,
                bootstrap=bootstrap,
                branch_rule=branch_rule,
                report=report,
            )

    return report


def verify_all(project: Project, report: Report, branch_rules: list[BranchRule]):
    """Verify all branches matching branch_rules."""
    for rule in branch_rules:
        for branch in rule.branches(project.repo):
            head_hash = project.repo.references[branch].target
            head = Commit(head_hash)
            bootstrap = Commit(rule.bootstrap)
            verify_branch(
                project=project,
                branch=branch,
                head=head,
                bootstrap=bootstrap,
                report=report,
                branch_rule=rule,
            )

    return report


def verify_branch(
    project: Project,
    branch: str,
    head: Commit,
    bootstrap: Commit,
    report: Report,
    branch_rule: Optional[BranchRule] = None,
) -> bool:
    """Verify branch against branch rules and commit rules."""
    if branch_rule and not validate_branch_rules(project, head, branch, branch_rule):
        report.add_violations(branch, head)
        return False

    if not validate_commit_rules(project, head, bootstrap, branch):
        report.add_violations(branch, head)
        return False

    return True
