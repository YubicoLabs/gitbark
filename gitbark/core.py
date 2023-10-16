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
from .rule import get_rule, RuleViolation, AllRule
from .util import cmd
from .objects import BranchRule, BarkRules
from functools import partial
from typing import Callable, Optional
import yaml

BARK_RULES_BRANCH = "bark_rules"
BARK_RULES = f"{BARK_CONFIG}/bark_rules.yaml"


def nearest_valid_ancestors(commit: Commit, cache: Cache) -> set[Commit]:
    """Return the nearest valid ancestors"""
    parents = commit.parents
    valid_ancestors = set()
    for parent in parents:
        if cache.get(parent.hash):
            valid_ancestors.add(parent)
        else:
            valid_ancestors.update(nearest_valid_ancestors(parent, cache))
    return valid_ancestors


def validate_rules(commit: Commit, project: Project) -> None:
    validators = nearest_valid_ancestors(commit, project.cache)
    if not validators:
        raise RuleViolation("No valid ancestors")

    if len(validators) > 1:
        rule = AllRule.of(
            "all",
            commit,
            project.cache,
            project.repo,
            *[get_rule(v, project) for v in validators],
        )
    else:
        rule = get_rule(validators.pop(), project)
    rule.validate(commit)

    # Also ensure that commit has valid rules
    try:
        get_rule(commit, project)
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
    if cache.get(commit.hash) is False:
        cache.remove(commit.hash)

    violation: Optional[RuleViolation] = None
    to_validate = [commit]
    while to_validate:
        c = to_validate.pop()
        if not cache.has(c.hash):
            if c == bootstrap:
                cache.set(c.hash, True)
                on_valid(c)
            else:
                parents = [p for p in c.parents if not cache.has(p.hash)]
                if parents:
                    to_validate.append(c)
                    to_validate.extend(parents)
                else:
                    try:
                        validate_rules(c, project)
                        on_valid(c)
                        cache.set(c.hash, True)
                    except RuleViolation as e:
                        violation = e
                        cache.set(c.hash, False)

    if not cache.get(commit.hash):
        # N.B. last commit to be validated was 'commit'
        assert violation is not None
        raise violation


def update_modules(project: Project, branch: str, commit: Commit) -> None:
    bark_modules = get_bark_rules(project, commit).modules
    prev_bark_modules = [
        set(get_bark_rules(project, p).modules) for p in commit.parents
    ]

    for module in bark_modules:
        if not prev_bark_modules or any(module not in p for p in prev_bark_modules):
            project.install_bark_module(module)


def validate_commit_rules(
    project: Project, head: Commit, bootstrap: Commit, branch: Optional[str] = None
) -> None:
    """Validates commit rules on branch"""
    on_valid: Callable[[Commit], None] = lambda commit: None
    if branch == BARK_RULES_BRANCH:
        # Need to update modules on each validated commit
        on_valid = partial(update_modules, project, branch)

    validate_commit(head, bootstrap, project, on_valid)


def get_bark_rules(project: Project, commit: Optional[Commit] = None) -> BarkRules:
    """Returns the latest branch_rules"""

    if not commit:
        bark_rules_branch = project.repo.lookup_branch(BARK_RULES_BRANCH)
        if not bark_rules_branch:
            return BarkRules([], [])

        commit = Commit(bark_rules_branch.target, project.repo)

    try:
        bark_rules_blob = commit.read_file(BARK_RULES)
    except FileNotFoundError:
        return BarkRules([], [])

    bark_rules_object = yaml.safe_load(bark_rules_blob)
    return BarkRules.parse(bark_rules_object)


def is_descendant(prev: Commit, new: Commit) -> bool:
    """Checks that the current tip is a descendant of the old tip"""

    _, exit_status = cmd(
        "git", "merge-base", "--is-ancestor", prev.hash, new.hash, check=False
    )

    if exit_status == 0:
        return True
    else:
        return False


def validate_branch_rules(
    project: Project, head: Commit, branch: str, branch_rule: BranchRule
) -> None:
    # Validate branch_rules
    # TODO: make this part more modular
    if branch_rule.ff_only:
        prev_head_hash = project.repo.branches[branch].target
        prev_head = Commit(prev_head_hash, project.repo)
        if not is_descendant(prev_head, head):
            raise RuleViolation(f"Commit is not a descendant of {prev_head.hash}")
