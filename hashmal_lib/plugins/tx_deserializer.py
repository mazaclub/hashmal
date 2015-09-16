import bitcoin
from bitcoin.core import CTransaction

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from base import BaseDock, Plugin
from hashmal_lib.gui_utils import monospace_font, floated_buttons, Separator, Amount
from hashmal_lib.tx_widget import TxWidget
from hashmal_lib.core.script import Script

def make_plugin():
    return Plugin([TxDeserializer])

class TxDeserializer(BaseDock):
    def __init__(self, handler):
        super(TxDeserializer, self).__init__(handler)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

    def init_metadata(self):
        self.tool_name = 'Transaction Deserializer'
        self.description = 'Deserializes transactions.'
        self.is_large = True

    def init_data(self):
        self.tx = None

    def init_actions(self):
        deserialize = ('Deserialize', self.deserialize_raw)
        self.advertised_actions['raw_transaction'] = [deserialize]

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
        if self.tx:
            txt = str(self.raw_tx_edit.toPlainText())
            self.handler.add_plugin_actions(self, menu, 'raw_transaction', txt)

        menu.exec_(self.mapToGlobal(position))

    def clear(self):
        self.tx_widget.clear()

    def deserialize_raw(self, txt):
        """Deserialize a raw transaction."""
        self.needsFocus.emit()
        self.raw_tx_edit.setPlainText(txt)
        self.deserialize()

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
