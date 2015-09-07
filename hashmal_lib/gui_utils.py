from decimal import Decimal

from PyQt4.QtGui import QFont, QHBoxLayout, QFrame, QLineEdit
from PyQt4 import QtCore

import config

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

class AmountEdit(QLineEdit):
    """QSpinBox does not support a maximum value
    of 0xffffffff. This class can be used in cases where a
    maximum value of 0xffffffff is needed."""
    def __init__(self, max_value=0xffffffff, parent=None):
        super(AmountEdit, self).__init__(parent)
        self.max_value = max_value
        self.textChanged.connect(self.check_text)

    def get_amount(self):
        txt = str(self.text())
        if len(txt) == 0:
            return 0
        if txt.startswith('0x'):
            i = int(txt, 16)
            return i
        i = int(txt)
        return i

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

hashmal_style = '''

QStatusBar[hasError=true], QLineEdit[hasError=true] {
  background: rgba(255, 0, 0, 25%);
}
'''
