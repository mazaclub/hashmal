import datetime

import bitcoin
from bitcoin.core import COutPoint, CTxIn, CTxOut, lx
from PyQt4.QtGui import *
from PyQt4 import QtCore

from gui_utils import Amount, monospace_font, HBox, floated_buttons, RawRole
from hashmal_lib.core.script import Script


class InputsTree(QWidget):
    """Model and View showing a transaction's inputs."""
    def __init__(self, parent=None):
        super(InputsTree, self).__init__(parent)
        self.model = QStandardItemModel()
        self.view = QTreeView()
        self.model.setColumnCount(3)
        self.model.setHorizontalHeaderLabels(['Prev Output', 'scriptSig', 'Sequence'])
        self.view.setAlternatingRowColors(True)
        self.view.setModel(self.model)
        self.view.header().setStretchLastSection(False)
        self.view.header().setResizeMode(0, QHeaderView.Interactive)
        self.view.header().setResizeMode(1, QHeaderView.Stretch)
        self.view.header().setResizeMode(2, QHeaderView.Interactive)
        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.customContextMenu)
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self.view)
        self.setLayout(vbox)

    def clear(self):
        self.model.setRowCount(0)

    def copy_script(self):
        """Copy the scriptSig to clipboard."""
        item = self.model.itemFromIndex(self.view.selectedIndexes()[1])
        QApplication.clipboard().setText(item.text())

    def copy_script_hex(self):
        """Copy the scriptSig to clipboard as hex."""
        item = self.model.itemFromIndex(self.view.selectedIndexes()[1])
        txt = item.data(RawRole).toString()
        QApplication.clipboard().setText(txt)

    def customContextMenu(self, pos):
        if len(self.view.selectedIndexes()) == 0:
            return
        menu = QMenu()
        menu.addAction('Copy Input Script', self.copy_script)
        menu.addAction('Copy Input Script Hex', self.copy_script_hex)

        menu.exec_(self.view.viewport().mapToGlobal(pos))

    def add_input(self, i):
        in_script = Script(i.scriptSig)
        item = map(lambda x: QStandardItem(x), [
            str(i.prevout),
            in_script.get_human(),
            str(i.nSequence)
        ])
        # Raw scriptSig is stored as RawRole.
        item[1].setData(QtCore.QVariant(in_script.get_hex()), RawRole)
        self.model.appendRow(item)

    def get_inputs(self):
        vin = []
        for i in range(self.model.rowCount()):
            prev_hash, prev_vout = str(self.model.item(i, 0).text()).split(':')
            in_script = str(self.model.item(i, 1).data(RawRole).toString())
            sequence = int(self.model.item(i, 2).text())

            outpoint = COutPoint(lx(prev_hash), int(prev_vout))
            i_input = CTxIn(outpoint, in_script.decode('hex'), sequence)
            vin.append(i_input)
        return vin

class OutputsTree(QWidget):
    """Model and View showing a transaction's outputs."""
    def __init__(self, parent=None):
        super(OutputsTree, self).__init__(parent)
        self.model = QStandardItemModel()
        self.view = QTreeView()
        self.model.setColumnCount(2)
        self.model.setHorizontalHeaderLabels(['Value', 'scriptPubKey'])
        self.view.setAlternatingRowColors(True)
        self.view.setModel(self.model)
        self.view.header().setResizeMode(0, QHeaderView.Interactive)
        self.view.header().setResizeMode(1, QHeaderView.Stretch)
        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.customContextMenu)
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self.view)
        self.setLayout(vbox)

    def clear(self):
        self.model.setRowCount(0)

    def copy_script(self):
        """Copy the scriptPubKey to clipboard."""
        item = self.model.itemFromIndex(self.view.selectedIndexes()[1])
        QApplication.clipboard().setText(item.text())

    def copy_script_hex(self):
        """Copy the scriptPubKey to clipboard as hex."""
        item = self.model.itemFromIndex(self.view.selectedIndexes()[1])
        txt = item.data(RawRole).toString()
        QApplication.clipboard().setText(txt)

    def customContextMenu(self, pos):
        if len(self.view.selectedIndexes()) == 0:
            return
        menu = QMenu()
        menu.addAction('Copy Output Script', self.copy_script)
        menu.addAction('Copy Output Script Hex', self.copy_script_hex)

        menu.exec_(self.view.viewport().mapToGlobal(pos))

    def add_output(self, o):
        out_script = Script(o.scriptPubKey)
        value = Amount(o.nValue)
        item = map(lambda x: QStandardItem(x), [
            value.get_str(),
            out_script.get_human()
        ])
        # Value in satoshis is stored as RawRole.
        item[0].setData(QtCore.QVariant(value.satoshis), RawRole)
        # Raw scriptPubKey is stored as RawRole.
        item[1].setData(QtCore.QVariant(out_script.get_hex()), RawRole)
        self.model.appendRow(item)

    def get_outputs(self):
        vout = []
        for i in range(self.model.rowCount()):
            value, ok = self.model.item(i, 0).data(RawRole).toInt()
            if not ok:
                raise Exception('Could not get satoshis for output %d' % i)
                return
            out_script = Script(str(self.model.item(i, 1).data(RawRole).toString()).decode('hex'))
            i_output = CTxOut(value, out_script.get_hex().decode('hex'))
            vout.append(i_output)
        return vout

    def amount_format_changed(self):
        """Parents should call this when config.amount_format changes.

        Refreshes TxOut amounts with the new format.
        """
        vout = self.get_outputs()
        self.clear()
        for o in vout:
            self.add_output(o)

