import unittest

import bitcoin
from bitcoin.core.scripteval import EvalScript

from hashmal_lib.core.script import Script, transform_human
from hashmal_lib.core.stack import Stack, ScriptExecution
from hashmal_lib.core.transaction import Transaction

class StackTest(unittest.TestCase):
    def setUp(self):
        super(StackTest, self).setUp()
        self.script_simple_addition = Script.from_human('0x02 0x03 OP_ADD')
        self.script_push_dup = Script.from_human('0x80 OP_DUP')

    def test_evaluate_script(self):
        execution = ScriptExecution()
        final_state = execution.evaluate(self.script_simple_addition)[-1]
        self.assertEqual(['\x05'], final_state.stack)

        final_state = execution.evaluate(self.script_push_dup)[-1]
        self.assertEqual(['\x80', '\x80'], final_state.stack)

        self.assertFalse(execution.script_verified)

    def test_python_bitcoinlib_evaluate_script(self):
        stack = []
        EvalScript(stack, self.script_simple_addition, None, 0)
        self.assertEqual(1, len(stack))
        self.assertEqual('\x05', stack[0])

        stack = []
        EvalScript(stack, self.script_push_dup, None, 0)
        self.assertEqual(2, len(stack))
        self.assertEqual('\x80', stack[0])
        self.assertEqual('\x80', stack[1])

    def test_step_script(self):
        # dict of {script: [stackAtStep0, stackAtStep1, ...], ...}
        step_tests = {
            self.script_simple_addition: [
                ['\x02'],
                ['\x02', '\x03'],
                ['\x05']
            ],
            self.script_push_dup: [
                ['\x80'],
                ['\x80', '\x80']
            ]
        }

        execution = ScriptExecution()
        for my_script, expected_states in step_tests.items():
            steps = execution.evaluate(my_script)
            for i, L in enumerate(expected_states):
                self.assertEqual(L, steps[i].stack)

    def test_p2sh_script_verification(self):
        # P2SH tx from Bitcoin Core tests.
        rawtx = '01000000010001000000000000000000000000000000000000000000000000000000000000000000006e493046022100c66c9cdf4c43609586d15424c54707156e316d88b0a1534c9e6b0d4f311406310221009c0fe51dbc9c4ab7cc25d3fdbeccf6679fe6827f08edf2b4a9f16ee3eb0e438a0123210338e8034509af564c62644c07691942e0c056752008a173c89f60ab2a88ac2ebfacffffffff010000000000000000015100000000'
        tx = Transaction.deserialize(rawtx.decode('hex'))
        tx_script = Script.from_human('OP_HASH160 0x8febbed40483661de6958d957412f82deed8e2f7 OP_EQUAL')
        execution = ScriptExecution()

        _ = execution.evaluate(tx_script, txTo=tx, inIdx=0)
        self.assertTrue(execution.script_passed)
        self.assertTrue(execution.script_verified)

        invalid_tx_script = Script.from_human('OP_HASH160 0x0febbed40483661de6958d957412f82deed8e2f7 OP_EQUAL')
        _ = execution.evaluate(invalid_tx_script, txTo=tx, inIdx=0)
        self.assertFalse(execution.script_passed)
        self.assertTrue(execution.script_verified)
