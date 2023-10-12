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

from gitbark.cli.util import click_prompt, CliFail
from gitbark.project import Project
from gitbark.git import Commit
from gitbark.objects import BarkRules, BranchRule
from gitbark.util import cmd
from gitbark.core import get_bark_rules
from importlib.metadata import entry_points
from dataclasses import asdict

from typing import Optional
import click
import os
import yaml
import re


BARK_IN_REPO_FOLDER = ".gitbark"
COMMIT_RULES = "commit_rules.yaml"
BARK_RULES = "bark_rules.yaml"
BARK_RULES_BRANCH = "bark_rules"
ACTIVE_BRANCH = "active_branch"


def newline() -> None:
    click.echo()


def _confirm_commit(
    commit_message: str,
    prompt: str = "Do you want 'bark' to commit the changes?",
):
    if click.confirm(prompt):
        cmd("git", "commit", "-m", commit_message)
        newline()
    else:
        click.echo("Please commit the changes and run 'bark setup' to continue!")
        exit(0)


def _confirm_generation(obj: dict, text: str, prompt: str):
    click.echo(text)
    newline()
    click.echo(yaml.safe_dump(obj))
    click.confirm(text=prompt, abort=True, err=True)


def _confirm_bark_rules(
    bark_rules: BarkRules,
    text: str = "Generated 'bark_rules.yaml'",
    prompt: str = "Do you confirm generation?",
):
    _confirm_generation(obj=asdict(bark_rules), text=text, prompt=prompt)


def _confirm_commit_rules(
    commit_rules: dict,
    text: str = "Generated 'commit_rules.yaml'",
    prompt: str = "Do you confirm generation?",
):
    _confirm_generation(obj=commit_rules, text=text, prompt=prompt)


def dump_and_stage(project: Project, file: str, content: str) -> None:
    gitbark_folder = f"{project.path}/.gitbark"
    if not os.path.exists(gitbark_folder):
        os.makedirs(gitbark_folder)

    with open(file, "w") as f:
        f.write(content)
    cmd("git", "add", file)


def checkout_or_orphan(project: Project, branch: str) -> None:
    curr_branch = cmd("git", "symbolic-ref", "--short", "HEAD")[0]
    if curr_branch == branch:
        return

    if not has_branch(project, branch):
        cmd("git", "checkout", "--orphan", branch)
        cmd("git", "reset", "--hard")
    else:
        cmd("git", "checkout", branch)


def get_commit_rules(project: Project):
    try:
        with open(f"{project.path}/{BARK_IN_REPO_FOLDER}/{COMMIT_RULES}", "r") as f:
            return yaml.safe_load(f)
    except Exception:
        return {"rules": []}


def add_rules_interactive(project: Project, branch: str) -> None:
    commit_rules = get_commit_rules(project)

    bark_init = entry_points(group="bark_init")
    bark_rules = entry_points(group="bark_rules")
    choices = {}
    for idx, ep in enumerate(bark_init):
        name = ep.name
        docs = bark_rules[name].load().__doc__
        choices[idx] = (name, docs)

    click.echo(f"Specify Commit Rules for the '{branch}' branch!")
    while True:
        newline()
        click.echo("Choose rule (leave blank to skip):")
        for choice, (name, description) in choices.items():
            click.echo(" [{0}] {1}\t\t{2}".format(choice, name, description))

        click_choices = [str(choice) for choice in choices.keys()]
        click_choices.append("")
        choice = click_prompt(
            prompt="",
            prompt_suffix=" >",
            default="",
            show_default=False,
            type=click.Choice(click_choices),
            show_choices=False,
        )
        newline()
        if not choice:
            break

        rule_id, _ = choices[int(choice)]
        click.echo(f"Configure the {rule_id} rule!")
        newline()
        init_cls = bark_init[rule_id].load()
        commit_rule = init_cls(project.repo)
        commit_rules["rules"].append(commit_rule)

    _confirm_commit_rules(commit_rules)

    dump_and_stage(
        project=project,
        file=f"{project.path}/{BARK_IN_REPO_FOLDER}/{COMMIT_RULES}",
        content=yaml.safe_dump(commit_rules, sort_keys=False),
    )


