
import subprocess
import os
import sys

class Navigation:
    def __init__(self) -> None:
        self.wd = os.getcwd()
    
    def get_root_path(self):
        try:
            self.wd = "/Users/ebonnici/Github/MasterProject/test-repo" # temporary change
            # git_root_path = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).rstrip()
            # list_files = os.listdir(git_root_path)
            # if ".gitbark" in list_files:
            #     self.wd = git_root_path
            # else:
            #     print("fatal: bark has not been initialized on this repository")
            #     sys.exit(1)
        except subprocess.CalledProcessError as e:
            print(e.output)
        


# x = Navigation()
# x.get_root_path()  
# print(x.wd)      
