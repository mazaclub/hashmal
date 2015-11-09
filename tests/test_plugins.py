import unittest

from hashmal_lib.plugins.variables import classify_data
from hashmal_lib.core import chainparams

class VariablesTest(unittest.TestCase):
    def setUp(self):
        chainparams.set_to_preset('Bitcoin')

    def test_data_classification(self):
        test_items = [
            ('', []),
            ('xyz', []),
            ('0x100', ['Hex']),
            ('100', ['Hex']),
            ('"word"', ['Text']),
            ('0000000000000000000000000000000000000000', ['Hash160', 'Hex']),
            ('0x0000000000000000000000000000000000000000', ['Hash160', 'Hex']),
            ('01000000010000000000000000000000000000000000000000000000000000000000000000ffffffff4d04ffff001d0104455468652054696d65732030332f4a616e2f32303039204368616e63656c6c6f72206f6e206272696e6b206f66207365636f6e64206261696c6f757420666f722062616e6b73ffffffff0100f2052a01000000434104678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5fac00000000', ['Raw Transaction', 'Hex']),
            ('000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f', ['64 Hex Digits', 'Hex']),
            ('0x000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f', ['64 Hex Digits', 'Hex'])
        ]

        for data, classification in test_items:
            categories = classify_data(data)
            self.assertEqual(set(categories), set(classification))
