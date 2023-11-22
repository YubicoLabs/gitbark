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

from ..core import (
    get_bark_rules,
    BARK_RULES,
    BARK_RULES_REF,
    BARK_RULES_BRANCH,
    BARK_REQUIREMENTS,
)
from ..objects import BarkRules, RuleData
from ..git import Commit, COMMIT_RULES, BARK_CONFIG
from ..project import Project
from ..util import cmd, BRANCH_REF_PREFIX

from ..cli.util import click_prompt, CliFail

from importlib.metadata import entry_points
from dataclasses import asdict
from typing import Optional

import click
import os
import yaml

ACTIVE_BRANCH = "active_branch"


def newline() -> None:
    click.echo()


def _confirm_commit(
    commit_message: str,
    prompt: str = "Do you want 'bark' to commit the changes?",
    manual_action: str = "Please commit the changes and run 'bark setup' to continue!",
):
    if click.confirm(prompt):
        cmd("git", "commit", "-m", commit_message)
        newline()
    else:
        click.echo(manual_action)
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
    gitbark_folder = f"{project.path}/{BARK_CONFIG}"
    if not os.path.exists(gitbark_folder):
        os.makedirs(gitbark_folder)

    with open(file, "w") as f:
        f.write(content)
    cmd("git", "add", file)


def checkout_or_orphan(project: Project, branch: str) -> None:
    if project.repo.branch == branch:
        return

    if branch not in project.repo.branches:
        cmd("git", "checkout", "--orphan", branch)
        cmd("git", "reset", "--hard")
    else:
        cmd("git", "checkout", branch)


def get_commit_rules(project: Project) -> dict:
    cr_file = os.path.join(project.path, COMMIT_RULES)
    if not os.path.exists(cr_file):
        return {}
    else:
        try:
            with open(cr_file, "r") as f:
                commit_rules_yaml = f.read()
            rules_data = yaml.safe_load(commit_rules_yaml)
            # try to parse the rules
            RuleData.parse_list(rules_data["rules"])
            return rules_data
        except ValueError as e:
            raise e


def has_valid_bark_rules(project: Project) -> bool:
    """Checks whether the bark_rules branch is correctly initialized"""
    if BARK_RULES_REF in project.repo.references:
        root_commit = Commit(
            bytes.fromhex(
                cmd("git", "rev-list", "--max-parents=0", BARK_RULES_REF)[0]
            ),  # root commit hash
            project.repo,
        )
        try:
            root_commit.get_commit_rules()  # will throw error if not parseable
        except Exception:
            raise CliFail(
                "No valid commit rules found for the bootstrap commit "
                f"({root_commit.hash.hex()}) on the "
                f"'{BARK_RULES_BRANCH}' branch!"
            )
        return True
    else:
        return False


def branch_in_bark_rules_yaml(project: Project, branch: str) -> bool:
    try:
        ref = f"{BRANCH_REF_PREFIX}{branch}"
        return bool(get_bark_rules(project).get_ref_rules(ref))
    except ValueError:
        raise CliFail("'bark_modules.yaml' configuration is invalid!")


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


def add_rules_interactive(ep_group: str, rules: list) -> None:
    bark_rules = [(ep.name, ep.load()) for ep in entry_points(group=ep_group)]
    choices = {}
    idx = 0
    for name, rule in bark_rules:
        if rule.setup:
            choices[idx] = (name, rule)
            idx += 1

    if not choices:
        raise CliFail("No configurable rules. Provide configuration manually.")

    while choices:
        newline()
        click.echo("Choose rule (leave blank to skip):")
        max_length_rule_name = max(len(name) for (name, _) in choices.values())
        for choice, (name, rule) in choices.items():
            click.echo(f" [{choice}] {name:{max_length_rule_name}}\t\t{rule.__doc__}")

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

        rule_id, rule = choices.pop(int(choice))
        click.echo(f"Configure the {rule_id} rule!")
        newline()

        rules.append(rule.setup())


