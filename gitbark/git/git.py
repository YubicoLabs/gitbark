from ..navigation import Navigation

import subprocess

class Git:
    def __init__(self) -> None:
        self.navigation = Navigation()
        self.navigation.get_root_path()

    def get_object(self, hash):
        return subprocess.check_output(["git", "cat-file", "-p", hash], text=True, cwd=self.navigation.wd)

    def rev_parse(self, args):
        try:
            return subprocess.check_output(["git", "rev-parse", args], text=True, cwd=self.navigation.wd, stderr=subprocess.STDOUT).rstrip()
        except subprocess.CalledProcessError as cpe:
            raise cpe
    
    def get_ref(self, pattern, discard_ref_name=True):
        return subprocess.check_output(["git", "show-ref", pattern, "-s" if discard_ref_name else ""], text=True, cwd=self.navigation.wd)

    def get_refs(self):
        return subprocess.check_output(["git", "show-ref"], text=True, cwd=self.navigation.wd)
    
    def for_each_ref(self, pattern, hash_only=True):
        if hash_only:
            return subprocess.check_output(["git", "for-each-ref", "--format=%(objectname)", pattern], text=True, cwd=self.navigation.wd)
    
    def show(self, args):
        return subprocess.check_output(args, text=True, cwd=self.navigation.wd, shell=True)
    
    def get_remote_refs(self):
        return self.for_each_ref(pattern="refs/remotes/")

    def get_file_diff(self, commit_hash_1, commit_hash_2):
        return subprocess.check_output(["git", "diff-tree", "--no-commit-id", "--name-only", commit_hash_1, commit_hash_2], text=True, cwd=self.navigation.wd)

    def update_ref(self, ref, new_ref):
        # TODO: Remove staged changes
        subprocess.run(f"git update-ref {ref} {new_ref}", cwd=self.navigation.wd, shell=True)

    def push_ref(self, refspec):
        subprocess.run(f"git push origin {refspec}", cwd=self.navigation.wd, shell=True)

    def restore_files(self):
        subprocess.run("git restore --staged .", cwd=self.navigation.wd, shell=True)
        subprocess.run("git restore .", cwd=self.navigation.wd, shell=True)

    def fetch(self, args):
        subprocess.run(f"git fetch {args}", cwd=self.navigation, shell=True)
    
    def symbolic_ref(self, ref):
        return subprocess.check_output(["git", "symbolic-ref", "--short", ref], text=True, cwd=self.navigation.wd).rstrip()




