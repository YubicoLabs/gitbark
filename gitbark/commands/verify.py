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


def verify_bark_rules(project: Project) -> BarkRules:
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
    return bark_rules


def verify_commit(project: Project, commit: Commit, bootstrap: Commit):
    """Verifies a commit.

    The given bootstrap is used to verify commit rules.
    """
    cache = project.get_cache(bootstrap)
    validate_commit_rules(
        cache=cache,
        head=commit,
        bootstrap=bootstrap,
    )


def verify_ref(
    project: Project,
    ref: str,
    head: Commit,
) -> None:
    """Verifies a ref.

    The head should be the current target of the ref.
    Uses bark_rules to find matching (commit and ref) rules for the given ref.
    """
    if ref == BARK_RULES_REF and project.bootstrap:
        # Validate bark_rules branch
        rules = [get_bark_rules(project).get_bark_rules(project.bootstrap.hash)]
    else:
        bark_rules = verify_bark_rules(project)
        rules = bark_rules.get_ref_rules(ref)

    if not rules:
        raise RuleViolation(f"No rules defined for {ref}")

    _do_verify_ref(
        project=project,
        ref=ref,
        head=head,
        rules=rules,
    )


def verify_all(project: Project):
    """Verify all branches matching branch_rules."""
    bark_rules = verify_bark_rules(project)

    violations = []
    rules = bark_rules.get_ref_rules()
    for ref, head in project.repo.references.items():
        try:
            _do_verify_ref(
                project=project,
                ref=ref,
                head=head,
                rules=[r for r in rules if r.pattern.match(ref)],
            )
        except RuleViolation as e:
            violations.append(e)

    if violations:
        raise RuleViolation("Not all branches were valid", violations)


def verify_ref_update(project: Project, ref: str, head: Commit):
    bark_rules = verify_bark_rules(project)
    _do_verify_ref(
        project=project,
        ref=ref,
        head=head,
        rules=bark_rules.get_ref_rules(ref),
    )


def _do_verify_ref(
    project: Project,
    ref: str,
    head: Commit,
    rules: list[RefRuleData],
) -> None:
    for rule in rules:
        bootstrap = Commit(rule.bootstrap, project.repo)
        cache = project.get_cache(bootstrap)
        validate_commit_rules(cache, head, bootstrap)
        validate_branch_rules(cache, head, ref, rule.rule_data)
