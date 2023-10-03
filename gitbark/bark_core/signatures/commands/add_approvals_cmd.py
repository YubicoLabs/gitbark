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

from gitbark.git import Commit
from gitbark.objects import CommitRuleData, CompositeCommitRuleData
from gitbark.cli.util import CliFail
from gitbark.util import cmd

from pygit2 import Blob
from typing import Union
import re
import sys
import click
import logging

logger = logging.getLogger(__name__)


@click.command()
@click.pass_context
@click.argument("commit_msg_file")
def add_approvals(ctx, commit_msg_file):
    """
    Include approvals in a merge commit message.

    NOTE: This command should only be invoked as part of a
    prepare-commit-msg hook.

    \b
    COMMIT_MSG_FILE the file that contains the commit msg.
    """

    project = ctx.obj["project"]
    repo = project.repo

    try:
        merge_head_hash = repo.revparse_single("MERGE_HEAD").id.__str__()
        merge_head = Commit(merge_head_hash)
    except Exception:
        return

    head = Commit(repo.revparse_single("HEAD").id)
    threshold = get_approval_threshold(head)
    if not threshold:
        return

    approvals = get_approvals(merge_head, project)
    if len(approvals) < threshold:
        raise CliFail(
            f"Found {len(approvals)} approvals for {merge_head.hash} "
            "but expected {threshold}."
        )

    click.echo(f"Found {len(approvals)} approvals for {merge_head.hash}!")
    sys.stdin = open("/dev/tty", "r")
    click.confirm(
        "Do you want to include them in the merge commit message?",
        abort=True,
        err=True,
    )
    write_approvals_to_commit_msg(
        approvals, commit_msg_file, project.project_path, merge_head
    )


def write_approvals_to_commit_msg(
    approvals: list[str],
    commit_msg_file: str,
    project_path: str,
    merge_head: Commit,
):
    with open(f"{project_path}/{commit_msg_file}", "w") as f:
        f.write("\n" * 2)
        f.write(f"Including commit: {merge_head.hash}\n" "Approval:\n")
        for approval in approvals:
            f.write(approval + "\n")


def get_approval_threshold(commit: Commit) -> Union[int, None]:
    commit_rules = commit.get_commit_rules()
    for rule in commit_rules.rules:
        if isinstance(rule, CommitRuleData) and rule.id == "require_approval":
            return int(rule.args["threshold"])
        elif isinstance(rule, CompositeCommitRuleData):
            for sub_rule in rule.rules:
                if sub_rule.id == "require_approval":
                    return int(sub_rule.args["threshold"])
    return None


def get_approvals(merge_head: Commit, project):
    repo = project.repo

    # Try to fetch approvals from remote
    try:
        cmd("git", "origin", "fetch", "refs/signatures/*:refs/signatures/*")
    except Exception:
        logger.error("Failed to fetch from 'refs/signatures'")

    references = repo.references.iterator()
    approvals = []
    for ref in references:
        if re.match(f"refs/signatures/{merge_head.hash}/*", ref.name):
            object = repo.get(ref.target)
            if isinstance(object, Blob):
                approvals.append(object.data.decode())

    return approvals
