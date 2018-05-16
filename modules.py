"""
    Class to load modules from a defined directory
"""

import sys
import os
import logging
import dubucore

modules_log = logging.getLogger('modules')

class Modules:
    moduledir = os.path.join(sys.path[0], "modules/")

    def __init__(self, auth, config):
        self.ns = {}
        self.config = config
        self.auth = auth

    def _findModules(self):
        """Find all modules"""
        modules = [m for m in os.listdir(self.moduledir) if m.startswith("module_") and m.endswith(".py")]
        return modules

    def _loadModules(self):
        """Load the modules"""
        env = {}
        for module in self._findModules():
            modules_log.info("load module - %s" % module)
            self.execfile(os.path.join(self.moduledir, module), env, env)

            if 'init' in env:
                modules_log.info("initialize module - %s" % module)
                env['init'](self.auth)
            # Add to namespace so we can find it later
            self.ns[module] = (env, env)


    def load(self):
        self._loadModules()

    """3.X replacement for 2.X execfile function."""
    def execfile(self, filepath, globals=None, locals=None):
        if globals is None:
            globals = {}
        globals.update({
            "__file__": filepath,
            "__name__": "__main__",
        })
        with open(filepath, 'rb') as file:
            exec(compile(file.read(), filepath, 'exec'), globals, locals)
