# Copyright 2023 Yubico AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from gitbark.git.commit import Commit
from gitbark.git.reference_update import ReferenceUpdate
from gitbark.git.git import Git
from gitbark.cache import Cache, CacheEntry
from pygit2 import Oid

import re
import yaml


def validate_branch_rules(ref_update:ReferenceUpdate, branch_name, branch_rule, cache:Cache):
    """Validates branch rules with respect to ReferenceUpdate
    
    Note: If no reference update, there is no need to evaluate branch_rules 
    """

    exact_branch_name = branch_name.split("/")
    exact_branch_name = exact_branch_name[-1]

    violations = []

    if not ref_update:
        git = Git()

        current_head = git.repo.revparse_single(branch_name)
        current_head = current_head.id.__str__()

        if cache.has(current_head):
            value = cache.get(current_head)
            if not value.valid and value.ref_update and value.branch_name == branch_name:
                return False, value.violations 
        # Not evaluating branch rules if no ref_update
        return True, violations

    if not re.search(f"refs/.*/{exact_branch_name}", ref_update.ref_name, re.M):
        # Not evaluating branch rules if branch_name does not match the ref being updated
        return True, violations
    
    if not branch_rule:
        branch_rule = get_default_branch_rule()

    # Checks if allow_force_push is included as a rule in branch_rules
    # TODO: allow_force_push should be renamed to fast-forward-only
    if "allow_force_push" in branch_rule:
        passes_force_push = validate_force_push(ref_update, branch_rule["allow_force_push"])
        if not passes_force_push:
            # print(ref_update.new_ref, " is not a descendant to ", ref_update.old_ref)
            violation = "Commit is not fast-forward"
            violations.append(violation)
            cache.set(ref_update.new_ref, CacheEntry(False, violations, ref_update=True, branch_name = branch_name))
            return False, violations

    return True, violations



def get_default_branch_rule():
    branch_rule = {
        "allow_force_push": False
    }
    return branch_rule

def validate_force_push(ref_update:ReferenceUpdate, allow_force_push):
    if ref_update.old_ref == "0"*40:
        return True
    if not allow_force_push:
        current = Commit(ref_update.new_ref)
        old = Commit(ref_update.old_ref)
        return is_descendant(current, old)
    return True

def is_descendant(current: Commit, old: Commit):
    """Checks that the current tip is a descendant of the old tip"""
    git = Git()

    _, exit_status = git.cmd("git", "merge-base", "--is-ancestor", old.hash, current.hash)

    if exit_status == 0:
        return True
    else:
        return False

def get_branch_rules():
    """Returns the latest branch_rules"""
    
    git = Git()
    branch_rules_head = git.repo.revparse_single("branch_rules").id.__str__()
    branch_rules_commit = Commit(branch_rules_head)

    branch_rules = branch_rules_commit.get_blob_object(".gitbark/branch_rules.yaml")
    branch_rules = yaml.safe_load(branch_rules)
    branch_rules = branch_rules["branches"]

    # Find matching branches
    for rule in branch_rules:
        pattern = rule["pattern"]
        regex_pattern = re.compile(f".*{pattern}")
        all_branches = list(git.repo.references)
        matching_branches = [branch for branch in all_branches if regex_pattern.match(branch)]
        rule["branches"] = matching_branches
    return branch_rules

