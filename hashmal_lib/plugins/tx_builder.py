import bitcoin
from bitcoin.core import COutPoint, CTxIn, CTxOut, lx, CMutableOutPoint, CMutableTxIn, CMutableTxOut

from PyQt4.QtGui import *
from PyQt4 import QtCore

from hashmal_lib.core.script import Script
from hashmal_lib.core import Transaction, chainparams
from hashmal_lib.widgets.tx import TxWidget, InputsTree, OutputsTree, TimestampWidget
from hashmal_lib.widgets.script import ScriptEditor
from hashmal_lib.gui_utils import Separator, floated_buttons, AmountEdit, HBox, monospace_font, OutputAmountEdit
from base import BaseDock, Plugin, Category

def make_plugin():
    return Plugin(TxBuilder)

class TxBuilder(BaseDock):

    tool_name = 'Transaction Builder'
    description = 'Transaction Builder helps you create transactions.'
    is_large = True
    category = Category.Tx

    def __init__(self, handler):
        super(TxBuilder, self).__init__(handler)
        self.raw_tx.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.raw_tx.customContextMenuRequested.connect(self.context_menu)

    def init_data(self):
        self.tx = None

    def create_layout(self):
        vbox = QVBoxLayout()
        self.tabs = tabs = QTabWidget()

        tabs.addTab(self.create_version_locktime_tab(), '&Version/Locktime')
        tabs.addTab(self.create_inputs_tab(), '&Inputs')
        tabs.addTab(self.create_outputs_tab(), '&Outputs')
        tabs.addTab(self.create_review_tab(), '&Review')
        self.setFocusProxy(self.tabs)

        self.tx_field_widgets = []
        tabs.insertTab(3, self.create_other_tab(), 'Ot&her')
        self.adjust_tx_fields()

        # Build the tx if the Review tab is selected.
        def maybe_build(i):
            if str(tabs.tabText(i)) == '&Review':
                self.build_transaction()
        tabs.currentChanged.connect(maybe_build)

        vbox.addWidget(tabs)
        return vbox

    def context_menu(self, position):
        menu = self.raw_tx.createStandardContextMenu(position)

        txt = str(self.raw_tx.toPlainText())
        if txt:
            self.handler.add_plugin_actions(self, menu, 'raw_transaction', txt)

        menu.exec_(self.raw_tx.viewport().mapToGlobal(position))

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
        self.inputs_editor = InputsEditor(self.handler.gui, self.inputs_tree)
        self.inputs_editor.setEnabled(False)

        rm_input_edit = QSpinBox()
        rm_input_edit.setRange(0, 0)
        rm_input_button = QPushButton('Remove input')

        def update_enabled_widgets():
            num_inputs = len(self.inputs_tree.get_inputs())
            rm_input_edit.setRange(0, num_inputs - 1)
            for i in [rm_input_edit, rm_input_button, self.inputs_editor]:
                i.setEnabled(num_inputs > 0)

        def add_input():
            outpoint = CMutableOutPoint(n=0)
            new_input = CMutableTxIn(prevout=outpoint)
            self.inputs_tree.add_input(new_input)

            update_enabled_widgets()
            if len(self.inputs_tree.get_inputs()) > 0:
                self.inputs_tree.view.selectRow(self.inputs_tree.model.rowCount() - 1)

        def rm_input():
            self.inputs_tree.model.removeRow(rm_input_edit.value())
            update_enabled_widgets()

        update_enabled_widgets()

        add_input_button = QPushButton('New input')
        add_input_button.setToolTip('Add a new input')
        add_input_button.clicked.connect(add_input)

        rm_input_button.clicked.connect(rm_input)

        form.addRow(self.inputs_tree)
        form.addRow(Separator())

        form.addRow(self.inputs_editor)

        form.addRow(Separator())
        form.addRow(floated_buttons([add_input_button]))
        form.addRow('Remove input:', HBox(rm_input_edit, rm_input_button))

        w = QWidget()
        w.setLayout(form)
        return w

    def create_outputs_tab(self):
        form = QFormLayout()
        self.outputs_tree = OutputsTree()
        self.outputs_editor = OutputsEditor(self.handler.gui, self.outputs_tree)
        self.outputs_editor.setEnabled(False)

        rm_output_edit = QSpinBox()
        rm_output_edit.setRange(0, 0)
        rm_output_button = QPushButton('Remove output')

        def update_enabled_widgets():
            num_outputs = len(self.outputs_tree.get_outputs())
            rm_output_edit.setRange(0, num_outputs - 1)
            for i in [rm_output_edit, rm_output_button, self.outputs_editor]:
                i.setEnabled(num_outputs > 0)

        def add_output():
            new_output = CMutableTxOut(0)
            self.outputs_tree.add_output(new_output)

            update_enabled_widgets()
            if len(self.outputs_tree.get_outputs()) > 0:
                self.outputs_tree.view.selectRow(self.outputs_tree.model.rowCount() - 1)

        def rm_output():
            self.outputs_tree.model.removeRow(rm_output_edit.value())
            update_enabled_widgets()

        update_enabled_widgets()

        add_output_button = QPushButton('New output')
        add_output_button.setToolTip('Add a new output')
        add_output_button.clicked.connect(add_output)

        rm_output_button.clicked.connect(rm_output)

        form.addRow(self.outputs_tree)
        form.addRow(Separator())

        form.addRow(self.outputs_editor)

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

        form.addRow('Raw Tx:', self.raw_tx)
        form.addRow(self.tx_widget)

        w = QWidget()
        w.setLayout(form)
        return w

    def create_other_tab(self):
        self.tx_fields_layout = QFormLayout()

        w = QWidget()
        w.setLayout(self.tx_fields_layout)
        return w

    def build_transaction(self):
        self.tx_widget.clear()
        self.tx = tx = Transaction()
        tx.nVersion = self.version_edit.get_amount()
        for i in self.inputs_tree.get_inputs():
            tx.vin.append(i)
        for o in self.outputs_tree.get_outputs():
            tx.vout.append(o)
        tx.nLockTime = self.locktime_edit.get_amount()

        for name, w in self.tx_field_widgets:
            if not name in [field[0] for field in tx.fields]:
                continue
            value = str(w.text())
            default = getattr(tx, name)
            if isinstance(default, int):
                value = w.get_amount()
            setattr(tx, name, value)

        self.raw_tx.setText(bitcoin.core.b2x(tx.serialize()))

        self.tx_widget.set_tx(tx)

    def on_option_changed(self, key):
        if key in ['amount_format', 'chainparams']:
            self.needsUpdate.emit()

    def adjust_tx_fields(self):
        """Show or hide tx field widgets."""
        tx_fields = chainparams.get_tx_fields()
        for field in tx_fields:
            name = field[0]
            if name in ['nVersion', 'vin', 'vout', 'nLockTime']:
                continue

            default_value = field[3]
            if name not in [j[0] for j in self.tx_field_widgets]:
                widget = QLineEdit()
                if isinstance(default_value, int):
                    # Special case for timestamp fields.
                    if name == 'Timestamp':
                        widget = TimestampWidget()
                        widget.timestamp_raw.setReadOnly(False)
                    else:
                        widget = AmountEdit()
                widget.setText(str(default_value))
                label = QLabel(''.join([name, ':']))
                self.tx_field_widgets.append((name, widget))
                self.tx_fields_layout.addRow(label, widget)

        tx_field_names = [i[0] for i in tx_fields]
        for name, w in self.tx_field_widgets:
            l = self.tx_fields_layout.labelForField(w)
            if name in tx_field_names:
                w.show()
                l.show()
            else:
                w.hide()
                l.hide()

        if tx_field_names == ['nVersion', 'vin', 'vout', 'nLockTime']:
            self.tabs.setTabEnabled(3, False)
        else:
            self.tabs.setTabEnabled(3, True)

    def refresh_data(self):
        self.adjust_tx_fields()
        self.build_transaction()
        self.outputs_tree.model.amount_format_changed()

