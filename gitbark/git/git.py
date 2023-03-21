from ..wd import WorkingDirectory

import os
import subprocess

class Git:
    def __init__(self) -> None:
        self.working_directory = WorkingDirectory()

    def get_object(self, hash):
        return subprocess.check_output(["git", "cat-file", "-p", hash], text=True, cwd=self.working_directory.wd)
    
    def object_exists(self, hash):
        try:
            subprocess.run(f"git cat-file -e {hash}", shell=True, stderr=subprocess.STDOUT)
            return True
        except subprocess.CalledProcessError as cpe:
            return False

    def rev_parse(self, args):
        try:
            return subprocess.check_output(["git", "rev-parse", args], text=True, cwd=self.working_directory.wd, stderr=subprocess.STDOUT).rstrip()
        except subprocess.CalledProcessError as cpe:
            raise cpe
    
    def get_ref(self, pattern, discard_ref_name=True):
        return subprocess.check_output(["git", "show-ref", pattern], text=True, cwd=self.working_directory.wd)

    def get_refs(self):
        return subprocess.check_output(["git", "show-ref"], text=True, cwd=self.working_directory.wd)
    
    def for_each_ref(self, pattern, hash_only=True):
        if hash_only:
            return subprocess.check_output(["git", "for-each-ref", "--format=%(objectname)", pattern], text=True, cwd=self.working_directory.wd)
    
    def show(self, args):
        return subprocess.check_output(args, text=True, cwd=self.working_directory.wd, shell=True)
    
    def get_remote_refs(self):
        return self.for_each_ref(pattern="refs/remotes/")

    def get_file_diff(self, commit_hash_1, commit_hash_2):
        return subprocess.check_output(["git", "diff-tree", "--no-commit-id", "--name-only", commit_hash_1, commit_hash_2], text=True, cwd=self.working_directory.wd)

    def update_ref(self, ref, new_ref):
        # TODO: Remove staged changes
        subprocess.run(f"git update-ref {ref} {new_ref}", cwd=self.working_directory.wd, shell=True)

    def push_ref(self, refspec):
        subprocess.run(f"git push origin {refspec}", cwd=self.working_directory.wd, shell=True)

    def restore_files(self):
        subprocess.run("git restore --staged .", cwd=self.working_directory.wd, shell=True)
        subprocess.run("git restore .", cwd=self.working_directory.wd, shell=True)

    def fetch(self, args):
        subprocess.run(f"git fetch {args}", cwd=self.working_directory, shell=True)
    
    def symbolic_ref(self, ref, short=True):
        if short:
            return subprocess.check_output(["git", "symbolic-ref", "--short", ref], text=True, cwd=self.working_directory.wd).rstrip()
        else:
            return subprocess.check_output(["git", "symbolic-ref", ref], text=True, cwd=self.working_directory.wd).rstrip()



