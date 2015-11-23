import unittest

from bitcoin.core import x, lx, b2x, b2lx

from hashmal_lib.plugins.addr_encoder import encode_address, decode_address
from hashmal_lib.plugins.block_analyzer import deserialize_block_or_header
from hashmal_lib.plugins import script_gen
from hashmal_lib.plugins.variables import classify_data
from hashmal_lib.core import chainparams

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
            ('01000000010000000000000000000000000000000000000000000000000000000000000000ffffffff4d04ffff001d0104455468652054696d65732030332f4a616e2f32303039204368616e63656c6c6f72206f6e206272696e6b206f66207365636f6e64206261696c6f757420666f722062616e6b73ffffffff0100f2052a01000000434104678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5fac00000000', ['Raw Transaction', 'Hex']),
            ('000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f', ['64 Hex Digits', 'Hex']),
            ('0x000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f', ['64 Hex Digits', 'Hex'])
        ]

        for data, classification in test_items:
            categories = classify_data(data)
            self.assertEqual(set(categories), set(classification), 'Incorrect classification for %s' % data)

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
    def test_create_p2pkh_script(self):
        template = None
        for i in script_gen.known_templates:
            if i.name == 'Pay-To-Public-Key-Hash Output':
                template = i
                break
        template_vars = {'recipient': '1111111111111111111114oLvT2'}

        script_out = script_gen.template_to_script(template, template_vars)
        self.assertEqual('OP_DUP OP_HASH160 0x0000000000000000000000000000000000000000 OP_EQUALVERIFY OP_CHECKSIG', script_out)

    def test_op_return_script(self):
        template = None
        for i in script_gen.known_templates:
            if i.name == 'Null Output':
                template = i
                break
        template_vars = {'text': 'testing'}

        script_out = script_gen.template_to_script(template, template_vars)
        self.assertEqual('OP_RETURN 0x74657374696e67', script_out)
