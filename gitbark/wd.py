
import subprocess
import os
import sys

class WorkingDirectory:
    def __init__(self) -> None:
        self.wd = self.get_working_directory()
    def get_working_directory(self):
        try:
            git_repo_root = ""
            if "TEST_WD" in os.environ:
                git_repo_root = os.environ["TEST_WD"]
            else:
                git_repo_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).rstrip()
            git_repo_content = os.listdir(git_repo_root)
            if ".gitbark" in git_repo_content:
                return git_repo_root
            else:
                print("fatal: bark has not been initialized on this repository")
                sys.exit(1)
        except subprocess.CalledProcessError as cpe:
            print(cpe.output)
            sys.exit(1)
