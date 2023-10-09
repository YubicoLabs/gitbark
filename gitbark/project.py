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

from .util import cmd
from .objects import BarkModule, BarkRules

from dataclasses import dataclass
from typing import Generator, Optional, Any
from enum import Enum
from pygit2 import Repository
import yaml
import os
import sqlite3
import contextlib
import random
import string
import sys
import json


@contextlib.contextmanager
def connect_db(db_path: str) -> Generator[sqlite3.Connection, None, None]:
    db_path = db_path
    with contextlib.closing(sqlite3.connect(db_path)) as db:
        with db:
            yield db


@dataclass
class CacheEntry:
    valid: bool
    violations: list[str]

    @classmethod
    def parse_from_db(cls, entry: Any) -> "CacheEntry":
        valid = bool(entry[0])
        violations = json.loads(entry[1])
        return cls(valid=valid, violations=violations)


class Cache:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.cache: dict[str, CacheEntry] = {}

    def get(self, key: str) -> Optional[CacheEntry]:
        if self.has(key):
            return self.cache.get(key)
        else:
            entry = self.get_from_db(key)
            if entry:
                self.set(key, entry.valid, entry.violations)
            return entry

    def get_from_db(self, key: str) -> Optional[CacheEntry]:
        with connect_db(self.db_path) as db:
            entry = db.execute(
                "SELECT valid, violations FROM cache_entries WHERE commit_hash = ? ",
                [key],
            ).fetchone()
            if entry:
                return CacheEntry.parse_from_db(entry)
            return None

    def save_to_db(self, key: str, entry: CacheEntry) -> None:
        with connect_db(self.db_path) as db:
            valid = int(entry.valid)
            violations = json.dumps(entry.violations)
            db.execute(
                "INSERT INTO cache_entries (commit_hash, valid, violations) "
                "VALUES (?, ?, ?)",
                [key, valid, violations],
            )

    def is_empty(self) -> bool:
        return len(self.cache) == 0

    def has(self, key: str):
        return key in self.cache

    def set(self, key: str, valid: bool, violations: list[str]):
        self.cache[key] = CacheEntry(valid, violations)

    def dump(self) -> None:
        for key, entry in self.cache.items():
            self.save_to_db(key, entry)


class PROJECT_FILES(str, Enum):
    CACHE = "cache.pickle"
    BOOTSTRAP = "bootstrap"
    DB = "db.db"


BARK_DIRECTORY = "bark"
ENV_DIRECTORY = "env"
BARK_MODULES_DIRECTORY = "bark_modules"


class Project:
    def __init__(self, path: str) -> None:
        self.path = path
        self.bark_directory = os.path.join(self.path, ".git", BARK_DIRECTORY)
        self.env_path = os.path.join(self.bark_directory, ENV_DIRECTORY)
        self.db_path = os.path.join(self.bark_directory, PROJECT_FILES.DB)

        if not os.path.exists(self.bark_directory):
            os.makedirs(self.bark_directory, exist_ok=True)

        if not os.path.exists(self.env_path):
            os.makedirs(self.env_path, exist_ok=True)
            cmd(sys.executable, "-m", "venv", self.env_path, cwd=self.path)

        sys.path.append(self.get_env_site_packages())

        if not os.path.exists(self.db_path):
            self.create_db()

        self.cache = Cache(self.db_path)
        self.bootstrap = self.get_bootstrap()
        self.repo = Repository(self.path)

    def create_db(self) -> None:
        with connect_db(self.db_path) as db:
            db.executescript(
                """
                CREATE TABLE bark_modules (
                    repo TEXT NOT NULL,
                    path TEXT NOT NULL,
                    PRIMARY KEY (repo)
                );
                CREATE TABLE cache_entries (
                    commit_hash TEXT NOT NULL,
                    valid INTEGER NOT NULL,
                    violations TEXT NOT NULL,
                    PRIMARY KEY (commit_hash) ON CONFLICT IGNORE
                );
                """
            )

    def db_module_name(self) -> str:
        random_string = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=8)
        )
        return f"module_{random_string}"

    def create_bark_module(self, bark_module: BarkModule) -> None:
        module_name = self.db_module_name()

        modules_directory = os.path.join(self.bark_directory, BARK_MODULES_DIRECTORY)
        if not os.path.exists(modules_directory):
            os.makedirs(modules_directory)

        modules_path = os.path.join(modules_directory, module_name)
        os.makedirs(modules_path)

        cmd("git", "clone", bark_module.repo, modules_path)
        with connect_db(self.db_path) as db:
            db.execute(
                "INSERT INTO bark_modules (repo, path) VALUES (?, ?)",
                [bark_module.repo, modules_path],
            )

    def install_bark_module(self, bark_module: BarkModule) -> None:
        bark_module_path = self.get_bark_module_path(bark_module)
        if not bark_module_path:
            self.create_bark_module(bark_module)
            bark_module_path = self.get_bark_module_path(bark_module)

        pip_path = os.path.join(self.env_path, "bin", "pip")
        cmd(pip_path, "install", f"git+file://{bark_module_path}@{bark_module.rev}")

    def get_env_site_packages(self) -> str:
        exec_path = os.path.join(self.env_path, "bin", "python")
        return cmd(
            exec_path,
            "-c",
            "from distutils.sysconfig import get_python_lib; print(get_python_lib())",
        )[0]

    def load_rule_entrypoints(self, bark_rules: BarkRules) -> None:
        entrypoints = {}

        for module in bark_rules.modules:
            bark_module = self.get_bark_module_config(module)
            rules = []
            if "rules" in bark_module:
                rules = bark_module["rules"]
            for rule in rules:
                id, entrypoint = rule["id"], rule["entrypoint"]
                entrypoints[id] = entrypoint

        self.rule_entrypoints = entrypoints

    def get_subcommand_entrypoints(self, bark_rules: BarkRules) -> list[str]:
        entrypoints = []

        for module in bark_rules.modules:
            bark_module = self.get_bark_module_config(module)
            subcommands = []
            if "subcommands" in bark_module:
                subcommands = bark_module["subcommands"]
            for subcommand in subcommands:
                entrypoints.append(subcommand["entrypoint"])
        return entrypoints

    def get_bark_module_config(self, bark_module: BarkModule):
        repo_path = self.get_bark_module_path(bark_module)
        bark_module, _ = cmd(
            "git",
            "cat-file",
            "-p",
            f"{bark_module.rev}:bark_module.yaml",
            cwd=repo_path,
        )
        return yaml.safe_load(bark_module)

    def get_bark_module_path(self, bark_module: BarkModule) -> str:
        with connect_db(self.db_path) as db:
            res = db.execute(
                "SELECT path FROM bark_modules WHERE repo = ?", [bark_module.repo]
            ).fetchone()
            if res:
                return res[0]
            return res

    def get_bootstrap(self) -> str:
        bootstrap_file = os.path.join(self.bark_directory, PROJECT_FILES.BOOTSTRAP)
        if os.path.exists(bootstrap_file):
            with open(bootstrap_file, "r") as f:
                return f.read()
        return ""

    def save_bootstrap(self) -> None:
        bootstrap_file = os.path.join(self.bark_directory, PROJECT_FILES.BOOTSTRAP)
        with open(bootstrap_file, "w") as f:
            f.write(self.bootstrap)

    def update(self) -> None:
        self.save_bootstrap()
        self.cache.dump()
