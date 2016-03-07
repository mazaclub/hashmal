import unittest
import sys
import __builtin__

from PyQt4.QtGui import QApplication
from PyQt4.QtTest import QTest
from PyQt4.QtCore import Qt

from hashmal_lib.core import chainparams
from hashmal_lib.main_window import HashmalMain
from hashmal_lib.plugins import variables

__builtin__.use_local_modules = True

chainparams.set_to_preset('Bitcoin')

app = QApplication(sys.argv)

class VariablesTest(unittest.TestCase):
    def setUp(self):
        super(VariablesTest, self).setUp()
        self.gui = HashmalMain(app)
        self.ui = self.gui.plugin_handler.get_plugin('Variables').ui
        chainparams.set_to_preset('Bitcoin')

    def test_general_data_classification(self):
        test_items = [
            ('', []),
            ('xyz', []),
            ('0x100', ['Hex']),
            ('100', ['Hex']),
            ('"word"', ['Text']),
            ('000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f', ['64 Hex Digits', 'Hex']),
            ('0x000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f', ['64 Hex Digits', 'Hex'])
        ]

        for data, classification in test_items:
            categories = variables.classify_data(data)
            self.assertEqual(set(categories), set(classification), 'Incorrect classification for %s: %s' % (data, categories))

    def test_address_classification(self):
        """Test classification of items added by Address Encoder."""
        test_items = [
            ('1111111111111111111114oLvT2', ['Address']),
            ('M7uAERuQW2AotfyLDyewFGcLUDtAYu9v5V', ['Address']),
            ('0000000000000000000000000000000000000000', ['Hash160', 'Hex']),
            ('0x0000000000000000000000000000000000000000', ['Hash160', 'Hex']),
        ]

        for data, classification in test_items:
            categories = variables.classify_data(data)
            self.assertEqual(set(categories), set(classification), 'Incorrect classification for %s: %s' % (data, categories))

    def test_script_template_classification(self):
        """Test classification of items added by Script Generator."""
        test_items = [
            ('OP_RETURN 0x01', ['Script Matching Template']),
            ('OP_DUP OP_HASH160 0x0000000000000000000000000000000000000000 OP_EQUALVERIFY OP_CHECKSIG', ['Script Matching Template']),
        ]

        for data, classification in test_items:
            categories = variables.classify_data(data)
            self.assertEqual(set(categories), set(classification), 'Incorrect classification for %s: %s' % (data, categories))
