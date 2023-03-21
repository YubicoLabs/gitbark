import pytest
from .utils.util import Environment

@pytest.fixture(scope="session")
def environment():
    environment = Environment("test_env_manual")
    yield environment
    environment.clean()

@pytest.fixture(scope="session")
def git_in_environment(environment:Environment):
    environment.local_repo.initialize_git()
    return environment

@pytest.fixture(scope="session")
def environment_with_hooks():
    environment = Environment("test_env_hooks")
    environment.remote.initialize_git()
    environment.local_repo.initialize_git()
    environment.external_repo.initialize_git()
    environment.local_repo.cmd("git", "remote", "add", "origin", environment.remote.wd)
    environment.external_repo.cmd("git", "remote", "add", "origin", environment.remote.wd)
    yield environment
    environment.clean()





