import unittest

from PyQt4.QtTest import QTest
from PyQt4.QtCore import Qt

from hashmal_lib.core import chainparams, Script
from hashmal_lib.plugins import stack
from .gui_test import PluginTest


chainparams.set_to_preset('Bitcoin')

class StackEvalTest(PluginTest):
    plugin_name = 'Stack Evaluator'
    # A valid P2SH transaction from Bitcon's unit tests.
    valid_p2sh_tx = '01000000010001000000000000000000000000000000000000000000000000000000000000000000006e493046022100c66c9cdf4c43609586d15424c54707156e316d88b0a1534c9e6b0d4f311406310221009c0fe51dbc9c4ab7cc25d3fdbeccf6679fe6827f08edf2b4a9f16ee3eb0e438a0123210338e8034509af564c62644c07691942e0c056752008a173c89f60ab2a88ac2ebfacffffffff010000000000000000015100000000'
    def setUp(self):
        super(StackEvalTest, self).setUp()
        self.ui.tx_script.clear()
        self.ui.execution_widget.clear()
        self.ui.tx_edit.clear()
        self.ui.input_idx.setValue(0)
        self.ui.block_height_edit.clear()
        self.ui.block_time_edit.clear()

    def test_script_passed(self):
        script_hex = Script.from_human('0x01').get_hex()
        self.ui.tx_script.setPlainText(script_hex)
        QTest.mouseClick(self.ui.do_button, Qt.LeftButton)

        self.assertTrue(self.ui.script_passed.isChecked())
        self.assertFalse(self.ui.script_verified.isChecked())

        script_hex = Script.from_human('0x00').get_hex()
        self.ui.tx_script.setPlainText(script_hex)
        QTest.mouseClick(self.ui.do_button, Qt.LeftButton)

        self.assertFalse(self.ui.script_passed.isChecked())
        self.assertFalse(self.ui.script_verified.isChecked())

    def test_basic_addition_script(self):
        script_hex = Script.from_human('0x01 0x02 OP_ADD').get_hex()
        expected_steps = [
            ('0', 'PUSHDATA', 'OP_1', '01 was pushed to the stack.'),
            ('1', 'PUSHDATA', 'OP_1 OP_2', '02 was pushed to the stack.'),
            ('2', 'OP_ADD', 'OP_3', '3 (1 + 2) was pushed to the stack.'),
        ]

        self.ui.tx_script.setPlainText(script_hex)
        QTest.mouseClick(self.ui.do_button, Qt.LeftButton)

        model = self.ui.execution_widget.model
        for row, items in enumerate(expected_steps):
            for column, text in enumerate(items):
                data = str(model.data(model.index(row, column)))
                self.assertEqual(text, data)

        # Script passed but was not verified.
        self.assertTrue(self.ui.script_passed.isChecked())
        self.assertFalse(self.ui.script_verified.isChecked())

    def test_verify_p2sh_script_with_valid_pubkey_script(self):
        script_hex = Script.from_human('OP_HASH160 0x8febbed40483661de6958d957412f82deed8e2f7 OP_EQUAL').get_hex()
        expected_steps = [
            # Push signature.
            ('0', 'PUSHDATA', '0x3046022100c66c9cdf4c43609586d15424c54707156e316d88b0a1534c9e6b0d4f311406310221009c0fe51dbc9c4ab7cc25d3fdbeccf6679fe6827f08edf2b4a9f16ee3eb0e438a01', '3046022100c66c9cdf4c43609586d15424c54707156e316d88b0a1534c9e6b0d4f311406310221009c0fe51dbc9c4ab7cc25d3fdbeccf6679fe6827f08edf2b4a9f16ee3eb0e438a01 was pushed to the stack.'),
            # Push redeem script.
            ('1', 'PUSHDATA', '0x3046022100c66c9cdf4c43609586d15424c54707156e316d88b0a1534c9e6b0d4f311406310221009c0fe51dbc9c4ab7cc25d3fdbeccf6679fe6827f08edf2b4a9f16ee3eb0e438a01 0x210338e8034509af564c62644c07691942e0c056752008a173c89f60ab2a88ac2ebfac', '210338e8034509af564c62644c07691942e0c056752008a173c89f60ab2a88ac2ebfac was pushed to the stack.'),
            # OP_HASH160 of public key script.
            ('2', 'OP_HASH160', '0x3046022100c66c9cdf4c43609586d15424c54707156e316d88b0a1534c9e6b0d4f311406310221009c0fe51dbc9c4ab7cc25d3fdbeccf6679fe6827f08edf2b4a9f16ee3eb0e438a01 0x8febbed40483661de6958d957412f82deed8e2f7', '8febbed40483661de6958d957412f82deed8e2f7 (HASH160 of 210338e8034509af564c62644c07691942e0c056752008a173c89f60ab2a88ac2ebfac) was pushed to the stack.'),
            # PUSHDATA of public key script.
            ('3', 'PUSHDATA', '0x3046022100c66c9cdf4c43609586d15424c54707156e316d88b0a1534c9e6b0d4f311406310221009c0fe51dbc9c4ab7cc25d3fdbeccf6679fe6827f08edf2b4a9f16ee3eb0e438a01 0x8febbed40483661de6958d957412f82deed8e2f7 0x8febbed40483661de6958d957412f82deed8e2f7', '8febbed40483661de6958d957412f82deed8e2f7 was pushed to the stack.'),
            # OP_EQUAL of public key script.
            ('4', 'OP_EQUAL', '0x3046022100c66c9cdf4c43609586d15424c54707156e316d88b0a1534c9e6b0d4f311406310221009c0fe51dbc9c4ab7cc25d3fdbeccf6679fe6827f08edf2b4a9f16ee3eb0e438a01 OP_1', '8febbed40483661de6958d957412f82deed8e2f7 == 8febbed40483661de6958d957412f82deed8e2f7, so 01 was pushed to the stack.'),
            # P2SH validation. Push public key from redeem script.
            ('5', 'PUSHDATA', '0x3046022100c66c9cdf4c43609586d15424c54707156e316d88b0a1534c9e6b0d4f311406310221009c0fe51dbc9c4ab7cc25d3fdbeccf6679fe6827f08edf2b4a9f16ee3eb0e438a01 0x0338e8034509af564c62644c07691942e0c056752008a173c89f60ab2a88ac2ebf', '0338e8034509af564c62644c07691942e0c056752008a173c89f60ab2a88ac2ebf was pushed to the stack.'),
            # P2SH validation. OP_CHECKSIG from redeem script.
            ('6', 'OP_CHECKSIG', 'OP_1', 'After CHECKSIG passed, 01 was pushed to the stack.'),
        ]

        self.ui.tx_edit.setPlainText(self.valid_p2sh_tx)
        self.ui.input_idx.setValue(0)
        self.ui.tx_script.setPlainText(script_hex)
        QTest.mouseClick(self.ui.do_button, Qt.LeftButton)

        model = self.ui.execution_widget.model
        for row, items in enumerate(expected_steps):
            for column, text in enumerate(items):
                data = str(model.data(model.index(row, column)))
                self.assertEqual(text, data)

        # Script passed and was verified.
        self.assertTrue(self.ui.script_passed.isChecked())
        self.assertTrue(self.ui.script_verified.isChecked())

    def test_verify_p2sh_script_with_invalid_pubkey_script(self):
        script_hex = Script.from_human('0x00').get_hex()
        expected_steps = [
            # Push signature.
            ('0', 'PUSHDATA', '0x3046022100c66c9cdf4c43609586d15424c54707156e316d88b0a1534c9e6b0d4f311406310221009c0fe51dbc9c4ab7cc25d3fdbeccf6679fe6827f08edf2b4a9f16ee3eb0e438a01', '3046022100c66c9cdf4c43609586d15424c54707156e316d88b0a1534c9e6b0d4f311406310221009c0fe51dbc9c4ab7cc25d3fdbeccf6679fe6827f08edf2b4a9f16ee3eb0e438a01 was pushed to the stack.'),
            # Push redeem script.
            ('1', 'PUSHDATA', '0x3046022100c66c9cdf4c43609586d15424c54707156e316d88b0a1534c9e6b0d4f311406310221009c0fe51dbc9c4ab7cc25d3fdbeccf6679fe6827f08edf2b4a9f16ee3eb0e438a01 0x210338e8034509af564c62644c07691942e0c056752008a173c89f60ab2a88ac2ebfac', '210338e8034509af564c62644c07691942e0c056752008a173c89f60ab2a88ac2ebfac was pushed to the stack.'),
            # Push of public key script.
            ('2', 'PUSHDATA', '0x3046022100c66c9cdf4c43609586d15424c54707156e316d88b0a1534c9e6b0d4f311406310221009c0fe51dbc9c4ab7cc25d3fdbeccf6679fe6827f08edf2b4a9f16ee3eb0e438a01 0x210338e8034509af564c62644c07691942e0c056752008a173c89f60ab2a88ac2ebfac OP_0', '00 was pushed to the stack.'),
        ]

        self.ui.tx_edit.setPlainText(self.valid_p2sh_tx)
        self.ui.input_idx.setValue(0)
        self.ui.tx_script.setPlainText(script_hex)
        QTest.mouseClick(self.ui.do_button, Qt.LeftButton)

        model = self.ui.execution_widget.model
        for row, items in enumerate(expected_steps):
            for column, text in enumerate(items):
                data = str(model.data(model.index(row, column)))
                self.assertEqual(text, data)

        self.assertEqual('scriptPubKey returned false', str(self.ui.execution_widget.error_edit.text()))
        # Script failed and wasn't verified.
        self.assertFalse(self.ui.script_passed.isChecked())
        self.assertFalse(self.ui.script_verified.isChecked())

