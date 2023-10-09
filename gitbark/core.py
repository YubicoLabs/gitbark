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

from .git import Commit
from .project import Cache, Project
from .rule import get_rules
from .util import cmd
from .objects import BranchRule, BarkRules
from functools import partial
from typing import Callable

BARK_RULES_BRANCH = "refs/heads/bark_rules"


def nearest_valid_ancestors(
    commit: Commit, cache: Cache, valid_ancestors: list[Commit]
) -> list[Commit]:
    """Return the nearest valid ancestors"""
    parents = commit.parents
    for parent in parents:
        value = cache.get(parent.hash)
        if value and value.valid:
            valid_ancestors.append(parent)
        else:
            _valid_ancestors = nearest_valid_ancestors(parent, cache, valid_ancestors)
            valid_ancestors.extend(_valid_ancestors)
    return valid_ancestors


def validate_rules(
    commit: Commit,
    validator: Commit,
    project: Project,
    branch: str,
):
    rules = get_rules(validator, project)
    passes_rules = True
    for rule in rules:
        if not rule.validate(commit):
            commit.add_rule_violation(rule.get_violation())
            passes_rules = False

    return passes_rules


def is_commit_valid(
    commit: Commit, bootstrap: Commit, branch: str, project: Project, on_valid
) -> bool:
    cache = project.cache
    to_validate = [commit]
    while to_validate:
        c = to_validate.pop(0)
        if not cache.has(c.hash):
            if c == bootstrap:
                cache.set(c.hash, True, [])
                on_valid(c)
            else:
                parents = [p for p in c.parents if not cache.has(p.hash)]
                if parents:
                    to_validate.extend(parents)
                    to_validate.append(c)
                else:
                    validators = nearest_valid_ancestors(c, cache, [])
                    valid = all(
                        validate_rules(c, v, project, branch) for v in validators
                    )
                    if valid:
                        on_valid(c)
                    cache.set(c.hash, valid, c.violations)

    entry = cache.get(commit.hash)
    assert entry is not None
    return entry.valid


def update_modules(project: Project, branch: str, commit: Commit):
    bark_modules = commit.get_bark_rules().modules
    prev_bark_modules = [set(p.get_bark_rules().modules) for p in commit.parents]

    for module in bark_modules:
        if not prev_bark_modules or any(module not in p for p in prev_bark_modules):
            project.install_bark_module(module)


def validate_commit_rules(
    project: Project, head: Commit, bootstrap: Commit, branch: str
) -> bool:
    """Validates commit rules on branch"""
    on_valid: Callable[[Commit], None] = lambda commit: None
    if branch == BARK_RULES_BRANCH:
        # Need to update modules on each validated commit
        on_valid = partial(update_modules, project, branch)

    return is_commit_valid(head, bootstrap, branch, project, on_valid)


def get_bark_rules(project: Project) -> BarkRules:
    """Returns the latest branch_rules"""

    branch_rules_head = Commit(project.repo.references[BARK_RULES_BRANCH].target)

    return branch_rules_head.get_bark_rules()


def is_descendant(prev: Commit, new: Commit):
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
) -> bool:
    # Validate branch_rules
    # TODO: make this part more modular
    passes_rules = True
    if branch_rule.ff_only:
        prev_head_hash = project.repo.references[branch].target
        prev_head = Commit(prev_head_hash)
        if not is_descendant(prev_head, head):
            head.add_rule_violation(f"Commit is not a descendant of {prev_head.hash}")
            passes_rules = False

    return passes_rules
