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
from .objects import BarkModule

from typing import Generator, Optional
from pygit2 import Repository
import platform
import yaml
import sys
import pickle
import pkg_resources
import os
import sqlite3
import contextlib
import random
import string


class Project:
    def __init__(
        self, project_path: str, env_path: str, cache: bytes, root_commit: str
    ) -> None:
        self.project_path = project_path
        self.env = Env(env_path)
        self.cache = Cache(cache)
        self.repo = Repository(project_path)
        self.root_commit = root_commit

    def set_root_commit(self, root_commit: str) -> None:
        self.root_commit = root_commit


class Store:
    def __init__(self, directory: str | None = None) -> None:
        self.directory = directory or self.get_cache_directory()
        self.db_path = os.path.join(self.directory, "db.db")

        if not os.path.exists(self.directory):
            os.makedirs(self.directory, exist_ok=True)

        if os.path.exists(self.db_path):
            return

        with self.connect(self.db_path) as db:
            db.executescript(
                """
                CREATE TABLE modules (
                    repo TEXT NOT NULL,
                    path TEXT NOT NULL,
                    PRIMARY KEY (repo)
                );
                CREATE TABLE projects (
                    project_path TEXT NOT NULL,
                    env_path TEXT NOT NULL,
                    cache BLOB,
                    root_commit TEXT NOT NULL,
                    PRIMARY KEY (project_path)
                );
                CREATE TABLE rules (
                    id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    entrypoint TEXT NOT NULL,
                    env_path TEXT NOT NULL,
                    PRIMARY KEY (id, env_path)
                );
                CREATE TABLE subcommands (
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    entrypoint TEXT NOT NULL,
                    env_path TEXT NOT NULL,
                    PRIMARY KEY (name, env_path)
                );           
            """
            )

    @classmethod
    def get_cache_directory(cls) -> str:
        cache_folder = os.path.join(os.path.expanduser("~/.cache"), "gitbark")
        return os.path.realpath(cache_folder)

    @contextlib.contextmanager
    def connect(
        self, db_path: str | None = None
    ) -> Generator[sqlite3.Connection, None, None]:
        db_path = db_path or self.db_path

        with contextlib.closing(sqlite3.connect(db_path)) as db:
            with db:
                yield db

    def db_module_name(self) -> str:
        random_string = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=8)
        )
        return f"module_{random_string}"

    def create_module(self, repo: str) -> tuple[str, str]:
        module_name = self.db_module_name()

        path = os.path.join(self.directory, module_name)
        os.makedirs(path)

        cmd("git", "clone", repo, path)

        with self.connect() as db:
            db.execute("INSERT INTO modules (repo, path) VALUES (?, ?)", [repo, path])

        return self.get_module(repo)

    def get_module(self, repo: str) -> tuple[str, str]:
        with self.connect() as db:
            return db.execute("SELECT * FROM modules WHERE repo = ?", (repo)).fetchone()

    @classmethod
    def db_project_name(cls) -> str:
        random_string = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=8)
        )
        return f"project_{random_string}"

    def create_project(
        self, project_path: str, cache: bytes = b"", root_commit: str = ""
    ) -> "Project":
        project_name = self.db_project_name()

        env_path = os.path.join(self.directory, project_name)
        os.makedirs(env_path)

        cmd("virtualenv", env_path, cwd=self.directory)

        with self.connect() as db:
            db.execute(
                "INSERT INTO projects (project_path, env_path, cache, root_commit) VALUES (?, ?, ?, ?)",
                [project_path, env_path, cache, root_commit],
            )

        return Project(project_path, env_path, cache, root_commit)

    def get_project(self, db_project_path: str) -> Optional["Project"]:
        with self.connect() as db:
            project = db.execute(
                "SELECT * FROM projects WHERE project_path = ?", [db_project_path]
            ).fetchone()
            if project:
                return Project(project[0], project[1], project[2], project[3])
            return None

    def update_project(self, project: Project) -> None:
        with self.connect() as db:
            db.execute(
                "UPDATE projects SET cache = ?, root_commit = ? WHERE project_path = ?",
                [project.cache.dump(), project.root_commit, project.project_path],
            )

    def create_rule(
        self, id: str, entrypoint: str, description: str, env_path: str
    ) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO rules (id, entrypoint, description, env_path) VALUES (?, ?, ?)",
                [id, entrypoint, description, env_path],
            )

    def get_rules_by_env(self, env_path: str):
        with self.connect() as db:
            mappings = db.execute(
                "SELECT id, description, entrypoint FROM rules WHERE env_path = ?",
                [env_path],
            ).fetchall()
            rules = []
            for id, description, entrypoint in mappings:
                rules.append(
                    {"id": id, "description": description, "entrypoint": entrypoint}
                )
            return rules

    def create_subcommand(
        self, name: str, description: str, entrypoint: str, env_path: str
    ) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO subcommands (name, description, entrypoint, env_path) VALUES (?, ?, ?, ?)",
                [name, description, entrypoint, env_path],
            )

    def get_subcommands_by_env(self, env_path: str):
        with self.connect() as db:
            mappings = db.execute(
                "SELECT name, description, entrypoint FROM subcommands WHERE env_path = ?",
                [env_path],
            ).fetchall()
            subcommands = []
            for name, description, entrypoint in mappings:
                subcommands.append(
                    {"name": name, "description": description, "entrypoint": entrypoint}
                )
            return subcommands


