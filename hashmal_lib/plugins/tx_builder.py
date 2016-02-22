import bitcoin
from bitcoin.core import COutPoint, CTxIn, CTxOut, x, lx, b2x, b2lx, CMutableOutPoint, CMutableTxIn, CMutableTxOut
from bitcoin.core.script import SIGHASH_ALL, SIGHASH_ANYONECANPAY, SignatureHash
from bitcoin.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from bitcoin.wallet import CBitcoinSecret

from PyQt4.QtGui import *
from PyQt4 import QtCore
from PyQt4.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant

from hashmal_lib.core.script import Script
from hashmal_lib.core import chainparams
from hashmal_lib.core.transaction import Transaction, sig_hash_name, sig_hash_explanation, sighash_types, sighash_types_by_value
from hashmal_lib.core.utils import format_hex_string
from hashmal_lib.widgets.tx import TxWidget, InputsTree, OutputsTree, TimestampWidget
from hashmal_lib.widgets.script import ScriptEditor
from hashmal_lib.gui_utils import Separator, floated_buttons, AmountEdit, HBox, monospace_font, OutputAmountEdit, RawRole
from base import BaseDock, Plugin, Category, augmenter
from item_types import ItemAction

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

    @augmenter
    def item_actions(self, *args):
        return [ItemAction(self.tool_name, 'Transaction', 'Edit', self.deserialize_item)]

    def init_data(self):
        self.tx = None

    def create_layout(self):
        vbox = QVBoxLayout()
        self.tabs = tabs = QTabWidget()

        tabs.addTab(self.create_version_locktime_tab(), '&Version/Locktime')
        tabs.addTab(self.create_inputs_tab(), '&Inputs')
        tabs.addTab(self.create_outputs_tab(), '&Outputs')
        tabs.addTab(self.create_review_tab(), '&Review')
        tabs.addTab(self.create_sign_tab(), 'Sig&n')
        self.setFocusProxy(self.tabs)

        self.tx_field_widgets = []
        tabs.insertTab(3, self.create_other_tab(), 'Ot&her')
        self.adjust_tx_fields()

        # Build the tx if the Review tab is selected.
        def maybe_build(i):
            if str(tabs.tabText(i)) == '&Review' or str(tabs.tabText(i)) == 'Sig&n':
                self.build_transaction()
        tabs.currentChanged.connect(maybe_build)

        vbox.addWidget(tabs)
        return vbox

    def context_menu(self, position):
        menu = self.raw_tx.createStandardContextMenu(position)

        txt = str(self.raw_tx.toPlainText())
        if txt:
            self.handler.add_plugin_actions(self, menu, txt)

        menu.exec_(self.raw_tx.viewport().mapToGlobal(position))

    def create_version_locktime_tab(self):
        form = QFormLayout()
        self.version_edit = AmountEdit()
        self.version_edit.setText('1')
        self.version_edit.setWhatsThis('Use this field to specify the version of your transaction. In Bitcoin, transactions are currently version 1.')

        self.locktime_edit = AmountEdit()
        self.locktime_edit.setText('0')
        self.locktime_edit.setWhatsThis('Use this field to specify the locktime of your transaction. For most common transactions, locktime is zero.')

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
        self.inputs_tree.view.setWhatsThis('The inputs of your transaction are displayed here.')
        self.inputs_editor = InputsEditor(self.handler.gui, self.inputs_tree)
        self.inputs_editor.setEnabled(False)

        def update_enabled_widgets():
            num_inputs = len(self.inputs_tree.get_inputs())
            self.inputs_editor.setEnabled(num_inputs > 0)

        def add_input():
            outpoint = CMutableOutPoint(n=0)
            new_input = CMutableTxIn(prevout=outpoint)
            self.inputs_tree.add_input(new_input)

            update_enabled_widgets()
            if len(self.inputs_tree.get_inputs()) > 0:
                self.inputs_tree.view.selectRow(self.inputs_tree.model.rowCount() - 1)

        update_enabled_widgets()

        add_input_button = QPushButton('New input')
        add_input_button.setToolTip('Add a new input')
        add_input_button.setWhatsThis('Clicking this button will add a new input to your transaction.')
        add_input_button.clicked.connect(add_input)

        form.addRow(self.inputs_tree)
        form.addRow(Separator())

        form.addRow(self.inputs_editor)

        form.addRow(Separator())
        form.addRow(floated_buttons([add_input_button]))

        w = QWidget()
        w.setLayout(form)
        return w

    def create_outputs_tab(self):
        form = QFormLayout()
        self.outputs_tree = OutputsTree()
        self.outputs_tree.view.setWhatsThis('The outputs of your transaction are displayed here.')
        self.outputs_editor = OutputsEditor(self.handler.gui, self.outputs_tree)
        self.outputs_editor.setEnabled(False)

        def update_enabled_widgets():
            num_outputs = len(self.outputs_tree.get_outputs())
            self.outputs_editor.setEnabled(num_outputs > 0)

        def add_output():
            new_output = CMutableTxOut(0)
            self.outputs_tree.add_output(new_output)

            update_enabled_widgets()
            if len(self.outputs_tree.get_outputs()) > 0:
                self.outputs_tree.view.selectRow(self.outputs_tree.model.rowCount() - 1)

        update_enabled_widgets()

        add_output_button = QPushButton('New output')
        add_output_button.setToolTip('Add a new output')
        add_output_button.setWhatsThis('Clicking this button will add a new output to your transaction.')
        add_output_button.clicked.connect(add_output)

        form.addRow(self.outputs_tree)
        form.addRow(Separator())

        form.addRow(self.outputs_editor)

        form.addRow(Separator())
        form.addRow(floated_buttons([add_output_button]))

        w = QWidget()
        w.setLayout(form)
        return w

    def create_review_tab(self):
        form = QFormLayout()

        self.raw_tx = QTextEdit()
        self.raw_tx.setWhatsThis('The transaction you build is displayed here.')
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

    def create_sign_tab(self):
        self.sighash_widget = SigHashWidget(self)
        return self.sighash_widget

    def deserialize_item(self, item):
        self.deserialize_raw(item.raw())

    def deserialize_raw(self, rawtx):
        """Update editor widgets with rawtx's data."""
        self.needsFocus.emit()
        try:
            tx = Transaction.deserialize(x(rawtx))
        except Exception:
            return
        else:
            self.version_edit.set_amount(tx.nVersion)
            self.inputs_tree.model.set_tx(tx)
            self.outputs_tree.model.set_tx(tx)
            self.locktime_edit.set_amount(tx.nLockTime)
            for name, w in self.tx_field_widgets:
                if name in ['nVersion', 'vin', 'vout', 'nLockTime']:
                    continue
                try:
                    value = getattr(tx, name)
                except AttributeError:
                    continue
                if isinstance(w, AmountEdit):
                    w.set_amount(value)
                else:
                    w.setText(str(value))
            self.build_transaction()

    def build_transaction(self):
        self.tx_widget.clear()
        self.sighash_widget.clear()
        self.tx = tx = Transaction()
        tx.nVersion = self.version_edit.get_amount()
        tx.vin = self.inputs_tree.get_inputs()
        tx.vout = self.outputs_tree.get_outputs()
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
        self.sighash_widget.set_tx(tx)

    def on_option_changed(self, key):
        if key == 'chainparams':
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

    def do_delete(self):
        index = self.mapper.currentIndex()
        self.tree.model.removeRow(index)

    def do_submit(self):
        self.mapper.submit()

