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

from ..git import Commit
from ..core import get_bark_rules
from ..project import Project
from ..rule import get_rules


def prepare_merge_msg(head: Commit, project: Project, commit_msg_file: str):
    bark_rules = get_bark_rules(project)
    project.load_rule_entrypoints(bark_rules)

    for rule in get_rules(head, project):
        rule.prepare_merge_msg(commit_msg_file)