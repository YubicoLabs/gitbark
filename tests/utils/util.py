
import subprocess
import os
import shutil
import yaml
from enum import Enum

LOCAL_REPO_PATH = "local"
REMOTE_REPO_PATH = "remote"
EXTERNAL_REPO_PATH = "attacker"

class User:
    def __init__(self, name, email, gpg_key_id="", ssh_key_path="") -> None:
        self.name = name
        self.email = email
        self.gpg_key_id = gpg_key_id
        self.ssh_key_path = ssh_key_path

class KeyType(Enum):
    GPG = 1
    SSH = 2

class Environment():
    def __init__(self, tempdir, users:list[User]) -> None:
        tempdir_path = f"{os.getcwd()}/{tempdir}"
        if not os.path.exists(tempdir_path):
            os.mkdir(tempdir_path)
        self.cwd = tempdir_path

        self.users: dict[str, User] = {user.name: user for user in users}

        self.local = Repo(f"{self.cwd}/{LOCAL_REPO_PATH}")
        self.external = Repo(f"{self.cwd}/{EXTERNAL_REPO_PATH}")
        self.remote = Remote(f"{self.cwd}/{REMOTE_REPO_PATH}")

        self.set_key_file_permissions()

    def set_key_file_permissions(self):
        ssh_path = f"{os.getcwd()}/tests/utils/ssh/.ssh"

        alice_key_path = f"{ssh_path}/alice.ssh"
        bob_key_path = f"{ssh_path}/bob.ssh"
        eve_key_path = f"{ssh_path}/eve.ssh"

        os.chmod(alice_key_path, 0o400)
        os.chmod(bob_key_path, 0o400)
        os.chmod(eve_key_path, 0o400)

    def clean(self):
        shutil.rmtree(self.cwd)



class Remote():
    def __init__(self, wd):
        if not os.path.exists(wd):
            os.mkdir(wd)
        self.wd = wd

    def initialize_git(self):
        self.cmd("git", "init", "--bare")
    
    def cmd(self, *args, shell=False):
        try:
            result = subprocess.run(args, capture_output=True, check=True, text=True, shell=shell, cwd=self.wd)
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except (subprocess.CalledProcessError, OSError) as e:
            print(f"Error running command: {e}")
            return e.stdout.strip(), e.stderr.strip(), e.returncode

class Repo():
    def __init__(self, wd) -> None:
        if not os.path.exists(wd):
            os.mkdir(wd)
        self.wd = wd

    def initialize_git(self):
        self.cmd("git", "init")
        self.cmd("git", "checkout", "-b", "main")

    def get_head(self):
        head, _ ,_  = self.cmd("git", "rev-parse", "HEAD")
        return head.strip()
    
    def initialize_commit_rules_on_branch(self, commit_rules, pubkeys, key_type:KeyType=KeyType.GPG, gpg_signing_key=None, ssh_key_path=None):
        self.cmd("echo nonsense > README.md", shell=True)
        self.create_commit_rules(commit_rules)
        self.add_pubkeys(pubkeys, key_type)
        self.cmd("git", "add", ".")
        if key_type == KeyType.GPG and gpg_signing_key:
            self.cmd("git", "commit", "-S", f"--gpg-sign={gpg_signing_key}", "-m", "Initial commit")
        else:
            self.configure_ssh_signing(ssh_key_path)
            self.cmd("git", "commit", "-S", "-m", "Initial commit")
        commit_hash, _, _ = self.cmd("git", "rev-parse", "HEAD")
        return commit_hash
    
    def initialize_branch_rules(self, commit_rules, branch_rules, pubkeys, key_type:KeyType=KeyType.GPG, gpg_signing_key=None, ssh_key_path=None):
        self.cmd("git", "checkout", "--orphan", "branch_rules")
        self.cmd("rm -rf .gitbark", shell=True)
        self.create_branch_rules(branch_rules)
        self.create_commit_rules(commit_rules)
        self.add_pubkeys(pubkeys, key_type)
        self.cmd("git", "add", ".")
        if key_type == KeyType.GPG and gpg_signing_key:
            self.cmd("git", "commit", "-S", f"--gpg-sign={gpg_signing_key}", "-m", "Initial branch_rules")
        else:
            self.configure_ssh_signing(ssh_key_path)
            self.cmd("git", "commit", "-S", "-m", "Initial branch rules")
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

    def configure_ssh_signing(self, ssh_key_path):
        self.cmd("git", "config", "gpg.format", "ssh")
        self.cmd("git", "config", "user.signingkey", ssh_key_path)

    def unconfigure_ssh_signing(self):
        self.cmd("git", "config", "gpg.format", "openpgp")

    def add_pubkeys(self, pubkeys, key_type:KeyType):
        os.mkdir(f"{self.wd}/.gitbark/.pubkeys")
        pubkeys_path = ""
        if key_type == KeyType.GPG:
            pubkeys_path = f"{os.getcwd()}/tests/utils/gpg/.pubkeys"
        else:
            pubkeys_path = f"{os.getcwd()}/tests/utils/ssh/.ssh"
        for pubkey in pubkeys:
            self.cmd("cp", f"{pubkeys_path}/{pubkey}", f"{self.wd}/.gitbark/.pubkeys")

    def add_pubkey(self, pubkey):
        pubkeys_path = f"{os.getcwd()}/tests/utils/gpg/.pubkeys"
        self.cmd("cp", f"{pubkeys_path}/{pubkey}", f"{self.wd}/.gitbark/.pubkeys")

    def cmd(self, *args, shell=False):
        try:
            result = subprocess.run(args, capture_output=True, check=True, text=True, shell=shell, cwd=self.wd)
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except (subprocess.CalledProcessError, OSError) as e:
            print(f"Error running command: {e}")
            return e.stdout.strip(), e.stderr.strip(), e.returncode
            
    