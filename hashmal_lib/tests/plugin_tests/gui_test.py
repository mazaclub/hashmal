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
    def setUp(self):
        super(GuiTest, self).setUp()
        self.gui = HashmalMain(app)

    def _set_chainparams(self, name):
        self.gui.settings_dialog.params_combo.set_chainparams(name)

