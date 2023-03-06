# Git bark 

A framework that verifies the integrity of a Git repository against pre-defined rules

**NOTE: This is work in progress**

## Setup
To setup Git bark, run `poetry install`. This will download all dependecies needed to run the application. 
There are two ways to run the commands, either `poetry run bark <command>` or if you are running in a poetry virtualenv, 
you can simply run `bark <command>`.

## Commands

### Install
To install `bark` on a repository that already has been intialized, run `bark install`. This command will validate the `branch_rules` branch and instruct the user to verify the hash of the root commit to be used as a boostrap commit in order to establish a root of trust.

### Verify
To verify a repository, run `bark verify`. This command will start to verify the `branch_rules` branch using the root commit as bootstrap. If the validation succeeds, all branches that match the defined branch patterns in the `branch_rules.yaml` file will be validated. 





