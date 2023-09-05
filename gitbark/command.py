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

from .store import Project, Store
from .git import get_root

from click import Command, Group, Option
from typing import Any, List
from click.core import Parameter
from abc import abstractmethod
import importlib
import inspect
import re


class BarkCommand(Command):
    """A bark subcommand."""

    def __init__(
        self,
        name: str | None,
        params: List[Parameter] | None = None,
        help: str | None = None,
        **kwargs
    ) -> None:
        super().__init__(
            name=name, callback=self.callback, help=help, params=params, **kwargs
        )

    def invoke(self, ctx) -> Any:
        self.project: Project = ctx.obj["project"]
        self.store: Store = ctx.obj["store"]
        super().invoke(ctx)

    @abstractmethod
    def callback(self):
        """The function that is executed as part of the command."""


def _add_subcommands(cli: Group):
    toplevel = get_root()
    store = Store()
    project = store.get_project(toplevel)
    if not project:
        return
    subcommands_data = project.env.get_subcommands()

    for subcommand in subcommands_data:
        cli.add_command(create_subcommand(subcommand))


def load_subcommand_module(entrypoint: str) -> BarkCommand:
    module = importlib.import_module(entrypoint)
    return getattr(module, "Command")


def options_from_class(cls) -> list[Option]:
    options = []
    for par in inspect.signature(cls.callback).parameters.values():
        if par.name not in ["self"]:
            options.append(
                Option(
                    param_decls=["--" + _parse_param_name(par.name)],
                    type=par.annotation,
                )
            )
    return options


def _parse_param_name(param_name: str) -> str:
    return re.sub("_", "-", param_name)


def create_subcommand(subcommand: dict) -> BarkCommand:
    subcommand_class = load_subcommand_module(subcommand["entrypoint"])
    options = options_from_class(subcommand_class)
    return subcommand_class(
        name=subcommand["name"],
        params=options,
        help=subcommand["description"],
    )
