import unittest

from bitcoin.core import COutPoint, CTxIn, CTxOut, CTransaction, x, lx, b2x, b2lx

from hashmal_lib.core import chainparams, Transaction, BlockHeader, Block

maza_raw_tx = '010000000279fd18c19fad871077a757804561e11d722296b68e6afd4d2a16c06d9c9a30b8000000006a4730440220380bf06cf81a43a9d425b6d34be7315e9ebb396081ecb94e291a906e6b9e36a6022060458349b8592a1d7133e77756a011e2d8e5749b67a2a94f3a5488e81458c00c0121024370144b106ab92b9bdf2cf2de6eb173f4656e581d27ed2c0f77479db338fc21ffffffff551d183e1f98a5a5e7f5b296ba6d77729babb7f90aaabe6b8eb128c624e10fce000000006b483045022100e1d89636d53334e29703dff014323cb8c9836e2b77f666477f185a1882cc2c7a02201d3af8352b2bf338b79a709a30fdf4e9c5166487b7af15fb48a85eac2e43c722012103c4e79c99c1cfcce534b4715ec9a8f6ccf735f050a58caf7b6126ebe4691aa480ffffffff025a232d00000000001976a9144fd5ae7260db3ddc49d058e6f200a486058c666288ac00127a00000000001976a9149d0d296ad8e00e57f90670215d9276765ba1c81788ac00000000'.decode('hex')

clams_raw_tx = '02000000404afb5501526139de11764d06f5110deeb1f9fd4aefec059ccf36135ad888edda689c1abc010000004948304502210091349ad30f0cf706a385b0bca04aa28f9f033228083a662b45d58e09df4058cb02200e2f17652b72ec514d174977fb2b799b5017bdf267fa557b0a7e7c429c4633ac01ffffffff0200000000000000000080a4607f000000002321037bedfabb451755cf6061636c8004dba32cb95095ba8cba61de236a70f95e3d2aac000000003045787072657373696f6e206f6620506f6c69746963616c2046726565646f6d3a204a65776973682066656d696e69736d'.decode('hex')

ppc_raw_tx = '0100000058e4615501a367e883a383167e64c84e9c068ba5c091672e434784982f877eede589cb7e53000000006a473044022043b9aee9187effd7e6c7bc444b09162570f17e36b4a9c02cf722126cc0efa3d502200b3ba14c809fa9a6f7f835cbdbbb70f2f43f6b30beaf91eec6b8b5981c80cea50121025edf500f18f9f2b3f175f823fa996fbb2ec52982a9aeb1dc2e388a651054fb0fffffffff0257be0100000000001976a91495efca2c6a6f0e0f0ce9530219b48607a962e77788ac45702000000000001976a914f28abfb465126d6772dcb4403b9e1ad2ea28a03488ac00000000'.decode('hex')

bitcoin_fields = [
    ('nVersion', b'<i', 4, 1),
    ('vin', 'inputs', None, None),
    ('vout', 'outputs', None, None),
    ('nLockTime', b'<I', 4, 0)
]

clams_fields = list(bitcoin_fields)
clams_fields.insert(1, ('Timestamp', b'<i', 4, 0))
clams_fields.append( ('ClamSpeech', 'bytes', None, b'') )

peercoin_fields = list(bitcoin_fields)
peercoin_fields.insert(1, ('Timestamp', b'<i', 4, 0))


