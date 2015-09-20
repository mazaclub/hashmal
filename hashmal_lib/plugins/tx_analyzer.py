import bitcoin
from bitcoin.core import b2lx

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from base import BaseDock, Plugin
from hashmal_lib.gui_utils import monospace_font, floated_buttons, Separator, Amount
from hashmal_lib.tx_widget import TxWidget
from hashmal_lib.core.script import Script
from hashmal_lib.core import Transaction

def make_plugin():
    return Plugin([TxAnalyzer])

class TxAnalyzer(BaseDock):
    def __init__(self, handler):
        super(TxAnalyzer, self).__init__(handler)
        self.raw_tx_edit.textChanged.emit()

    def init_metadata(self):
        self.tool_name = 'Transaction Analyzer'
        self.description = 'Deserializes transactions and verifies their inputs.'
        self.is_large = True

    def init_data(self):
        self.tx = None

    def init_actions(self):
        deserialize = ('Deserialize', self.deserialize_raw)
        verify = ('Verify inputs', self.do_verify_inputs)
        self.advertised_actions['raw_transaction'] = [deserialize, verify]

    def create_layout(self):
        form = QFormLayout()

        self.raw_tx_edit = QPlainTextEdit()
        self.raw_tx_edit.setFont(monospace_font)
        self.raw_tx_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.raw_tx_edit.customContextMenuRequested.connect(self.context_menu)
        self.raw_tx_edit.textChanged.connect(self.check_raw_tx)

        self.raw_tx_invalid = QLabel('Cannot parse transaction.')
        self.raw_tx_invalid.setProperty('hasError', True)

        tabs = QTabWidget()
        tabs.addTab(self.create_deserialize_tab(), 'Deserialize')
        tabs.addTab(self.create_verify_tab(), 'Verify')

        tabs.setTabToolTip(0, 'View the transaction in human-readable form')
        tabs.setTabToolTip(1, 'Download previous transactions and verify inputs')

        form.addRow('Raw Tx:', self.raw_tx_edit)
        form.addRow(self.raw_tx_invalid)
        form.addRow(tabs)
        return form

    def create_deserialize_tab(self):
        form = QFormLayout()

        self.deserialize_button = QPushButton('Deserialize')
        self.deserialize_button.clicked.connect(self.deserialize)
        btn_hbox = floated_buttons([self.deserialize_button])

        self.tx_widget = TxWidget()
        self.tx_widget.inputs_tree.view.customContextMenuRequested.disconnect(self.tx_widget.inputs_tree.customContextMenu)
        self.tx_widget.inputs_tree.view.customContextMenuRequested.connect(self.inputs_context_menu)

        form.addRow(self.tx_widget)

        w = QWidget()
        w.setLayout(form)
        return w

    def create_verify_tab(self):
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapAllRows)

        self.inputs_box = QSpinBox()

        self.verify_button = QPushButton('Verify')
        self.verify_button.clicked.connect(self.verify_input)

        self.verify_all_button = QPushButton('Verify All')
        self.verify_all_button.clicked.connect(self.verify_inputs)

        self.result_edit = QLineEdit()
        self.result_edit.setReadOnly(True)

        form.addRow('Verify Input:', floated_buttons([self.inputs_box, self.verify_button]))
        form.addRow(floated_buttons([self.verify_all_button]))
        form.addRow('Result:', self.result_edit)

        w = QWidget()
        w.setLayout(form)
        return w

    def context_menu(self, position):
        menu = QMenu()
        if self.tx:
            txt = str(self.raw_tx_edit.toPlainText())
            self.handler.add_plugin_actions(self, menu, 'raw_transaction', txt)

        menu.exec_(self.mapToGlobal(position))

    def inputs_context_menu(self, position):
        inputs = self.tx_widget.inputs_tree
        def inputs_context_verify():
            item = inputs.model.itemFromIndex(inputs.view.selectedIndexes()[0])
            row = item.row()
            self.do_verify_input(self.tx, row)

        menu = QMenu()
        if self.tx:
            menu = inputs.context_menu()
            menu.addAction('Verify script', inputs_context_verify)

        menu.exec_(inputs.view.viewport().mapToGlobal(position))

    def clear(self):
        self.tx_widget.clear()

    def check_raw_tx(self):
        txt = str(self.raw_tx_edit.toPlainText())
        tx = None
        valid = True
        try:
            tx = Transaction.deserialize(txt.decode('hex'))
        except Exception:
            valid = False

        self.tx = tx
        self.deserialize_button.setEnabled(valid)
        self.inputs_box.setEnabled(valid)
        self.verify_button.setEnabled(valid)
        self.verify_all_button.setEnabled(valid)
        self.tx_widget.setEnabled(valid)
        self.clear()
        if valid:
            self.raw_tx_invalid.hide()
            self.inputs_box.setRange(0, len(tx.vin) - 1)
            self.deserialize()
        elif txt:
            self.raw_tx_invalid.show()
        else:
            self.raw_tx_invalid.hide()

    def deserialize_raw(self, txt):
        """Deserialize a raw transaction."""
        self.needsFocus.emit()
        self.raw_tx_edit.setPlainText(txt)
        self.deserialize()

    def deserialize(self):
        self.clear()
        self.tx_widget.set_tx(self.tx)
        self.status_message('Deserialized transaction {}'.format(bitcoin.core.b2lx(self.tx.GetHash())))

    def do_verify_input(self, tx, in_idx):
        raw_prev_tx = None
        tx_in = tx.vin[in_idx]
        txid = b2lx(tx_in.prevout.hash)
        prev_out_n = tx_in.prevout.n

        try:
            raw_prev_tx = self.handler.dock_widgets['Blockchain'].download_raw_tx(txid)
        except Exception as e:
#            self.status_message('Could not download previous tx {}'.format(txid), True)
            self.status_message(str(e), True)
            return False

        try:
            prev_tx = Transaction.deserialize(raw_prev_tx.decode('hex'))
            result = bitcoin.core.scripteval.VerifyScript(tx_in.scriptSig, prev_tx.vout[prev_out_n].scriptPubKey, tx, in_idx)
            self.result_edit.setText('Successfully verified input {}'.format(in_idx))
        except Exception as e:
            self.result_edit.setText(str(e))
            self.status_message(str(e), True)
            return False

        return True

    def do_verify_inputs(self, txt):
        self.needsFocus.emit()
        self.raw_tx_edit.setPlainText(txt)
        tx = Transaction.deserialize(txt.decode('hex'))
        failed_inputs = []
        self.result_edit.setText('Verifying...')
        for i in range(len(tx.vin)):
            if not self.do_verify_input(tx, i):
                failed_inputs.append(i)

        result = 'Successfully verified all inputs.'
        ret_val = True
        if failed_inputs:
            result = 'Failed to verify inputs: {}'.format(failed_inputs)
            ret_val = False
        if len(tx.vin) == 0:
            result = 'Transaction has no inputs.'
        self.result_edit.setText(result)
        return ret_val

    def verify_input(self):
        tx = None
        try:
            txt = str(self.raw_tx_edit.toPlainText())
            tx = Transaction.deserialize(txt.decode('hex'))
        except Exception:
            self.status_message('Could not deserialize transaction.', True)
            return
        in_idx = self.inputs_box.value()

        self.do_verify_input(tx, in_idx)

    def verify_inputs(self):
        txt = str(self.raw_tx_edit.toPlainText())
        self.do_verify_inputs(txt)

    def on_option_changed(self, key):
        if key == 'amount_format':
            self.needsUpdate.emit()

    def refresh_data(self):
        if self.tx:
            self.deserialize()

