import struct

import bitcoin
from bitcoin.core import __make_mutable, b2x, b2lx, CBlockHeader
from bitcoin.core.serialize import ser_read, Hash, BytesSerializer, VectorSerializer

from transaction import Transaction

block_header_fields = [
    ('nVersion', b'<i', 4, 1),
    ('hashPrevBlock', 'bytes', 32, b'\x00'*32),
    ('hashMerkleRoot', 'bytes', 32, b'\x00'*32),
    ('nTime', b'<I', 4, 0),
    ('nBits', b'<I', 4, 0),
    ('nNonce', b'<I', 4, 0)
]
"""Fields of block header.

Do not modify this list! Use chainparams.set_block_header_fields()
or a preset via chainparams.set_to_preset().
"""

block_fields = [
    ('vtx', 'vectortx', None, None)
]

@__make_mutable
class BlockHeader(CBlockHeader):
    """Cryptocurrency block header.

    Subclassed from CBlockHeader so that its fields
    (e.g. nVersion, nTime) can be altered.

    Use chainparams.set_tx_fields() to modify the global
    block_header_fields list.

    For the most common purposes, chainparams.set_to_preset()
    can be used instead.
    """
    def __init__(self, nVersion=2, hashPrevBlock=b'\x00'*32, hashMerkleRoot=b'\x00'*32, nTime=0, nBits=0, nNonce=0, fields=None, kwfields=None):
        super(BlockHeader, self).__init__(nVersion, hashPrevBlock, hashMerkleRoot, nTime, nBits, nNonce)
        if kwfields is None: kwfields = {}
        for k, v in kwfields.items():
            setattr(self, k, v)
        self.set_serialization(fields)

    @classmethod
    def header_length(cls):
        """Returns the expected length of block headers."""
        return sum([i[2] for i in block_header_fields])

    @classmethod
    def from_header(cls, header):
        """Instantiate from a BlockHeader or CBlockHeader instance."""
        if header.__class__ is BlockHeader:
            # In case from_header() is called after chainparams changes,
            # ensure the other header gets the new fields.
            for attr, _, _, default in block_header_fields:
                try:
                    getattr(header, attr)
                except AttributeError:
                    setattr(header, attr, default)
            return header
        elif header.__class__ is CBlockHeader:
            kwargs = dict((i, getattr(header, i)) for i in ['nVersion','hashPrevBlock','hashMerkleRoot','nTime','nBits','nNonce'])
            return cls(**kwargs)

    def set_serialization(self, fields=None):
        """Set the serialization format.

        This allows block headers to exist that do not comply with the
        global block_header_fields list.
        """
        if fields is None:
            fields = list(block_header_fields)
        self.fields = fields
        for name, _, _, default in self.fields:
            try:
                getattr(self, name)
            except AttributeError:
                setattr(self, name, default)

    @classmethod
    def stream_deserialize(cls, f):
        self = cls()
        if not hasattr(self, 'fields'):
            setattr(self, 'fields', list(block_header_fields))
        for attr, fmt, num_bytes, _ in self.fields:
            if fmt not in ['bytes']:
                setattr(self, attr, struct.unpack(fmt, ser_read(f, num_bytes))[0])
            elif fmt == 'bytes':
                setattr(self, attr, ser_read(f, num_bytes))
        return self

    def stream_serialize(self, f):
        for attr, fmt, num_bytes, _ in self.fields:
            if fmt not in ['bytes']:
                f.write(struct.pack(fmt, getattr(self, attr)))
            elif fmt == 'bytes':
                f.write(getattr(self, attr))

    def as_hex(self):
        return b2x(self.serialize())


