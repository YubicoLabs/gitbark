import subprocess

class GitWrapper:
    def __init__(self) -> None:
        self.wd =  "/Users/ebonnici/Github/MasterProject/test-repo"

    def get_object(self, hash):
        return subprocess.check_output(["git", "cat-file", "-p", hash], text=True, cwd=self.wd)

    def rev_parse(self, args):
        return subprocess.check_output(["git", "rev-parse", args], text=True, cwd=self.wd)
    
    def get_ref(self, pattern, discard_ref_name=True):
        return subprocess.check_output(["git", "show-ref", pattern, "--heads", "-s" if discard_ref_name else ""], text=True, cwd=self.wd)

    def get_heads(self):
        return subprocess.check_output(["git", "show-ref", "--heads"], text=True, cwd=self.wd)

    def get_file_diff(self, commit_hash_1, commit_hash_2):
        return subprocess.check_output(["git", "diff-tree", "--no-commit-id", "--name-only", commit_hash_1, commit_hash_2], text=True, cwd=self.wd)

    def update_ref(self, ref, new_ref, old_ref):
        return subprocess.run("git", "update-ref", ref, new_ref, old_ref)

