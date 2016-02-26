import unittest
from collections import OrderedDict

from bitcoin.core import x, lx, b2x, b2lx

from hashmal_lib.plugins.addr_encoder import encode_address, decode_address
from hashmal_lib.plugins.block_analyzer import deserialize_block_or_header
from hashmal_lib.plugins import script_gen
from hashmal_lib.plugins.variables import classify_data
from hashmal_lib.core import chainparams, Script

class VariablesTest(unittest.TestCase):
    def setUp(self):
        chainparams.set_to_preset('Bitcoin')

    def test_data_classification(self):
        test_items = [
            ('', []),
            ('xyz', []),
            ('0x100', ['Hex']),
            ('100', ['Hex']),
            ('"word"', ['Text']),
            ('000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f', ['64 Hex Digits', 'Hex']),
            ('0x000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f', ['64 Hex Digits', 'Hex'])
        ]

        for data, classification in test_items:
            categories = classify_data(data)
            self.assertEqual(set(categories), set(classification), 'Incorrect classification for %s: %s' % (data, categories))

class BlockAnalyzerTest(unittest.TestCase):
    btc_genesis = '0100000000000000000000000000000000000000000000000000000000000000000000003ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a29ab5f49ffff001d1dac2b7c0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff4d04ffff001d0104455468652054696d65732030332f4a616e2f32303039204368616e63656c6c6f72206f6e206272696e6b206f66207365636f6e64206261696c6f757420666f722062616e6b73ffffffff0100f2052a01000000434104678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5fac00000000'
    btc_genesis_header = btc_genesis[:160]
    def setUp(self):
        chainparams.set_to_preset('Bitcoin')

    def test_deserialize_header(self):
        blk, header = deserialize_block_or_header(self.btc_genesis_header)
        self.assertEqual(1, header.nVersion)
        self.assertEqual(b'\x00'*32, header.hashPrevBlock)
        self.assertEqual('4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b', b2lx(header.hashMerkleRoot))
        self.assertEqual(1231006505, header.nTime)
        self.assertEqual(0x1d00ffff, header.nBits)
        self.assertEqual(2083236893, header.nNonce)

        self.assertIs(None, blk)

    def test_deserialize_block(self):
        blk, header = deserialize_block_or_header(self.btc_genesis)
        self.assertEqual(1, header.nVersion)
        self.assertEqual(b'\x00'*32, header.hashPrevBlock)
        self.assertEqual('4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b', b2lx(header.hashMerkleRoot))
        self.assertEqual(1231006505, header.nTime)
        self.assertEqual(0x1d00ffff, header.nBits)
        self.assertEqual(2083236893, header.nNonce)

        self.assertEqual(1, len(blk.vtx))
        self.assertEqual('4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b', b2lx(blk.vtx[0].GetHash()))

        self.assertEqual('000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f', b2lx(blk.GetHash()))
        self.assertEqual('000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f', b2lx(header.GetHash()))

class AddrEncoderTest(unittest.TestCase):
    def test_decode_address(self):
        addr = '1111111111111111111114oLvT2'
        h160, version = decode_address(addr)
        self.assertEqual(b'\x00' * 20, h160)
        self.assertEqual(0, version)

    def test_encode_address(self):
        h160 = b'\x00' * 20
        version = 0
        addr = encode_address(h160, version)
        self.assertEqual('1111111111111111111114oLvT2', str(addr))

