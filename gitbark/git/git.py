from pygit2 import Repository

import subprocess
import re

from gitbark import globals

class Git:
    def __init__(self) -> None:
        self.working_directory = globals.working_directory
        self.repo = Repository(self.working_directory.wd)

    def get_object(self, hash):
        return self.repo.get(hash)    
    
    def get_refs(self, pattern):
        return [ref for ref in self.repo.references.iterator() if re.match(pattern, ref.name)]

    def get_file_diff(self, commit_hash_1, commit_hash_2):
        diff = self.repo.diff(commit_hash_1, commit_hash_2)
        files = []
        for delta in diff.deltas:
            files.append(delta.new_file.path)
        return files

    def update_ref(self, ref, new_ref):
        subprocess.run(f"git update-ref {ref} {new_ref}", cwd=self.working_directory.wd, shell=True)

    def push_ref(self, refspec):
        subprocess.run(f"git push origin {refspec}", cwd=self.working_directory.wd, shell=True)

    def restore_files(self):
        subprocess.run("git restore --staged .", cwd=self.working_directory.wd, shell=True)
        subprocess.run("git restore .", cwd=self.working_directory.wd, shell=True)

    def fetch(self, args):
        subprocess.run(f"git fetch {args}", cwd=self.working_directory, shell=True)

    def cmd(self, *args):
        try:
            result = subprocess.run(args, capture_output=True, check=True, text=True, cwd=self.working_directory.wd)
            return result.stdout.strip(), result.returncode
        except (subprocess.CalledProcessError, OSError) as e:
            return e.stdout.strip(), e.returncode
    
    def symbolic_ref(self, ref, short=True):
        # return self.repo.revparse_single(ref).name
        return self.repo.lookup_reference(ref).target


