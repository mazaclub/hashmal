import unittest
from collections import namedtuple

from hashmal_lib.core import utils
from hashmal_lib import gui_utils

class UtilsTest(unittest.TestCase):
    def test_is_hex(self):
        hex_tests = (
            ('0x0', True),
            ('0x00', True),
            ('0', True),
            ('00', True),
            ('f', True),
            ('x', False),
            ('0x', False),
        )
        for value, expected in hex_tests:
            self.assertEqual(expected, utils.is_hex(value))

    def test_format_hex_string(self):
        format_tests = (
            ('0x0', True, '0x00'),
            ('0x0', False, '00'),
            ('ff', True, '0xff'),
            ('ff', False, 'ff'),
            ('0x000', True, '0x0000'),
            ('0x000', False, '0000'),
        )
        for value, with_prefix, expected in format_tests:
            self.assertEqual(expected, utils.format_hex_string(value, with_prefix=with_prefix))

    def test_push_script(self):
        push_tests = (
            ('1010', '021010'),
            ('0000000000000000000000000000000000000000', '140000000000000000000000000000000000000000'),
        )
        for value, expected in push_tests:
            self.assertEqual(expected, utils.push_script(value))

LabelTest = namedtuple('LabelTest', ('attr', 'label'))

class GuiUtilsTest(unittest.TestCase):
    def test_view_label_for_block_headers(self):
        test_items = [
            LabelTest('nVersion', 'Version'),
            LabelTest('hashPrevBlock', 'Prev Block Hash'),
            LabelTest('hashMerkleRoot', 'Merkle Root Hash'),
            LabelTest('nTime', 'Time'),
            LabelTest('nBits', 'Bits'),
            LabelTest('nNonce', 'Nonce'),
        ]
        for test in test_items:
            self.assertEqual(test.label, gui_utils.get_label_for_attr(test.attr))

    def test_view_label_for_tx_fields(self):
        test_items = [
            LabelTest('nVersion', 'Version'),
            LabelTest('nLockTime', 'Lock Time'),
            # Previous outpoint
            LabelTest('hash', 'Hash'),
            LabelTest('n', 'Index'),
            # TxIn
            LabelTest('scriptSig', 'Sig Script'),
            LabelTest('nSequence', 'Sequence'),
            # TxOut
            LabelTest('nValue', 'Value'),
            LabelTest('scriptPubKey', 'Pub Key Script')
        ]
        for test in test_items:
            self.assertEqual(test.label, gui_utils.get_label_for_attr(test.attr))
