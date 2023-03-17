
import subprocess
import os



LOCAL_REPO_PATH = "local"
REMOTE_REPO_PATH = "remote"
EXTERNAL_REPO_PATH = "attacker"
TRUSTED_KEY_ID='7DD61D90C0FC215E'
UNTRUSTED_KEY_ID='3504E1A6A48F7C8E'

class Environment():
    def __init__(self) -> None:
        self.cwd = f"{os.getcwd()}/tests/clients"
        self.local_repo = Repo(f"{self.cwd}/{LOCAL_REPO_PATH}")
        self.trusted_key_id='7DD61D90C0FC215E'
        self.untrusted_key_id='3504E1A6A48F7C8E'


class Repo():
    def __init__(self, wd) -> None:
        self.wd = wd
        self.start_head = self.get_start_head()

    def cmd(self, *args, shell=False):
        try:
            result = subprocess.run(args, capture_output=True, check=True, text=True, shell=shell, cwd=self.wd)
            return result.stdout.strip(), result.returncode
        except (subprocess.CalledProcessError, OSError) as e:
            print(f"Error running command: {e}")

    def get_start_head(self):
        head, _ = self.cmd("git", "rev-parse", "HEAD")
        return head
    
    def restore(self):
        self.cmd("git", "reset", "--hard", self.start_head)
    