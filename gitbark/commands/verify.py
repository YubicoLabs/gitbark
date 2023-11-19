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
from ..objects import BarkRules, RefRuleData
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

    bark_rules = get_bark_rules(project)
    rule_data = bark_rules.get_bark_rules(bootstrap.hash).rule_data
    validate_branch_rules(cache, head, BARK_RULES_REF, rule_data)


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
        bark_rules = get_bark_rules(project)

        if all:
            # Verify all branches defined by bark_rules
            verify_all(project, bark_rules)
        elif ref and head:
            # Verify target branch
            if ref == BARK_RULES_REF and project.bootstrap:
                # Validate bark_rules branch
                rules = [bark_rules.get_bark_rules(project.bootstrap.hash)]
            else:
                verify_bark_rules(project)
                rules = bark_rules.get_ref_rules(ref)

            verify_ref(
                project=project,
                ref=ref,
                head=head,
                rules=rules,
            )


def verify_all(project: Project, bark_rules: BarkRules):
    """Verify all branches matching branch_rules."""
    verify_bark_rules(project)

    violations = []
    rules = bark_rules.get_ref_rules()
    for ref, head in project.repo.references.items():
        matching_rules = [r for r in rules if r.pattern.match(ref)]
        if matching_rules:
            try:
                verify_ref(
                    project=project,
                    ref=ref,
                    head=head,
                    rules=matching_rules,
                )
            except RuleViolation as e:
                violations.append(e)

    if violations:
        raise RuleViolation("Not all branches were valid", violations)


def verify_ref(
    project: Project,
    ref: str,
    head: Commit,
    rules: list[RefRuleData],
) -> None:
    """Verify branch against branch rules and commit rules."""

    if not rules:
        raise RuleViolation(f"No rules defined for {ref}")
    for rule in rules:
        bootstrap = Commit(rule.bootstrap, project.repo)
        cache = project.get_cache(bootstrap)
        validate_commit_rules(cache, head, bootstrap)
        validate_branch_rules(cache, head, ref, rule.rule_data)
