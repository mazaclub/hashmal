import io

import bitcoin
from bitcoin.core import CTransaction

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from base import BaseDock
from hashmal_lib.gui_utils import monospace_font, floated_buttons, Separator, Amount
from hashmal_lib.core.script import Script


class TxDeserializer(BaseDock):
    def __init__(self, handler):
        super(TxDeserializer, self).__init__(handler)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)
        self.config.optionChanged.connect(self.on_config_changed)

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

        # version, inputs, outputs, locktime

        self.version_edit = QLineEdit()
        self.version_edit.setReadOnly(True)

        self.inputs_tree = inputs = QTreeWidget()
        inputs.setColumnCount(3)
        inputs.setHeaderLabels(['Prev Output', 'scriptSig', 'Sequence'])
        inputs.setAlternatingRowColors(True)
        inputs.header().setStretchLastSection(False)
        inputs.header().setResizeMode(0, QHeaderView.Interactive)
        inputs.header().setResizeMode(1, QHeaderView.Stretch)
        inputs.header().setResizeMode(2, QHeaderView.Interactive)

        self.outputs_tree = outputs = QTreeWidget()
        outputs.setColumnCount(2)
        outputs.setHeaderLabels(['Value', 'scriptPubKey'])
        outputs.setAlternatingRowColors(True)
        outputs.header().setResizeMode(0, QHeaderView.Interactive)
        outputs.header().setResizeMode(1, QHeaderView.Stretch)

        self.locktime_edit = QLineEdit()
        self.locktime_edit.setReadOnly(True)

        form.addRow('Raw Tx:', self.raw_tx_edit)
        form.addRow(btn_hbox)
        form.addRow(Separator())
        form.addRow('Version:', self.version_edit)
        form.addRow('Inputs:', inputs)
        form.addRow('Outputs:', outputs)
        form.addRow('LockTime:', self.locktime_edit)

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
        self.version_edit.clear()
        self.inputs_tree.clear()
        self.outputs_tree.clear()
        self.locktime_edit.clear()

    def deserialize(self):
        self.clear()
        txt = str(self.raw_tx_edit.toPlainText())
        try:
            buf = io.BytesIO(txt.decode('hex'))
        except Exception:
            self.status_message('Raw transaction must be hex.', True)
            return
        try:
            self.tx = tx = CTransaction.stream_deserialize(buf)
        except Exception:
            self.status_message('Cannot deserialize transaction.', True)
            return

        self.version_edit.setText(str(tx.nVersion))

        for i in tx.vin:
            in_script = Script(i.scriptSig)
            item = QTreeWidgetItem([
                str(i.prevout),
                in_script.get_human(),
                str(i.nSequence)
            ])
            self.inputs_tree.addTopLevelItem(item)

        for o in tx.vout:
            out_script = Script(o.scriptPubKey)
            value = Amount(o.nValue)
            item = QTreeWidgetItem([
                value.get_str(),
                out_script.get_human()
            ])
            self.outputs_tree.addTopLevelItem(item)

        self.locktime_edit.setText(str(tx.nLockTime))

        self.status_message('Deserialized transaction {}'.format(bitcoin.core.b2lx(tx.GetHash())))

    def on_config_changed(self, key):
        if key == 'amount_format':
            self.needsUpdate.emit()

    def refresh_data(self):
        self.deserialize()
