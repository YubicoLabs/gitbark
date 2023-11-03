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

from .git import Commit, BARK_CONFIG
from .project import Cache, Project
from .rule import RuleViolation, CommitRule, AllCommitRule, BranchRule
from .objects import BranchRuleData, BarkRules, RuleData
from typing import Callable, Optional
import yaml

BARK_RULES_BRANCH = "bark_rules"
BARK_RULES = f"{BARK_CONFIG}/bark_rules.yaml"
BARK_REQUIREMENTS = f"{BARK_CONFIG}/requirements.txt"


def get_commit_rule(commit: Commit, project: Project) -> CommitRule:
    rule_data = commit.get_commit_rules()
    return CommitRule.load_rule(rule_data, commit, project.cache, project.repo)


def nearest_valid_ancestors(commit: Commit, cache: Cache) -> set[Commit]:
    """Return the nearest valid ancestors"""
    parents = commit.parents
    valid_ancestors = set()
    for parent in parents:
        if cache.get(parent):
            valid_ancestors.add(parent)
        else:
            valid_ancestors.update(nearest_valid_ancestors(parent, cache))
    return valid_ancestors


def validate_rules(commit: Commit, project: Project) -> None:
    validators = nearest_valid_ancestors(commit, project.cache)
    if not validators:
        raise RuleViolation("No valid ancestors")

    if len(validators) > 1:
        rule: CommitRule = AllCommitRule(
            "all",
            commit,
            project.cache,
            project.repo,
            [get_commit_rule(v, project) for v in validators],
        )
    else:
        rule = get_commit_rule(validators.pop(), project)
    rule.validate(commit)

    # Also ensure that commit has valid rules
    try:
        get_commit_rule(commit, project)
    except Exception as e:
        raise RuleViolation(f"invalid commit rules: {e}")


def validate_commit(
    commit: Commit,
    bootstrap: Commit,
    project: Project,
    on_valid: Callable[[Commit], None],
) -> None:
    cache = project.cache

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
                        validate_rules(c, project)
                        on_valid(c)
                        cache.set(c, True)
                    except RuleViolation as e:
                        violation = e
                        cache.set(c, False)

    if not cache.get(commit):
        # N.B. last commit to be validated was 'commit'
        assert violation is not None
        raise violation


def validate_branch_rules(
    project: Project, head: Commit, branch: str, branch_rule: BranchRuleData
) -> None:
    """Validated HEAD of branch according to branch rules"""
    bark_rules_branch = project.repo.lookup_branch(BARK_RULES_BRANCH)
    validator = Commit(bark_rules_branch.target.raw, project.repo)
    rule_data = RuleData.parse_list(branch_rule.rules)
    rule = BranchRule.load_rule(rule_data, validator, project.cache, project.repo)
    rule.validate(head, branch)


def validate_commit_rules(
    project: Project, head: Commit, bootstrap: Commit, branch: Optional[str] = None
) -> None:
    """Validates commit rules on branch"""
    on_valid: Callable[[Commit], None] = lambda commit: None
    if branch == BARK_RULES_BRANCH:
        # Need to update modules on each validated commit
        def on_valid(commit: Commit) -> None:
            requirements = commit.read_file(BARK_REQUIREMENTS)
            project.install_modules(requirements)

    try:
        validate_commit(head, bootstrap, project, on_valid)
    except RuleViolation as e:
        error_message = f"Validation errors for commit '{head.hash.hex()}'"
        if branch:
            error_message += f" on branch '{branch}'"
        raise RuleViolation(error_message, [e])


def get_bark_rules_commit(project: Project) -> Optional[Commit]:
    """Gets the latest commit on bark_rules."""
    bark_rules_branch = project.repo.lookup_branch(BARK_RULES_BRANCH)
    if not bark_rules_branch:
        return None
    return Commit(bark_rules_branch.target.raw, project.repo)


def get_bark_rules(project: Project, commit: Optional[Commit] = None) -> BarkRules:
    """Returns the latest branch_rules"""

    commit = commit or get_bark_rules_commit(project)
    if not commit:
        return BarkRules([], [])

    try:
        bark_rules_blob = commit.read_file(BARK_RULES)
    except FileNotFoundError:
        return BarkRules([], [])

    bark_rules_object = yaml.safe_load(bark_rules_blob)
    return BarkRules.parse(bark_rules_object)