def add_branches_interactive(project: Project, branch: str) -> None:
    try:
        bark_rules = get_bark_rules(project)
    except Exception:
        bark_rules = BarkRules([], [])

    click.echo(f"Configure how the '{branch}' branch should be validated!\n")

    ff_only = click.confirm(
        f"Do you want to enforce fast-forward changes on the '{branch}'?"
    )
    bootstrap = project.repo.resolve_refish(branch)[0].id
    if not click.confirm(
        f"Do you want to verify the '{branch}' branch using "
        f"the bootstrap commit {bootstrap}?"
    ):
        bootstrap = click_prompt(
            "Enter the hash of the bootstrap commit you want to use"
        )

    branch_rule = BranchRule(pattern=branch, bootstrap=str(bootstrap), ff_only=ff_only)
    bark_rules.branches.append(branch_rule)

    _confirm_bark_rules(bark_rules)

    dump_and_stage(
        project=project,
        file=f"{project.path}/{BARK_IN_REPO_FOLDER}/{BARK_RULES}",
        content=yaml.safe_dump(asdict(bark_rules), sort_keys=False),
    )


def add_modules_interactive(project: Project) -> None:
    try:
        bark_rules = get_bark_rules(project)
    except Exception:
        bark_rules = BarkRules([], [])

    click.echo("Define what Bark Modules to add!\n")
    while True:
        module = click_prompt(
            prompt="Module to add (leave blank to skip)",
            default="",
            show_default=False,
        )
        if not module:
            break

        project.install_bark_module(module)
        bark_rules.modules.append(module)

    _confirm_bark_rules(bark_rules)

    dump_and_stage(
        project=project,
        file=f"{project.path}/{BARK_IN_REPO_FOLDER}/{BARK_RULES}",
        content=yaml.safe_dump(asdict(bark_rules), sort_keys=False),
    )


def has_valid_bark_rules(project: Project) -> bool:
    """Checks whether the bark_rules branch is correctly initialized"""
    if has_branch(project, BARK_RULES_BRANCH):
        # Get the bootstrap commit
        root_commit = cmd("git", "rev-list", "--max-parents=0", BARK_RULES_BRANCH)[0]
        if not has_commit_rules(Commit(root_commit)):
            # Should have commit_rules
            raise CliFail(
                "No valid commit rules found for the bootstrap commit "
                f"({root_commit}) on the '{BARK_RULES_BRANCH}' branch!"
            )
        return True
    else:
        return False


def branch_in_bark_rules_yaml(project: Project, branch: str) -> bool:
    branch_rules = get_bark_rules(project).branches

    for branch_rule in branch_rules:
        pattern = re.compile(f".*{branch}")
        for b in branch_rule.branches(project.repo):
            if re.match(pattern, b):
                return True
    return False


def has_branch(project: Project, branch: str):
    if not project.repo.lookup_branch(branch):
        return False
    return True


def has_commit_rules(commit: Commit) -> bool:
    try:
        commit.get_commit_rules()
        return True
    except Exception:
        return False


def save_active_branch(project: Project, branch: str) -> None:
    with open(f"{project.bark_directory}/{ACTIVE_BRANCH}", "w") as f:
        f.write(branch)


def get_active_branch(project: Project) -> Optional[str]:
    file = f"{project.bark_directory}/{ACTIVE_BRANCH}"
    if os.path.exists(file):
        with open(file, "r") as f:
            return f.read()
    return None


def remove_active_branch(project: Project):
    os.remove(f"{project.bark_directory}/{ACTIVE_BRANCH}")


def setup(project: Project) -> None:

    curr_branch = cmd("git", "symbolic-ref", "--short", "HEAD")[0]

    if not has_valid_bark_rules(project):
        if curr_branch != BARK_RULES_BRANCH:
            save_active_branch(project, curr_branch)
            checkout_or_orphan(project, BARK_RULES_BRANCH)
            curr_branch = BARK_RULES_BRANCH

        add_modules_interactive(project)
        newline()
        add_rules_interactive(project, BARK_RULES_BRANCH)

        _confirm_commit(commit_message="Add initial modules and rules (made by bark).")

    active_branch = get_active_branch(project)
    if active_branch:  # checkout if we have an active branch
        checkout_or_orphan(project, active_branch)
        curr_branch = active_branch
        remove_active_branch(project)

    if has_branch(project, curr_branch):
        head = Commit(project.repo.revparse_single(curr_branch).id)
        if not has_commit_rules(head):
            add_rules_interactive(project, curr_branch)
            _confirm_commit(commit_message="Initial rules (made by bark).")
    else:
        add_rules_interactive(project, curr_branch)
        _confirm_commit(commit_message="Initial rules (made by bark).")

    if curr_branch != BARK_RULES_BRANCH and not branch_in_bark_rules_yaml(
        project, curr_branch
    ):
        cmd("git", "checkout", BARK_RULES_BRANCH)
        add_branches_interactive(project, curr_branch)
        _confirm_commit(f"Add {curr_branch} to bark_rules (made by bark).")
        cmd(
            "git", "checkout", curr_branch
        )  # run this if the commit was made in interactive mode

    click.echo("Bark is initialized!")