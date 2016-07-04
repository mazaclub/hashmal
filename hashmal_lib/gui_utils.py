import decimal
from decimal import Decimal

from PyQt4 import QtGui
from PyQt4.QtGui import QColor, QFont, QHBoxLayout, QFrame, QLineEdit, QHeaderView
from PyQt4 import QtCore

from bitcoin.core import b2x, lx, b2lx

from hashmal_lib.core.script import Script
import config

RawRole = QtCore.Qt.UserRole + 1
"""DataRole that is considered "raw" / "non-human-readable."

For example, the hex data of a human-readable script.
"""

monospace_font = QFont('Monospace')
monospace_font.setPointSize(9)
monospace_font.setStyleHint(QFont.TypeWriter)

script_file_filter = 'Coinscripts (*.coinscript);;Text files (*.txt);;All files (*.*)'

default_colors = {
    'booleanoperators': 'green',
    'comments': 'gray',
    'conditionals': 'green',
    'keywords': 'saddlebrown',
    'numbers': 'maroon',
    'strings': 'royalblue',
    'typenames': 'saddlebrown',
    'variables': 'goldenrod',
}

def get_default_color(color_key):
    """Get the default color for color_key."""
    return default_colors.get(color_key)

def get_default_colors():
    """Get the default colors for all color keys."""
    return default_colors.items()

def settings_color(settings, color_key):
    """Get the value (or default value) of color_key in settings.

    Args:
        settings (QSettings): A QSettings object to retrieve the value from.
        color_key (str): The QSettings key for a color.

    """
    args = ['color/%s' % color_key]
    if color_key in default_colors.keys():
        args.append(default_colors[color_key])
    return QColor(settings.value(*args))

def get_label_for_attr(name):
    """Get a display-appropriate label for an attribute name."""
    # Special case for Bitcoin previous outpoint indices.
    def parse_special_case(text):
        if text == 'n':
            return 'Index'
    # Convert snake_case. (e.g. 'block_height' --> 'BlockHeight')
    def parse_snake_case(text):
        if '_' in text:
            words = text.split('_')
            return ''.join([word.capitalize() for word in words])
    # Convert Hungarian notation. (e.g. 'nVersion' --> 'Version')
    def parse_hungarian_notation(text):
        if len(text) <= 1 or text[0].isupper():
            return
        prefix_len = 0
        for i, char in enumerate(text):
            if char == ' ':
                return
            elif char.isupper():
                prefix_len = i
                break
        if prefix_len:
            # Place prefix at the end if it's a word.
            if prefix_len > 2:
                prefix = text[:prefix_len]
                return ''.join([text[prefix_len:], prefix.capitalize()])
            # Otherwise, remove the prefix.
            return text[prefix_len:]
    # Split words (e.g. 'PrevBlock' --> 'Prev Block')
    def split_words(text):
        if text.islower():
            return
        capital_idxs = []
        for i, char in enumerate(text):
            if char.isupper():
                capital_idxs.append(i)

        if len(capital_idxs) > 0:
            idx = 0
            words = []
            for i in capital_idxs:
                if i == idx:
                    continue
                words.append(text[idx:i].capitalize())
                idx = i
            words.append(text[idx:])
            return ' '.join(words)
    # Capitalize all-lowercase attribute name.
    def capitalize_word(text):
        if text.islower():
            return text.capitalize()

    for func in [parse_special_case, parse_snake_case, parse_hungarian_notation, split_words, capitalize_word]:
        new_name = func(name)
        if new_name:
            name = new_name
    return name

class FieldInfo(object):
    """GUI-relevant field info for a data field."""
    def __init__(self, field, cls, qvariant_method):
        self.attr = field.attr
        self.fmt = field.fmt
        self.num_bytes = field.num_bytes
        self.default = field.default_value
        self.metadata = field.metadata
        self._field = field
        self.cls = cls
        self.qvariant_method = qvariant_method

    def is_coin_amount(self):
        """Get whether this field represents an amount of coins."""
        return self._field.is_coin_amount()

    def get_view_header(self):
        """Get the header label for a view."""
        name = get_label_for_attr(self.attr)
        header = {
            QtCore.Qt.DisplayRole: name,
            QtCore.Qt.EditRole: name,
            QtCore.Qt.ToolTipRole: name,
        }
        return header

    def get_header_resize_mode(self):
        """Get the header resize model for a view.

        Returns None if no resize mode should be assigned.
        """
        if self.fmt == 'script':
            return QHeaderView.Stretch
        elif self.fmt == 'hash':
            return QHeaderView.Interactive
        elif self.qvariant_method in ['toInt', 'toUInt', 'toLongLong', 'toULongLong', 'toFloat']:
            return QHeaderView.ResizeToContents
        return None

    def format_data(self, value, role = QtCore.Qt.DisplayRole):
        """Format data for a view."""
        data = None
        if self.fmt == 'script':
            s = Script(value)
            if role == RawRole:
                data = s.get_hex()
            else:
                data = s.get_asm()
        # Hashes are presented as hex-encoded little-endian strings.
        elif self.fmt == 'hash':
            data = b2lx(value)
        # Hex-encode byte strings.
        elif self.fmt == 'bytes':
            data = b2x(value)
        elif self.cls in [int, float]:
            data = value
            if role in [QtCore.Qt.DisplayRole, QtCore.Qt.ToolTipRole]:
                data = str(data)
        return data

    def get_qvariant_data(self, qvariant):
        """Get data from a QVariant."""
        value = None
        method = getattr(qvariant, self.qvariant_method)
        if self.fmt == 'script':
            value = Script.from_asm(str(method()))
        # Switch endianness and decode hex.
        elif self.fmt == 'hash':
            value = lx(str(method()))
        elif self.qvariant_method in ['toInt', 'toUInt', 'toLongLong', 'toULongLong', 'toFloat']:
            tmp, ok = method()
            if ok:
                value = tmp
        elif self.qvariant_method == 'toString':
            value = str(method())
        return value

