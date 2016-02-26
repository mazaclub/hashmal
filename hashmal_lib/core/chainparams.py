from collections import namedtuple
import struct

import bitcoin
from bitcoin.core.script import (FindAndDelete, SIGHASH_ALL, SIGHASH_NONE,
            SIGHASH_SINGLE, SIGHASH_ANYONECANPAY, CScript, OP_CODESEPARATOR,
            OPCODE_NAMES, OPCODES_BY_NAME, DISABLED_OPCODES)

import block
import transaction
import opcodes
import stack

active_preset = None

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
        - tx_serializer (class): Transaction serializer class. If not specified, the default
            serializer, TransactionSerializer, will be used. This argument is only necessary
            if the ParamsPreset has transactions with complex serialization formats.
        - block_header_fields (list): Block header format. Same form as tx_fields.
            If not specified, the 80-byte Bitcoin block header format is used.
        - block_fields (list): Block (excluding header) format.
        - opcode_overrides (list): List of 3-tuples in the form:
            (value, name, func), where:
                - value (int): Opcode value.
                - name (str): Opcode name.
                - func: Function that takes stack data and executes the opcode.
                    This function should take the arguments (stack, txTo, inIdx, flags, err_raiser) and
                    return (stack, opcode, log_message).
            Opcode overrides allow chainparams presets to affect only a small set of
            opcodes without having to change them all via the 'opcode_names' and 'opcodes_by_name' arguments.
            These overrides are accounted for in the Stack class, which is the script execution engine
            used if none is specified by the ParamsPreset.
        - script_engine_cls (class): Script execution engine class. If not specified, Stack will be used.
        - opcode_names (dict): Dict of {opcode_value: opcode_name}.
        - opcodes_by_name (dict): Dict of {opcode_name: opcode_value}.
        - disabled_opcodes (list): List of disabled opcode values.

    """
    def __init__(self, **kwargs):
        self.name = ''
        self.tx_fields = []
        self.tx_serializer = transaction.TransactionSerializer
        self.block_header_fields = list(_bitcoin_header_fields)
        self.block_fields = list(_bitcoin_block_fields)
        self.opcode_overrides = list(_bitcoin_opcode_overrides)
        self.script_engine_cls = stack.Stack
        self.opcode_names = dict(OPCODE_NAMES)
        self.opcodes_by_name = dict(OPCODES_BY_NAME)
        self.disabled_opcodes = list(DISABLED_OPCODES)

        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def raw_signature_hash(cls, script, txTo, inIdx, hashtype):
        HASH_ONE = b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

        if inIdx >= len(txTo.vin):
            return (HASH_ONE, "inIdx %d out of range (%d)" % (inIdx, len(txTo.vin)))
        txtmp = transaction.Transaction.from_tx(txTo)

        for txin in txtmp.vin:
            txin.scriptSig = b''
        txtmp.vin[inIdx].scriptSig = FindAndDelete(script, CScript([OP_CODESEPARATOR]))

        if (hashtype & 0x1f) == SIGHASH_NONE:
            txtmp.vout = []

            for i in range(len(txtmp.vin)):
                if i != inIdx:
                    txtmp.vin[i].nSequence = 0

        elif (hashtype & 0x1f) == SIGHASH_SINGLE:
            outIdx = inIdx
            if outIdx >= len(txtmp.vout):
                return (HASH_ONE, "outIdx %d out of range (%d)" % (outIdx, len(txtmp.vout)))

            tmp = txtmp.vout[outIdx]
            txtmp.vout = []
            for i in range(outIdx):
                txtmp.vout.append(bitcoin.core.CMutableTxOut())
            txtmp.vout.append(tmp)

            for i in range(len(txtmp.vin)):
                if i != inIdx:
                    txtmp.vin[i].nSequence = 0

        if hashtype & SIGHASH_ANYONECANPAY:
            tmp = txtmp.vin[inIdx]
            txtmp.vin = []
            txtmp.vin.append(tmp)

        s = txtmp.serialize()
        s += struct.pack(b"<I", hashtype)

        hash = bitcoin.core.Hash(s)

        return (hash, None)

    @classmethod
    def signature_hash(cls, script, txTo, inIdx, hashtype):
        (h, err) = cls.raw_signature_hash(script, txTo, inIdx, hashtype)
        if err is not None:
            raise ValueError(err)
        return h



_bitcoin_header_fields = [
    ('nVersion', b'<i', 4, 1),
    ('hashPrevBlock', 'bytes', 32, b'\x00'*32),
    ('hashMerkleRoot', 'bytes', 32, b'\x00'*32),
    ('nTime', b'<I', 4, 0),
    ('nBits', b'<I', 4, 0),
    ('nNonce', b'<I', 4, 0)
]

_bitcoin_block_fields = [
    ('vtx', 'vectortx', None, None)
]

_bitcoin_opcode_overrides = []

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
            ('ClamSpeech', 'bytes', None, b'')],
        tx_serializer = transaction.ClamsTxSerializer,
        block_fields = list(_bitcoin_block_fields) + [('blockSig', 'bytes', None, None)],
        opcode_overrides=[(0xb0, 'OP_CHECKLOCKTIMEVERIFY', opcodes.clams_checklocktimeverify)]
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

def add_preset(preset):
    global presets_list, presets
    # Check the argument's type.
    if not isinstance(preset, ParamsPreset):
        raise Exception('Chainparams preset must be an instance of ParamsPreset (or a subclass).')
    if preset.name in presets.keys() or preset in presets_list:
        raise Exception('Chainparams preset "%s" already exists.' % preset.name)

    presets_list.append(preset)
    presets = dict((i.name, i) for i in presets_list)

def remove_preset(preset):
    global presets_list, presets, active_preset
    if preset not in presets_list:
        raise Exception('Chainparams preset "%s" does not exist.' % preset.name)
    # Can't remove the Bitcoin preset.
    if preset.name == 'Bitcoin':
        raise Exception('Cannot remove the default chainparams preset (Bitcoin).')
    # If we're removing the active preset, switch to Bitcoin.
    if preset == active_preset:
        set_to_preset('Bitcoin')

    presets_list.remove(preset)
    presets = dict((i.name, i) for i in presets_list)

def get_presets():
    return list(presets_list)

def get_tx_fields():
    return transaction.transaction_fields

def set_tx_fields(fields):
    """Set the format of transactions.

    This affects all Transaction instances created afterward.
    """
    transaction.transaction_fields = list(fields)

def set_tx_serializer(cls):
    transaction.Transaction.set_serializer_class(cls)

def get_block_header_fields():
    return block.block_header_fields

def set_block_header_fields(fields):
    """Set the format of block headers.

    This affects all BlockHeader instances created afterward.
    """
    block.block_header_fields = list(fields)

def get_block_fields():
    return block.block_fields

def set_block_fields(fields):
    """Set the format of blocks (excluding their headers).

    This affects all Block instances created afterward.
    """
    block.block_fields = list(fields)

def get_opcode_overrides():
    return opcodes.overridden_opcodes

def set_opcode_overrides(ops):
    """Set the overridden behavior of specified opcodes.

    This affects all Stack steps that run afterward.
    """
    opcodes.set_overridden_opcodes(ops)

def set_opcodes(op_names, ops_by_name, disabled_ops):
    return opcodes.set_opcodes(op_names, ops_by_name, disabled_ops)

def get_script_engine_class():
    return stack.get_script_engine()

def set_script_engine_class(cls):
    return stack.set_script_engine(cls)

def set_to_preset(name):
    """Reset chainparams to the preset name."""
    global active_preset
    # Will throw an exception if name isn't a preset.
    params = presets[name]
    active_preset = params
    set_tx_fields(params.tx_fields)
    set_tx_serializer(params.tx_serializer)
    set_block_header_fields(params.block_header_fields)
    set_block_fields(params.block_fields)
    set_script_engine_class(params.script_engine_cls)
    set_opcodes(params.opcode_names, params.opcodes_by_name, params.disabled_opcodes)
    set_opcode_overrides(params.opcode_overrides)

def signature_hash(script, txTo, inIdx, hashtype):
    if not active_preset:
        raise Exception("No chainparams preset is active.")
    return active_preset.signature_hash(script, txTo, inIdx, hashtype)
