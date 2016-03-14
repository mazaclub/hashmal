import unittest

from PyQt4.QtTest import QTest

from bitcoin.core import b2lx
from hashmal_lib.core import chainparams
from hashmal_lib.core.block import deserialize_block_or_header
from hashmal_lib.plugins import block_analyzer
from .gui_test import PluginTest

btc_genesis = '0100000000000000000000000000000000000000000000000000000000000000000000003ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a29ab5f49ffff001d1dac2b7c0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff4d04ffff001d0104455468652054696d65732030332f4a616e2f32303039204368616e63656c6c6f72206f6e206272696e6b206f66207365636f6e64206261696c6f757420666f722062616e6b73ffffffff0100f2052a01000000434104678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5fac00000000'
btc_genesis_header = btc_genesis[:160]

class BlockAnalyzerTest(unittest.TestCase):
    def setUp(self):
        super(BlockAnalyzerTest, self).setUp()
        chainparams.set_to_preset('Bitcoin')

    def test_deserialize_genesis_block_header(self):
        blk, header = deserialize_block_or_header(btc_genesis_header)
        self.assertEqual(1, header.nVersion)
        self.assertEqual(b'\x00'*32, header.hashPrevBlock)
        self.assertEqual('4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b', b2lx(header.hashMerkleRoot))
        self.assertEqual(1231006505, header.nTime)
        self.assertEqual(0x1d00ffff, header.nBits)
        self.assertEqual(2083236893, header.nNonce)

        self.assertIs(None, blk)

    def test_deserialize_genesis_block(self):
        blk, header = deserialize_block_or_header(btc_genesis)
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

class BlockAnalyzerGUITest(PluginTest):
    plugin_name = 'Block Analyzer'
    def setUp(self):
        super(BlockAnalyzerGUITest, self).setUp()
        self.ui.raw_block_edit.clear()
        self.ui.block_widget.clear()
        self._set_chainparams('Bitcoin')

    def test_deserialize_genesis_block_header(self):
        self.ui.raw_block_edit.setPlainText(btc_genesis_header)

        expected_header_items = [
            '1',
            '00'*32,
            '4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b',
            '1231006505',
            '486604799',
            '2083236893',
        ]

        model = self.ui.block_widget.header_widget.model
        for row, text in enumerate(expected_header_items):
            data = model.data(model.index(row, 0))
            self.assertEqual(text, data)

    def test_deserialize_genesis_block(self):
        self.ui.raw_block_edit.setPlainText(btc_genesis)

        expected_header_items = [
            '1',
            '00'*32,
            '4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b',
            '1231006505',
            '486604799',
            '2083236893',
        ]

        expected_tx_items = [
            '4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b',
        ]

        model = self.ui.block_widget.header_widget.model
        for row, text in enumerate(expected_header_items):
            data = model.data(model.index(row, 0))
            self.assertEqual(text, data)

        model = self.ui.block_widget.txs_widget.model
        for row, text in enumerate(expected_tx_items):
            item = model.item(row, 0)
            data = str(item.text())
            self.assertEqual(text, data)
