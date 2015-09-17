import unittest

from hashmal_lib.core import chainparams, transaction

maza_raw_tx = '010000000279fd18c19fad871077a757804561e11d722296b68e6afd4d2a16c06d9c9a30b8000000006a4730440220380bf06cf81a43a9d425b6d34be7315e9ebb396081ecb94e291a906e6b9e36a6022060458349b8592a1d7133e77756a011e2d8e5749b67a2a94f3a5488e81458c00c0121024370144b106ab92b9bdf2cf2de6eb173f4656e581d27ed2c0f77479db338fc21ffffffff551d183e1f98a5a5e7f5b296ba6d77729babb7f90aaabe6b8eb128c624e10fce000000006b483045022100e1d89636d53334e29703dff014323cb8c9836e2b77f666477f185a1882cc2c7a02201d3af8352b2bf338b79a709a30fdf4e9c5166487b7af15fb48a85eac2e43c722012103c4e79c99c1cfcce534b4715ec9a8f6ccf735f050a58caf7b6126ebe4691aa480ffffffff025a232d00000000001976a9144fd5ae7260db3ddc49d058e6f200a486058c666288ac00127a00000000001976a9149d0d296ad8e00e57f90670215d9276765ba1c81788ac00000000'.decode('hex')

clams_raw_tx = '02000000404afb5501526139de11764d06f5110deeb1f9fd4aefec059ccf36135ad888edda689c1abc010000004948304502210091349ad30f0cf706a385b0bca04aa28f9f033228083a662b45d58e09df4058cb02200e2f17652b72ec514d174977fb2b799b5017bdf267fa557b0a7e7c429c4633ac01ffffffff0200000000000000000080a4607f000000002321037bedfabb451755cf6061636c8004dba32cb95095ba8cba61de236a70f95e3d2aac000000003045787072657373696f6e206f6620506f6c69746963616c2046726565646f6d3a204a65776973682066656d696e69736d'.decode('hex')

ppc_raw_tx = '0100000058e4615501a367e883a383167e64c84e9c068ba5c091672e434784982f877eede589cb7e53000000006a473044022043b9aee9187effd7e6c7bc444b09162570f17e36b4a9c02cf722126cc0efa3d502200b3ba14c809fa9a6f7f835cbdbbb70f2f43f6b30beaf91eec6b8b5981c80cea50121025edf500f18f9f2b3f175f823fa996fbb2ec52982a9aeb1dc2e388a651054fb0fffffffff0257be0100000000001976a91495efca2c6a6f0e0f0ce9530219b48607a962e77788ac45702000000000001976a914f28abfb465126d6772dcb4403b9e1ad2ea28a03488ac00000000'.decode('hex')

bitcoin_fields = [
    ('nVersion', b'<i', 4),
    ('vin', 'inputs', None),
    ('vout', 'outputs', None),
    ('nLockTime', b'<I', 4)
]

clams_fields = list(bitcoin_fields)
clams_fields.insert(1, ('Timestamp', b'<i', 4))
clams_fields.append( ('ClamSpeech', 'bytes', None) )

peercoin_fields = list(bitcoin_fields)
peercoin_fields.insert(1, ('Timestamp', b'<i', 4))

class ChainparamsTest(unittest.TestCase):
    def setUp(self):
        super(ChainparamsTest, self).setUp()
        chainparams.set_tx_fields(bitcoin_fields)

    def test_bitcoin_fields(self):
        tx = transaction.Transaction.deserialize(maza_raw_tx)
        self.assertEqual(bitcoin_fields, tx.fields)
        self.assertEqual(maza_raw_tx, tx.serialize())

    def test_clams_fields(self):
        chainparams.set_tx_fields(clams_fields)
        tx = transaction.Transaction.deserialize(clams_raw_tx)
        self.assertNotEqual(bitcoin_fields, tx.fields)
        self.assertIn(('ClamSpeech', 'bytes', None), tx.fields)
        self.assertEqual(clams_raw_tx, tx.serialize())

    def test_peercoin_fields(self):
        chainparams.set_tx_fields(peercoin_fields)
        tx = transaction.Transaction.deserialize(ppc_raw_tx)
        self.assertNotEqual(bitcoin_fields, tx.fields)
        self.assertIn(('Timestamp', b'<i', 4), tx.fields)
        self.assertEqual(ppc_raw_tx, tx.serialize())

    def test_change_tx_fields(self):
        tx = transaction.Transaction.deserialize(maza_raw_tx)

        chainparams.set_tx_fields(peercoin_fields)
        tx2 = transaction.Transaction.deserialize(ppc_raw_tx)

        self.assertNotEqual(tx.fields, tx2.fields)

    def test_preset_chainparams(self):
        chainparams.set_to_preset('Bitcoin')
        tx = transaction.Transaction.deserialize(maza_raw_tx)
        self.assertRaises(Exception, transaction.Transaction.deserialize, clams_raw_tx)
        self.assertRaises(Exception, transaction.Transaction.deserialize, ppc_raw_tx)

        chainparams.set_to_preset('Clams')
        tx = transaction.Transaction.deserialize(clams_raw_tx)
        self.assertRaises(Exception, transaction.Transaction.deserialize, maza_raw_tx)
        self.assertRaises(Exception, transaction.Transaction.deserialize, ppc_raw_tx)

        chainparams.set_to_preset('Peercoin')
        tx = transaction.Transaction.deserialize(ppc_raw_tx)
        self.assertRaises(Exception, transaction.Transaction.deserialize, clams_raw_tx)
        self.assertRaises(Exception, transaction.Transaction.deserialize, maza_raw_tx)