class InputsEditor(BaseEditor):
    def __init__(self, main_window, tree, parent=None):
        super(InputsEditor, self).__init__(tree, parent)
        self.prev_tx = QLineEdit()
        self.prev_tx.setToolTip('Transaction ID of the tx with the output being spent')
        self.prev_tx.setWhatsThis('Use this field to specify the transaction that contains the output you\'re spending.')

        self.prev_vout = AmountEdit()
        self.prev_vout.setToolTip('Output index of the previous transaction')
        self.prev_vout.setWhatsThis('Use this field to specify the output you are spending of the previous transaction.')

        self.script = ScriptEditor(main_window)
        self.script.setToolTip('Script that will be put on the stack before the previous output\'s script.')
        self.script.setWhatsThis('Enter a script here. This script will be evaluated directly before the script of the output you are spending. Any values that are pushed onto the stack when this script finishes its execution are present when the output script is evaluated afterward.')

        self.sequence = AmountEdit()
        self.sequence.setText('4294967295')
        self.sequence.setWhatsThis('Use this field to specify the sequence value. It\'s likely that you should leave this as its default (maximum) value.')
        maxify_input_sequence = QPushButton('Max')
        maxify_input_sequence.clicked.connect(lambda: self.sequence.setText('0xffffffff'))
        maxify_input_sequence.setWhatsThis('This button will set the sequence to its default value.')

        for i in [self.prev_tx, self.prev_vout, self.script, self.sequence]:
            i.setFont(monospace_font)

        self.mapper.addMapping(self.prev_tx, 0)
        self.mapper.addMapping(self.prev_vout, 1, 'amount')
        self.mapper.addMapping(self.script, 2, 'humanText')
        self.mapper.addMapping(self.sequence, 3, 'amount')

        delete_button = QPushButton('Remove Input')
        delete_button.setToolTip('Remove this input from the transaction')
        delete_button.clicked.connect(self.do_delete)
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
        form.addRow(floated_buttons([delete_button, submit_button]))

        self.setLayout(form)


