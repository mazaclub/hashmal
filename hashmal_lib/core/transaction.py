import struct

from bitcoin.core import CMutableTransaction, CMutableTxIn, CMutableTxOut, b2x
from bitcoin.core.serialize import ser_read, BytesSerializer, VectorSerializer
from bitcoin.core.script import SIGHASH_ALL, SIGHASH_NONE, SIGHASH_SINGLE, SIGHASH_ANYONECANPAY

transaction_fields = [
    ('nVersion', b'<i', 4, 1),
    ('vin', 'inputs', None, None),
    ('vout', 'outputs', None, None),
    ('nLockTime', b'<I', 4, 0)
]
"""Fields of transactions.

Do not modify this list! Use chainparams.set_tx_fields()
or a preset via chainparams.set_to_preset().
"""

transaction_previous_outpoint_fields = [
    ('hash', 'hash', 32, b'\x00'*32),
    ('n', b'<I', 4, 0xffffffff)
]

transaction_input_fields = [
    ('prevout', 'prevout', None, None),
    ('scriptSig', 'script', None, None),
    ('nSequence', b'<I', 4, 0xffffffff)
]

transaction_output_fields = [
    ('nValue', b'<q', 8, -1),
    ('scriptPubKey', 'script', None, None)
]

sighash_types = {
    'SIGHASH_ALL': SIGHASH_ALL,
    'SIGHASH_NONE': SIGHASH_NONE,
    'SIGHASH_SINGLE': SIGHASH_SINGLE,
    'SIGHASH_ANYONECANPAY': SIGHASH_ANYONECANPAY,
}
sighash_types_by_value = dict((v, k) for k, v in sighash_types.items())

def sig_hash_name(hash_type):
    """Return the name of a sighash type."""
    anyone_can_pay = False
    if hash_type & SIGHASH_ANYONECANPAY:
        anyone_can_pay = True
        hash_type = hash_type & 0x1f
    s = sighash_types_by_value.get(hash_type)
    if not s:
        return None
    if anyone_can_pay:
        s = ' | '.join([s, 'SIGHASH_ANYONECANPAY'])
    return s

def sig_hash_explanation(hash_type):
    """Return a description of a hash type.

    Explanations taken from https://bitcoin.org/en/developer-guide#signature-hash-types.
    """
    explanations = {
        SIGHASH_ALL: 'Signs all the inputs and outputs, protecting everything except the signature scripts against modification.',
        SIGHASH_NONE: 'Signs all of the inputs but none of the outputs, allowing anyone to change where the satoshis are going unless other signatures using other signature hash flags protect the outputs.',
        SIGHASH_SINGLE: 'The only output signed is the one corresponding to this input (the output with the same output index number as this input), ensuring nobody can change your part of the transaction but allowing other signers to change their part of the transaction. The corresponding output must exist or the value "1" will be signed, breaking the security scheme. This input, as well as other inputs, are included in the signature. The sequence numbers of other inputs are not included in the signature, and can be updated.',
        SIGHASH_ALL | SIGHASH_ANYONECANPAY: 'Signs all of the outputs but only this one input, and it also allows anyone to add or remove other inputs, so anyone can contribute additional satoshis but they cannot change how many satoshis are sent nor where they go.',
        SIGHASH_NONE | SIGHASH_ANYONECANPAY: 'Signs only this one input and allows anyone to add or remove other inputs or outputs, so anyone who gets a copy of this input can spend it however they\'d like.',
        SIGHASH_SINGLE | SIGHASH_ANYONECANPAY: 'Signs this one input and its corresponding output. Allows anyone to add or remove other inputs.',
    }
    return explanations.get(hash_type)


