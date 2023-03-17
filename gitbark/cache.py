
from .wd import WorkingDirectory

import os
import pickle



class CacheEntry:
    def __init__(self, valid, violations) -> None:
        self.valid = valid
        self.violations = violations
    
class Cache:
    def __init__(self) -> None:
        working_directory = WorkingDirectory()

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



