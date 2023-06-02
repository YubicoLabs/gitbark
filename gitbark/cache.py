import os
import pickle

from gitbark import globals

class CacheEntry:
    def __init__(self, valid, violations, ref_update = False, branch_name = "") -> None:
        self.valid = valid
        self.violations = violations
        self.ref_update = ref_update
        self.branch_name = branch_name
    
class Cache:
    def __init__(self) -> None:
        working_directory = globals.working_directory

        self.CACHE_FILE_PATH = f"{working_directory.wd}/.git/gitbark_data/cache.pickle"
        self.CACHE_FILE_PATH_PARENT = f"{working_directory.wd}/.git/gitbark_data"
        self.cache = {}
        if not os.path.exists(self.CACHE_FILE_PATH_PARENT):
            os.mkdir(self.CACHE_FILE_PATH_PARENT)
            
        if os.path.exists(self.CACHE_FILE_PATH):
            with open(self.CACHE_FILE_PATH, 'rb') as f:
                self.cache = pickle.load(f)
        
    
    def get(self, key) -> CacheEntry:
        value = self.cache.get(key)
        return value

    def has(self, key):
        return key in self.cache
    
    def set(self, key, value:CacheEntry):
        self.cache[key] = value
    
    def dump(self):
        with open(self.CACHE_FILE_PATH, 'wb') as f:
            pickle.dump(self.cache, f)



