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

BARK_RULES_BRANCH = "refs/heads/bark_rules"


def nearest_valid_ancestors(
    commit: Commit, cache: Cache, valid_ancestors=[]
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
    if branch == BARK_RULES_BRANCH:
        project.load_rule_entrypoints()

    rules = get_rules(validator, project)
    passes_rules = True
    for rule in rules:
        if not rule.validate(commit):
            commit.add_rule_violation(rule.get_violation())
            passes_rules = False

    return passes_rules


def get_children_map(commit: Commit):
    queue = [commit]
    children: dict[str, list[Commit]] = {}
    processed = set()
    while len(queue) > 0:
        current = queue.pop(0)
        if current.hash not in processed:
            processed.add(current.hash)
            parents = current.parents
            for parent in parents:
                if parent.hash in children:
                    children[parent.hash].append(current)
                    queue.append(parent)
                else:
                    children[parent.hash] = [current]
                    queue.append(parent)
    return children


def is_commit_valid(
    commit: Commit, bootstrap: Commit, branch: str, project: Project
) -> bool:
    cache = project.cache

    value = cache.get(commit.hash)
    if value:
        commit.violations = value.violations
        return value.valid

    if commit == bootstrap:
        cache.set(commit.hash, True, commit.violations)
        update_modules(commit, branch, project)
        return True

    validators = set()
    for parent in commit.parents:
        if is_commit_valid(parent, bootstrap, branch, project):
            validators.add(parent)
        else:
            for validator in nearest_valid_ancestors(parent, project.cache):
                validators.add(validator)

    if not all(
        validate_rules(commit, validator, project, branch) for validator in validators
    ):
        cache.set(commit.hash, False, commit.violations)
        return False
    else:
        cache.set(commit.hash, True, commit.violations)
        update_modules(commit, branch, project)
        return True


def is_commit_valid_iterative(
    commit: Commit, bootstrap: Commit, branch: str, project: Project
) -> bool:
    cache = project.cache

    value = cache.get(commit.hash)
    if value:
        commit.violations = value.violations
        return value.valid

    if commit == bootstrap:
        cache.set(commit.hash, True, commit.violations)
        update_modules(commit, branch, project)
        return True

    commit_to_children = get_children_map(commit)

    cache.set(bootstrap.hash, True, commit.violations)
    queue = [bootstrap]

    processed = set()
    validated = set()
    while len(queue) > 0:
        current = queue.pop(0)
        if current.hash not in processed:
            processed.add(current.hash)
            children = []
            if current.hash in commit_to_children:
                children = commit_to_children[current.hash]

            for child in reversed(children):
                if child.hash in validated:
                    continue
                parents = child.parents
                validators = []
                visited_validators = set()
                for parent in parents:
                    value = cache.get(parent.hash)
                    if value:
                        if value.valid:
                            validators.append(parent)
                            visited_validators.add(parent.hash)
                        else:
                            nearest_validators = nearest_valid_ancestors(
                                parent, project.cache
                            )
                            for validator in nearest_validators:
                                if validator.hash not in visited_validators:
                                    validators.append(validator)
                                    visited_validators.add(validator.hash)

                if not all(
                    validate_rules(child, validator, project, branch)
                    for validator in validators
                ):
                    cache.set(child.hash, False, child.violations)
                else:
                    cache.set(child.hash, True, child.violations)
                    update_modules(commit, branch, project)
                validated.add(child.hash)
                queue.append(child)

    value = cache.get(commit.hash)
    return False if not value else value.valid


def update_modules(commit: Commit, branch: str, project: Project):
    if branch != BARK_RULES_BRANCH:
        return

    bark_modules = commit.get_bark_rules().modules
    prev_bark_modules = [p.get_bark_rules().modules for p in commit.parents]

    update_required = False

    for modules in prev_bark_modules:
        if len(modules) != prev_bark_modules:
            update_required = True
        else:
            modules.sort(key=lambda x: x.repo)
            bark_modules.sort(key=lambda x: x.repo)
            if not all(x is y for x, y in zip(bark_modules, modules)):
                update_required = True

    if update_required or len(prev_bark_modules) == 0:
        for module in bark_modules:
            project.install_bark_module(module)


def validate_commit_rules(
    project: Project, head: Commit, bootstrap: Commit, branch: str
) -> bool:
    """Validates commit rules on branch"""
    count, _ = cmd("git", "rev-list", "--count", head.hash)
    count = int(count)
    if count > 999 and project.cache.is_empty():
        return is_commit_valid_iterative(head, bootstrap, branch, project)
    else:
        return is_commit_valid(head, bootstrap, branch, project)


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
