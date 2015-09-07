from decimal import Decimal

from PyQt4.QtGui import QFont, QHBoxLayout, QFrame
from PyQt4 import QtCore

import config

monospace_font = QFont('Monospace')
monospace_font.setPointSize(9)
monospace_font.setStyleHint(QFont.TypeWriter)

script_file_filter = 'Coinscripts (*.coinscript);;Text files (*.txt);;All files (*.*)'

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
    def __init__(self, parent=None):
        super(Separator, self).__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Raised)
        self.setLineWidth(6)
        self.setMidLineWidth(2)

    def sizeHint(self):
        return QtCore.QSize(6, 8)

class Amount(object):
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

hashmal_style = '''

QStatusBar[hasError=true], QLineEdit[hasError=true] {
  background: rgba(255, 0, 0, 25%);
}
'''
