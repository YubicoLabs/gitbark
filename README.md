# GitBark 

`GitBark` is a framework that protects the integrity of git repositories. Its primary objective is to enforce strict adherence to predefined rules and policies for git commits. By doing so, it can ensure that all changes made to the repositories are authorized and approved, among other crucial functions.  


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



# Components

## Commit Rules
Commit rules can be thought of as a set of conditions that a commit must meet to be considered valid. For instance, the rules may state that certain files must not be modified, or that the commit must be signed by a specific key. These rules are defined within a YAML file named `commit_rules.yaml`, which is checked into the git repository `GitBark` is configured to run on. Since this file is under version control, every commit points to a specific version of the `commit_rules.yaml` file. 

A commit is considered valid if it passes the rules defined in its "nearest" **valid** ancestor commits. We call these commits **validators**, which are the commits that define the rules that a new commit should be validated against. The **validators** for a commit **c** are chosen the following way:

* If the parent of **c** itself is valid, the parent becomes a **validator** for **c**
* If the parent of **c** is not valid, **c** inherits all **validators** that the parent has. 

Once the validator commits are collected, the commit rules defined in them are applied to the commit being validated. The commit is considered valid if it passess ALL these rules. 

### Example commit rules

```yaml
rules:
    - rule: "require_signature"
      allowed_keys: ".pubkeys/*.pub"
    - rule: "require_approval"
      allowed_keys: "(alice|bob).pub"
      threshold: 2
    - any:
        - rule: "file_not_modified"
          pattern: "sensitive_file.json"
        - rule: "require_signature"
          allowed_keys: ".pubkeys/bob.pub" 
```
The above commit rules enforce the following:

* `require_signature`: Commits need to be signed by a key whose public key matches the pattern ".pubkeys/*.pub". 
* `require_approval`: All merge commits need to include 2 signatures over the MERGE_HEAD, one by Alice and one by Bob. 
* `any`: One of the subrules contained within the `any` clause must be met. I.e, either a commit does not modify "sensitive_file.json" or the commit is signed by bob. 

Note that not all commits are expected to be valid. For example if a pull request is received containg a commit from an external contributor, that commit will most likely not be valid. However, we may still allow it as long as the merge commit is valid, which implies that it is signed by an authorized individual and that it  and contains two "approving" signatures over the commit which is invalid.  

### Commit Rule Validation
To validate commits on a branch, a Bootstrap Commit is needed, which defines the initial commit rules for the branch, and is automatically considered valid. Usually the bootstrap commit will be the root commit, but any commit can be chosen as the bootstrap commit. Bootstrap commits for branches are defined in the Branch Rules. 

## Branch Rules
Branch Rules are per-repository, and define rules for named branches (or branches matching a pattern), such as if we should allow rewrites to history (force pushes), and if they should be validated according any commit rules using a specific bootstrap commit. 

The branch rules are stored in a special branch, named `branch_rules`. This special branch:
* Starts from a new root (orphaned commit) with commit rules for the branch. 
* Does not allow history rewrites (no force pushes).
* Uses its root commit as bootstrap commit, and must be valid.
* The root commit (bootstrap commit) must be marked as trusted by the user. 
* Includes the exact branch rules in the `branch_rules.yaml` file.

### Example of Branch Rules
```yaml
branches:
 - pattern: "main"  # Rules for the "main" branch
   validate_from: "commit_hash_xyx"
   allow_force_push: false   # Probably the default and not needed.
 - pattern: "(release|feature)/.+"  # Rules for any branch starting with "release/" or "feature/"
   validate_from: "commit_hash_xyx"
   allow_force_push: true  # We will allow changes to the history of these
```
The above branch rules state that the "main" branch, as well as any branches starting with "release/" or "feature/" need to be valid, using the commit with id "commit_hash_xyx" as their bootstrap bootstrap commit. Furthermore, the "main" branch requires *fast-foward* changes, meaning that a new commit is only allowed if it is a descendant of the commit the branch currently points to. This restriciton does not apply on the other branches.

