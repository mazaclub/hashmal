import unittest
from collections import namedtuple

import bitcoin
from bitcoin.core.script import *

from hashmal_lib.core.script import Script, transform_human

# Test item with hex and human representations.
ScriptItem = namedtuple('ScriptItem', ('hex', 'human'))

class ScriptTest(unittest.TestCase):

    def test_script_from_hex_to_human(self):
        i = ScriptItem('6a0105', 'OP_RETURN 0x05')
        s = Script(i.hex.decode('hex'))
        self.assertEqual(s.get_human(), i.human)

        i = ScriptItem('6a01010131', 'OP_RETURN 0x01 1')
        s = Script(i.hex.decode('hex'))
        self.assertEqual(s.get_human(), i.human)

        i = ScriptItem('76a914000000000000000000000000000000000000000088ac', 'OP_DUP OP_HASH160 0x0000000000000000000000000000000000000000 OP_EQUALVERIFY OP_CHECKSIG')
        s = Script(i.hex.decode('hex'))
        self.assertEqual(s.get_human(), i.human)

    def test_script_from_human_to_human_and_hex(self):
        i = ScriptItem('0102010393', '0x02 0x03 OP_ADD')
        s = Script.from_human(i.human)
        self.assertEqual(s.get_hex(), i.hex)
        self.assertEqual(s.get_human(), i.human)

        i = ScriptItem('51', 'OP_1')
        s = Script.from_human(i.human)
        self.assertEqual(s.get_hex(), i.hex)
        self.assertEqual(s.get_human(), i.human)

    def test_compatibility_with_cscript(self):
        cs = CScript(['01'.decode('hex'), OP_DUP, OP_HASH160])
        s = Script(cs)
        self.assertEqual(s.get_human(), '0x01 OP_DUP OP_HASH160')


class ParsingTest(unittest.TestCase):

    def test_transform_human(self):
        variables = {
            'numberOne': '0x01',
            'stringOne': '"1"',
        }
        human_tests = [
            ('0x02 "test" 0x03', '010204746573740103'),
            ('$numberOne 0x01', '01010101'),
            ('0x10 $stringOne 0x11', '011001310111'),
            # nonexistent variable
            ('$one 0x05', '04246f6e650105')
        ]
        for text, expected_hex in human_tests:
            txt, _ = transform_human(text, variables)
            s = Script.from_human(txt)
            self.assertEqual(s.get_hex(), expected_hex)

    def test_hex_transform(self):
        hex_tests = [
            ('5', '0x05'),
            ('0x20', '0x20'),
            ('1 2 0x89 3', '0x01 0x02 0x89 0x03'),
            ('1 0x2 0x89 3', '0x01 0x02 0x89 0x03')
        ]
        for text, expected in hex_tests:
            result, _ = transform_human(text)
            self.assertEqual(expected, result)

    def test_variable_transform(self):
        variables = {'seven': '0x7'}
        scr = '$seven 0x07 OP_EQUAL'
        self.assertEqual('0x07 0x07 OP_EQUAL', transform_human(scr, variables)[0])

    def test_opcode_transform(self):
        ops_tests = [
            ('ADD', 'OP_ADD'),
            ('0x2 0x5 DUP', '0x02 0x05 OP_DUP'),
            ('1 2 ADD', '0x01 0x02 OP_ADD')
        ]
        for text, expected in ops_tests:
            result, _ = transform_human(text)
            self.assertEqual(expected, result)

    def test_string_literal_transform(self):
        str_tests = [
            ('1 "1"', '0x01 0x31', '0x01 1'),
            ('test 123 "123"', 'test 0x0123 0x313233', 'test 0x0123 123')
        ]
        for text, expected, human in str_tests:
            result, _ = transform_human(text)
            self.assertEqual(expected, result)
            self.assertEqual(Script.from_human(result).get_human(), human)
