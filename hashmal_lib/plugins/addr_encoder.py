import bitcoin
from bitcoin.core import x, b2x
from bitcoin.base58 import CBase58Data

from PyQt4.QtGui import *
from PyQt4 import QtCore

from base import BaseDock, Plugin, Category, augmenter
from hashmal_lib.gui_utils import monospace_font, Separator
from variables import is_hex, VariableType

def make_plugin():
    return Plugin(AddrEncoder)

def is_address(x):
    try:
        data = CBase58Data(x)
    except Exception:
        return False
    return len(x) >= 26 and len(x) <= 35

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

    def init_actions(self):
        encode_hash160 = ('Encode Address', self.encode_hash160)
        self.advertised_actions['hash160'] = [encode_hash160]

    def init_data(self):
        pass

    @augmenter
    def variable_types(self, data):
        if not data.get('Address'):
            address = VariableType('Address', 'address', is_address)
            data[address.name] = address
        if not data.get('Hash160'):
            hash160 = VariableType('Hash160', 'hash160', lambda x: is_hex(x) and (len(x) == 42 if x.startswith('0x') else len(x) == 40))
            data[hash160.name] = hash160

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

    def encode_address(self):
        hash160 = str(self.hash_line.text())
        if len(hash160) != 40:
            self.address_line.setText('Hash160 must be 40 characters.')
            self.status_message('Hash160 must be 40 characters.', True)
            return
        try:
            i = int(hash160, 16)
        except ValueError:
            self.address_line.setText('Hash160 must contain only hex characters.')
            self.status_message('Hash160 must contain only hex characters.', True)
            return

        version = self.addr_version.value()
        hash160 = x(hash160)
        addr = encode_address(hash160, version)
        self.address_line.setText(str(addr))
        self.status_message('Encoded address "%s".' % str(addr))

    def encode_hash160(self, hash160):
        self.needsFocus.emit()
        self.hash_line.setText(hash160)
        self.encode_address()
