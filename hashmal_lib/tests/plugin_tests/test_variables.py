import unittest

from PyQt4.QtTest import QTest

from hashmal_lib.plugins import variables
from .gui_test import PluginTest

class VariablesTest(PluginTest):
    plugin_name = 'Variables'
    def setUp(self):
        super(VariablesTest, self).setUp()
        self.ui.new_var_key.clear()
        self.ui.new_var_value.clear()
        self._set_chainparams('Bitcoin')

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
        if not self.gui.plugin_handler.get_plugin('Address Encoder').ui.is_enabled:
            self.skipTest('The Address Encoder plugin is not enabled.')
        test_items = [
            ('1111111111111111111114oLvT2', ['Address']),
            ('M7uAERuQW2AotfyLDyewFGcLUDtAYu9v5V', ['Address']),
            ('ffffffffffffffffffffffffffffffffffffffff', ['Hash160', 'Hex']),
            ('0xffffffffffffffffffffffffffffffffffffffff', ['Hash160', 'Hex']),
        ]

        for data, classification in test_items:
            categories = variables.classify_data(data)
            self.assertEqual(set(categories), set(classification), 'Incorrect classification for %s: %s' % (data, categories))

    def test_script_template_classification(self):
        """Test classification of items added by Script Generator."""
        if not self.gui.plugin_handler.get_plugin('Script Generator').ui.is_enabled:
            self.skipTest('The Script Generator plugin is not enabled.')
        test_items = [
            ('OP_RETURN 0x01', ['Script Matching Template']),
            ('OP_DUP OP_HASH160 0xffffffffffffffffffffffffffffffffffffffff OP_EQUALVERIFY OP_CHECKSIG', ['Script Matching Template']),
        ]

        for data, classification in test_items:
            categories = variables.classify_data(data)
            self.assertEqual(set(categories), set(classification), 'Incorrect classification for %s: %s' % (data, categories))
