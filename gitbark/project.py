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
from .git import Commit, Repository

from typing import Generator, Optional
from enum import Enum
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

    def get(self, commit: Commit) -> Optional[bool]:
        entry = self._db.execute(
            "SELECT valid FROM cache_entries WHERE commit_hash = ? ",
            [commit.hash.hex()],
        ).fetchone()
        return bool(entry[0]) if entry else None

    def has(self, commit: Commit) -> bool:
        res = self._db.execute(
            "SELECT EXISTS(SELECT 1 FROM cache_entries WHERE commit_hash = ?)",
            [commit.hash.hex()],
        ).fetchone()
        return bool(res[0])

    def set(self, commit: Commit, valid: bool) -> None:
        self._db.execute(
            "INSERT INTO cache_entries (commit_hash, valid) " "VALUES (?, ?)",
            [commit.hash.hex(), int(valid)],
        )

    def remove(self, commit: Commit) -> None:
        self._db.execute(
            "DELETE FROM cache_entries WHERE commit_hash = ? ",
            [commit.hash.hex()],
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
            self.create_env()

        sys.path.append(self.get_env_site_packages())

        if not os.path.exists(self.db_path):
            self.create_db()

        self.cache = Cache(self.db_path)
        self.repo = Repository(self.path)
        self.bootstrap = self._load_bootstrap()

    @staticmethod
    def exists(path: str) -> bool:
        bark_directory = os.path.join(path, ".git", BARK_DIRECTORY)
        return os.path.exists(bark_directory)

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

    def create_env(self) -> None:
        os.makedirs(self.env_path, exist_ok=True)
        cmd(sys.executable, "-m", "venv", self.env_path, cwd=self.path)
        return

        exec_path = os.path.join(self.env_path, "bin", "python")
        env_path = cmd(exec_path, "-c", "import sys; print(':'.join(sys.path))")[
            0
        ].split(":")
        additional = [p for p in sys.path[1:] if p not in env_path]
        env_site = self.get_env_site_packages()
        with open(os.path.join(env_site, "gitbark.pth"), "w") as f:
            f.write("\n".join(additional))

    def install_modules(self, requirements: bytes) -> None:
        r_file = os.path.join(self.bark_directory, "requirements.txt")

        if os.path.exists(r_file):
            with open(r_file, "rb") as f:
                old_reqs = f.read()
        else:
            old_reqs = b""

        if requirements != old_reqs:
            with open(r_file, "wb") as f:
                f.write(requirements)

            pip_path = os.path.join(self.env_path, "bin", "pip")
            cmd(
                pip_path,
                "install",
                "-r",
                r_file,
                env={"PYTHONPATH": ":".join(sys.path)},
            )

    def get_env_site_packages(self) -> str:
        exec_path = os.path.join(self.env_path, "bin", "python")
        return cmd(
            exec_path,
            "-c",
            "from sysconfig import get_paths; print(get_paths()['purelib'])",
        )[0]

    def _load_bootstrap(self) -> Optional[Commit]:
        bootstrap_file = os.path.join(self.bark_directory, PROJECT_FILES.BOOTSTRAP)
        if os.path.exists(bootstrap_file):
            with open(bootstrap_file, "r") as f:
                commit_hash = bytes.fromhex(f.read())
            if commit_hash:
                return Commit(commit_hash, self.repo)
        return None

    def _save_bootstrap(self) -> None:
        if self.bootstrap:
            bootstrap_file = os.path.join(self.bark_directory, PROJECT_FILES.BOOTSTRAP)
            with open(bootstrap_file, "w") as f:
                f.write(self.bootstrap.hash.hex())

    def update(self) -> None:
        self._save_bootstrap()
        self.cache.close()