class LockTimeWidget(QWidget):
    """Displays a transaction's locktime.

    Displays the raw int and the human-readable interpretation
    side-by-side."""
    def __init__(self, parent=None):
        super(LockTimeWidget, self).__init__(parent)
        self.locktime_raw = QLineEdit()
        self.locktime_human = QLineEdit()
        for i in [self.locktime_raw, self.locktime_human]:
            i.setReadOnly(True)
        hbox = HBox(self.locktime_raw, self.locktime_human)
        hbox.setContentsMargins(0, 6, 0, 0)
        self.setLayout(hbox)

    def clear(self):
        self.locktime_raw.clear()
        self.locktime_human.clear()

    def set_locktime(self, locktime):
        """Formats the raw and human-readable locktimes."""
        self.locktime_raw.setText(str(locktime))
        if locktime < 500000000 and locktime > 0:
            self.locktime_human.setText('Block %d' % locktime)
        elif locktime >= 500000000:
            time = datetime.datetime.utcfromtimestamp(locktime)
            self.locktime_human.setText(' '.join([time.strftime('%Y-%m-%d %H:%M:%S'), 'UTC']))
        else:
            self.locktime_human.setText('Not locked.')

class TxProperties(QWidget):
    """Displays properties of a transaction (e.g. isFinal)."""
    def __init__(self, parent=None):
        super(TxProperties, self).__init__(parent)
        self.tx_size_edit = QLineEdit()
        self.tx_size_edit.setReadOnly(True)
        tx_size = HBox(QLabel('Size:'), self.tx_size_edit)
        tx_size.setContentsMargins(0, 0, 0, 0)
        self.tx_size = QWidget()
        self.tx_size.setLayout(tx_size)
        self.tx_size.setToolTip('Size (in bytes) of the serialized tx')

        self.is_final = QCheckBox('Is Final')
        self.is_final.setToolTip('True if all inputs have a Sequence of 0xffffffff')
        self.is_coinbase = QCheckBox('Is Coinbase')
        self.is_coinbase.setToolTip('True if the tx generates new coins via mining')
        for i in [self.is_final, self.is_coinbase]:
            i.setEnabled(False)
        hbox = floated_buttons([self.tx_size, self.is_final, self.is_coinbase], left=True)
        hbox.setContentsMargins(16, 0, 0, 0)
        self.setLayout(hbox)

    def clear(self):
        self.tx_size_edit.clear()
        self.is_final.setChecked(False)
        self.is_coinbase.setChecked(False)

    def set_tx(self, tx):
        self.tx_size_edit.setText(str(len(tx.serialize())))
        if len(tx.vin) > 0:
            self.is_final.setChecked(all(i.is_final() for i in tx.vin))
        else:
            self.is_final.setChecked(False)
        self.is_coinbase.setChecked(tx.is_coinbase())

class TxWidget(QWidget):
    """Displays the deserialized fields of a transaction."""
    def __init__(self, parent=None):
        super(TxWidget, self).__init__(parent)
        form = QFormLayout()

        self.tx_id = QLineEdit()
        self.tx_id.setReadOnly(True)

        self.version_edit = QLineEdit()
        self.version_edit.setReadOnly(True)
        self.inputs_tree = inputs = InputsTree()
        self.outputs_tree = outputs = OutputsTree()
        self.locktime_edit = LockTimeWidget()

        self.tx_properties = TxProperties()

        form.addRow('Tx ID:', self.tx_id)
        form.addRow('Version:', self.version_edit)
        form.addRow('Inputs:', inputs)
        form.addRow('Outputs:', outputs)
        form.addRow('LockTime:', self.locktime_edit)
        form.addRow('Metadata:', self.tx_properties)

        self.setLayout(form)

    def set_tx(self, tx):
        self.version_edit.setText(str(tx.nVersion))

        for i in tx.vin:
            self.add_input(i)

        for o in tx.vout:
            self.add_output(o)

        self.locktime_edit.set_locktime(tx.nLockTime)

        self.tx_properties.set_tx(tx)
        self.tx_id.setText(bitcoin.core.b2lx(tx.GetHash()))

    def clear(self):
        self.version_edit.clear()
        self.inputs_tree.clear()
        self.outputs_tree.clear()
        self.locktime_edit.clear()
        self.tx_properties.clear()

    def add_input(self, i):
        self.inputs_tree.add_input(i)

    def add_output(self, o):
        self.outputs_tree.add_output(o)