### Commit Rules for the Branch Rules branch
Since the `branch_rules.yaml` among other things defines what
bootstrap commits should be used to validate different branches it is essential
to protect the integrity of this file and the `branch_rules` branch. In particular,
only a limited set of authorized individuals should be able to change the
branch_rules.yaml file. As such, the branch_rules branch has commit
rules itself that are validated using the root commit of the branch as bootstrap
commit. 

Suggestions for commit rules for the `branch_rules` branch are the following:
* Requiring a signature from a set of keys.
* Disallow non-Valid parents (since the only commits on this branch are to modify the rules, they should all be valid)
* Disallow multiple parents (there should be no need to merge commits here)


### Repository Validation
To validate a repository, the first step involves validating the `branch_rules`
branch, and making sure the commit it points to is valid according to the
commit rules. This step is important to ensure that we can retrieve a trusted
version of the `branch_rules.yaml` file, which directly impacts how
other branches are validated as it specifies the bootstrap commits to be used.
The first time the `branch_rules` branch is validated, the hash of the bootstrap
commit for the `branch_rules` branch is shown to the user for verification.

Once the `branch_rules` branch has been validated, the rules defined within
the `branch_rules.yaml` file, referenced by the commit to which
the `branch_rules` branch points, are obtained. All branches that match the
defined patterns in `branch_rules.yaml` are validated using the specified
bootstrap commits.

When receiving updates on the local repository, typically via the git
pull and git fetch commands, GitBark runs the validation, and
refuses to receive changes that violate the rules. The same holds when
locally making/submitting changes via the `git commit` and `git push`
commands. Users running GitBark are not able to commit or push changes
that violate the rules. This is to ensure the local repository always remains in
a consistent and trustworthy state in relation to established rules.

# Installation
To install GitBark run the following command:

`pip install "git+https://github.com/YubicoLabs/gitbark.git"`

# Usage

## Setup
To setup GitBark to run on a git repository, perform the following steps:

* 1\. Checkout you `main` branch and create following files and folders
    * 1\.1 Create a folder named `.gitbark/` in the root of your project
    * 1\.2 Inside `.gitbark/` create the `commit_rules.yaml` file and specify the rules you want to enforce. Use the [examples](#example-commit-rules) as a suggested starting point.
    * 1\.3 If you enforce rules with the `allowed_keys` parameter, create a folder named `.pubkeys` within `.gitbark/` and include the corresponding public keys.
    * 1\.4 Commit the files - this commit should serve as your bootstrap commit for the branch you're in.

* 2\. Create the `branch_rules` using the following command `git checkout --orphan branch_rules`
* 3\. Inside the `branch_rules` branch, perform the following steps
    * 3\.1 Perform steps 1.1-1.3 to create the commit rules for this branch. 
    * 3\.2 Create the `branch_rules.yaml` file and specify what branches should be validated and with what bootstrap commit. The `branch_rules.yaml` file might look like this 
    ```yaml
    branches:
        - pattern: "main"  # Rules for the "main" branch
          validate_from: "commit_hash_xyx" # the hash of the bootstrap commit created in step 1.4
          allow_force_push: false 
    ```
    * 3\.3 Commit all files - this commit will be the root commit for the `branch_rules` branch, and will also serve as the bootstrap commit for this branch. 


## Initialization
To initialize `GitBark` on a repository that has already been setup in accordance with the steps listed [above](#setup), run `bark install`. This command will validate the entire repository, and instruct the user to verify the hash of the bootstrap commit for the `branch_rules` branch. Furthermore, this command will install the necessary Git Hooks so that `GitBark` runs the verification on repository updates. 

## Verify
To verify a repository, run `bark verify`. When running this command on a specific branch, `GitBark` will validate that branch. If you want to validate the entire repository run `bark verify --all`. It is also possible to verify a branch not specified in the `branch_rules.yaml`, by explicitly specifying the bootstrap commit as follows `bark verify --bootstrap=<commit_hash>` file. 





