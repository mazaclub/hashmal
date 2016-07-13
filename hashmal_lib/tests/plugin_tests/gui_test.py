import unittest
import sys
import __builtin__

from PyQt4.QtGui import QApplication

from hashmal_lib.core import chainparams
from hashmal_lib.main_window import HashmalMain

__builtin__.use_local_modules = True

chainparams.set_to_preset('Bitcoin')

app = QApplication(sys.argv)

class GuiTest(unittest.TestCase):
    """Base class for Qt tests."""
    @classmethod
    def setUpClass(cls):
        cls.gui = HashmalMain(app)
        cls.gui.platform.set_testing_mode(True)

    @classmethod
    def tearDownClass(cls):
        cls.gui.close()

    def _set_chainparams(self, name):
        self.gui.settings_dialog.params_combo.set_chainparams(name)

class PluginTest(GuiTest):
    """Base class for plugin tests."""
    plugin_name = ''
    @classmethod
    def setUpClass(cls):
        super(PluginTest, cls).setUpClass()
        cls.ui = cls.gui.plugin_handler.get_plugin(cls.plugin_name).ui