class OutputsEditor(BaseEditor):
    def __init__(self, main_window, tree, parent=None):
        super(OutputsEditor, self).__init__(tree, parent)
        self.out_value = OutputAmountEdit()
        self.out_value.setToolTip('Output amount')
        self.out_value.setWhatsThis('Use this field to specify the value of this output. Depending on your settings, the value may be in satoshis (no decimals), or coins (1 coin = 100000000 satoshis).')
        self.script = ScriptEditor(main_window)
        self.script.setToolTip('Script that will be put on the stack after the input that spends it.')
        self.script.setWhatsThis('Enter a script here. This script will be evaluated directly after the script of the input that spends it in the future. This script will have access to the values that are on the stack after the input script that spends it has executed.')
        for i in [self.out_value, self.script]:
            i.setFont(monospace_font)

        self.mapper.addMapping(self.out_value, 0, 'satoshis')
        self.mapper.addMapping(self.script, 1, 'humanText')

        submit_button = QPushButton('Save')
        submit_button.setToolTip('Update input with the above data')
        submit_button.clicked.connect(self.do_submit)
        delete_button = QPushButton('Remove Output')
        delete_button.setToolTip('Remove this output from the transaction')
        delete_button.clicked.connect(self.do_delete)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow('Amount: ', self.out_value)
        form.addRow('Output script: ', self.script)
        form.addRow(floated_buttons([delete_button, submit_button]))
        self.setLayout(form)


# Widgets for signing transactions.

class SigHashModel(QAbstractTableModel):
    """Models a transaction's signature hash."""
    SigHashName = 5
    SigHashExplanation = 6
    def __init__(self, parent=None):
        super(SigHashModel, self).__init__(parent)
        self.clear()

    def clear(self):
        self.beginResetModel()
        self.utxo_script = None
        self.tx = None
        self.inIdx = 0
        self.sighash_type = SIGHASH_ALL
        self.anyone_can_pay = False
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 1

    def columnCount(self, parent=QModelIndex()):
        return 7

    def data(self, index, role = Qt.DisplayRole):
        if not index.isValid():
            return None

        if role not in [Qt.DisplayRole, Qt.ToolTipRole, Qt.EditRole]:
            return None

        data = None
        c = index.column()
        if c == 0:
            if self.utxo_script:
                data = self.utxo_script.get_human()
        elif c == 1:
            if self.tx:
                data = b2x(self.tx.serialize())
        elif c == 2:
            data = self.inIdx
        elif c == 3:
            data = sighash_types_by_value[self.sighash_type]
        elif c == 4:
            if role == Qt.CheckStateRole:
                data = Qt.Checked if self.anyone_can_pay else Qt.Unchecked
            else:
                data = self.anyone_can_pay
        elif c == self.SigHashName:
            data = sig_hash_name(self.sighash_type | SIGHASH_ANYONECANPAY if self.anyone_can_pay else self.sighash_type)
        elif c == self.SigHashExplanation:
            data = sig_hash_explanation(self.sighash_type | SIGHASH_ANYONECANPAY if self.anyone_can_pay else self.sighash_type)

        return data

    def setData(self, index, value, role = Qt.EditRole):
        if not index.isValid():
            return False
        c = index.column()

        if c == 0:
            try:
                self.utxo_script = Script.from_human(str(value.toString()))
            except Exception:
                return False
            self.dataChanged.emit(self.index(index.row(), c), self.index(index.row(), c))
        elif c == 1:
            try:
                self.tx = Transaction.deserialize(x(str(value.toString())))
            except Exception:
                return False
            self.dataChanged.emit(self.index(index.row(), c), self.index(index.row(), c))
        elif c == 2:
            tmpIdx, ok = value.toInt()
            if not ok:
                return False
            self.inIdx = tmpIdx
            self.dataChanged.emit(self.index(index.row(), c), self.index(index.row(), c))
        elif c == 3:
            if role == Qt.EditRole:
                val = str(value.toString())
                sighash_type = sighash_types.get(val)
                if not sighash_type:
                    return False
                self.sighash_type = sighash_type
            elif role == RawRole:
                tmpType, ok = value.toInt()
                if not ok:
                    return False
                self.sighash_type = tmpType
            self.dataChanged.emit(self.index(index.row(), c), self.index(index.row(), self.SigHashExplanation))
        elif c == 4:
            self.anyone_can_pay = value.toBool()
            self.dataChanged.emit(self.index(index.row(), c), self.index(index.row(), self.SigHashExplanation))

        return True

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def set_tx(self, tx):
        self.setData(self.index(0, 1), QVariant(b2x(tx.serialize())))

    def get_fields(self):
        """Returns the fields necessary to sign the transaction."""
        hash_type = self.sighash_type
        if self.anyone_can_pay:
            hash_type = hash_type | SIGHASH_ANYONECANPAY
        return (self.utxo_script, self.tx, self.inIdx, hash_type)

    def set_fields(self, script=None, txTo=None, inIdx=None, hashType=None):
        """Populate model.

        Args:
            script (str): Human-readable script.
            txTo (Transaction): Transaction.
            inIdx (int): Input index.
            hashType (int): SigHash type.

        """
        if script is not None:
            self.setData(self.index(0, 0), QVariant(script))
        if txTo is not None:
            self.setData(self.index(0, 1), QVariant(b2x(txTo.serialize())))
        if inIdx is not None:
            self.setData(self.index(0, 2), QVariant(inIdx))
        if hashType is not None:
            self.setData(self.index(0, 3), QVariant(hashType & 0x1f), RawRole)
            self.setData(self.index(0, 4), QVariant(hashType & SIGHASH_ANYONECANPAY))

