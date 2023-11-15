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

from typing import Generator, Optional
import os
import sqlite3
import contextlib


@contextlib.contextmanager
def connect_db(db_path: str) -> Generator[sqlite3.Connection, None, None]:
    db_path = db_path
    with contextlib.closing(sqlite3.connect(db_path)) as db:
        with db:
            yield db


def _create_db(db_path: str) -> None:
    with connect_db(db_path) as db:
        db.executescript(
            """
            CREATE TABLE cache_entries (
                commit_hash TEXT NOT NULL,
                valid INTEGER NOT NULL,
                PRIMARY KEY (commit_hash) ON CONFLICT IGNORE
            );
            """
        )


class Cache:
    def __init__(self, db_path: str) -> None:
        if not os.path.exists(db_path):
            _create_db(db_path)
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