class TransactionTest(unittest.TestCase):
    def setUp(self):
        super(TransactionTest, self).setUp()
        chainparams.set_to_preset('Bitcoin')

    def test_bitcoin_fields(self):
        tx = Transaction.deserialize(maza_raw_tx)
        self.assertEqual(bitcoin_fields, tx.fields)
        self.assertEqual(maza_raw_tx, tx.serialize())

    def test_clams_fields(self):
        chainparams.set_tx_fields(clams_fields)
        tx = Transaction.deserialize(clams_raw_tx)
        self.assertNotEqual(bitcoin_fields, tx.fields)
        self.assertIn(('ClamSpeech', 'bytes', None, b''), tx.fields)
        self.assertEqual(clams_raw_tx, tx.serialize())

    def test_peercoin_fields(self):
        chainparams.set_tx_fields(peercoin_fields)
        tx = Transaction.deserialize(ppc_raw_tx)
        self.assertNotEqual(bitcoin_fields, tx.fields)
        self.assertIn(('Timestamp', b'<i', 4, 0), tx.fields)
        self.assertEqual(ppc_raw_tx, tx.serialize())

    def test_change_tx_fields(self):
        tx = Transaction.deserialize(maza_raw_tx)

        chainparams.set_tx_fields(peercoin_fields)
        tx2 = Transaction.deserialize(ppc_raw_tx)

        self.assertNotEqual(tx.fields, tx2.fields)
        self.assertEqual(1, len(tx2.fields) - len(tx.fields))

    def test_preset_chainparams(self):
        chainparams.set_to_preset('Bitcoin')
        tx = Transaction.deserialize(maza_raw_tx)
        self.assertRaises(Exception, Transaction.deserialize, clams_raw_tx)
        self.assertRaises(Exception, Transaction.deserialize, ppc_raw_tx)

        chainparams.set_to_preset('Clams')
        tx = Transaction.deserialize(clams_raw_tx)
        self.assertRaises(Exception, Transaction.deserialize, maza_raw_tx)
        self.assertRaises(Exception, Transaction.deserialize, ppc_raw_tx)

        chainparams.set_to_preset('Peercoin')
        tx = Transaction.deserialize(ppc_raw_tx)
        self.assertRaises(Exception, Transaction.deserialize, clams_raw_tx)
        self.assertRaises(Exception, Transaction.deserialize, maza_raw_tx)

    def test_init_with_field_keyword_args(self):
        ins = (
            CTxIn(COutPoint(lx('537ecb89e5ed7e872f988447432e6791c0a58b069c4ec8647e1683a383e867a3'), 0),
                  x('473044022043b9aee9187effd7e6c7bc444b09162570f17e36b4a9c02cf722126cc0efa3d502200b3ba14c809fa9a6f7f835cbdbbb70f2f43f6b30beaf91eec6b8b5981c80cea50121025edf500f18f9f2b3f175f823fa996fbb2ec52982a9aeb1dc2e388a651054fb0f'))
        )
        outs = (
            CTxOut(114263, x('76a91495efca2c6a6f0e0f0ce9530219b48607a962e77788ac')),
            CTxOut(2125893, x('76a914f28abfb465126d6772dcb4403b9e1ad2ea28a03488ac'))
        )
        fields_data = {'Timestamp': 1432478808}
        tx = Transaction(ins, outs, 0, 2, peercoin_fields, fields_data)
        self.assertEqual(tx.fields, peercoin_fields)
        self.assertEqual(tx.Timestamp, 1432478808)

    def test_from_tx_with_transaction_argument(self):
        tx = Transaction()
        chainparams.set_to_preset('Peercoin')
        self.assertRaises(AttributeError, getattr, tx, 'Timestamp')
        tx2 = Transaction.from_tx(tx)
        self.assertIsNot(tx, tx2)
        self.assertEqual(tx2.Timestamp, 0)

    def test_from_tx_with_ctransaction_argument(self):
        tx = CTransaction()
        chainparams.set_to_preset('Peercoin')
        self.assertRaises(AttributeError, getattr, tx, 'Timestamp')
        tx2 = Transaction.from_tx(tx)
        self.assertIs(tx.__class__, CTransaction)
        self.assertEqual(tx2.Timestamp, 0)

    def test_serialize_as_hex(self):
        tx = Transaction.deserialize(maza_raw_tx)
        self.assertEqual(maza_raw_tx.encode('hex'), tx.as_hex())


bitcoin_raw_header = '0100000000000000000000000000000000000000000000000000000000000000000000003ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a29ab5f49ffff001d1dac2b7c'.decode('hex')

