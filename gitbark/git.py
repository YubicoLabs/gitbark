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

from .objects import CommitRuleData, BarkRules
from gitbark import globals

from dataclasses import dataclass
from pygit2 import Commit as _Commit, Tree
from typing import Union
import yaml
import re


def _glob_match_single(pattern: str, name: str) -> bool:
    pattern = re.escape(pattern).replace("\\*", ".*")
    return bool(re.match(f"^{pattern}$", name))


def _glob_files(tree: Tree, patterns: list[list[str]], prefix="") -> list[str]:
    matches = []
    for child in tree:
        name = child.name
        matching_patterns = []
        for p in patterns:
            if _glob_match_single(p[0], name):
                if p[0] == "**":
                    matching_patterns.append(p)
                matching_patterns.append(p[1:])
        if isinstance(child, Tree):
            if matching_patterns:
                matching_patterns = [p for p in matching_patterns if p]
                matches.extend(
                    _glob_files(child, matching_patterns, f"{prefix}{name}/")
                )
        else:
            if [] in matching_patterns:
                matches.append(prefix + name)
            else:  # Also allow skipping **/
                for m in matching_patterns:
                    while m[0] == "**":
                        m = m[1:]
                    if len(m) == 1 and _glob_match_single(m[0], name):
                        matches.append(prefix + name)
                        break
    return matches


class Commit:
    """Git commit class

    This class serves as a wrapper for a Git commit object
    """

    def __init__(self, hash: str) -> None:
        """Init Commit with commit hash"""
        self.__repo = globals.repo
        self.__object: _Commit = self.__repo.get(hash)
        self.hash = str(hash)

    @property
    def author(self) -> tuple[str, str]:
        """A tuple with the author name and email."""
        return self.__object.author.name, self.__object.author.email

    @property
    def parents(self) -> list["Commit"]:
        """The list of parent commits."""
        return [Commit(hash) for hash in self.__object.parent_ids]

    @property
    def signature(self) -> tuple[bytes, bytes]:
        """A tuple with the signature and subject."""
        return self.__object.gpg_signature

    @property
    def message(self) -> str:
        """The commit message."""
        return self.__object.message

    @property
    def object(self) -> bytes:
        """The raw commit object."""
        return self.__object.read_raw()

    def __eq__(self, other) -> bool:
        return self.hash == other.hash

    def __hash__(self) -> int:
        return int(self.hash, base=16)

    def list_files(self, pattern: Union[list[str], str], root: str = "") -> list[str]:
        tree = self.__repo.revparse_single(f"{self.hash}:{root}")
        if not isinstance(tree, Tree):
            raise ValueError(f"'{root}' does not point to a tree")

        if isinstance(pattern, list):
            patterns = pattern
        else:
            patterns = [pattern]
        if root and not root.endswith("/"):
            root = root + "/"
        split_patterns = [p.split("/") for p in patterns]
        return _glob_files(tree, split_patterns, root)

    def read_file(self, filename: str) -> bytes:
        """Read the file content of a file in the commit."""
        return self.__repo.revparse_single(f"{self.hash}:{filename}").data

    def get_commit_rules(self) -> CommitRuleData:
        """Get the commit rules associated with a commit."""
        commit_rules_blob = self.read_file(".gitbark/commit_rules.yaml")
        rules = yaml.safe_load(commit_rules_blob)["rules"]
        if len(rules) > 1:
            rules = {"all": rules}
        elif len(rules) == 1:
            rules = rules[0]
        else:
            rules = {"none": None}
        return CommitRuleData.parse(rules)

    def get_bark_rules(self) -> BarkRules:
        """Get the bark rule associated with a commit."""
        bark_rules_blob = self.read_file(".gitbark/bark_rules.yaml")
        bark_rules_object = yaml.safe_load(bark_rules_blob)
        return BarkRules.parse(bark_rules_object)


@dataclass
class ReferenceUpdate:
    """Git reference update class

    This class serves as a wrapper for a Git reference-update
    """

    old_ref: str
    new_ref: str
    ref_name: str
