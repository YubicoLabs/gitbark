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

from .git import Commit, BARK_CONFIG, is_descendant, BRANCH_REF_PREFIX
from .project import Cache, Project
from .rule import RuleViolation, CommitRule, AllCommitRule, RefRule
from .objects import BarkRules, RuleData
from typing import Callable, Optional
import yaml

BARK_RULES_BRANCH = "bark_rules"
BARK_RULES_REF = f"{BRANCH_REF_PREFIX}{BARK_RULES_BRANCH}"
BARK_RULES = f"{BARK_CONFIG}/bark_rules.yaml"
BARK_REQUIREMENTS = f"{BARK_CONFIG}/requirements.txt"


def _get_commit_rule(commit: Commit, cache: Cache) -> CommitRule:
    rule_data = commit.get_commit_rules()
    return CommitRule.load_rule(rule_data, commit, cache)


def _nearest_valid_ancestors(commit: Commit, cache: Cache) -> set[Commit]:
    """Return the nearest valid ancestors"""
    parents = commit.parents
    valid_ancestors = set()
    for parent in parents:
        if cache.get(parent):
            valid_ancestors.add(parent)
        else:
            valid_ancestors.update(_nearest_valid_ancestors(parent, cache))
    return valid_ancestors


def _validate_rules(commit: Commit, cache: Cache) -> None:
    validators = _nearest_valid_ancestors(commit, cache)
    if not validators:
        raise RuleViolation("No valid ancestors")

    if len(validators) > 1:
        rule: CommitRule = AllCommitRule(
            "all",
            commit,
            cache,
            [_get_commit_rule(v, cache) for v in validators],
        )
    else:
        rule = _get_commit_rule(validators.pop(), cache)
    rule.validate(commit)

    # Also ensure that commit has valid rules
    try:
        _get_commit_rule(commit, cache)
    except Exception as e:
        raise RuleViolation(f"invalid commit rules: {e}")


def _validate_commit(
    commit: Commit,
    bootstrap: Commit,
    cache: Cache,
    on_valid: Callable[[Commit], None],
) -> None:
    if not is_descendant(bootstrap, commit):
        raise RuleViolation(f"Bootstrap '{bootstrap.hash.hex()}' is not an ancestor")

    # Re-validate if previously invalid
    if cache.get(commit) is False:
        cache.remove(commit)

    violation: Optional[RuleViolation] = None
    to_validate = [commit]
    while to_validate:
        c = to_validate.pop()
        if not cache.has(c):
            if c == bootstrap:
                cache.set(c, True)
                on_valid(c)
            else:
                parents = [p for p in c.parents if not cache.has(p)]
                if parents:
                    to_validate.append(c)
                    to_validate.extend(parents)
                else:
                    try:
                        _validate_rules(c, cache)
                        on_valid(c)
                        cache.set(c, True)
                    except RuleViolation as e:
                        violation = e
                        cache.set(c, False)

    if not cache.get(commit):
        # N.B. last commit to be validated was 'commit'
        assert violation is not None
        raise violation


def validate_ref_rules(
    cache: Cache, head: Commit, ref: str, rule_data: RuleData
) -> None:
    """Validated HEAD of ref according to ref rules"""
    validator = head.repo.references[BARK_RULES_REF]
    rule = RefRule.load_rule(rule_data, validator, cache)
    rule.validate(head, ref)


def validate_commit_rules(
    cache: Cache,
    head: Commit,
    bootstrap: Commit,
    on_valid: Callable[[Commit], None] = lambda commit: None,
) -> None:
    """Validates commit rules for a given commit"""
    if head == bootstrap:
        on_valid(bootstrap)
        return

    try:
        _validate_commit(head, bootstrap, cache, on_valid)
    except RuleViolation as e:
        error_message = f"Validation errors for commit '{head}'"
        raise RuleViolation(error_message, [e])


def get_bark_rules_commit(project: Project) -> Optional[Commit]:
    """Gets the latest commit on bark_rules."""
    return project.repo.references.get(BARK_RULES_REF)


def get_bark_rules(project: Project, commit: Optional[Commit] = None) -> BarkRules:
    """Returns the latest bark_rules"""

    commit = commit or get_bark_rules_commit(project)
    if not commit:
        return BarkRules([], [])

    try:
        bark_rules_blob = commit.read_file(BARK_RULES)
    except FileNotFoundError:
        return BarkRules([], [])

    bark_rules_object = yaml.safe_load(bark_rules_blob)
    return BarkRules.parse(bark_rules_object)
