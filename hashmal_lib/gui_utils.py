import decimal
from decimal import Decimal

from PyQt4 import QtGui
from PyQt4.QtGui import QFont, QHBoxLayout, QFrame, QLineEdit
from PyQt4 import QtCore

import config

RawRole = QtCore.Qt.UserRole + 1
"""DataRole that is considered "raw" / "non-human-readable."

For example, the hex data of a human-readable script.
"""

monospace_font = QFont('Monospace')
monospace_font.setPointSize(9)
monospace_font.setStyleHint(QFont.TypeWriter)

script_file_filter = 'Coinscripts (*.coinscript);;Text files (*.txt);;All files (*.*)'

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
    Widgets that use instances of this class should connect
    to the singleton config.Config's optionChanged signal,
    and account for changes to 'amount_format'.
    """
    def __init__(self, satoshis=0):
        super(Amount, self).__init__()
        self.satoshis = satoshis
        self.config = config.get_config()
        self.fmt = self.config.get_option('amount_format', 'satoshis')

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


hashmal_entry_points = {
    'hashmal.plugin': [
        'Address Encoder = hashmal_lib.plugins.addr_encoder:make_plugin',
        'Block Analyzer = hashmal_lib.plugins.block_analyzer:make_plugin',
        'Blockchain = hashmal_lib.plugins.blockchain:make_plugin',
        'Item Types = hashmal_lib.plugins.item_types:make_plugin',
        'Script Generator = hashmal_lib.plugins.script_gen:make_plugin',
        'Stack Evaluator = hashmal_lib.plugins.stack:make_plugin',
        'Transaction Analyzer = hashmal_lib.plugins.tx_analyzer:make_plugin',
        'Transaction Builder = hashmal_lib.plugins.tx_builder:make_plugin',
        'Variables = hashmal_lib.plugins.variables:make_plugin',
        'Wallet RPC = hashmal_lib.plugins.wallet_rpc:make_plugin'
    ]
}


required_plugins = ['Item Types', 'Stack Evaluator', 'Variables']
"""These plugins are needed and cannot be disabled."""

default_plugins = ['Blockchain', 'Item Types', 'Script Generator', 'Stack Evaluator', 'Transaction Analyzer',
                   'Transaction Builder', 'Variables', 'Wallet RPC']


hashmal_style = '''

QStatusBar[hasError=true], QLineEdit[hasError=true],
QLabel[hasError=true], QTextEdit[hasError=true], QPlainTextEdit[hasError=true] {
  background: rgba(255, 0, 0, 25%);
}
'''
