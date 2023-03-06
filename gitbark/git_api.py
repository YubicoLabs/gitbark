import subprocess
import re

class GitApi:
    def __init__(self) -> None:
        self.wd =  "/Users/ebonnici/Github/MasterProject/test-repo"

    def get_object(self, hash):
        return subprocess.check_output(["git", "cat-file", "-p", hash], text=True, cwd=self.wd)

    def rev_parse(self, args):
        return subprocess.check_output(["git", "rev-parse", args], text=True, cwd=self.wd)
    
    def get_ref(self, pattern, discard_ref_name=True):
        return subprocess.check_output(["git", "show-ref", pattern, "-s" if discard_ref_name else ""], text=True, cwd=self.wd)

    def get_refs(self):
        return subprocess.check_output(["git", "show-ref"], text=True, cwd=self.wd)
    
    def for_each_ref(self, hash_only=True):
        if hash_only:
            return subprocess.check_output(["git", "for-each-ref", "--format=%(objectname)", "refs/remotes/"], text=True, cwd=self.wd)

    def get_remote_refs(self):
        return self.for_each_ref()

    def get_file_diff(self, commit_hash_1, commit_hash_2):
        return subprocess.check_output(["git", "diff-tree", "--no-commit-id", "--name-only", commit_hash_1, commit_hash_2], text=True, cwd=self.wd)

    def update_ref(self, ref, new_ref):
        # TODO: Remove staged changes
        subprocess.run(f"echo {new_ref} > .git/{ref}", cwd=self.wd, shell=True)

    def restore_files(self):
        subprocess.run("git restore --staged .", cwd=self.wd, shell=True)
        subprocess.run("git restore .", cwd=self.wd, shell=True)



