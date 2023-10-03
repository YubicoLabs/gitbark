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

from typing import Generator, Optional
from enum import StrEnum
from pygit2 import Repository
import yaml
import pickle
import pkg_resources
import os
import sqlite3
import contextlib
import random
import string


class CacheEntry:
    def __init__(self, valid: bool, violations: list[str]) -> None:
        self.valid = valid
        self.violations = violations


class Cache:
    def __init__(self, file: str) -> None:
        self.file = file
        try:
            self.cache: dict[str, CacheEntry] = self.load()
        except Exception as e:
            raise e

    def get(self, key: str) -> Optional[CacheEntry]:
        value = self.cache.get(key)
        return value

    def is_empty(self) -> bool:
        return len(self.cache) == 0

    def has(self, key: str):
        return key in self.cache

    def set(self, key: str, value: CacheEntry):
        self.cache[key] = value

    def load(self):
        if os.path.exists(self.file):
            with open(self.file, "rb") as f:
                return pickle.load(f)
        return {}

    def dump(self) -> None:
        with open(self.file, "wb") as f:
            pickle.dump(self.cache, f)


class PROJECT_FILES(StrEnum):
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
            cmd("virtualenv", self.env_path, cwd=self.path)

        if not os.path.exists(self.db_path):
            self.create_db()

        self.cache = self.get_cache()
        self.bootstrap = self.get_bootstrap()
        self.repo = Repository(self.path)

    @contextlib.contextmanager
    def connect_db(
        self, db_path: str | None = None
    ) -> Generator[sqlite3.Connection, None, None]:
        db_path = db_path or self.db_path

        with contextlib.closing(sqlite3.connect(db_path)) as db:
            with db:
                yield db

    def create_db(self) -> None:
        with self.connect_db(self.db_path) as db:
            db.executescript(
                """
                CREATE TABLE bark_modules (
                    repo TEXT NOT NULL,
                    path TEXT NOT NULL,
                    PRIMARY KEY (repo)
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
        with self.connect_db() as db:
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
        cmd(pip_path, "install", f"git+file:///{bark_module_path}@{bark_module.rev}")

    def load_rule_entrypoints(self, bark_rules: BarkRules) -> None:
        entrypoints = {}

        # Add bark_core rules
        for rule in get_bark_core_rules():
            id, entrypoint = rule["id"], rule["entrypoint"]
            entrypoints[id] = entrypoint

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

        # Add bark_core subcommands
        for subcommand in get_bark_core_subcommands():
            entrypoints.append(subcommand["entrypoint"])

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
        with self.connect_db() as db:
            bark_module_path = db.execute(
                "SELECT path FROM bark_modules WHERE repo = ?", [bark_module.repo]
            ).fetchone()
            return bark_module_path

    def get_cache(self) -> Cache:
        cache_file = os.path.join(self.bark_directory, PROJECT_FILES.CACHE)
        return Cache(cache_file)

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

    def save_cache(self) -> None:
        self.cache.dump()

    def update(self) -> None:
        self.save_bootstrap()
        self.save_cache()


def _get_bark_core_config():
    bark_module = pkg_resources.resource_string(__name__, "bark_core/bark_module.yaml")
    return yaml.safe_load(bark_module)


def get_bark_core_rules():
    return _get_bark_core_config()["rules"]


def get_bark_core_subcommands():
    return _get_bark_core_config()["subcommands"]
