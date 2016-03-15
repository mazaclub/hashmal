import unittest

from hashmal_lib.core.serialize import *

txout_value_field = Field('nValue', b'<q', 8, -1, metadata=(FIELD_COIN,))

class FieldTest(unittest.TestCase):
    def test_field_equality(self):
        other_field = Field('nValue', b'<q', 8, -1, metadata=(FIELD_COIN,))
        self.assertEqual(txout_value_field, other_field)

        other_field = Field('nValue', b'<q', 8, -1)
        self.assertNotEqual(txout_value_field, other_field)

    def test_is_coin_amount(self):
        self.assertTrue(txout_value_field.is_coin_amount())

        txout_field_without_metadata = Field('nValue', b'<q', 8, -1)
        self.assertFalse(txout_field_without_metadata.is_coin_amount())
