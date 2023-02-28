# Git Integrity Verifier


## Commit rules verification

```python
Input: commit
Output: PASSED or FAILED

valid_commits = {}
def is_valid(commit):
    # If commit is the bootstrap commit, it is explicitly trusted
    if commit == bootstrap_commit:
        valid_commits[commit] = True
        return True
    
    parents = commit.parents
    validators = []

    for parent in parents:
        if is_valid(parent):
            valid_commits[parent] = True
            validators.append(parent)
        else:
            nearest_valid_ancestor = find_nearest_valid_ancestor(parent)
    
    passes_rules = True
    for validator in validators:
        if not verify_rules(commit, validator.rules):
            passes_rules = False

    if passes_rules:
        valid_commits[commit] = True
        return True
    else: 
        return False

    # Find all validators


    # If parent is valid, use it as validator
    if is_valid(parent):
        return verify_rules(commit, parent.rules)
    # Recursively find the nearest valid ancestor
    else: 
        nearest_valid_ancestor = find_nearest_valid_ancestor(parent)
        return verify_rules(commit, nearest_valid_ancestor.rules)
```

```python
def find_validators(parents):

```




```python
def verify_rules(commit, rules):
    if passes_rules(commit, rules):
        return True
    else:
        return False
```



```python
def find_nearest_valid_ancestor(commit):
    if valid_commits[commit]:
        return commit
    
    return find_nearest_valid_ancestor(commit.parent)

```

## Example of commit rules
Commit rules should be defined on the following form:
- rule_set: <scope, <rule | rule_set>>
- rule: <target, expression>
- expression: 




Example:

rules:
```yaml
rules:
    - type: signature 
      name: Require specific GPG key for commits
      allowed_keys: ./pubkeys
      
    - type: files
      name: Only allow files in build folder to be modified by specific developers
      file_paths: [build/*] 
      allowed_keys: [elias.pub]

      


```


## Commit Object

A commit object contains the following fields:

- tree (SHA1 hash)
- parents (list of SHA1 hash of parent commits)
- author (<name, email>, the one writing the code)
- commiter (<name, email>, the one putting the commit to the repository)
- signature (gpg signature)
- commit message (text)
- files (files modified)
- valid (true or false)
- rules (rules defined for commit)

A tree node contains the following fields:
- blob entry (<file permissions, blob hash, file name>)
- tree entry  


