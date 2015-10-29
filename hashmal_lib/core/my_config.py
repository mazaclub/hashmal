import os
import sys
import json
from copy import deepcopy

# From Encompass
def config_file_path():
    """Return the filesystem path for the Hashmal config file."""
    path = os.getcwd()
    if 'HOME' in os.environ:
        path = os.path.join(os.environ['HOME'], '.config', 'Hashmal')
    elif 'APPDATA' in os.environ:
        path = os.path.join(os.environ['APPDATA'], 'Hashmal')
    elif 'LOCALAPPDATA' in os.environ:
        path = os.path.join(os.environ['LOCALAPPDATA'], 'Hashmal')

    if not os.path.exists(path):
        os.mkdir(path)
    return os.path.join(path, 'hashmal.conf')

class Config(object):
    """Configuration state."""
    def __init__(self):
        super(Config, self).__init__()
        self.options = {}

    def load(self, filename=None):
        if not filename:
            filename = config_file_path()
        if not os.path.exists(filename):
            open(filename, 'w').close()
            self.options = {'filename': filename}
            return
        try:
            with open(filename, 'r') as f:
                options = json.loads(f.read())
                self.options = byteify(options)
        except:
            self.options = {}
        if self.options is None:
            self.options = {}
        self.options['filename'] = filename

    def save(self):
        filename = self.options.get('filename')
        if not filename:
            filename = os.path.abspath('hashmal.conf')
        if not os.path.exists(filename):
            open(filename, 'w').close()
        with open(filename, 'w') as f:
            conf = json.dumps(self.options, indent=4, sort_keys=True)
            f.write(conf)

    def get_option(self, key, default=None):
        value = self.options.get(key, default)
        if isinstance(value, unicode): value = str(value)
        # Return a copy
        return deepcopy(value)

    def set_option(self, key, value, do_save=True):
        self.options[key] = value
        if do_save:
            self.save()

# http://stackoverflow.com/questions/956867/how-to-get-string-objects-instead-of-unicode-ones-from-json-in-python
def byteify(input):
    if isinstance(input, dict):
        return {byteify(key):byteify(value) for key,value in input.iteritems()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input
