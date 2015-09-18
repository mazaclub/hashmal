from collections import namedtuple

import transaction

ParamsPreset = namedtuple('ParamsPreset', ('name', 'tx_fields'))

BitcoinPreset = ParamsPreset('Bitcoin',
           [('nVersion', b'<i', 4),
            ('vin', 'inputs', None),
            ('vout', 'outputs', None),
            ('nLockTime', b'<I', 4)])

ClamsPreset = ParamsPreset('Clams',
           [('nVersion', b'<i', 4),
            ('Timestamp', b'<i', 4),
            ('vin', 'inputs', None),
            ('vout', 'outputs', None),
            ('nLockTime', b'<I', 4),
            ('ClamSpeech', 'bytes', None)])

PeercoinPreset = ParamsPreset('Peercoin',
           [('nVersion', b'<i', 4),
            ('Timestamp', b'<i', 4),
            ('vin', 'inputs', None),
            ('vout', 'outputs', None),
            ('nLockTime', b'<I', 4)])

presets_list = [
        BitcoinPreset,
        ClamsPreset,
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
