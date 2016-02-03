import unittest

from hashmal_lib.core import utils

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