def _get_bark_core_config():
    bark_module = pkg_resources.resource_string(__name__, "bark_core/bark_module.yaml")
    return yaml.safe_load(bark_module)


def get_bark_core_rules():
    return _get_bark_core_config()["rules"]


def get_bark_core_subcommands():
    return _get_bark_core_config()["subcommands"]


class Env:
    def __init__(self, env_path: str) -> None:
        self.store = Store()
        self.env_path = env_path

    def get_activate_script(self):
        system = platform.system()

        if system == "Darwin":
            activate_path = os.path.join(self.env_path, "bin", "activate")
            activate_script = f"source {activate_path}"
        elif system == "Windows":
            activate_script = os.path.join(self.env_path, "Scripts", "activate.bat")
        elif system == "Linux":
            activate_script = os.path.join(self.env_path, "bin", "activate")
        else:
            raise ValueError("Unsupported platform!")

        return activate_script

    def activate(self):
        activate_script = self.get_activate_script()
        cmd(activate_script, shell=True)

    def deactivate(self):
        cmd("deactivate")

    def is_activated(self):
        return sys.prefix != sys.base_prefix

    def _install_module(self, module: BarkModule):
        store_module = self.store.get_module(module.repo)
        if not store_module:
            store_module = self.store.create_module(module.repo)

        _, path = store_module

        cmd("git", "checkout", module.rev, cwd=path)
        cmd("python", "-m", "pip", "install", ".", cwd=path)

        bark_module, _ = cmd("git", "cat-file", "-p", "bark_module.yaml", cwd=path)
        bark_module = yaml.safe_load(bark_module)

        rules = []
        if "rules" in bark_module:
            rules = bark_module["rules"]
        for rule in rules:
            id, description, entrypoint = rule
            # Need to check if we have the rule mapping, and if so update
            # otherwise create
            self.store.create_rule(id, entrypoint, description, self.env_path)

        subcommands = []
        if "subcommands" in bark_module:
            subcommands = bark_module["subcommands"]
        for subcommand in subcommands:
            name, description, entrypoint = subcommand
            self.store.create_subcommand(name, description, entrypoint, self.env_path)

    def install_modules(self, modules: list[BarkModule]):
        for module in modules:
            self._install_module(module)

    def get_rule_entrypoints(self) -> dict:
        entrypoints = {}
        # Add bark_core rules
        for rule in get_bark_core_rules():
            id, entrypoint = rule["id"], rule["entrypoint"]
            entrypoints[id] = entrypoint

        for rule in self.store.get_rules_by_env(self.env_path):
            id, entrypoint = rule["id"], rule["entrypoint"]
            entrypoints[id] = entrypoint

        return entrypoints

    def get_subcommands(self) -> list[dict]:
        subcommands = get_bark_core_subcommands()
        for subcommand in self.store.get_subcommands_by_env(self.env_path):
            subcommands.append(subcommand)

        return subcommands


class CacheEntry:
    def __init__(self, valid: bool, violations: list[str]) -> None:
        self.valid = valid
        self.violations = violations


class Cache:
    def __init__(self, content: bytes) -> None:
        self.cache: dict[str, CacheEntry] = self.load(content)

    def get(self, key: str) -> Optional[CacheEntry]:
        value = self.cache.get(key)
        return value

    def is_empty(self) -> bool:
        return len(self.cache) == 0

    def has(self, key: str):
        return key in self.cache

    def set(self, key: str, value: CacheEntry):
        self.cache[key] = value

    def load(self, content: bytes) -> dict:
        if content:
            return pickle.loads(content)
        return {}

    def dump(self) -> bytes:
        return pickle.dumps(self.cache)
