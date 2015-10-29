import unittest

import bitcoin
from bitcoin.core.scripteval import EvalScript

from hashmal_lib.core.script import Script, transform_human
from hashmal_lib.core.stack import Stack

class StackTest(unittest.TestCase):
    def setUp(self):
        super(StackTest, self).setUp()
        self.script_simple_addition = Script.from_human('0x02 0x03 OP_ADD')
        self.script_push_dup = Script.from_human('0x80 OP_DUP')

    def test_evaluate_script(self):
        my_stack = Stack()
        my_stack.set_script(self.script_simple_addition)
        stack = my_stack.evaluate()
        self.assertEqual(1, len(stack))
        self.assertEqual('\x05', stack[0])

        my_stack.set_script(self.script_push_dup)
        stack = my_stack.evaluate()
        self.assertEqual(2, len(stack))
        self.assertEqual('\x80', stack[0])
        self.assertEqual('\x80', stack[1])

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

        my_stack = Stack()
        for my_script, expected_states in step_tests.items():
            my_stack.set_script(my_script)
            iterator = my_stack.step()
            for i in expected_states:
                stack_state, _ = iterator.next()
                self.assertEqual(i, stack_state)