def _field_info_for_struct_format(fmt):
    cls, qvariant_method = None, None
    char = fmt[1]
    if char in ['b', 'B', 'h', 'H', 'i', 'I', 'l', 'L', 'q', 'Q']:
        cls = int
        qvariant_method = 'toInt'
        if char == 'q':
            qvariant_method = 'toLongLong'
        elif char == 'Q':
            qvariant_method = 'toULongLong'
        elif char == char.upper():
            qvariant_method = 'toUInt'
    elif char in ['f', 'd']:
        cls = float
        qvariant_method = 'toFloat'
    return cls, qvariant_method

def field_info(field):
    """Get GUI-relevant info for a data field."""
    cls, qvariant_method = str, 'toString'

    if field.fmt.startswith(('<', '>')) and len(field.fmt) == 2:
        cls, qvariant_method = _field_info_for_struct_format(field.fmt)

    return FieldInfo(field, cls, qvariant_method)

def HBox(*widgets):
    """Create an HBoxLayout with the widgets passed."""
    hbox = QHBoxLayout()
    for w in widgets:
        hbox.addWidget(w)
    return hbox

def floated_buttons(btns, left=False):
    """Returns a HBoxLayout with buttons floated to the right or left."""
    hbox = QHBoxLayout()
    for b in btns:
        hbox.addWidget(b)
    if left:
        hbox.addStretch(1)
    else:
        hbox.insertStretch(0, 1)
    return hbox

def add_shortcuts(items):
    """Add shortcuts (ampersands) to items."""
    used = [] # assigned shortcuts
    items = list(items)
    for i, item in enumerate(items):
        char_index = 0
        # Loop through letters to find an unused shortcut.
        while item[char_index] in used:
            char_index += 1
            if char_index >= len(item):
                char_index = 0
                break
        used.append(item[char_index])
        if char_index == 0:
            items[i] = ''.join(['&', item])
        else:
            items[i] = ''.join([item[0:char_index], '&', item[char_index:]])
    return items

class Separator(QFrame):
    """A raised horizontal line to separate widgets."""
    def __init__(self, parent=None):
        super(Separator, self).__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Raised)
        self.setLineWidth(6)
        self.setMidLineWidth(2)

    def sizeHint(self):
        return QtCore.QSize(6, 8)

class Amount(object):
    """Bitcoin output amount.

    Internally, the amount is stored as satoshis.
    """
    def __init__(self, satoshis=0):
        super(Amount, self).__init__()
        self.satoshis = satoshis
        self.config = config.get_config()
        self.fmt = self.config.get_option('amount_format', 'satoshis')
        self.config.optionChanged.connect(self.on_option_changed)

    @staticmethod
    def known_formats():
        return ['satoshis', 'coins']

    def get_str(self):
        value = str(self.satoshis)
        if self.fmt == 'satoshis':
            value = str(self.satoshis)
        elif self.fmt == 'coins':
            value = '{:.8f}'.format(Decimal(self.satoshis) / pow(10, 8))
        # fallback to satoshis
        else:
            value = str(self.satoshis)
        return value

    def on_option_changed(self, key):
        if key == 'amount_format':
            self.fmt = self.config.get_option('amount_format', 'satoshis')

class OutputAmountEdit(QLineEdit):
    def __init__(self, parent=None):
        super(OutputAmountEdit, self).__init__(parent)
        self.config = config.get_config()
        self.config.optionChanged.connect(self.on_option_changed)
        self.amount_format = self.config.get_option('amount_format', 'coins')
        self.textChanged.connect(self.check_text)

    @QtCore.pyqtProperty(str)
    def satoshis(self):
        return str(self.get_satoshis())

    @satoshis.setter
    def satoshis(self, value):
        # QString --> str
        self.set_satoshis(str(value))

    def get_satoshis(self):
        """Get amount in satoshis."""
        amount = str(self.text())
        if not amount:
            return 0
        if self.amount_format == 'satoshis':
            return int(amount)
        elif self.amount_format == 'coins':
            return int(float(amount) * pow(10, 8))

    def set_satoshis(self, amount):
        if self.amount_format == 'satoshis':
            self.setText(str(amount))
        elif self.amount_format == 'coins':
            amount = Decimal(amount) / pow(10, 8)
            amount = amount.quantize(Decimal('0.00000001'), rounding=decimal.ROUND_DOWN)
            self.setText('{:f}'.format(amount))

    def check_text(self):
        try:
            i = self.get_satoshis()
        except Exception as e:
            print(e)
            self.setProperty('hasError', True)
            return
        else:
            if i < 0:
                self.setProperty('hasError', True)
                return
            self.setProperty('hasError', False)
        finally:
            self.style().polish(self)

    def update_format(self):
        satoshis = self.get_satoshis()
        self.amount_format = self.config.get_option('amount_format', 'coins')
        self.set_satoshis(satoshis)

    def on_option_changed(self, key):
        if key == 'amount_format':
            self.update_format()