class BaseEditor(QWidget):
    """Item editor for inputs or outputs."""
    def __init__(self, tree, parent=None):
        super(BaseEditor, self).__init__(parent)
        self.tree = tree
        self.mapper = QDataWidgetMapper()
        self.mapper.setModel(self.tree.model)
        self.mapper.setSubmitPolicy(QDataWidgetMapper.ManualSubmit)
        self.tree.view.selectionModel().selectionChanged.connect(self.selection_changed)

    def selection_changed(self, selected, deselected):
        try:
            index = selected.indexes()[0]
            self.setEnabled(True)
        except IndexError:
            self.setEnabled(False)
            return
        self.mapper.setCurrentIndex(index.row())

    def do_submit(self):
        self.mapper.submit()

class InputsEditor(BaseEditor):
    def __init__(self, main_window, tree, parent=None):
        super(InputsEditor, self).__init__(tree, parent)
        self.prev_tx = QLineEdit()
        self.prev_tx.setToolTip('Transaction ID of the tx with the output being spent')

        self.prev_vout = AmountEdit()
        self.prev_vout.setToolTip('Output index of the previous transaction')

        self.script = ScriptEditor(main_window)
        self.script.setToolTip('Script that will be put on the stack before the previous output\'s script.')

        self.sequence = AmountEdit()
        self.sequence.setText('4294967295')
        maxify_input_sequence = QPushButton('Max')
        maxify_input_sequence.clicked.connect(lambda: self.sequence.setText('0xffffffff'))

        for i in [self.prev_tx, self.prev_vout, self.script, self.sequence]:
            i.setFont(monospace_font)

        self.mapper.addMapping(self.prev_tx, 0)
        self.mapper.addMapping(self.prev_vout, 1, 'amount')
        self.mapper.addMapping(self.script, 2, 'humanText')
        self.mapper.addMapping(self.sequence, 3, 'amount')

        submit_button = QPushButton('Save')
        submit_button.setToolTip('Update input with the above data')
        submit_button.clicked.connect(self.do_submit)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow('Previous Transaction: ', self.prev_tx)
        form.addRow('Previous Tx Output: ', self.prev_vout)
        form.addRow('Input script: ', self.script)
        seq_desc = QLabel('Sequence is mostly deprecated.\nIf an input has a sequence that\'s not the maximum value, the transaction\'s locktime will apply.')
        seq_desc.setWordWrap(True)
        form.addRow(seq_desc)
        form.addRow('Sequence: ', HBox(self.sequence, maxify_input_sequence))
        form.addRow(floated_buttons([submit_button]))

        self.setLayout(form)


class OutputsEditor(BaseEditor):
    def __init__(self, main_window, tree, parent=None):
        super(OutputsEditor, self).__init__(tree, parent)
        self.out_value = OutputAmountEdit()
        self.out_value.setToolTip('Output amount')
        self.script = ScriptEditor(main_window)
        self.script.setToolTip('Script that will be put on the stack after the input that spends it.')
        for i in [self.out_value, self.script]:
            i.setFont(monospace_font)

        self.mapper.addMapping(self.out_value, 0, 'satoshis')
        self.mapper.addMapping(self.script, 1, 'humanText')

        submit_button = QPushButton('Save')
        submit_button.setToolTip('Update input with the above data')
        submit_button.clicked.connect(self.do_submit)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow('Amount: ', self.out_value)
        form.addRow('Output script: ', self.script)
        form.addRow(floated_buttons([submit_button]))
        self.setLayout(form)

