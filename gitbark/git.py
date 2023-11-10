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

from .objects import RuleData
from .util import cmd, branch_name

from dataclasses import dataclass
from pygit2 import Commit as _Commit, Tree, Repository as _Repository
from typing import Union, Tuple, Optional
import yaml
import re

BARK_CONFIG = ".bark"
COMMIT_RULES = f"{BARK_CONFIG}/commit_rules.yaml"


def _glob_match_single(pattern: str, name: str) -> bool:
    pattern = re.escape(pattern).replace("\\*", ".*")
    return bool(re.match(f"^{pattern}$", name))


def _glob_files(tree: Tree, patterns: list[list[str]], prefix="") -> set[str]:
    matches = set()
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
                matches.update(
                    _glob_files(child, matching_patterns, f"{prefix}{name}/")
                )
        else:
            if [] in matching_patterns:
                matches.add(prefix + name)
            else:  # Also allow skipping **
                for m in matching_patterns:
                    while m[0] == "**":
                        m = m[1:]
                    if len(m) == 1 and _glob_match_single(m[0], name):
                        matches.add(prefix + name)
                        break
    return matches


class Commit:
    """Git commit class

    This class serves as a wrapper for a Git commit object
    """

    def __init__(self, hash: bytes, repo: "Repository") -> None:
        """Init Commit with commit hash"""
        self.repo = repo
        if not isinstance(hash, bytes):
            raise ValueError(f"Commit hash is not bytes {hash}")
        self._object: _Commit = repo._object.get(hash.hex())

    @property
    def hash(self) -> bytes:
        return self._object.id.raw

    @property
    def tree_hash(self) -> bytes:
        return self._object.tree_id.raw

    @property
    def author(self) -> tuple[str, str]:
        """A tuple with the author name and email."""
        return self._object.author.name, self._object.author.email

    @property
    def parents(self) -> list["Commit"]:
        """The list of parent commits."""
        return [Commit(oid.raw, self.repo) for oid in self._object.parent_ids]

    @property
    def signature(self) -> tuple[bytes, bytes]:
        """A tuple with the signature and subject."""
        return self._object.gpg_signature

    @property
    def message(self) -> str:
        """The commit message."""
        return self._object.message

    @property
    def object(self) -> bytes:
        """The raw commit object."""
        return self._object.read_raw()

    def __eq__(self, other) -> bool:
        return other and self.hash == other.hash

    def __hash__(self) -> int:
        return int.from_bytes(self.hash, "big")

    def list_files(self, pattern: Union[list[str], str], root: str = "") -> set[str]:
        """List files matching a glob pattern in the commit."""
        tree = self.repo._object.revparse_single(f"{self.hash.hex()}:{root}")
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
        try:
            return self.repo._object.revparse_single(
                f"{self.hash.hex()}:{filename}"
            ).data
        except KeyError:
            raise FileNotFoundError(f"'{filename}' does not exist in commit")

    def get_files_modified(self, other: "Commit") -> set[str]:
        """Get a list of files modified between two commits."""
        diff = self.repo._object.diff(self.hash.hex(), other.hash.hex())
        modified: set[str] = set()
        for delta in diff.deltas:
            modified.update((delta.new_file.path, delta.old_file.path))
        return modified

    def get_commit_rules(self) -> RuleData:
        """Get the commit rules associated with a commit."""
        try:
            commit_rules_blob = self.read_file(COMMIT_RULES)
            rules_data = yaml.safe_load(commit_rules_blob)["rules"] or []
        except FileNotFoundError:
            rules_data = []
        return RuleData.parse_list(rules_data)


class Repository:
    """Git repo wrapper class"""

    def __init__(self, path: str) -> None:
        self._path = path
        self._object = _Repository(path)

    @property
    def head(self) -> Commit:
        return Commit(self._object.head.target.raw, self)

    @property
    def current_ref(self) -> str:
        return self._object.references["HEAD"].target

    @property
    def references(self) -> dict[str, Commit]:
        return {
            ref.name: Commit(ref.target.raw, self)
            for ref in self._object.references.iterator()
        }

    def branch_exists(self, branch: str) -> bool:
        return branch in self._object.branches

    def resolve(self, name: str) -> Tuple[Commit, Optional[str]]:
        commit, ref = self._object.resolve_refish(name)
        return Commit(commit.id.raw, self), (ref.name if ref else None)

    def checkout(self, branch: str, orhpan: bool = False) -> None:
        if branch_name(self.current_ref) == branch:
            return
        if not self.branch_exists(branch):
            if orhpan:
                cmd("git", "checkout", "--orphan", branch, cwd=self._path)
                cmd("git", "reset", "--hard", cwd=self._path)
            else:
                cmd("git", "checkout", "-b", branch, cwd=self._path)
        else:
            cmd("git", "checkout", branch, cwd=self._path)

    def commit(self, message: str = "Default msg", *options: str) -> None:
        cmd("git", "commit", "-m", message, *options, cwd=self._path)


@dataclass
class ReferenceUpdate:
    """Git reference update class

    This class serves as a wrapper for a Git reference-update
    """

    old_ref: str
    new_ref: str
    ref_name: str