class AmountEdit(QLineEdit):
    """QSpinBox does not support a maximum value
    of 0xffffffff. This class can be used in cases where a
    maximum value of 0xffffffff is needed."""
    def __init__(self, max_value=0xffffffff, parent=None):
        super(AmountEdit, self).__init__(parent)
        self.max_value = max_value
        self.textChanged.connect(self.check_text)

    @QtCore.pyqtProperty(str)
    def amount(self):
        return str(self.get_amount())

    @amount.setter
    def amount(self, value):
        self.set_amount(value)

    def get_amount(self):
        txt = str(self.text())
        if len(txt) == 0:
            return 0
        if txt.startswith('0x'):
            i = int(txt, 16)
        else:
            i = int(txt)
        return i

    def set_amount(self, amount):
        if isinstance(amount, QtCore.QVariant):
            amount = amount.toUInt()
        self.setText(str(amount))

    def check_text(self):
        try:
            i = self.get_amount()
        except Exception:
            self.setProperty('hasError', True)
            return
        else:
            if i < 0 or i > self.max_value:
                self.setProperty('hasError', True)
                return
            self.setProperty('hasError', False)
        finally:
            self.style().polish(self)


# http://stackoverflow.com/questions/11472284/how-to-set-a-read-only-checkbox-in-pyside-pyqt
class ReadOnlyCheckBox(QtGui.QCheckBox):
    def __init__( self, *args ):
        super(ReadOnlyCheckBox, self).__init__(*args) # will fail if passing **kwargs
        self._readOnly = True

    def isReadOnly( self ):
        return self._readOnly

    def mousePressEvent( self, event ):
        if ( self.isReadOnly() ):
            event.accept()
        else:
            super(ReadOnlyCheckBox, self).mousePressEvent(event)

    def mouseMoveEvent( self, event ):
        if ( self.isReadOnly() ):
            event.accept()
        else:
            super(ReadOnlyCheckBox, self).mouseMoveEvent(event)

    def mouseReleaseEvent( self, event ):
        if ( self.isReadOnly() ):
            event.accept()
        else:
            super(ReadOnlyCheckBox, self).mouseReleaseEvent(event)

    def keyPressEvent( self, event ):
        if ( self.isReadOnly() ):
            event.accept()
        else:
            super(ReadOnlyCheckBox, self).keyPressEvent(event)

    @QtCore.pyqtSlot(bool)
    def setReadOnly( self, state ):
        self._readOnly = state

    readOnly = QtCore.pyqtProperty(bool, isReadOnly, setReadOnly)


hashmal_builtin_plugins = [
    ('Address Encoder', 'hashmal_lib.plugins.addr_encoder:make_plugin'),
    ('Block Analyzer', 'hashmal_lib.plugins.block_analyzer:make_plugin'),
    ('Blockchain', 'hashmal_lib.plugins.blockchain:make_plugin'),
    ('Chainparams', 'hashmal_lib.plugins.chainparams:make_plugin'),
    ('Item Types', 'hashmal_lib.plugins.item_types:make_plugin'),
    ('Log', 'hashmal_lib.plugins.log:make_plugin'),
    ('Script Generator', 'hashmal_lib.plugins.script_gen:make_plugin'),
    ('Stack Evaluator', 'hashmal_lib.plugins.stack:make_plugin'),
    ('Transaction Analyzer', 'hashmal_lib.plugins.tx_analyzer:make_plugin'),
    ('Transaction Builder', 'hashmal_lib.plugins.tx_builder:make_plugin'),
    ('Variables', 'hashmal_lib.plugins.variables:make_plugin'),
    ('Wallet RPC', 'hashmal_lib.plugins.wallet_rpc:make_plugin'),
]

hashmal_entry_points = {
    'hashmal.plugin': [' = '.join(i) for i in hashmal_builtin_plugins],
}

required_plugins = ['Chainparams', 'Item Types', 'Log', 'Stack Evaluator', 'Variables']
"""These plugins are needed and cannot be disabled."""

default_plugins = ['Blockchain', 'Chainparams', 'Item Types', 'Log', 'Script Generator', 'Stack Evaluator',
                    'Transaction Analyzer', 'Transaction Builder', 'Variables', 'Wallet RPC']