class ScriptGenTest(unittest.TestCase):
    def setUp(self):
        super(ScriptGenTest, self).setUp()
        templates = OrderedDict()
        for i in script_gen.known_templates:
            templates[i.name] = i
        self.templates = templates

    def test_create_p2pkh_script(self):
        template = self.templates['Pay-To-Public-Key-Hash Output']

        templates_vars = [
                {'Recipient': '1111111111111111111114oLvT2'},
                {'Recipient': '0' * 40},
                {'Recipient': '0x' + '0' * 40}
        ]

        for template_vars in templates_vars:
            script_out = script_gen.template_to_script(template, template_vars)
            self.assertEqual('OP_DUP OP_HASH160 0x0000000000000000000000000000000000000000 OP_EQUALVERIFY OP_CHECKSIG', script_out)

    def test_create_p2pk_script(self):
        template = self.templates['Pay-To-Public-Key']

        templates_vars = [
                {'Recipient': '0x03569988948d05ddf970d610bc52f0d47fb21ec307a35d3cbeba6d11accfcd3c6a'},
                {'Recipient': '03569988948d05ddf970d610bc52f0d47fb21ec307a35d3cbeba6d11accfcd3c6a'}
        ]

        for template_vars in templates_vars:
            script_out = script_gen.template_to_script(template, template_vars)
            self.assertEqual('0x03569988948d05ddf970d610bc52f0d47fb21ec307a35d3cbeba6d11accfcd3c6a OP_CHECKSIG', script_out)

    def test_op_return_script(self):
        template = self.templates['Null Output']
        template_vars = {'Text': 'testing'}

        script_out = script_gen.template_to_script(template, template_vars)
        self.assertEqual('OP_RETURN 0x74657374696e67', script_out)

    def test_create_p2sh_sig_script(self):
        template = self.templates['Pay-To-Script-Hash Signature Script']

        templates_vars = [
                {'Signature': '0x304402200a156e3e5617cc1d795dfe0c02a5c7dab3941820f194eabd6107f81f25e0519102204d8c585635e03c9137b239893701dc280e25b162011e6474d0c9297d2650b46901',
                'RedeemScript': 'OP_1 0x0208b5b58fd9bf58f1d71682887182e7abd428756264442eec230dd021c193f8d9 0x0245af4f2b1ae21c9310a3211f8d5debb296175e20b3a14b173ff30428e03d502d OP_2 OP_CHECKMULTISIG'},
                {'Signature': '0x304402200a156e3e5617cc1d795dfe0c02a5c7dab3941820f194eabd6107f81f25e0519102204d8c585635e03c9137b239893701dc280e25b162011e6474d0c9297d2650b46901',
                'RedeemScript': '0x51210208b5b58fd9bf58f1d71682887182e7abd428756264442eec230dd021c193f8d9210245af4f2b1ae21c9310a3211f8d5debb296175e20b3a14b173ff30428e03d502d52ae'}
        ]

        for template_vars in templates_vars:
            script_out = script_gen.template_to_script(template, template_vars)
            self.assertEqual('0x304402200a156e3e5617cc1d795dfe0c02a5c7dab3941820f194eabd6107f81f25e0519102204d8c585635e03c9137b239893701dc280e25b162011e6474d0c9297d2650b46901 0x51210208b5b58fd9bf58f1d71682887182e7abd428756264442eec230dd021c193f8d9210245af4f2b1ae21c9310a3211f8d5debb296175e20b3a14b173ff30428e03d502d52ae', script_out)

    def test_is_template_script(self):
        template = self.templates['Pay-To-Public-Key-Hash Output']
        scr = Script.from_human('OP_DUP OP_HASH160 0x0000000000000000000000000000000000000000 OP_EQUALVERIFY OP_CHECKSIG')
        self.assertTrue(script_gen.is_template_script(scr, template))

        scr = Script.from_human('OP_DUP OP_HASH160 0x0000000000000000000000000000000000000000 OP_EQUAL OP_CHECKSIG')
        self.assertFalse(script_gen.is_template_script(scr, template))

        scr = Script.from_human('OP_DUP OP_HASH160 0x00000000000000000000000000000000000000 OP_EQUALVERIFY OP_CHECKSIG')
        self.assertFalse(script_gen.is_template_script(scr, template))

        scr = Script.from_human('0x03569988948d05ddf970d610bc52f0d47fb21ec307a35d3cbeba6d11accfcd3c6a OP_CHECKSIG')
        self.assertTrue(script_gen.is_template_script(scr, self.templates['Pay-To-Public-Key']))

        scr = Script.from_human('0x3045022100f89cffc794d3c43bbaec99f61d0bb2eb72ea1df4be407f375e98f7039caab83d02204b24170189348f82d9af3049aadc1160904e7ef0ba3bc96f3fd241053f0b6de101 0x028f917ac4353d2027ef1be2d02b4dd657ef2ecf67191760c957e79f198b3579c6')
        self.assertTrue(script_gen.is_template_script(scr, self.templates['Signature Script']))

        scr = Script.from_human('0x304402200a156e3e5617cc1d795dfe0c02a5c7dab3941820f194eabd6107f81f25e0519102204d8c585635e03c9137b239893701dc280e25b162011e6474d0c9297d2650b46901 0x51210208b5b58fd9bf58f1d71682887182e7abd428756264442eec230dd021c193f8d9210245af4f2b1ae21c9310a3211f8d5debb296175e20b3a14b173ff30428e03d502d52ae')
        self.assertTrue(script_gen.is_template_script(scr, self.templates['Pay-To-Script-Hash Signature Script']))

        scr = Script.from_human('OP_0 0x304402200a156e3e5617cc1d795dfe0c02a5c7dab3941820f194eabd6107f81f25e0519102204d8c585635e03c9137b239893701dc280e25b162011e6474d0c9297d2650b46901 0x51210208b5b58fd9bf58f1d71682887182e7abd428756264442eec230dd021c193f8d9210245af4f2b1ae21c9310a3211f8d5debb296175e20b3a14b173ff30428e03d502d52ae')
        self.assertTrue(script_gen.is_template_script(scr, self.templates['Pay-To-Script-Hash Multisig Signature Script']))
