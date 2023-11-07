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
    BARK_RULES_REF,
)
from ..objects import BarkRules
from ..git import Commit
from ..rule import RuleViolation
from ..project import Project
from ..cli.util import CliFail

from typing import Optional


def verify_bark_rules(project: Project):
    """Verifies the bark_rules branch."""
    head = project.repo.references[BARK_RULES_REF]
    bootstrap = project.bootstrap
    if not bootstrap:
        raise CliFail("No bootstrap commit selected")

    validate_commit_rules(project, head, bootstrap, BARK_RULES_REF)


def verify(
    project: Project,
    ref: Optional[str] = None,
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
            ref=ref,
        )
    else:
        verify_bark_rules(project)

        bark_rules = get_bark_rules(project)

        if all:
            # Verify all branches defined by bark_rules
            verify_all(project, bark_rules)
        elif ref and head:
            # Verify target branch
            # TODO: raise some error if no branch_rule matches the branch
            verify_branch(
                project=project,
                ref=ref,
                head=head,
                bark_rules=bark_rules,
            )


def verify_all(project: Project, bark_rules: BarkRules):
    """Verify all branches matching branch_rules."""
    violations = []
    for ref, head in project.repo.references.items():
        try:
            verify_branch(
                project=project,
                ref=ref,
                head=head,
                bark_rules=bark_rules,
            )
        except RuleViolation as e:
            violations.append(e)
    if violations:
        raise RuleViolation("Not all branches were valid", violations)


def verify_branch(
    project: Project,
    ref: str,
    head: Commit,
    bark_rules: BarkRules,
) -> None:
    """Verify branch against branch rules and commit rules."""

    for rule in bark_rules.get_branch_rules(ref):
        bootstrap = Commit(bytes.fromhex(rule.bootstrap), project.repo)
        validate_commit_rules(project, head, bootstrap, ref)
        validate_branch_rules(project, head, ref, rule)