bitcoin_header_fields = [
    ('nVersion', b'<i', 4, 1),
    ('hashPrevBlock', 'bytes', 32, b'\x00'*32),
    ('hashMerkleRoot', 'bytes', 32, b'\x00'*32),
    ('nTime', b'<I', 4, 0),
    ('nBits', b'<I', 4, 0),
    ('nNonce', b'<I', 4, 0)
]

class BlockHeaderTest(unittest.TestCase):
    def setUp(self):
        super(BlockHeaderTest, self).setUp()
        chainparams.set_to_preset('Bitcoin')

    def test_bitcoin_fields(self):
        self.assertEqual(BlockHeader.header_length(), 80)
        header = BlockHeader.deserialize(bitcoin_raw_header)
        self.assertEqual(bitcoin_header_fields, header.fields)

    def test_serialize_as_hex(self):
        header = BlockHeader.deserialize(bitcoin_raw_header)
        self.assertEqual(bitcoin_raw_header.encode('hex'), header.as_hex())

bitcoin_raw_block = '0100000000000000000000000000000000000000000000000000000000000000000000003ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a29ab5f49ffff001d1dac2b7c0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff4d04ffff001d0104455468652054696d65732030332f4a616e2f32303039204368616e63656c6c6f72206f6e206272696e6b206f66207365636f6e64206261696c6f757420666f722062616e6b73ffffffff0100f2052a01000000434104678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5fac00000000'.decode('hex')

clams_raw_block = '07000000e4f9a8c328439e9e4aafe6090ef46238ea9b2fe8d2cbf17fce881a51b9c8ac2718f7ce4ce75ebc5ac6c2d872f9c7098f1601e7300cc55aab28ed04b54e324ed240695956daeb001b00000000020200000040695956010000000000000000000000000000000000000000000000000000000000000000ffffffff0403126f0bffffffff010000000000000000000000000000020000004069595601c07c8709388cb589e8c9db523d9619d3dcedf3b338178cbaa6343fb641a4e8310100000048473044022034e7215232df91f5d3c8bec4da07ea230db94de55ac6ef451afdbf6e46693bf6022007196949a85cebce1dc00e68d21168ae4bfe712e4875a6a3eb7aa3cfcd89754101ffffffff030000000000000000004000b14f000000002321037bedfabb451755cf6061636c8004dba32cb95095ba8cba61de236a70f95e3d2aac80867353000000002321037bedfabb451755cf6061636c8004dba32cb95095ba8cba61de236a70f95e3d2aac000000003445787072657373696f6e206f6620506f6c69746963616c2046726565646f6d3a20536570617261746973742066656d696e69736d473045022100b4e1b24eff6f0c7945c1cabc2d37ac88df861fe37f9bc22ac3c8594bac58f6f9022044e8dfde90dc28d06ba17d5c2b9b3a65ad1cdc03c3e0f8f5655d1f5b9c8cfa0b'.decode('hex')

class BlockTest(unittest.TestCase):
    def setUp(self):
        super(BlockTest, self).setUp()
        chainparams.set_to_preset('Bitcoin')

    def test_get_header(self):
        blk = Block.deserialize(bitcoin_raw_block)
        header = blk.get_header()
        self.assertEqual(bitcoin_raw_header, header.serialize())

    def test_serialize_as_hex(self):
        blk = Block.deserialize(bitcoin_raw_block)
        self.assertEqual(bitcoin_raw_block.encode('hex'), blk.as_hex())

    def test_clams_fields(self):
        chainparams.set_to_preset('Clams')
        blk = Block.deserialize(clams_raw_block)
        self.assertEqual(clams_raw_block.encode('hex'), blk.as_hex())
        self.assertEqual('3045022100b4e1b24eff6f0c7945c1cabc2d37ac88df861fe37f9bc22ac3c8594bac58f6f9022044e8dfde90dc28d06ba17d5c2b9b3a65ad1cdc03c3e0f8f5655d1f5b9c8cfa0b', b2x(blk.blockSig))
