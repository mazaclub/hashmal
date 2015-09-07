import bitcoin
from bitcoin.core import COutPoint, CTxIn, CTxOut, lx
from PyQt4.QtGui import *
from PyQt4 import QtCore

from gui_utils import Amount, monospace_font
from hashmal_lib.core.script import Script

class InputsTree(QTreeWidget):
    def __init__(self, parent=None):
        super(InputsTree, self).__init__(parent)
        self.setColumnCount(3)
        self.setHeaderLabels(['Prev Output', 'scriptSig', 'Sequence'])
        self.setAlternatingRowColors(True)
        self.header().setStretchLastSection(False)
        self.header().setResizeMode(0, QHeaderView.Interactive)
        self.header().setResizeMode(1, QHeaderView.Stretch)
        self.header().setResizeMode(2, QHeaderView.Interactive)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.customContextMenu)

    def copy_script(self):
        item = self.currentItem()
        QApplication.clipboard().setText(item.text(1))

    def copy_script_hex(self):
        item = self.currentItem()
        script = Script.from_human(str(item.text(1)))
        QApplication.clipboard().setText(script.get_hex())

    def customContextMenu(self, pos):
        menu = QMenu()
        item = self.currentItem()
        if self.isItemSelected(item):
            menu.addAction('Copy Input Script', self.copy_script)
            menu.addAction('Copy Input Script Hex', self.copy_script_hex)

        menu.exec_(self.viewport().mapToGlobal(pos))

    def add_input(self, i):
        in_script = Script(i.scriptSig)
        item = QTreeWidgetItem([
            str(i.prevout),
            in_script.get_human(),
            str(i.nSequence)
        ])
        for i in range(3):
            item.setFont(i, monospace_font)
        self.addTopLevelItem(item)

    def get_inputs(self):
        vin = []
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            prev_hash, prev_vout = str(item.text(0)).split(':')
            in_script = Script.from_human(str(item.text(1)))
            sequence = int(item.text(2))
            outpoint = COutPoint(lx(prev_hash), int(prev_vout))
            i_input = CTxIn(outpoint, in_script.get_hex().decode('hex'), sequence)
            vin.append(i_input)
        return vin

class OutputsTree(QTreeWidget):
    def __init__(self, parent=None):
        super(OutputsTree, self).__init__(parent)
        self.setColumnCount(2)
        self.setHeaderLabels(['Value', 'scriptPubKey'])
        self.setAlternatingRowColors(True)
        self.header().setResizeMode(0, QHeaderView.Interactive)
        self.header().setResizeMode(1, QHeaderView.Stretch)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.customContextMenu)

    def copy_script(self):
        item = self.currentItem()
        QApplication.clipboard().setText(item.text(1))

    def copy_script_hex(self):
        item = self.currentItem()
        script = Script.from_human(str(item.text(1)))
        QApplication.clipboard().setText(script.get_hex())

    def customContextMenu(self, pos):
        menu = QMenu()
        item = self.currentItem()
        if self.isItemSelected(item):
            menu.addAction('Copy Output Script', self.copy_script)
            menu.addAction('Copy Output Script Hex', self.copy_script_hex)

        menu.exec_(self.viewport().mapToGlobal(pos))

    def add_output(self, o):
        out_script = Script(o.scriptPubKey)
        value = Amount(o.nValue)
        item = QTreeWidgetItem([
            value.get_str(),
            out_script.get_human()
        ])
        for i in range(2):
            item.setFont(i, monospace_font)
        self.addTopLevelItem(item)

    def get_outputs(self):
        vout = []
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            value = str(item.text(0))
            if '.' in value:
                value = int(float(value) * pow(10, 8))
            else:
                value = int(value)
            out_script = Script.from_human(str(item.text(1)))
            i_output = CTxOut(value, out_script.get_hex().decode('hex'))
            vout.append(i_output)
        return vout

class TxWidget(QWidget):
    def __init__(self, parent=None):
        super(TxWidget, self).__init__(parent)
        form = QFormLayout()

        self.tx_id = QLineEdit()
        self.tx_id.setReadOnly(True)

        self.version_edit = QLineEdit()
        self.version_edit.setReadOnly(True)

        self.inputs_tree = inputs = InputsTree()

        self.outputs_tree = outputs = OutputsTree()

        self.locktime_edit = QLineEdit()
        self.locktime_edit.setReadOnly(True)

        form.addRow('Tx ID:', self.tx_id)
        form.addRow('Version:', self.version_edit)
        form.addRow('Inputs:', inputs)
        form.addRow('Outputs:', outputs)
        form.addRow('LockTime:', self.locktime_edit)

        self.setLayout(form)

    def set_tx(self, tx):
        self.version_edit.setText(str(tx.nVersion))

        for i in tx.vin:
            self.add_input(i)

        for o in tx.vout:
            self.add_output(o)

        self.locktime_edit.setText(str(tx.nLockTime))

        self.tx_id.setText(bitcoin.core.b2lx(tx.GetHash()))

    def clear(self):
        self.version_edit.clear()
        self.inputs_tree.clear()
        self.outputs_tree.clear()
        self.locktime_edit.clear()

    def add_input(self, i):
        self.inputs_tree.add_input(i)

    def add_output(self, o):
        self.outputs_tree.add_output(o)
