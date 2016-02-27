import struct

from bitcoin.core import CMutableTransaction, CMutableTxIn, CMutableTxOut, CMutableOutPoint, b2x
from bitcoin.core.serialize import ser_read, BytesSerializer, VectorSerializer, VarIntSerializer
from bitcoin.core.script import SIGHASH_ALL, SIGHASH_NONE, SIGHASH_SINGLE, SIGHASH_ANYONECANPAY

from script import Script

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
        for name, _, _, default in self.fields:
            if not hasattr(self, name):
                setattr(self, name, default)

    @classmethod
    def from_outpoint(cls, outpoint):
        kwfields = {}
        for attr, _, _, default in transaction_previous_outpoint_fields:
            if hasattr(outpoint, attr):
                kwfields[attr] = getattr(outpoint, attr)

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
        for name, _, _, default in self.fields:
            if not hasattr(self, name):
                setattr(self, name, default)

    @classmethod
    def from_txin(cls, txin):
        kwfields = {}
        prevout = None
        for attr, _, _, default in transaction_input_fields:
            if attr == 'prevout':
                prevout = OutPoint.from_outpoint(txin.prevout)
            elif hasattr(txin, attr):
                kwfields[attr] = getattr(txin, attr)

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
        for name, _, _, default in self.fields:
            if not hasattr(self, name):
                setattr(self, name, default)

    @classmethod
    def from_txout(cls, txout):
        kwfields = {}
        for attr, _, _, default in transaction_output_fields:
            if hasattr(txout, attr):
                kwfields[attr] = getattr(txout, attr)

        return cls(kwfields=kwfields)

class TransactionSerializer(object):
    """Default transaction serialization handler."""
    def stream_deserialize(self, tx, f):
        kwargs = {}
        for attr, fmt, num_bytes, _ in tx.fields:
            if fmt == 'inputs':
                self.deserialize_inputs(tx, kwargs, attr, fmt, num_bytes, f)
            elif fmt == 'outputs':
                self.deserialize_outputs(tx, kwargs, attr, fmt, num_bytes, f)
            else:
                self.deserialize_field(tx, kwargs, attr, fmt, num_bytes, f)
        return kwargs

    def stream_serialize(self, tx, f):
        for attr, fmt, num_bytes, _ in tx.fields:
            if fmt == 'inputs':
                self.serialize_inputs(tx, attr, fmt, num_bytes, f)
            elif fmt == 'outputs':
                self.serialize_outputs(tx, attr, fmt, num_bytes, f)
            else:
                self.serialize_field(tx, attr, fmt, num_bytes, f)

    def struct_deserialize(self, kwargs, attr, fmt, num_bytes, f):
        pos = f.tell()
        try:
            kwargs[attr] = struct_deserialize(fmt, num_bytes, f)
            return True
        except Exception as e:
            f.seek(pos)
            return False

    def struct_serialize(self, obj, attr, fmt, num_bytes, f):
        pos = f.tell()
        try:
            struct_serialize(getattr(obj, attr), fmt, f)
            return True
        except Exception:
            f.seek(pos)
            return False

    def deserialize_outpoint(self, tx, kwargs, attr, fmt, num_bytes, f):
        fields = list(transaction_previous_outpoint_fields)
        for op_attr, op_fmt, op_num_bytes, _ in fields:
            if self.struct_deserialize(kwargs, op_attr, op_fmt, op_num_bytes, f):
                continue
            if op_fmt == 'hash':
                kwargs[op_attr] = ser_read(f, op_num_bytes)

    def deserialize_inputs(self, tx, kwargs, attr, fmt, num_bytes, f):
        n = VarIntSerializer.stream_deserialize(f)
        r = []
        fields = list(transaction_input_fields)
        for i in range(n):
            txin_kwargs = {}
            for txi_attr, txi_fmt, txi_num_bytes, _ in fields:
                if self.struct_deserialize(txin_kwargs, txi_attr, txi_fmt, txi_num_bytes, f):
                    continue
                if txi_fmt == 'prevout':
                    prevout_kwargs = {}
                    self.deserialize_outpoint(tx, prevout_kwargs, txi_attr, txi_fmt, txi_num_bytes, f)
                    txin_kwargs[txi_attr] = OutPoint(kwfields=prevout_kwargs)
                elif txi_fmt == 'script':
                    txin_kwargs[txi_attr] = Script(BytesSerializer.stream_deserialize(f))
            r.append(TxIn(kwfields=txin_kwargs))
        kwargs['vin'] = r

    def deserialize_outputs(self, tx, kwargs, attr, fmt, num_bytes, f):
        n = VarIntSerializer.stream_deserialize(f)
        r = []
        fields = list(transaction_output_fields)
        for i in range(n):
            txout_kwargs = {}
            for txo_attr, txo_fmt, txo_num_bytes, _ in fields:
                if self.struct_deserialize(txout_kwargs, txo_attr, txo_fmt, txo_num_bytes, f):
                    continue
                if txo_fmt == 'script':
                    txout_kwargs[txo_attr] = Script(BytesSerializer.stream_deserialize(f))
            r.append(TxOut(kwfields=txout_kwargs))
        kwargs['vout'] = r

    def serialize_outpoint(self, outpoint, fmt, num_bytes, f):
        for op_attr, op_fmt, op_num_bytes, _ in outpoint.fields:
            if self.struct_serialize(outpoint, op_attr, op_fmt, op_num_bytes, f):
                continue
            if op_fmt == 'hash':
                f.write(getattr(outpoint, op_attr))

    def serialize_inputs(self, tx, attr, fmt, num_bytes, f):
        VarIntSerializer.stream_serialize(len(tx.vin), f)
        for txin in tx.vin:
            for txi_attr, txi_fmt, txi_num_bytes, _ in txin.fields:
                if self.struct_serialize(txin, txi_attr, txi_fmt, txi_num_bytes, f):
                    continue
                if txi_fmt == 'prevout':
                    self.serialize_outpoint(getattr(txin, txi_attr), txi_fmt, txi_num_bytes, f)
                elif txi_fmt == 'script':
                    BytesSerializer.stream_serialize(getattr(txin, txi_attr), f)

    def serialize_outputs(self, tx, attr, fmt, num_bytes, f):
        VarIntSerializer.stream_serialize(len(tx.vout), f)
        for txout in tx.vout:
            for txo_attr, txo_fmt, txo_num_bytes, _ in txout.fields:
                if self.struct_serialize(txout, txo_attr, txo_fmt, txo_num_bytes, f):
                    continue
                if txo_fmt == 'script':
                    BytesSerializer.stream_serialize(getattr(txout, txo_attr), f)

    def deserialize_field(self, tx, kwargs, attr, fmt, num_bytes, f):
        if self.struct_deserialize(kwargs, attr, fmt, num_bytes, f):
            return
        elif fmt == 'bytes':
            kwargs[attr] = BytesSerializer.stream_deserialize(f)

    def serialize_field(self, tx, attr, fmt, num_bytes, f):
        if self.struct_serialize(tx, attr, fmt, num_bytes, f):
            return
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
        kwfields = {}
        vin_attr = ''
        vout_attr = ''
        for attr, fmt, _, default in transaction_fields:
            if fmt in ['inputs', 'outputs']:
                if fmt == 'inputs':
                    vin_attr = attr
                elif fmt == 'outputs':
                    vout_attr = attr
                continue
            if hasattr(tx, attr):
                kwfields[attr] = getattr(tx, attr)


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

