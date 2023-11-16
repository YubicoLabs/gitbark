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
    BARK_REQUIREMENTS,
)
from ..objects import BarkRules, BranchRuleData
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

    def on_valid(commit: Commit) -> None:
        requirements = commit.read_file(BARK_REQUIREMENTS)
        project.install_modules(requirements)

    cache = project.get_cache(bootstrap)
    validate_commit_rules(cache, head, bootstrap, on_valid)


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
        cache = project.get_cache(bootstrap)
        validate_commit_rules(
            cache=cache,
            head=head,
            bootstrap=bootstrap,
        )
    else:
        verify_bark_rules(project)

        bark_rules = get_bark_rules(project)

        if all:
            # Verify all branches defined by bark_rules
            verify_all(project, bark_rules)
        elif ref and head:
            # Verify target branch
            rules = bark_rules.get_branch_rules(ref)
            verify_branch(
                project=project,
                ref=ref,
                head=head,
                rules=rules,
            )


def verify_all(project: Project, bark_rules: BarkRules):
    """Verify all branches matching branch_rules."""
    violations = []
    for branch in project.repo.branches:
        head, ref = project.repo.resolve(branch)
        assert ref
        rules = bark_rules.get_branch_rules(ref)
        if rules:
            try:
                verify_branch(
                    project=project,
                    ref=ref,
                    head=head,
                    rules=rules,
                )
            except RuleViolation as e:
                violations.append(e)

    if violations:
        raise RuleViolation("Not all branches were valid", violations)


def verify_branch(
    project: Project,
    ref: str,
    head: Commit,
    rules: list[BranchRuleData],
) -> None:
    """Verify branch against branch rules and commit rules."""

    if not rules:
        raise RuleViolation(f"No rules defined for {ref}")
    for rule in rules:
        bootstrap = Commit(bytes.fromhex(rule.bootstrap), project.repo)
        cache = project.get_cache(bootstrap)
        validate_commit_rules(cache, head, bootstrap)
        validate_branch_rules(cache, head, ref, rule)