class Block(BlockHeader):
    """A block including all transactions in it.

    Most of this code is copied directly from the CBlock class in python-bitcoinlib.
    https://github.com/petertodd/python-bitcoinlib/blob/master/bitcoin/core/__init__.py
    """
    @staticmethod
    def build_merkle_tree_from_txids(txids):
        """Build a full Block merkle tree from txids

        txids - iterable of txids

        Returns a new merkle tree in deepest first order. The last element is
        the merkle root.

        WARNING! If you're reading this because you're learning about crypto
        and/or designing a new system that will use merkle trees, keep in mind
        that the following merkle tree algorithm has a serious flaw related to
        duplicate txids, resulting in a vulnerability. (CVE-2012-2459) Bitcoin
        has since worked around the flaw, but for new applications you should
        use something different; don't just copy-and-paste this code without
        understanding the problem first.
        """
        merkle_tree = list(txids)

        size = len(txids)
        j = 0
        while size > 1:
            for i in range(0, size, 2):
                i2 = min(i+1, size-1)
                merkle_tree.append(Hash(merkle_tree[j+i] + merkle_tree[j+i2]))

            j += size
            size = (size + 1) // 2

        return merkle_tree

    @staticmethod
    def build_merkle_tree_from_txs(txs):
        """Build a full merkle tree from transactions"""
        txids = [tx.GetHash() for tx in txs]
        return Block.build_merkle_tree_from_txids(txids)

    @classmethod
    def from_block(cls, blk):
        if blk.__class__ is Block:
            # In case from_block() is called after chainparams changes,
            # ensure the other block gets the new fields.
            for attr, _, _, default in block_header_fields:
                try:
                    getattr(blk, attr)
                except AttributeError:
                    setattr(blk, attr, default)
            return blk
        elif blk.__class__ is CBlock:
            kwargs = dict((i, getattr(blk, i)) for i in ['nVersion','hashPrevBlock','hashMerkleRoot','nTime','nBits','nNonce'])
            return cls(**kwargs)


    def calc_merkle_root(self):
        """Calculate the merkle root

        The calculated merkle root is not cached; every invocation
        re-calculates it from scratch.
        """
        if not len(self.vtx):
            raise ValueError('Block contains no transactions')
        return self.build_merkle_tree_from_txs(self.vtx)[-1]

    def __init__(self, nVersion=2, hashPrevBlock=b'\x00'*32, hashMerkleRoot=b'\x00'*32, nTime=0, nBits=0, nNonce=0, vtx=(), header_fields=None, block_fields=None, kwfields=None):
        """Create a new block"""
        super(Block, self).__init__(nVersion, hashPrevBlock, hashMerkleRoot, nTime, nBits, nNonce, header_fields)
        if kwfields is None: kwfields = {}
        for k, v in kwfields.items():
            setattr(self, k, v)

        self.set_serialization(block_fields)
        vMerkleTree = tuple(Block.build_merkle_tree_from_txs(vtx))
        object.__setattr__(self, 'vMerkleTree', vMerkleTree)
        object.__setattr__(self, 'vtx', tuple(Transaction.from_tx(tx) for tx in vtx))

    def get_header(self):
        """Return the block header

        Returned header is a new object.
        """
        d = {}
        for attr, _, _, _ in self.fields:
            d[attr] = getattr(self, attr)
        return BlockHeader(**d)

    def GetHash(self):
        return self.get_header().GetHash()

    def set_serialization(self, fields=None):
        """Set the serialization format.

        This allows blocks to exist that do not comply with the
        global block_fields list.
        """
        if fields is None:
            fields = list(block_fields)
        self.block_fields = fields
        for name, _, _, default in self.block_fields:
            if not hasattr(self, name):
                setattr(self, name, default)

    @classmethod
    def stream_deserialize(cls, f):
        self = super(Block, cls).stream_deserialize(f)
        for attr, fmt, num_bytes, _ in self.block_fields:
            if fmt not in ['bytes', 'vectortx']:
                setattr(self, attr, struct.unpack(fmt, ser_read(f, num_bytes))[0])
            elif fmt == 'bytes':
                setattr(self, attr, BytesSerializer.stream_deserialize(f))
            elif fmt == 'vectortx':
                setattr(self, attr, VectorSerializer.stream_deserialize(Transaction, f))

        setattr(self, 'vMerkleTree', tuple(Block.build_merkle_tree_from_txs(getattr(self, 'vtx'))))
        return self

    def stream_serialize(self, f):
        super(Block, self).stream_serialize(f)
        for attr, fmt, num_bytes, _ in self.block_fields:
            if fmt not in ['bytes', 'vectortx']:
                f.write(struct.pack(fmt, getattr(self, attr)))
            elif fmt == 'bytes':
                BytesSerializer.stream_serialize(getattr(self, attr), f)
            elif fmt == 'vectortx':
                VectorSerializer.stream_serialize(Transaction, getattr(self, attr), f)
