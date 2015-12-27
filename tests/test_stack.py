import unittest

import bitcoin
from bitcoin.core.scripteval import EvalScript

from hashmal_lib.core.script import Script, transform_human
from hashmal_lib.core.stack import Stack, ScriptExecution

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

