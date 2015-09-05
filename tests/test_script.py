import unittest

import bitcoin
from bitcoin.core.script import *

from hashmal_lib.core.script import Script


class ScriptTest(unittest.TestCase):

    def test_script_from_hex(self):
        s = Script('6a0105'.decode('hex'))
        self.assertEqual(s.get_human(), 'OP_RETURN 0x05')

        s = Script('76a914000000000000000000000000000000000000000088ac'.decode('hex'))
        self.assertEqual(s.get_human(), 'OP_DUP OP_HASH160 0x0000000000000000000000000000000000000000 OP_EQUALVERIFY OP_CHECKSIG')

    def test_script_from_human(self):
        s = Script.from_human('0x02 0x03 OP_ADD')
        self.assertEqual(s.get_hex(), '0102010393')

        s = Script.from_human('OP_1')
        self.assertEqual(s.get_hex(), '51')

    def test_compatibility_with_cscript(self):
        cs = CScript(['01'.decode('hex'), OP_DUP, OP_HASH160])
        s = Script(cs)
        self.assertEqual(s.get_human(), '0x01 OP_DUP OP_HASH160')

