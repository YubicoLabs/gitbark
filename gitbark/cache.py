
import os
import pickle


CACHE_FILE_PATH = "/Users/ebonnici/Github/MasterProject/test-repo/cache.pickle"


class CacheEntry:
    def __init__(self, valid, violations) -> None:
        self.valid = valid
        self.violations = violations
    


class Cache:
    def __init__(self) -> None:
        self.cache = {}
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



