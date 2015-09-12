import bitcoin
from bitcoin.core import CTransaction

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from base import BaseDock
from hashmal_lib.gui_utils import monospace_font, floated_buttons, Separator, Amount
from hashmal_lib.tx_widget import TxWidget
from hashmal_lib.core.script import Script


class TxDeserializer(BaseDock):
    def __init__(self, handler):
        super(TxDeserializer, self).__init__(handler)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

    def init_metadata(self):
        self.tool_name = 'Transaction Deserializer'
        self.description = 'Deserializes transactions.'

    def init_data(self):
        self.tx = None

    def create_layout(self):
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)


        self.raw_tx_edit = QPlainTextEdit()
        self.raw_tx_edit.setFont(monospace_font)

        self.deserialize_button = QPushButton('Deserialize')
        self.deserialize_button.clicked.connect(self.deserialize)
        btn_hbox = floated_buttons([self.deserialize_button])

        self.tx_widget = TxWidget()

        form.addRow('Raw Tx:', self.raw_tx_edit)
        form.addRow(btn_hbox)
        form.addRow(Separator())
        form.addRow(self.tx_widget)

        return form

    def context_menu(self, position):
        menu = QMenu()
        menu.addAction('Clear Fields', self.clear)
        set_spend = menu.addAction('Set as spending transaction in Stack Evaluator', self.set_as_spending_tx)
        set_spend.setEnabled(True if self.tx else False)

        menu.exec_(self.mapToGlobal(position))

    def set_as_spending_tx(self):
        txt = str(self.raw_tx_edit.toPlainText())
        self.handler.set_stack_spending_tx(txt)

    def clear(self):
        self.tx_widget.clear()

    def deserialize(self):
        self.clear()
        txt = str(self.raw_tx_edit.toPlainText())
        if not txt:
            return
        try:
            txt = txt.decode('hex')
        except Exception:
            self.status_message('Raw transaction must be hex.', True)
            return
        try:
            self.tx = tx = CTransaction.deserialize(txt)
        except Exception:
            self.status_message('Cannot deserialize transaction.', True)
            return

        self.tx_widget.set_tx(tx)

        self.status_message('Deserialized transaction {}'.format(bitcoin.core.b2lx(tx.GetHash())))

    def on_option_changed(self, key):
        if key == 'amount_format':
            self.needsUpdate.emit()

    def refresh_data(self):
        self.deserialize()
