# GitBark 

`GitBark` is a framework that protects the integrity of git repositories. Its primary objective is to enforce strict adherence to predefined rules and policies for git commits.


**NOTE: This is work in progress**

# License
```
Copyright 2023 Yubico AB

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

**Table of contents**
- [Usage](#usage)
- [Installation](#installation)
- [Commit Rules](#commit-rules)
- [Bark Rules](#bark-rules)
- [Receiving updates](#receiving-updates)

# Usage
```
Usage: bark [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  install  Install GitBark in repo.
  verify   Verify repository or branch.
```

The `--help` argument can also be used to get detailed information about specific subcommands.

```
bark verify --help
```

# Installation
Currently GitBark can only be installed from source using the following command:

```
pip install "git+https://github.com/YubicoLabs/gitbark.git"
```


# Commit Rules
Commit rules can be thought of as a set of conditions that a commit must meet to be considered valid. These rules are defined within a YAML file named `commit_rules.yaml`, which is checked into the git repository `GitBark` is configured to run on. Since this file is under version control, every commit points to a specific version of the `commit_rules.yaml` file. 

## Specification
The specification of the `commit_rules.yaml` file is shown below:


### commit_rules.yaml - top level
| Attribute      | Description |
| -----------    | ----------- |
| [`rules`](#commit_rulesyaml---rules)        | the list of rules to be enforced (all rules within this clause need to be satisfied)       |
|       |         |

### commit_rules.yaml - rules
| Attribute      | Description |
| -----------    | ----------- |
| `rule`         | the id of the rule to enforce |
| `args`         | (optional) the list of additional parameters to pass to the rule        |
| `any`          | (optional) a list of rules to be enforced (at least one of the rules within this clause needs to be satisfied)|
|||

### Example specification
An example specification using rules exposed by [`GitBark Core`](https://github.com/YubicoLabs/gitbark-core)

```yaml
    rules:
      - rule: require_signature
        args: [authorized_keys=alice.pub]
```

## Validation
A commit is considered valid if it passes the rules defined in its "nearest" **valid** ancestor commits. We call these commits **validators**, which are the commits that define the rules that a new commit should be validated against. The **validators** for a commit **c** are chosen the following way:

* If the parent of **c** itself is valid, the parent becomes a **validator** for **c**
* If the parent of **c** is not valid, **c** inherits all **validators** that the parent has. 

Once the validator commits are collected, the commit rules defined in them are applied to the commit being validated. The commit is considered valid if it passes ALL these rules. 

## Bootstrap
Since the validation follows a recursive pattern, at some point we will reach that does not have any parents or has parents that do not define any rules. This present a bootstrapping issue which we solve using a bootstrap commit, that define the initial rules for a branch and is explicitly trusted and considered valid. Bootstrap commits for specific branches are defined in [Bark Rules](#bark-rules). 

# Bark Rules
Bark Rules are per-repository, and define the rules for named branches (or branches matching a pattern), such as if we should allow rewrites to history (force pushes), and if they should be validated according to any commit rules using a specific bootstrap commit. Furthermore, these rules define the GitBark modules (modules that expose commit rules and subcommands) to import into the project.

The Bark Rules are stored in a file named `bark_rules.yaml` which is checked into a special orphaned branch, named `bark_rules`. 

## Specification
The specification of the `bark_rules.yaml` file is listed below:

### bark_rules.yaml - top level
| Attribute      | Description |
| -----------    | ----------- |
| [`modules`](#bark_rulesyaml---modules) | list of GitBark modules        |
| [`branches`](#bark_rulesyaml---branches)      | list of configurations for branches        |

### bark_rules.yaml - modules
| Attribute      | Description                |
| -------------- | -------------------------- |
| repo           | the Git repository URL     |
| rev            | the revision to clone from |

### bark_rules.yaml - branches
| Attribute      | Description                   |
| -------------- | ----------------------------- |
| pattern        | the branch name regex pattern |
| ff_only        | (optional: default `False`) set to `True` to enforce fast-forward only changes.     |
| bootstrap      | the hash of the bootstrap commit to use when validating the branch                              |


### Example specification

```yaml
modules:
  - repo: https://github.com/YubicoLabs/gitbark-core
    rev: v1.2.3
branches:
  - pattern: main
    bootstrap: 029ab6a31f8f1e3f03f5db8c5d938c51d2c5f73b
    ff_only: True
```
This specification implies that the "main" branch, need to be valid, using the commit with hash *"029ab6a31f8f1e3f03f5db8c5d938c51d2c5f73b"* as the bootstrap commit. Furthermore, it states that only fast-forward changes are allowed. 

## Root of trust
Since the `bark_rules.yaml` file among other things defines what bootstrap commits should be used to validate different branches, it is essential to protect the integrity of the `bark_rules` branch itself. As such, the `bark_rules` branch has Commit Rules itself that are validated using the root commit (of the `bark_rules` branch) as bootstrap. All other bootstrap commits for commit validation are covered by this bootstrap commit. As such, when the system is initialized, the user is asked to confirm the hash of this commit (like when connecting to an SSH server the first time). 

# Receiving updates
When receiving repository updates, typically via the "push", "pull" commands of Git, GitBark enforces the rules on any changes to existing local refs (that should be validated according to Bark Rules), and refuses to receive violating changes. 

This way, rules can be enforced securely across repository clones without needing to trust intermediate clones. For example, a team developers may enforce specific rules on their local clones even if a central Git hosting service does not yet support enforcing those rules, and may allow updates that violate those rules. The local clones will always remain in a consistent and trustworthy state in relation to established rules.  








