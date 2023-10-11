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

from typing import Generator, Optional
from enum import Enum
from pygit2 import Repository
import os
import sqlite3
import contextlib
import sys


@contextlib.contextmanager
def connect_db(db_path: str) -> Generator[sqlite3.Connection, None, None]:
    db_path = db_path
    with contextlib.closing(sqlite3.connect(db_path)) as db:
        with db:
            yield db


class Cache:
    def __init__(self, db_path: str) -> None:
        self._db = sqlite3.connect(db_path)

    def get(self, key: str) -> Optional[bool]:
        entry = self._db.execute(
            "SELECT valid FROM cache_entries WHERE commit_hash = ? ",
            [key],
        ).fetchone()
        return bool(entry[0]) if entry else None

    def has(self, key: str) -> bool:
        res = self._db.execute(
            "SELECT EXISTS(SELECT 1 FROM cache_entries WHERE commit_hash = ?)",
            [key],
        ).fetchone()
        return bool(res[0])

    def set(self, key: str, valid: bool) -> None:
        self._db.execute(
            "INSERT INTO cache_entries (commit_hash, valid) " "VALUES (?, ?)",
            [key, int(valid)],
        )

    def remove(self, key: str) -> None:
        self._db.execute(
            "DELETE FROM cache_entries WHERE commit_hash = ? ",
            [key],
        )

    def close(self) -> None:
        self._db.commit()
        self._db.close()


class PROJECT_FILES(str, Enum):
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
                CREATE TABLE cache_entries (
                    commit_hash TEXT NOT NULL,
                    valid INTEGER NOT NULL,
                    PRIMARY KEY (commit_hash) ON CONFLICT IGNORE
                );
                """
            )

    def install_bark_module(self, bark_module: str) -> None:
        pip_path = os.path.join(self.env_path, "bin", "pip")
        cmd(pip_path, "install", bark_module)

    def get_env_site_packages(self) -> str:
        exec_path = os.path.join(self.env_path, "bin", "python")
        return cmd(
            exec_path,
            "-c",
            "from distutils.sysconfig import get_python_lib; print(get_python_lib())",
        )[0]

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
        self.cache.close()