class TransactionSerializer(object):
    """Default transaction serialization handler."""
    def stream_deserialize(self, tx, f):
        kwargs = {}
        for attr, fmt, num_bytes, _ in tx.fields:
            self.deserialize_field(tx, kwargs, attr, fmt, num_bytes, f)
        return kwargs

    def stream_serialize(self, tx, f):
        for attr, fmt, num_bytes, _ in tx.fields:
            self.serialize_field(tx, attr, fmt, num_bytes, f)

    def deserialize_field(self, tx, kwargs, attr, fmt, num_bytes, f):
        if fmt not in ['inputs', 'outputs', 'bytes']:
            kwargs[attr] = struct.unpack(fmt, ser_read(f, num_bytes))[0]
        elif fmt == 'inputs':
            kwargs[attr] = VectorSerializer.stream_deserialize(CMutableTxIn, f)
        elif fmt == 'outputs':
            kwargs[attr] = VectorSerializer.stream_deserialize(CMutableTxOut, f)
        elif fmt == 'bytes':
            kwargs[attr] =  BytesSerializer.stream_deserialize(f)

    def serialize_field(self, tx, attr, fmt, num_bytes, f):
        if fmt not in ['inputs', 'outputs', 'bytes']:
            f.write(struct.pack(fmt, getattr(tx, attr)))
        elif fmt == 'inputs':
            VectorSerializer.stream_serialize(CMutableTxIn, tx.vin, f)
        elif fmt == 'outputs':
            VectorSerializer.stream_serialize(CMutableTxOut, tx.vout, f)
        elif fmt == 'bytes':
            BytesSerializer.stream_serialize(getattr(tx, attr), f)

class Transaction(CMutableTransaction):
    """Cryptocurrency transaction.

    Subclassed from CMutableTransaction so that its fields
    (e.g. nVersion, nLockTime) can be altered.

    Use chainparams.set_tx_fields() to modify the global
    transaction_fields list.

    For the most common purposes, chainparams.set_to_preset()
    can be used instead.
    """
    serializer_class = TransactionSerializer
    def __init__(self, vin=None, vout=None, locktime=0, version=1, fields=None, kwfields=None):
        super(Transaction, self).__init__(vin, vout, locktime, version)
        if kwfields is None: kwfields = {}
        for k, v in kwfields.items():
            setattr(self, k, v)
        self.set_serialization(fields)

    @classmethod
    def set_serializer_class(cls, ser_class):
        cls.serializer_class = ser_class

    def set_serialization(self, fields=None):
        """Set the serialization format.

        This allows transactions to exist that do not comply with the
        global transaction_fields list.
        """
        self.serializer_class = Transaction.serializer_class
        if fields is None:
            fields = list(transaction_fields)
        self.fields = fields
        for name, _, _, default in self.fields:
            try:
                getattr(self, name)
            except AttributeError:
                setattr(self, name, default)

    @classmethod
    def stream_deserialize(cls, f):
        self = cls()
        kwargs = self.serializer_class().stream_deserialize(self, f)
        for k, v in kwargs.items():
            setattr(self, k, v)
        return self

    def stream_serialize(self, f):
        self.serializer_class().stream_serialize(self, f)

    @classmethod
    def from_tx(cls, tx):
        if not issubclass(tx.__class__, Transaction):
            return super(Transaction, cls).from_tx(tx)
        else:

            kwfields = {}
            for attr, _, _, default in transaction_fields:
                if attr in ['vin', 'vout']:
                    continue
                if hasattr(tx, attr):
                    kwfields[attr] = getattr(tx, attr)


            vin = [CMutableTxIn.from_txin(txin) for txin in tx.vin]
            vout = [CMutableTxOut.from_txout(txout) for txout in tx.vout]
            kwfields['vin'] = vin
            kwfields['vout'] = vout
            return cls(kwfields=kwfields)

    def as_hex(self):
        return b2x(self.serialize())

# Known serializer classes

class ClamsTxSerializer(TransactionSerializer):
    """Clams transaction serializer.

    Required because transaction serialization depends on transaction version.
    """
    def deserialize_field(self, tx, kwargs, attr, fmt, num_bytes, f):
        if attr != 'ClamSpeech':
            return super(ClamsTxSerializer, self).deserialize_field(tx, kwargs, attr, fmt, num_bytes, f)
        if kwargs['nVersion'] > 1:
            return super(ClamsTxSerializer, self).deserialize_field(tx, kwargs, attr, fmt, num_bytes, f)

    def serialize_field(self, tx, attr, fmt, num_bytes, f):
        if attr != 'ClamSpeech':
            return super(ClamsTxSerializer, self).serialize_field(tx, attr, fmt, num_bytes, f)
        if tx.nVersion > 1:
            return super(ClamsTxSerializer, self).serialize_field(tx, attr, fmt, num_bytes, f)

