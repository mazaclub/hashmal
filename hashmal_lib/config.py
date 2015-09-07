from PyQt4.QtGui import *
from PyQt4 import QtCore


from hashmal_lib.core import my_config


# Singleton instance
hashmal_config = None

def set_config(c):
    global hashmal_config
    hashmal_config = c

def get_config():
    return hashmal_config

class Config(QtCore.QObject):
    """Wrapper for core.Config.

    This exists so that widgets can connect to optionChanged
    if they require themselves to update with a certain option.
    """

    optionChanged = QtCore.pyqtSignal(str, name='optionChanged')
    def __init__(self, parent=None):
        super(Config, self).__init__(parent)
        self.conf = my_config.Config()
        self.conf.load()
        set_config(self)

    def get_option(self, key, default=None):
        return self.conf.get_option(key, default)

    def set_option(self, key, value, do_save=True):
        self.conf.set_option(key, value, do_save)
        self.optionChanged.emit(key)
