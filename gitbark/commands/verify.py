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
from ..rule import RuleViolation
from ..project import Project

from typing import Optional


def verify_bark_rules(project: Project):
    """Verifies the bark_rules branch."""
    bootstrap = Commit(project.bootstrap, project.repo)
    head = Commit(project.repo.lookup_branch(BARK_RULES_BRANCH).target, project.repo)
    verify_branch(
        project=project,
        branch=BARK_RULES_BRANCH,
        head=head,
        bootstrap=bootstrap,
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
) -> None:
    """Verifies a branch or the entire repository.

    If `all` is set, the entire repository will be validated. Otherwise
    `branch` will be validated.
    """

    if bootstrap and head:
        validate_commit_rules(
            project=project,
            head=head,
            bootstrap=bootstrap,
            branch=branch,
        )
    else:
        verify_bark_rules(project)

        bark_rules = get_bark_rules(project)
        branch_rules = bark_rules.branches

        if all:
            # Verify all branches matching branch_rules
            verify_all(project, branch_rules)
        elif branch and head:
            # Verify target branch
            branch_rule = get_branch_rule(project, branch, branch_rules)
            if branch_rule:
                bootstrap = Commit(branch_rule.bootstrap, project.repo)
            # TODO: raise some error if no branch_rule matches the branch
            if bootstrap:
                verify_branch(
                    project=project,
                    branch=branch,
                    head=head,
                    bootstrap=bootstrap,
                    branch_rule=branch_rule,
                )


def verify_all(project: Project, branch_rules: list[BranchRule]):
    """Verify all branches matching branch_rules."""
    violations = []
    for rule in branch_rules:
        for branch in rule.branches(project.repo):
            head_hash = project.repo.branches[branch].target
            head = Commit(head_hash, project.repo)
            bootstrap = Commit(rule.bootstrap, project.repo)
            try:
                verify_branch(
                    project=project,
                    branch=branch,
                    head=head,
                    bootstrap=bootstrap,
                    branch_rule=rule,
                )
            except RuleViolation as e:
                violations.append(e)
    if violations:
        raise RuleViolation("Not all branches were valid", violations)


def verify_branch(
    project: Project,
    branch: str,
    head: Commit,
    bootstrap: Commit,
    branch_rule: Optional[BranchRule] = None,
) -> None:
    """Verify branch against branch rules and commit rules."""
    if branch_rule:
        validate_branch_rules(project, head, branch, branch_rule)

    validate_commit_rules(project, head, bootstrap, branch)