class SigHashWidget(QWidget):
    """Model and view of a transaction's signature hash."""
    def __init__(self, dock, parent=None):
        super(SigHashWidget, self).__init__(parent)
        self.dock = dock
        self.model = SigHashModel()

        self.mapper = QDataWidgetMapper()
        self.mapper.setModel(self.model)

        self.utxo_script = ScriptEditor(self.dock.handler.gui)
        self.utxo_script.setToolTip('Script from the unspent output')
        self.utxo_script.setWhatsThis('Enter the output script from the unspent output you are spending here.')
        self.utxo_script.setFixedHeight(42)
        self.inIdx = QSpinBox()
        self.inIdx.setRange(0, 0)
        self.inIdx.setToolTip('Input to sign')
        self.inIdx.setWhatsThis('This specifies the input that will be signed.')
        self.sighash_type = QComboBox()
        self.sighash_type.setToolTip('Signature hash type')
        self.sighash_type.setWhatsThis('Use this to specify the signature hash flag you want to use. The flags have different effects and are explained in the box to the right.')
        self.sighash_type.addItems(['SIGHASH_ALL', 'SIGHASH_NONE', 'SIGHASH_SINGLE'])
        self.anyone_can_pay = QCheckBox('SIGHASH_ANYONECANPAY')
        self.anyone_can_pay.setWhatsThis('Use this to add the ANYONECANPAY flag to your signature hash type. Its effect is explained in the box to the right.')
        self.sighash_name = QLineEdit()
        self.sighash_name.setToolTip('Signature hash name')
        self.sighash_name.setWhatsThis('The full name of your current signature hash type is shown here.')
        self.sighash_explanation = QTextEdit()
        self.sighash_explanation.setToolTip('Signature hash explanation')
        self.sighash_explanation.setWhatsThis('A description of your current signature hash type is shown here.')
        for i in [self.sighash_name, self.sighash_explanation]:
            i.setReadOnly(True)

        self.mapper.addMapping(self.utxo_script, 0, 'humanText')
        self.mapper.addMapping(self.inIdx, 2)
        self.mapper.addMapping(self.sighash_type, 3)
        self.mapper.addMapping(self.anyone_can_pay, 4)
        self.mapper.addMapping(self.sighash_name, SigHashModel.SigHashName)
        self.mapper.addMapping(self.sighash_explanation, SigHashModel.SigHashExplanation)

        self.privkey_edit = QLineEdit()
        self.privkey_edit.setWhatsThis('Use this to enter a private key with which to sign the transaction.')
        self.privkey_edit.setPlaceholderText('Enter a private key')
        self.sign_button = QPushButton('Sign')
        self.sign_button.setToolTip('Sign transaction')
        self.sign_button.setWhatsThis('Clicking this button will attempt to sign the transaction with your private key.')
        self.sign_button.clicked.connect(self.sign_transaction)
        self.verify_script = QCheckBox('Verify script')
        self.verify_script.setToolTip('Verify input script')
        self.verify_script.setWhatsThis('If this is checked, Hashmal will attempt to verify the completed script.')
        signing_form = QFormLayout()
        privkey_hbox = QHBoxLayout()
        privkey_hbox.addWidget(self.privkey_edit, stretch=1)
        privkey_hbox.addWidget(self.sign_button)
        privkey_hbox.addWidget(self.verify_script)
        self.result_edit = QLineEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setPlaceholderText('Result of signing')
        self.result_edit.setWhatsThis('The result of signing the transaction will be shown here.')
        signing_form.addRow('Private Key:', privkey_hbox)
        signing_form.addRow('Result:', self.result_edit)

        tx_form = QFormLayout()
        tx_form.addRow('Unspent Output Script:', self.utxo_script)
        tx_form.addRow('Input To Sign:', self.inIdx)

        sighash_controls = QFormLayout()
        sighash_controls.addRow('SigHash flag:', self.sighash_type)
        sighash_controls.addRow(self.anyone_can_pay)
        sighash_info = QVBoxLayout()
        sighash_info.addWidget(self.sighash_name)
        sighash_info.addWidget(self.sighash_explanation)
        sighash_layout = QHBoxLayout()
        sighash_layout.addLayout(sighash_controls)
        sighash_layout.addLayout(sighash_info)

        vbox = QVBoxLayout()
        vbox.addLayout(signing_form)
        vbox.addWidget(Separator())
        vbox.addLayout(tx_form)
        vbox.addWidget(Separator())
        vbox.addLayout(sighash_layout)
        self.setLayout(vbox)

        self.mapper.toFirst()

    def set_tx(self, tx):
        self.inIdx.setRange(0, len(tx.vin) - 1)
        self.model.set_tx(tx)
        self.mapper.toFirst()

    def clear(self):
        self.result_edit.clear()
        self.result_edit.setProperty('hasError', False)
        self.style().polish(self.result_edit)
        self.model.clear()

    def set_result_message(self, text, error=False):
        self.result_edit.setText(text)
        self.result_edit.setProperty('hasError', error)
        self.style().polish(self.result_edit)
        if error:
            self.dock.error(text)
        else:
            self.dock.info(text)

    def sign_transaction(self):
        """Sign the transaction."""
        script, txTo, inIdx, hash_type = self.model.get_fields()
        if inIdx >= len(txTo.vin):
            self.set_result_message('Nonexistent input specified for signing.', error=True)
            return
        if not script:
            self.set_result_message('Invalid output script.', error=True)
            return
        privkey = self.get_private_key()
        if not privkey:
            self.set_result_message('Could not parse private key.', error=True)
            return
        sig_hash = chainparams.signature_hash(script, txTo, inIdx, hash_type)

        sig = privkey.sign(sig_hash)
        hash_type_hex = format_hex_string(hex(hash_type), with_prefix=False).decode('hex')
        sig = sig + hash_type_hex
        txTo.vin[inIdx].scriptSig = Script([sig, privkey.pub])

        if self.verify_script.isChecked():
            # Try verify
            try:
                VerifyScript(txTo.vin[inIdx].scriptSig, script, txTo, inIdx, (SCRIPT_VERIFY_P2SH,))
            except Exception as e:
                self.set_result_message('Error when verifying: %s' % str(e), error=True)
                return

        self.dock.deserialize_raw(b2x(txTo.serialize()))
        # Deserializing a tx clears the model, so re-populate.
        self.model.set_fields(script=script.get_human(), inIdx=inIdx, hashType=hash_type)
        self.set_result_message('Successfully set scriptSig for input %d (SigHash type: %s).' % (inIdx, sig_hash_name(hash_type)))

    def get_private_key(self):
        """Attempt to parse the private key that was input."""
        txt = str(self.privkey_edit.text())
        privkey = None
        if len(txt) == 64:
            privkey = CBitcoinSecret.from_secret_bytes(x(txt))

        return privkey


