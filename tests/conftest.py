import pytest
from .utils.util import Environment

@pytest.fixture(scope="session")
def environment():
    environment = Environment("test_env")
    yield environment
    environment.clean()

@pytest.fixture(scope="session")
def git_in_environment(environment:Environment):
    environment.local_repo.initialize_git()
    return environment





