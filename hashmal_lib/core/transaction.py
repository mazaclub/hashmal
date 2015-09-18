import struct

import bitcoin
from bitcoin.core import CMutableTransaction, CTxIn, CTxOut
from bitcoin.core.serialize import ser_read, BytesSerializer, VectorSerializer

transaction_fields = [
    ('nVersion', b'<i', 4),
    ('vin', 'inputs', None),
    ('vout', 'outputs', None),
    ('nLockTime', b'<I', 4)
]
"""Fields of transactions.

Do not modify this list! Use chainparams.set_tx_fields()
or a preset via chainparams.set_to_preset().
"""

class Transaction(CMutableTransaction):
    """Cryptocurrency transaction.

    Subclassed from CMutableTransaction so that its fields
    (e.g. nVersion, nLockTime) can be altered.

    Use chainparams.set_tx_fields() to modify the global
    transaction_fields list.

    For the most common purposes, chainparams.set_to_preset()
    can be used instead.
    """
    def __init__(self, vin=None, vout=None, locktime=0, version=1, fields=None):
        super(Transaction, self).__init__(vin, vout, locktime, version)
        self.set_serialization(fields)

    def set_serialization(self, fields=None):
        """Set the serialization format.

        This allows transactions to exist that do not comply with the
        global transaction_fields list.
        """
        if fields is None:
            fields = list(transaction_fields)
        self.fields = fields
        for name, _, _ in self.fields:
            try:
                getattr(self, name)
            except AttributeError:
                setattr(self, name, None)

    @classmethod
    def stream_deserialize(cls, f):
        self = cls()
        for attr, fmt, num_bytes in self.fields:
            if fmt not in ['inputs', 'outputs', 'bytes']:
                setattr(self, attr, struct.unpack(fmt, ser_read(f, num_bytes))[0])
            elif fmt == 'inputs':
                setattr(self, attr, VectorSerializer.stream_deserialize(CTxIn, f))
            elif fmt == 'outputs':
                setattr(self, attr, VectorSerializer.stream_deserialize(CTxOut, f))
            elif fmt == 'bytes':
                setattr(self, attr, BytesSerializer.stream_deserialize(f))
        return self

    def stream_serialize(self, f):
        for attr, fmt, num_bytes in self.fields:
            if fmt not in ['inputs', 'outputs', 'bytes']:
                f.write(struct.pack(fmt, getattr(self, attr)))
            elif fmt == 'inputs':
                VectorSerializer.stream_serialize(CTxIn, self.vin, f)
            elif fmt == 'outputs':
                VectorSerializer.stream_serialize(CTxOut, self.vout, f)
            elif fmt == 'bytes':
                BytesSerializer.stream_serialize(getattr(self, attr), f)

