import bitcoin
from bitcoin.core import x, b2x
from bitcoin.base58 import CBase58Data

from PyQt4.QtGui import *
from PyQt4 import QtCore

from base import BaseDock, Plugin, Category, augmenter
from hashmal_lib.gui_utils import monospace_font, Separator
from item_types import Item, ItemAction

def make_plugin():
    return Plugin(AddrEncoder)

class Hash160Item(Item):
    name = 'Hash160'
    @classmethod
    def coerce_item(cls, data):
        def ensure_hex(v):
            if v.startswith('0x'):
                v = v[2:]
            if len(v.decode('hex')) != 20:
                raise Exception('Value is not a hash160')
            return v

        try:
            value = ensure_hex(data)
            if value:
                return cls(value)
        except Exception:
            return None

    def raw(self):
        return self.value

class AddressItem(Item):
    name = 'Address'
    @classmethod
    def coerce_item(cls, data):
        def coerce_address(v):
            addr_data = CBase58Data(v)
            if len(v) >= 26 and len(v) <= 35:
                return addr_data

        try:
            value = coerce_address(data)
            if value:
                return cls(value)
        except Exception:
            return None

    def __init__(self, *args):
        super(AddressItem, self).__init__(*args)
        def copy_hash160():
            QApplication.clipboard().setText(self.value.encode('hex'))
        self.actions.append(('Copy RIPEMD-160 Hash', copy_hash160))

    def raw(self):
        return b2x(self.value.to_bytes())

def decode_address(txt):
    """Decode txt into a RIPEMD-160 hash.

    Will raise if txt is not a valid address.

    Returns:
        Two-tuple of (raw_bytes, address_version)
    """
    addr = CBase58Data(txt)
    raw = addr.to_bytes()
    return (addr.to_bytes(), addr.nVersion)

def encode_address(hash160, addr_version=0):
    """Encode hash160 into an address."""
    assert len(hash160) == 20, 'Invalid RIPEMD-160 hash'
    addr = CBase58Data.from_bytes(hash160, addr_version)
    return addr

class AddrEncoder(BaseDock):

    tool_name = 'Address Encoder'
    description = '\n'.join([
            'Address Encoder encodes/decodes addresses with version bytes (blockchain identifiers).',
            'Addresses are decoded into their 20-byte RIPEMD-160 hashes.'
    ])
    category = Category.Key

    def __init__(self, handler):
        super(AddrEncoder, self).__init__(handler)
        self.widget().setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

    def init_data(self):
        pass

    @augmenter
    def item_types(self, arg):
        return [AddressItem, Hash160Item]

    @augmenter
    def item_actions(self, *args):
        return [
            ItemAction(self.tool_name, 'Address', 'Decode', self.decode_item),
            ItemAction(self.tool_name, 'Hash160', 'Encode', self.encode_item)
        ]

    def create_layout(self):
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapAllRows)

        self.address_line = QLineEdit()
        self.address_line.setWhatsThis('Enter a cryptocurrency address in this field to decode it into its raw format.')
        self.address_line.setFont(monospace_font)
        self.address_line.setPlaceholderText('Enter an address')
        self.setFocusProxy(self.address_line)
        self.decode_button = QPushButton('Decode')
        self.decode_button.clicked.connect(self.decode_address)

        self.hash_line = QLineEdit()
        self.hash_line.setWhatsThis('Enter a raw RIPEMD-160 hash in this field to encode it into an address.')
        self.hash_line.setFont(monospace_font)
        self.hash_line.setPlaceholderText('Enter a RIPEMD-160 hash')
        self.addr_version = QSpinBox()
        self.addr_version.setWhatsThis('The address version determines what character an address will start with, and is used to distinguish addresses for different cryptocurrencies.')
        self.addr_version.setRange(0, 255)
        self.encode_button = QPushButton('Encode')
        self.encode_button.clicked.connect(self.encode_address)

        addr_box = QHBoxLayout()
        addr_box.addWidget(self.address_line, stretch=1)
        addr_box.addWidget(self.decode_button)

        version_box = QHBoxLayout()
        version_box.addWidget(QLabel('Address Version:'))
        version_box.addWidget(self.addr_version)
        version_box.addWidget(self.encode_button)

        sep = Separator()

        form.addRow('Address:', addr_box)
        form.addRow(sep)
        form.addRow('Hash160:', self.hash_line)
        form.addRow(version_box)

        return form

    def decode_address(self):
        txt = str(self.address_line.text())
        try:
            addr_bytes, version = decode_address(txt)
        except Exception:
            self.hash_line.setText('Could not decode address.')
            self.addr_version.setValue(0)
            return

        self.hash_line.setText(b2x(addr_bytes))
        self.addr_version.setValue(version)

    def decode_item(self, item):
        self.needsFocus.emit()
        self.address_line.setText(str(item))
        self.decode_button.animateClick()

    def encode_address(self):
        hash160 = str(self.hash_line.text())
        if len(hash160) != 40:
            self.address_line.setText('Hash160 must be 40 characters.')
            self.error('Hash160 must be 40 characters.')
            return
        try:
            i = int(hash160, 16)
        except ValueError:
            self.address_line.setText('Hash160 must contain only hex characters.')
            self.error('Hash160 must contain only hex characters.')
            return

        version = self.addr_version.value()
        hash160 = x(hash160)
        addr = encode_address(hash160, version)
        self.address_line.setText(str(addr))
        self.info('Encoded address "%s".' % str(addr))

    def encode_hash160(self, hash160):
        self.needsFocus.emit()
        self.hash_line.setText(hash160)
        self.encode_button.animateClick()

    def encode_item(self, item):
        self.encode_hash160(item.raw())
