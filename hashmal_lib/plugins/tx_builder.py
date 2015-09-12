import bitcoin
from bitcoin.core import COutPoint, CTxIn, CTxOut, CMutableTransaction, lx

from PyQt4.QtGui import *

from hashmal_lib.core.script import Script
from hashmal_lib.tx_widget import TxWidget, InputsTree, OutputsTree
from hashmal_lib.gui_utils import Separator, floated_buttons, AmountEdit, HBox, monospace_font
from base import BaseDock, Plugin

def make_plugin():
    return Plugin([TxBuilder])

class TxBuilder(BaseDock):

    def init_metadata(self):
        self.tool_name = 'Transaction Builder'
        self.description = 'Transaction Builder helps you create transactions.'
        self.is_large = True

    def init_data(self):
        self.tx = None

    def create_layout(self):
        vbox = QVBoxLayout()
        tabs = QTabWidget()

        tabs.addTab(self.create_version_locktime_tab(), '&Version/Locktime')
        tabs.addTab(self.create_inputs_tab(), '&Inputs')
        tabs.addTab(self.create_outputs_tab(), '&Outputs')
        tabs.addTab(self.create_review_tab(), '&Review')

        vbox.addWidget(tabs)
        return vbox


    def create_version_locktime_tab(self):
        form = QFormLayout()
        self.version_edit = AmountEdit()
        self.version_edit.setText('1')

        self.locktime_edit = AmountEdit()
        self.locktime_edit.setText('0')

        version_desc = QLabel('A transaction\'s version determines how it is interpreted.\n\nBitcoin transactions are currently version 1.')
        locktime_desc = QLabel('A transaction\'s locktime defines the earliest time or block that it may be added to the blockchain.\n\nLocktime only applies if it\'s non-zero and at least one input has a Sequence that\'s not the maximum possible value.')
        for i in [version_desc, locktime_desc]:
            i.setWordWrap(True)
        for i in [self.version_edit, self.locktime_edit]:
            i.setFont(monospace_font)

        form.addRow(version_desc)
        form.addRow('Version:', self.version_edit)
        form.addRow(Separator())
        form.addRow(locktime_desc)
        form.addRow('Locktime:', self.locktime_edit)

        w = QWidget()
        w.setLayout(form)
        return w

    def create_inputs_tab(self):
        form = QFormLayout()
        self.inputs_tree = InputsTree()

        input_prev_tx = QLineEdit()
        input_prev_tx.setToolTip('Transaction ID of the tx with the output being spent')

        input_prev_vout = AmountEdit()
        input_prev_vout.setToolTip('Output index of the previous transaction')

        input_script = QTextEdit()
        input_script.setToolTip('Script that will be put on the stack before the previous output\'s script.')

        input_sequence = AmountEdit()
        input_sequence.setText('4294967295')
        maxify_input_sequence = QPushButton('Max')
        maxify_input_sequence.clicked.connect(lambda: input_sequence.setText('0xffffffff'))

        rm_input_edit = QSpinBox()
        rm_input_edit.setRange(0, 0)
        rm_input_button = QPushButton('Remove input')

        def add_input():
            try:
                outpoint = COutPoint(lx(str(input_prev_tx.text())), input_prev_vout.get_amount())
                in_script = Script.from_human(str(input_script.toPlainText()))
                new_input = CTxIn(outpoint, in_script.get_hex().decode('hex'), input_sequence.get_amount())
            except Exception as e:
                self.status_message(str(e), True)
                return
            else:
                self.inputs_tree.add_input(new_input)
                rm_input_edit.setRange(0, len(self.inputs_tree.get_inputs()) - 1)

        def rm_input():
            in_num = rm_input_edit.value()
            self.inputs_tree.model.takeRow(in_num)
            rm_input_edit.setRange(0, len(self.inputs_tree.get_inputs()) - 1)

        add_input_button = QPushButton('Add input')
        add_input_button.setToolTip('Add the above input')
        add_input_button.clicked.connect(add_input)

        rm_input_button.clicked.connect(rm_input)

        for i in [input_prev_tx, input_prev_vout, input_script, input_sequence]:
            i.setFont(monospace_font)

        form.addRow(self.inputs_tree)
        form.addRow(Separator())

        form.addRow('Previous Transaction:', input_prev_tx)
        form.addRow('Previous Tx Output:', input_prev_vout)
        form.addRow('Input script:', input_script)
        seq_desc = QLabel('Sequence is mostly deprecated.\nIf an input has a sequence that\'s not the maximum value, the transaction\'s locktime will apply.')
        seq_desc.setWordWrap(True)
        form.addRow(seq_desc)
        form.addRow('Sequence:', HBox(input_sequence, maxify_input_sequence))

        form.addRow(Separator())
        form.addRow(floated_buttons([add_input_button]))
        form.addRow('Remove input:', HBox(rm_input_edit, rm_input_button))

        w = QWidget()
        w.setLayout(form)
        return w

    def create_outputs_tab(self):
        form = QFormLayout()
        self.outputs_tree = OutputsTree()

        output_value = QLineEdit()

        output_script = QTextEdit()
        output_script.setToolTip('Script that will be put on the stack after the input that spends it.')

        rm_output_edit = QSpinBox()
        rm_output_edit.setRange(0, 0)
        rm_output_button = QPushButton('Remove output')

        def add_output():
            try:
                val_str = str(output_value.text())
                value = 0
                if '.' in val_str:
                    value = int(float(val_str) * pow(10, 8))
                else:
                    value = int(val_str)
                out_script = Script.from_human(str(output_script.toPlainText()))
                new_output = CTxOut(value, out_script.get_hex().decode('hex'))
            except Exception as e:
                self.status_message(str(e), True)
                return
            else:
                self.outputs_tree.add_output(new_output)
                rm_output_edit.setRange(0, len(self.outputs_tree.get_outputs()) - 1)

        def rm_output():
            out_n = rm_output_edit.value()
            self.outputs_tree.model.takeRow(out_n)
            rm_output_edit.setRange(0, len(self.outputs_tree.get_outputs()) - 1)

        add_output_button = QPushButton('Add output')
        add_output_button.setToolTip('Add the above output')
        add_output_button.clicked.connect(add_output)

        rm_output_button.clicked.connect(rm_output)

        value_desc = QLabel('Include a decimal point if this value is not in satoshis.')
        value_desc.setWordWrap(True)

        for i in [output_value, output_script]:
            i.setFont(monospace_font)

        form.addRow(self.outputs_tree)
        form.addRow(Separator())

        form.addRow(value_desc)
        form.addRow('Value:', output_value)
        form.addRow('Output script:', output_script)

        form.addRow(Separator())
        form.addRow(floated_buttons([add_output_button]))
        form.addRow('Remove output:', HBox(rm_output_edit, rm_output_button))

        w = QWidget()
        w.setLayout(form)
        return w

    def create_review_tab(self):
        form = QFormLayout()

        self.raw_tx = QTextEdit()
        self.raw_tx.setReadOnly(True)

        self.tx_widget = TxWidget()

        build_button = QPushButton('Build transaction')
        build_button.setToolTip('Build a tx from the data in the previous tabs')
        build_button.clicked.connect(self.build_transaction)

        form.addRow('Raw Tx:', self.raw_tx)
        form.addRow(self.tx_widget)
        form.addRow(floated_buttons([build_button]))

        w = QWidget()
        w.setLayout(form)
        return w

    def build_transaction(self):
        self.tx_widget.clear()
        self.tx = tx = CMutableTransaction()
        tx.nVersion = self.version_edit.get_amount()
        for i in self.inputs_tree.get_inputs():
            tx.vin.append(i)
        for o in self.outputs_tree.get_outputs():
            tx.vout.append(o)
        tx.nLockTime = self.locktime_edit.get_amount()

        self.raw_tx.setText(bitcoin.core.b2x(tx.serialize()))

        self.tx_widget.set_tx(tx)

    def on_option_changed(self, key):
        if key == 'amount_format':
            self.needsUpdate.emit()

    def refresh_data(self):
        self.build_transaction()
        self.outputs_tree.amount_format_changed()
