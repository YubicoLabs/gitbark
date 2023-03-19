
import subprocess
import os
import shutil
import yaml

LOCAL_REPO_PATH = "local"
REMOTE_REPO_PATH = "remote"
EXTERNAL_REPO_PATH = "attacker"

class Environment():
    def __init__(self, tempdir) -> None:
        tempdir_path = f"{os.getcwd()}/{tempdir}"
        if not os.path.exists(tempdir_path):
            os.mkdir(tempdir_path)
        self.cwd = tempdir_path

        self.local_repo = Repo(f"{self.cwd}/{LOCAL_REPO_PATH}")
        self.external_repo = Repo(f"{self.cwd}/{EXTERNAL_REPO_PATH}")

        self.user1_key_id = "7DD61D90C0FC215E"
        self.user2_key_id = "3504E1A6A48F7C8E"
    
    def clean(self):
        shutil.rmtree(self.cwd)

class Repo():
    def __init__(self, wd) -> None:
        if not os.path.exists(wd):
            os.mkdir(wd)
        self.wd = wd

    def initialize_git(self):
        self.cmd("git", "init")

    def reset_to_previous_commit(self):
        self.cmd("git","reset", "--hard", "HEAD^")

    def initialize_commit_rules_on_branch(self, commit_rules, pubkeys, signing_key):
        self.create_commit_rules(commit_rules)
        self.add_pubkeys(pubkeys)
        self.cmd("git", "add", ".")
        self.cmd("git", "commit", "-S", f"--gpg-sign={signing_key}", "-m", "Initial commit")
        commit_hash, _ = self.cmd("git", "rev-parse", "HEAD")
        return commit_hash
    
    def initialize_branch_rules(self, commit_rules, branch_rules, pubkeys, signing_key):
        self.cmd("git", "checkout", "--orphan", "branch_rules")
        self.cmd("rm -rf .gitbark", shell=True)
        self.create_branch_rules(branch_rules)
        self.create_commit_rules(commit_rules)
        self.add_pubkeys(pubkeys)
        self.cmd("git", "add", ".")
        self.cmd("git", "commit", "-S", f"--gpg-sign={signing_key}", "-m", "Initial branch_rules")
        self.cmd("git", "checkout", "main")

    def add_commit_rule(self, commit_rule):
        with open(f"{self.wd}/.gitbark/commit_rules.yaml", "r+") as f:
            commit_rules = yaml.safe_load(f)
            commit_rules["rules"].append(commit_rule)
            yaml.dump(commit_rules, f)

    def create_commit_rules(self, commit_rules:dict):
        if not os.path.exists(f"{self.wd}/.gitbark"):
            os.mkdir(f"{self.wd}/.gitbark")
        with open(f"{self.wd}/.gitbark/commit_rules.yaml", "w") as f:
            yaml.dump(commit_rules, f)

    def create_branch_rules(self, branch_rules:dict):
        if not os.path.exists(f"{self.wd}/.gitbark"):
            os.mkdir(f"{self.wd}/.gitbark")
        with open(f"{self.wd}/.gitbark/branch_rules.yaml", "w") as f:
            yaml.dump(branch_rules, f)
    
    def configure_git_user(self, name, email):
        self.cmd("git", "config", "user.name", name)
        self.cmd("git", "config", "user.email", email)

    def add_pubkeys(self, pubkeys):
        os.mkdir(f"{self.wd}/.gitbark/.pubkeys")
        pubkeys_path = f"{os.getcwd()}/tests/utils/gpg/.pubkeys"
        for pubkey in pubkeys:
            self.cmd("cp", f"{pubkeys_path}/{pubkey}", f"{self.wd}/.gitbark/.pubkeys")

    def add_pubkey(self, pubkey):
        pubkeys_path = f"{os.getcwd()}/tests/utils/gpg/.pubkeys"
        self.cmd("cp", f"{pubkeys_path}/{pubkey}", f"{self.wd}/.gitbark/.pubkeys")     

    def cmd(self, *args, shell=False):
        try:
            result = subprocess.run(args, capture_output=True, check=True, text=True, shell=shell, cwd=self.wd)
            return result.stdout.strip(), result.returncode
        except (subprocess.CalledProcessError, OSError) as e:
            print(f"Error running command: {e}")
    