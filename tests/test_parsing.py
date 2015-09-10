import unittest

from hashmal_lib.core.script import Script
from hashmal_lib.script_widget import transform_human

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
            ('1 2 0x89 3', '0x01 0x02 0x89 0x03')
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
