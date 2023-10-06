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

from .objects import CommitRulesData, BarkRules
from gitbark import globals

from dataclasses import dataclass
from pygit2 import Commit as _Commit
import yaml


class Commit:
    """Git commit class

    This class serves as a wrapper for a Git commit object
    """

    def __init__(self, hash: str) -> None:
        """Init Commit with commit hash"""
        self.__repo = globals.repo
        self.hash = str(hash)
        self.__object: _Commit = self.__repo.get(hash)
        self.violations: list[str] = []

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

    def add_rule_violation(self, violation: str) -> None:
        self.violations.append(violation)

    def get_commit_rules(self) -> CommitRulesData:
        """Get the commit rules associated with a commit."""
        commit_rules_blob = self.__repo.revparse_single(
            f"{self.hash}:.gitbark/commit_rules.yaml"
        ).data
        commit_rules = yaml.safe_load(commit_rules_blob)
        return CommitRulesData.parse(commit_rules)

    def get_bark_rules(self) -> BarkRules:
        """Get the bark rule associated with a commit."""
        bark_rules_blob = self.__repo.revparse_single(
            f"{self.hash}:.gitbark/bark_rules.yaml"
        ).data
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
