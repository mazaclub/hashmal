import struct
from io import BytesIO

from bitcoin.core import CMutableTransaction, CMutableTxIn, CMutableTxOut, CMutableOutPoint, b2x
from bitcoin.core.serialize import ser_read, BytesSerializer, VectorSerializer, VarIntSerializer
from bitcoin.core.script import SIGHASH_ALL, SIGHASH_NONE, SIGHASH_SINGLE, SIGHASH_ANYONECANPAY

from script import Script
from serialize import *

transaction_fields = [
    Field('nVersion', b'<i', 4, 1),
    Field('vin', 'inputs', None, None),
    Field('vout', 'outputs', None, None),
    Field('nLockTime', b'<I', 4, 0)
]
"""Fields of transactions.

Do not modify this list! Use chainparams.set_tx_fields()
or a preset via chainparams.set_to_preset().
"""

transaction_previous_outpoint_fields = [
    Field('hash', 'hash', 32, b'\x00'*32),
    Field('n', b'<I', 4, 0xffffffff)
]

transaction_input_fields = [
    Field('prevout', 'prevout', None, None),
    Field('scriptSig', 'script', None, None),
    Field('nSequence', b'<I', 4, 0xffffffff)
]

transaction_output_fields = [
    Field('nValue', b'<q', 8, -1, metadata=(FIELD_COIN,)),
    Field('scriptPubKey', 'script', None, None)
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

def struct_deserialize(fmt, num_bytes, buf):
    return struct.unpack(fmt, ser_read(buf, num_bytes))[0]

def struct_serialize(value, fmt, buf):
    return buf.write(struct.pack(fmt, value))

class OutPoint(CMutableOutPoint):
    """Previous outpoint.

    Subclassed from CMutableOutPoint so that its fields can be altered.
    """
    def __init__(self, hash=b'\x00'*32, n=0xffffffff, kwfields=None):
        super(OutPoint, self).__init__(hash, n)
        self.serializer_class = Transaction.serializer_class
        if kwfields is None:
            kwfields = {}
        for k, v in kwfields.items():
            setattr(self, k, v)

        self.fields = list(transaction_previous_outpoint_fields)
        for field in self.fields:
            if not hasattr(self, field.attr):
                setattr(self, field.attr, field.default_value)

    @classmethod
    def from_outpoint(cls, outpoint):
        kwfields = {}
        for field in transaction_previous_outpoint_fields:
            if hasattr(outpoint, field.attr):
                kwfields[field.attr] = getattr(outpoint, field.attr)

        return cls(kwfields=kwfields)

class TxIn(CMutableTxIn):
    """Transaction input.

    Subclassed from CMutableTxIn so that its fields can be altered.
    """
    def __init__(self, prevout=None, scriptSig=Script(), nSequence=0xffffffff, kwfields=None):
        super(TxIn, self).__init__(prevout, scriptSig, nSequence)
        if not isinstance(self.prevout, OutPoint):
            self.prevout = OutPoint.from_outpoint(self.prevout)
        self.serializer_class = Transaction.serializer_class
        if kwfields is None:
            kwfields = {}
        for k, v in kwfields.items():
            setattr(self, k, v)

        self.fields = list(transaction_input_fields)
        for field in self.fields:
            if not hasattr(self, field.attr):
                setattr(self, field.attr, field.default_value)

    @classmethod
    def from_txin(cls, txin):
        kwfields = {}
        prevout = None
        for field in transaction_input_fields:
            if field.attr == 'prevout':
                prevout = OutPoint.from_outpoint(txin.prevout)
            elif hasattr(txin, field.attr):
                kwfields[field.attr] = getattr(txin, field.attr)

        return cls(prevout=prevout, kwfields=kwfields)

class TxOut(CMutableTxOut):
    """Transaction output.

    Subclassed from CMutableTxOut so that its fields can be altered.
    """
    def __init__(self, nValue=-1, scriptPubKey=Script(), kwfields=None):
        super(TxOut, self).__init__(nValue, scriptPubKey)
        self.serializer_class = Transaction.serializer_class
        if kwfields is None:
            kwfields = {}
        for k, v in kwfields.items():
            setattr(self, k, v)

        self.fields = list(transaction_output_fields)
        for field in self.fields:
            if not hasattr(self, field.attr):
                setattr(self, field.attr, field.default_value)

    @classmethod
    def from_txout(cls, txout):
        kwfields = {}
        for field in transaction_output_fields:
            if hasattr(txout, field.attr):
                kwfields[field.attr] = getattr(txout, field.attr)

        return cls(kwfields=kwfields)

class TransactionSerializer(object):
    """Default transaction serialization handler."""
    def stream_deserialize(self, tx, f):
        kwargs = {}
        for field in tx.fields:
            if field.fmt == 'inputs':
                self.deserialize_inputs(kwargs, f)
            elif field.fmt == 'outputs':
                self.deserialize_outputs(kwargs, f)
            else:
                self.deserialize_field(kwargs, field, f)
        return kwargs

    def stream_serialize(self, tx, f):
        for i in self.serialization_iter(tx, f):
            pass

    def serialization_iter(self, tx, f):
        """Returns a generator that serializes tx.

        After each write, the length of f and the field that was written
        are yielded. If a variable-length integer is written, None is yielded
        instead of a field.
        """
        for field in tx.fields:
            if field.fmt == 'inputs':
                for i in self.serialize_inputs(tx, f):
                    yield i
            elif field.fmt == 'outputs':
                for i in self.serialize_outputs(tx, f):
                    yield i
            else:
                yield self.serialize_field(tx, field, f)

    def struct_deserialize(self, field, f):
        """Deserialize a field using struct.unpack()."""
        pos = f.tell()
        try:
            return struct_deserialize(field.fmt, field.num_bytes, f), True
        except Exception as e:
            f.seek(pos)
            return None, False

    def struct_serialize(self, obj, field, f):
        """Serialize a field using struct.pack()."""
        pos = f.tell()
        try:
            struct_serialize(getattr(obj, field.attr), field.fmt, f)
            return True
        except Exception:
            f.seek(pos)
            return False

    def deserialize_outpoint(self, kwargs, f):
        """Deserialize an outpoint."""
        for field in transaction_previous_outpoint_fields:
            self.deserialize_field(kwargs, field, f)

    def serialize_outpoint(self, outpoint, f):
        """Serialize an outpoint."""
        for field in outpoint.fields:
            yield self.serialize_field(outpoint, field, f)

    def deserialize_input(self, f):
        """Deserialize an input."""
        txin_kwargs = {}
        for field in transaction_input_fields:
            if field.fmt == 'prevout':
                prevout_kwargs = {}
                self.deserialize_outpoint(prevout_kwargs, f)
                txin_kwargs[field.attr] = OutPoint(kwfields=prevout_kwargs)
            else:
                self.deserialize_field(txin_kwargs, field, f)
        return TxIn(kwfields=txin_kwargs)

    def serialize_input(self, txin, f):
        """Serialize an input."""
        for field in txin.fields:
            if field.fmt == 'prevout':
                for i in self.serialize_outpoint(getattr(txin, field.attr), f):
                    yield i
            else:
                yield self.serialize_field(txin, field, f)

    def deserialize_inputs(self, kwargs, f):
        """Deserialize transaction inputs."""
        n = VarIntSerializer.stream_deserialize(f)
        r = []
        for i in range(n):
            r.append(self.deserialize_input(f))
        kwargs['vin'] = r

    def serialize_inputs(self, tx, f):
        """Serialize transaction inputs."""
        VarIntSerializer.stream_serialize(len(tx.vin), f)
        yield f.tell(), None
        for txin in tx.vin:
            for i in self.serialize_input(txin, f):
                yield i

    def deserialize_output(self, f):
        """Deserialize an output."""
        txout_kwargs = {}
        for field in transaction_output_fields:
            self.deserialize_field(txout_kwargs, field, f)

        return TxOut(kwfields=txout_kwargs)

    def serialize_output(self, txout, f):
        """Serialize an output."""
        for field in txout.fields:
            yield self.serialize_field(txout, field, f)

    def deserialize_outputs(self, kwargs, f):
        """Deserialize transaction outputs."""
        n = VarIntSerializer.stream_deserialize(f)
        r = []
        for i in range(n):
            r.append(self.deserialize_output(f))
        kwargs['vout'] = r

    def serialize_outputs(self, tx, f):
        """Serialize transaction outputs."""
        VarIntSerializer.stream_serialize(len(tx.vout), f)
        yield f.tell(), None
        for txout in tx.vout:
            for i in self.serialize_output(txout, f):
                yield i

    def deserialize_field(self, kwargs, field, f):
        """Deserialize a field."""
        value, ok = self.struct_deserialize(field, f)
        if ok:
            kwargs[field.attr] = value
        elif field.fmt == 'bytes':
            kwargs[field.attr] = BytesSerializer.stream_deserialize(f)
        elif field.fmt == 'hash':
            kwargs[field.attr] = ser_read(f, field.num_bytes)
        elif field.fmt == 'script':
            kwargs[field.attr] = Script(BytesSerializer.stream_deserialize(f))

    def serialize_field(self, obj, field, f):
        """Serialize a field."""
        if self.struct_serialize(obj, field, f):
            pass
        elif field.fmt in ['bytes', 'script']:
            BytesSerializer.stream_serialize(getattr(obj, field.attr), f)
        elif field.fmt == 'hash':
            f.write(getattr(obj, field.attr))
        return f.tell(), field

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
    def __init__(self, vin=None, vout=None, nLockTime=0, nVersion=1, fields=None, kwfields=None):
        super(Transaction, self).__init__(vin, vout, nLockTime, nVersion)
        if not all(isinstance(txin, TxIn) for txin in self.vin):
            self.vin = [TxIn.from_txin(txin) for txin in self.vin]
        if not all(isinstance(txout, TxOut) for txout in self.vout):
            self.vout = [TxOut.from_txout(txout) for txout in self.vout]
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
        for field in self.fields:
            if not hasattr(self, field.attr):
                setattr(self, field.attr, field.default_value)

    @classmethod
    def stream_deserialize(cls, f):
        self = cls()
        kwargs = self.serializer_class().stream_deserialize(self, f)
        for k, v in kwargs.items():
            setattr(self, k, v)
        return self

    def stream_serialize(self, f):
        self.serializer_class().stream_serialize(self, f)

    def serialization_iter(self, f=None):
        if f is None:
            f = BytesIO()
        return self.serializer_class().serialization_iter(self, f)

    @classmethod
    def from_tx(cls, tx):
        kwfields = {}
        vin_attr = ''
        vout_attr = ''
        for field in transaction_fields:
            if field.fmt in ['inputs', 'outputs']:
                if field.fmt == 'inputs':
                    vin_attr = field.attr
                elif field.fmt == 'outputs':
                    vout_attr = field.attr
                continue
            if hasattr(tx, field.attr):
                kwfields[field.attr] = getattr(tx, field.attr)


        vin = [TxIn.from_txin(txin) for txin in tx.vin]
        vout = [TxOut.from_txout(txout) for txout in tx.vout]
        kwfields[vin_attr] = vin
        kwfields[vout_attr] = vout
        return cls(kwfields=kwfields)

    def as_hex(self):
        return b2x(self.serialize())

# Known serializer classes

class ClamsTxSerializer(TransactionSerializer):
    """Clams transaction serializer.

    Required because transaction serialization depends on transaction version.
    """
    def deserialize_field(self, kwargs, field, f):
        if field.attr != 'ClamSpeech':
            return super(ClamsTxSerializer, self).deserialize_field(kwargs, field, f)
        if kwargs['nVersion'] > 1:
            return super(ClamsTxSerializer, self).deserialize_field(kwargs, field, f)

    def serialize_field(self, obj, field, f):
        if field.attr != 'ClamSpeech':
            return super(ClamsTxSerializer, self).serialize_field(obj, field, f)
        if obj.nVersion > 1:
            return super(ClamsTxSerializer, self).serialize_field(obj, field, f)

