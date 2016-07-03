import unittest

from bitcoin.core.scripteval import EvalScript

from hashmal_lib.core.script import Script
from hashmal_lib.core.stack import ScriptExecution
from hashmal_lib.core.transaction import Transaction, TxIn, TxOut, OutPoint

class StackTest(unittest.TestCase):
    def setUp(self):
        super(StackTest, self).setUp()
        self.script_simple_addition = Script.from_asm('0x02 0x03 OP_ADD')
        self.script_push_dup = Script.from_asm('0x70 OP_DUP')

    def test_evaluate_script(self):
        execution = ScriptExecution()
        final_state = execution.evaluate(self.script_simple_addition)[-1]
        self.assertEqual(['\x05'], final_state.stack)

        final_state = execution.evaluate(self.script_push_dup)[-1]
        self.assertEqual(['\x70', '\x70'], final_state.stack)

        self.assertFalse(execution.script_verified)

    def test_python_bitcoinlib_evaluate_script(self):
        stack = []
        EvalScript(stack, self.script_simple_addition, None, 0)
        self.assertEqual(1, len(stack))
        self.assertEqual('\x05', stack[0])

        stack = []
        EvalScript(stack, self.script_push_dup, None, 0)
        self.assertEqual(2, len(stack))
        self.assertEqual('\x70', stack[0])
        self.assertEqual('\x70', stack[1])

    def test_step_script(self):
        # dict of {script: [stackAtStep0, stackAtStep1, ...], ...}
        step_tests = {
            self.script_simple_addition: [
                ['\x02'],
                ['\x02', '\x03'],
                ['\x05']
            ],
            self.script_push_dup: [
                ['\x70'],
                ['\x70', '\x70']
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
        tx_script = Script.from_asm('OP_HASH160 0x8febbed40483661de6958d957412f82deed8e2f7 OP_EQUAL')
        execution = ScriptExecution()

        _ = execution.evaluate(tx_script, txTo=tx, inIdx=0)
        self.assertTrue(execution.script_passed)
        self.assertTrue(execution.script_verified)

        invalid_tx_script = Script.from_asm('OP_HASH160 0x0febbed40483661de6958d957412f82deed8e2f7 OP_EQUAL')
        _ = execution.evaluate(invalid_tx_script, txTo=tx, inIdx=0)
        self.assertFalse(execution.script_passed)
        self.assertFalse(execution.script_verified)

    def test_valid_flow_control(self):
        valid_tests = (
            ('1 1', 'IF IF 1 ELSE 0 ENDIF ENDIF'),
            ('1 0', 'IF IF 1 ELSE 0 ENDIF ENDIF'),
            ('1 1', 'IF IF 1 ELSE 0 ENDIF ELSE IF 0 ELSE 1 ENDIF ENDIF'),
            ('0 0', 'IF IF 1 ELSE 0 ENDIF ELSE IF 0 ELSE 1 ENDIF ENDIF'),
            ('1 0', 'NOTIF IF 1 ELSE 0 ENDIF ENDIF'),
            ('1 1', 'NOTIF IF 1 ELSE 0 ENDIF ENDIF'),
            ('1 0', 'NOTIF IF 1 ELSE 0 ENDIF ELSE IF 0 ELSE 1 ENDIF ENDIF'),
            ('0 1', 'NOTIF IF 1 ELSE 0 ENDIF ELSE IF 0 ELSE 1 ENDIF ENDIF'),
        )
        valid_scripts = []
        for script_sig, script_pubkey in valid_tests:
            script_sig = Script.from_asm(script_sig)
            script_pubkey = Script.from_asm(script_pubkey)
            valid_scripts.append((script_sig, script_pubkey))

        execution = ScriptExecution()

        for script_sig, script_pubkey in valid_scripts:
            tx = build_spending_tx(script_sig, build_crediting_tx(script_pubkey))
            _ = execution.evaluate(script_pubkey, txTo=tx, inIdx=0)
            self.assertTrue(execution.script_passed)
            self.assertTrue(execution.script_verified)

    def test_invalid_flow_control(self):
        invalid_tests = (
            ('0 1', 'IF IF 1 ELSE 0 ENDIF ENDIF'),
            ('0 0', 'IF IF 1 ELSE 0 ENDIF ENDIF'),
            ('1 0', 'IF IF 1 ELSE 0 ENDIF ELSE IF 0 ELSE 1 ENDIF ENDIF'),
            ('0 1', 'IF IF 1 ELSE 0 ENDIF ELSE IF 0 ELSE 1 ENDIF ENDIF'),
            ('0 0', 'NOTIF IF 1 ELSE 0 ENDIF ENDIF'),
            ('0 1', 'NOTIF IF 1 ELSE 0 ENDIF ENDIF'),
            ('1 1', 'NOTIF IF 1 ELSE 0 ENDIF ELSE IF 0 ELSE 1 ENDIF ENDIF'),
            ('0 0', 'NOTIF IF 1 ELSE 0 ENDIF ELSE IF 0 ELSE 1 ENDIF ENDIF'),
        )
        invalid_scripts = []
        for script_sig, script_pubkey in invalid_tests:
            script_sig = Script.from_asm(script_sig)
            script_pubkey = Script.from_asm(script_pubkey)
            invalid_scripts.append((script_sig, script_pubkey))

        execution = ScriptExecution()

        for script_sig, script_pubkey in invalid_scripts:
            tx = build_spending_tx(script_sig, build_crediting_tx(script_pubkey))
            _ = execution.evaluate(script_pubkey, txTo=tx, inIdx=0)
            self.assertFalse(execution.script_passed)
            self.assertFalse(execution.script_verified)


def build_spending_tx(script_sig, credit_tx):
    tx = Transaction(nVersion=1, nLockTime=0)
    txin = TxIn(OutPoint(credit_tx.GetHash(), 0), script_sig)
    tx.vin = [txin]
    txout = TxOut(0, Script())
    tx.vout = [txout]
    return tx

def build_crediting_tx(script_pubkey):
    tx = Transaction(nVersion=1, nLockTime=0)
    txin = TxIn()
    txin.scriptSig = Script.from_asm('0x00 0x00')
    tx.vin.append(txin)
    txout = TxOut(0, script_pubkey)
    tx.vout.append(txout)
    return tx

