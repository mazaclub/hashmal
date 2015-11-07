from collections import namedtuple

import transaction

class ParamsPreset(object):
    """Chainparams preset.

    Attributes:
        - name (str): Identifier (e.g. 'Bitcoin').
        - tx_fields (list): Transaction format. List of 4-tuples in the form:
            (attribute_name, fmt, num_bytes, default), where:
                - attribute_name (str): Name of the tx attribute.
                - fmt (str): struct format string, or for special cases,
                    'inputs', 'outputs', or 'bytes'.
                - num_bytes (int): Number of bytes for deserializer to read,
                - default: Default value.

    """
    def __init__(self, **kwargs):
        self.name = ''
        self.tx_fields = []

        for k, v in kwargs.items():
            setattr(self, k, v)

BitcoinPreset = ParamsPreset(
        name='Bitcoin',
        tx_fields=[('nVersion', b'<i', 4, 1),
            ('vin', 'inputs', None, None),
            ('vout', 'outputs', None, None),
            ('nLockTime', b'<I', 4, 0)]
)

ClamsPreset = ParamsPreset(
        name='Clams',
        tx_fields=[('nVersion', b'<i', 4, 1),
            ('Timestamp', b'<i', 4, 0),
            ('vin', 'inputs', None, None),
            ('vout', 'outputs', None, None),
            ('nLockTime', b'<I', 4, 0),
            ('ClamSpeech', 'bytes', None, b'')]
)

FreicoinPreset = ParamsPreset(
        name='Freicoin',
        tx_fields=[('nVersion', b'<i', 4, 1),
            ('vin', 'inputs', None, None),
            ('vout', 'outputs', None, None),
            ('nLockTime', b'<I', 4, 0),
            ('RefHeight', b'<i', 4, 0)]
)

PeercoinPreset = ParamsPreset(
        name='Peercoin',
        tx_fields=[('nVersion', b'<i', 4, 1),
            ('Timestamp', b'<i', 4, 0),
            ('vin', 'inputs', None, None),
            ('vout', 'outputs', None, None),
            ('nLockTime', b'<I', 4, 0)]
)

presets_list = [
        BitcoinPreset,
        ClamsPreset,
        FreicoinPreset,
        PeercoinPreset
]

presets = dict((i.name, i) for i in presets_list)


def get_tx_fields():
    return transaction.transaction_fields

def set_tx_fields(fields):
    """Set the format of transactions.

    This affects all Transaction instances created afterward.
    """
    transaction.transaction_fields = list(fields)

def set_to_preset(name):
    """Reset chainparams to the preset name."""
    # Will throw an exception if name isn't a preset.
    params = presets[name]
    set_tx_fields(params.tx_fields)
