import unittest
from collections import namedtuple

from bitcoin.core.script import *

from hashmal_lib.core.compiler import set_variables_dict
from hashmal_lib.core.script import Script, get_asm_context

# Test item with hex and asm representations.
ScriptItem = namedtuple('ScriptItem', ('hex', 'asm'))

class ScriptTest(unittest.TestCase):
    def setUp(self):
        set_variables_dict({})

    def test_script_from_hex_to_asm(self):
        i = ScriptItem('6a0105', 'OP_RETURN OP_5')
        s = Script(i.hex.decode('hex'))
        self.assertEqual(s.get_asm(), i.asm)

        i = ScriptItem('6a01010131', 'OP_RETURN OP_1 "1"')
        s = Script(i.hex.decode('hex'))
        self.assertEqual(s.get_asm(), i.asm)

        i = ScriptItem('76a91400000000000000000000000000000000000000ff88ac', 'OP_DUP OP_HASH160 0x00000000000000000000000000000000000000ff OP_EQUALVERIFY OP_CHECKSIG')
        s = Script(i.hex.decode('hex'))
        self.assertEqual(s.get_asm(), i.asm)

    def test_script_from_asm_to_asm_and_hex(self):
        i = ScriptItem('525393', 'OP_2 OP_3 OP_ADD')
        s = Script.from_asm(i.asm)
        self.assertEqual(s.get_hex(), i.hex)
        self.assertEqual(s.get_asm(), i.asm)

        i = ScriptItem('0051', 'OP_0 OP_1')
        s = Script.from_asm(i.asm)
        self.assertEqual(s.get_hex(), i.hex)
        self.assertEqual(s.get_asm(), i.asm)

        i = ScriptItem('510474657374', 'OP_1 "test"')
        s = Script.from_asm(i.asm)
        self.assertEqual(s.get_hex(), i.hex)
        self.assertEqual(s.get_asm(), i.asm)

    def test_compatibility_with_cscript(self):
        cs = CScript(['01'.decode('hex'), OP_DUP, OP_HASH160])
        s = Script(cs)
        self.assertEqual(s.get_asm(), 'OP_1 OP_DUP OP_HASH160')


    def test_asm_with_variables(self):
        variables = {
            'numberOne': '0x01',
            'stringOne': '"1"',
        }
        set_variables_dict(variables)
        asm_tests = [
            ('0x02 "test" 0x03', '52047465737453'),
            ('$numberOne 0x01', '5151'),
            ('0x10 $stringOne 0x11', '6001310111'),
            # nonexistent variable
            ('$one 0x05', '04246f6e6555')
        ]
        for text, expected_hex in asm_tests:
            s = Script.from_asm(text)
            self.assertEqual(s.get_hex(), expected_hex)

    def test_number_parsing(self):
        hex_tests = [
            ('5', 'OP_5'),
            ('0a', 'OP_10'),
            ('0x90', '0x90'),
            ('1 2 0x89 3', 'OP_1 OP_2 0x89 OP_3'),
            ('1 0x2 0x89 3', 'OP_1 OP_2 0x89 OP_3'),
            ('140', '0x8c'),
        ]
        for text, expected in hex_tests:
            result = Script.from_asm(text).get_asm()
            self.assertEqual(expected, result)

    def test_implicit_opcodes(self):
        ops_tests = [
            ('ADD', 'OP_ADD'),
            ('0x2 0x5 DUP', 'OP_2 OP_5 OP_DUP'),
            ('2 3 ADD', 'OP_2 OP_3 OP_ADD')
        ]
        for text, expected in ops_tests:
            result = Script.from_asm(text).get_asm()
            self.assertEqual(expected, result)

    def test_string_literals(self):
        str_tests = (
            ('"a"',         '0161'),
            ('2 "2"',       '520132'),
            ('"1 2"',       '03312032'),
            ('0 "1 2"',     '0003312032'),
            ('0 "1 2" 3',   '000331203253'),
            ('"2 3 4"',     '053220332034'),
            ('1 "2 3 4" 5', '5105322033203455'),
        )
        for text, expected in str_tests:
            s = Script.from_asm(text)
            self.assertEqual(expected, s.get_hex())

class TxScriptTest(unittest.TestCase):
    def setUp(self):
        set_variables_dict({})

    def test_txscript(self):
        for text, expected in (
            ('5 + 2;', 'OP_5 OP_2 OP_ADD',),
            ('5 + 2; 6 + 3;', 'OP_5 OP_2 OP_ADD OP_6 OP_3 OP_ADD',),
        ):
            s = Script.from_txscript(text)
            self.assertEqual(expected, s.get_asm())

    def test_variable_substitution(self):
        variables = {
            'numberOne': '0x01',
            'stringOne': '"1"',
        }
        set_variables_dict(variables)

        for text, expected in (
            ('$numberOne + 2;', 'OP_2 OP_1ADD',),
            ('2 + $numberOne;', 'OP_2 OP_1ADD',),
        ):
            s = Script.from_txscript(text)
            self.assertEqual(expected, s.get_asm())

class ContextTest(unittest.TestCase):
    def test_asm_context(self):
        src = '5 OP_2 OP_ADD'
        expected = [
            (0, 1, '5', 'Opcode'),
            (2, 6, 'OP_2', 'Opcode'),
            (7, 13, 'OP_ADD', 'Opcode'),
        ]
        context_tips = get_asm_context(src)
        self.assertEqual(expected, context_tips)

    def test_variables(self):
        src = '5 $myVar OP_ADD'
        expected = [
            (0, 1, '5', 'Opcode'),
            (2, 8, '$myVar', 'Variable'),
            (9, 15, 'OP_ADD', 'Opcode'),
        ]
        context_tips = get_asm_context(src)
        self.assertEqual(expected, context_tips)
