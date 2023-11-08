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

from gitbark.cli.__main__ import cli, _DefaultFormatter
from gitbark.cli.util import CliFail
from gitbark.objects import BranchRuleData, BarkRules
from gitbark.core import BARK_RULES_REF
from gitbark.util import branch_name

from .util import Environment, disable_bark

from click.testing import CliRunner

import logging
import pytest
import os


@pytest.fixture(autouse=True, scope="session")
def test_bark_module():
    cwd = os.getcwd()
    return os.path.join(cwd, "tests", "test_bark_module")


@pytest.fixture(scope="session")
def _env_clean_state(tmp_path_factory):
    env_path = tmp_path_factory.mktemp("env")
    dump_path = tmp_path_factory.mktemp("dump")
    env = Environment(env_path)
    env.dump(dump_path)
    return env, dump_path


@pytest.fixture(scope="session")
def _env_initialized_state(
    _env_clean_state: tuple[Environment, str], tmp_path_factory, test_bark_module
):
    env, _ = _env_clean_state

    bootstrap_main = env.repo.commit("Initial commit.")

    branch_rule = BranchRuleData(
        pattern="main", bootstrap=bootstrap_main.hash.hex(), rules=[]
    )
    bark_rules = BarkRules(branches=[branch_rule])
    env.repo.add_bark_rules(bark_rules, test_bark_module)

    dump_path = tmp_path_factory.mktemp("dump")
    env.dump(dump_path)
    return env, dump_path


@pytest.fixture(scope="session")
def _env_installed_state(
    _env_initialized_state: tuple[Environment, str], tmp_path_factory, bark_cli
):
    env, _ = _env_initialized_state

    cwd = os.getcwd()
    os.chdir(env.repo.repo_dir)
    bark_cli("install", input="y")
    os.chdir(cwd)

    dump_path = tmp_path_factory.mktemp("dump")
    env.dump(dump_path)
    return env, dump_path


@pytest.fixture(scope="session")
def _env_bark_rules_invalid_state(
    _env_installed_state: tuple[Environment, str], tmp_path_factory
):
    env, _ = _env_installed_state

    always_fail_rules = {"rules": [{"always_fail": None}]}
    env.repo.add_commit_rules(
        commit_rules=always_fail_rules, branch=branch_name(BARK_RULES_REF)
    )

    with disable_bark(env.repo) as repo:
        repo.commit(branch=branch_name(BARK_RULES_REF))

    dump_path = tmp_path_factory.mktemp("dump")
    env.dump(dump_path)
    return env, dump_path


@pytest.fixture(scope="function")
def env_clean(_env_clean_state: tuple[Environment, str]):
    env, dump = _env_clean_state
    env.restore_from_dump(dump)
    return env


@pytest.fixture(scope="function")
def env_initialized(_env_initialized_state: tuple[Environment, str]):
    env, dump = _env_initialized_state
    env.restore_from_dump(dump)
    return env


@pytest.fixture(scope="function")
def env_installed(_env_installed_state: tuple[Environment, str]):
    env, dump = _env_installed_state
    env.restore_from_dump(dump)
    return env


@pytest.fixture(scope="function")
def env_bark_rules_invalid(_env_bark_rules_invalid_state: tuple[Environment, str]):
    env, dump = _env_bark_rules_invalid_state
    env.restore_from_dump(dump)
    return env


@pytest.fixture(scope="session")
def bark_cli():
    return _bark_cli


def _bark_cli(*argv, **kwargs):
    handler = logging.StreamHandler()
    handler.setLevel(logging.WARNING)
    handler.setFormatter(_DefaultFormatter())
    logging.getLogger().addHandler(handler)

    runner = CliRunner(mix_stderr=True)
    result = runner.invoke(cli, argv, obj={}, **kwargs)
    if result.exit_code != 0:
        if isinstance(result.exception, CliFail):
            raise SystemExit()
        raise result.exception
    return result
