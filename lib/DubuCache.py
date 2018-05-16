"""
    Cache implementation for dububot.
"""

import time
import logging

cachelog = logging.getLogger("cache")

class DubuCache:

    def __init__(self, name = "dubuCache", limitHours = 1):
        self.cache = {}
        self.name = name
        self.limitHours = limitHours

    def __contains__(self, key):
        return key in self.cache

    def add(self, key, value):
        self.cache[key] = {"stamp": time.time(), 'value': value}

    def addDict(self, adict):
        for k,v in adict.items():
            self.add(k, v)
    
    def value(self, key):
        if key in self.cache:
            return self.cache[key]['value']
        else:
            return None

    def print(self):
        print(self.cache)

    def items(self):
        i = {}
        for (k, v) in self.cache.items():
            i[k] = v['value']
        return i

    def keys(self):
        return set(self.cache.keys())

    def cleanup(self):
        """Remove records older than limitHours."""
        limitSeconds = self.limitHours * 3600
        c = dict(self.cache)
        for (k, v) in c.items():
            if (time.time() - v["stamp"] > limitSeconds):
                del self.cache[k]
                cachelog.info("{} - cleaned up {}".format(self.name, k))

    @property
    def size(self):
        return len(self.cache)