def add_commit_rules_interactive(project: Project) -> None:
    commit_rules = get_commit_rules(project).get("rules", [])
    curr_branch = project.repo.branch
    click.echo(f"Specify Commit Rules for the '{curr_branch}' branch!")
    add_rules_interactive("bark_commit_rules", commit_rules)

    commit_rules = {"rules": commit_rules}
    _confirm_commit_rules(commit_rules)

    dump_and_stage(
        project=project,
        file=f"{project.path}/{COMMIT_RULES}",
        content=yaml.safe_dump(commit_rules, sort_keys=False),
    )


def add_branch_rules_interactive(branch: str) -> list:
    click.echo(f"Specify Branch Rules for the '{branch}' branch!")
    branch_rules: list = []
    add_rules_interactive("bark_branch_rules", branch_rules)
    return branch_rules


def add_branches_interactive(project: Project, branch: str) -> None:
    if project.repo.branch != BARK_RULES_BRANCH:
        checkout_or_orphan(project, BARK_RULES_BRANCH)

    try:
        bark_rules = get_bark_rules(project)
    except ValueError:
        raise CliFail("'bark_modules.yaml' configuration is invalid!")

    click.echo(f"Configure how the '{branch}' branch should be validated!\n")

    bootstrap = project.repo.resolve(branch)[0].hash.hex()
    if not click.confirm(
        f"Do you want to verify the '{branch}' branch using "
        f"commit {bootstrap} as bootstrap?"
    ):
        bootstrap = click_prompt(
            "Enter the hash of the bootstrap commit you want to use"
        )

    rules = add_branch_rules_interactive(branch)

    # TODO: Re-use existing bootstrap entries
    bark_rules.project.append(
        {
            "bootstrap": bootstrap,
            "refs": [
                {
                    "pattern": f"refs/heads/{branch}",
                    "rules": rules,
                }
            ],
        }
    )

    _confirm_bark_rules(bark_rules)

    dump_and_stage(
        project=project,
        file=f"{project.path}/{BARK_RULES}",
        content=yaml.safe_dump(asdict(bark_rules), sort_keys=False),
    )


def add_modules_interactive(project: Project) -> None:
    if project.repo.branch != BARK_RULES_BRANCH:
        checkout_or_orphan(project, BARK_RULES_BRANCH)

    click.echo("Define what Bark Modules to add!\n")
    requirements = []
    while True:
        module = click_prompt(
            prompt="Module to add (leave blank to skip)",
            default="",
            show_default=False,
        )
        if not module:
            break

        requirements.append(module)

    content = "\n".join(requirements)
    project.install_modules(content.encode())

    dump_and_stage(
        project=project,
        file=f"{project.path}/{BARK_REQUIREMENTS}",
        content=content,
    )


def setup(project: Project) -> None:
    branch = project.repo.branch
    if not branch:
        raise CliFail("No branch checked out")

    if not has_valid_bark_rules(project):
        if branch != BARK_RULES_BRANCH:
            save_active_branch(project, branch)
            checkout_or_orphan(project, BARK_RULES_BRANCH)
            branch = BARK_RULES_BRANCH

        add_modules_interactive(project)
        newline()
        add_commit_rules_interactive(project)

        rules = add_branch_rules_interactive(BARK_RULES_BRANCH)
        bark_rules = get_bark_rules(project)
        bark_rules.bark_rules = rules
        _confirm_bark_rules(bark_rules)

        dump_and_stage(
            project=project,
            file=f"{project.path}/{BARK_RULES}",
            content=yaml.safe_dump(asdict(bark_rules), sort_keys=False),
        )

        _confirm_commit(commit_message="Add initial modules and rules (made by bark).")

    active_branch = get_active_branch(project)
    if active_branch:  # checkout if we have an active branch
        checkout_or_orphan(project, active_branch)
        branch = active_branch
        remove_active_branch(project)

    if not get_commit_rules(project):
        add_commit_rules_interactive(project)
        _confirm_commit(commit_message="Initial rules (made by bark).")

    if branch != BARK_RULES_BRANCH and not branch_in_bark_rules_yaml(project, branch):
        cmd("git", "checkout", BARK_RULES_BRANCH)
        add_branches_interactive(project, branch)
        _confirm_commit(f"Add {branch} to bark_rules (made by bark).")
        cmd(
            "git", "checkout", branch
        )  # run this if the commit was made in interactive mode

    click.echo("Bark is initialized!")
