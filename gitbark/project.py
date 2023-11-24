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
from .git import Commit, Repository, is_descendant
from .cache import Cache

from typing import Optional
from enum import Enum
import os
import sys
import re


class PROJECT_FILES(str, Enum):
    BOOTSTRAP = "bootstrap"
    CACHE = "cache"


BARK_DIRECTORY = "bark"
ENV_DIRECTORY = "env"
BARK_MODULES_DIRECTORY = "bark_modules"

CACHE_NAME_PATTERN = re.compile(r"([0-9a-f]{40})\.db")


class Project:
    def __init__(self, path: str) -> None:
        self.path = path
        self.bark_directory = os.path.join(self.path, ".git", BARK_DIRECTORY)
        self.env_path = os.path.join(self.bark_directory, ENV_DIRECTORY)
        self.cache_directory = os.path.join(self.bark_directory, PROJECT_FILES.CACHE)

        if not os.path.exists(self.bark_directory):
            os.makedirs(self.bark_directory, exist_ok=True)

        if not os.path.exists(self.env_path):
            self.create_env()

        if not os.path.exists(self.cache_directory):
            os.makedirs(self.cache_directory, exist_ok=True)

        sys.path.append(self.get_env_site_packages())

        self.repo = Repository(self.path)
        self._caches: dict[Commit, Cache] = {}
        self._load_caches()
        self.bootstrap = self._load_bootstrap()

    def _load_caches(self):
        for fname in os.listdir(self.cache_directory):
            m = CACHE_NAME_PATTERN.match(fname)
            if m:
                key = Commit(bytes.fromhex(m.group(1)), self.repo)
                self._caches[key] = Cache(os.path.join(self.cache_directory, fname))

    def get_cache(self, bootstrap: Commit) -> Cache:
        if bootstrap in self._caches:
            return self._caches[bootstrap]

        for bs, cache in self._caches.items():
            if is_descendant(bs, bootstrap) and cache.get(bootstrap):
                return cache

        cache = Cache(os.path.join(self.cache_directory, f"{bootstrap.hash.hex()}.db"))
        self._caches[bootstrap] = cache
        return cache

    @staticmethod
    def exists(path: str) -> bool:
        bark_directory = os.path.join(path, ".git", BARK_DIRECTORY)
        return os.path.exists(bark_directory)

    def create_env(self) -> None:
        # Create venv
        os.makedirs(self.env_path, exist_ok=True)
        cmd(sys.executable, "-m", "venv", self.env_path, cwd=self.path)

        # Add additional site-packages
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
            cmd(pip_path, "install", "-r", r_file)

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
        for cache in self._caches.values():
            cache.close()
