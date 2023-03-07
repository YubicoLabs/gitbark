
from .navigation import Navigation

import os
import pickle


navigation = Navigation()
navigation.get_root_path() 

CACHE_FILE_PATH = f"{navigation.wd}/.git/gitbark_data/cache.pickle"
CACHE_FILE_PATH_PARENT = f"{navigation.wd}/.git/gitbark_data"


class CacheEntry:
    def __init__(self, valid, violations) -> None:
        self.valid = valid
        self.violations = violations
    


class Cache:
    def __init__(self) -> None:
        self.cache = {}
        if not os.path.exists(CACHE_FILE_PATH_PARENT):
            os.mkdir(CACHE_FILE_PATH_PARENT)
            
        if os.path.exists(CACHE_FILE_PATH):
            with open(CACHE_FILE_PATH, 'rb') as f:
                self.cache = pickle.load(f)
        
    
    def get(self, key) -> CacheEntry:
        value = self.cache.get(key)
        return value

    def has(self, key):
        return key in self.cache
    
    def set(self, key, value:CacheEntry):
        self.cache[key] = value
    
    def dump(self):
        with open(CACHE_FILE_PATH, 'wb') as f:
            pickle.dump(self.cache, f)



