# Copyright 2023 Yubico AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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



