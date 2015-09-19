import datetime

import bitcoin
from bitcoin.core import COutPoint, CTxIn, CTxOut, lx
from PyQt4.QtGui import *
from PyQt4 import QtCore

from gui_utils import Amount, monospace_font, HBox, floated_buttons, RawRole
from hashmal_lib.core import chainparams
from hashmal_lib.core.script import Script
import config

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
        hbox.setContentsMargins(0, 0, 0, 0)
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

class TimestampWidget(QWidget):
    """Displays a transaction's timestamp.

    This is only used by certain chains. Namely, Peercoin descendants.
    Displays the raw int and the human-readable time side-by-side.
    """
    def __init__(self, parent=None):
        super(TimestampWidget, self).__init__(parent)
        self.timestamp_raw = QLineEdit()
        self.timestamp_human = QLineEdit()
        for i in [self.timestamp_raw, self.timestamp_human]:
            i.setReadOnly(True)
        hbox = HBox(self.timestamp_raw, self.timestamp_human)
        hbox.setContentsMargins(0, 0, 0, 0)
        self.setLayout(hbox)
        self.timestamp_raw.textChanged.connect(self.update_time)

    def clear(self):
        self.timestamp_raw.clear()
        self.timestamp_human.clear()

    def update_time(self):
        """Update human-readable time to reflect raw."""
        timestamp_str = self.timestamp_raw.text()
        if not timestamp_str:
            self.timestamp_human.clear()
            return
        timestamp = int(timestamp_str)
        time = datetime.datetime.utcfromtimestamp(timestamp)
        self.timestamp_human.setText(' '.join([time.strftime('%Y-%m-%d %H:%M:%S'), 'UTC']))
        self.setToolTip('{} ({})'.format(str(timestamp), str(self.timestamp_human.text())))

    def set_time(self, timestamp):
        """Formats the raw and human-readable timestamps."""
        self.timestamp_raw.setText(str(timestamp))
        self.update_time()

    def setText(self, text):
        self.set_time(int(text))

    def text(self):
        return self.timestamp_raw.text()

    def get_amount(self):
        """This is for compatibility with AmountEdit."""
        return int(self.text())

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
        self.config = config.get_config()
        self.config.optionChanged.connect(self.on_option_changed)
        # Widgets for tx fields
        self.field_widgets = []

        form = QFormLayout()

        self.tx_id = QLineEdit()
        self.tx_id.setReadOnly(True)

        self.version_edit = QLineEdit()
        self.version_edit.setReadOnly(True)
        self.inputs_tree = inputs = InputsTree()
        self.outputs_tree = outputs = OutputsTree()
        self.locktime_edit = LockTimeWidget()

        self.field_widgets.append(('nVersion', self.version_edit))
        self.field_widgets.append(('vin', self.inputs_tree))
        self.field_widgets.append(('vout', self.outputs_tree))
        self.field_widgets.append(('nLockTime', self.locktime_edit))

        self.tx_properties = TxProperties()

        self.tx_fields_layout = QFormLayout()
        self.tx_fields_layout.setContentsMargins(0, 0, 0, 0)
        self.tx_fields_layout.addRow(QLabel('Version:'), self.version_edit)
        self.tx_fields_layout.addRow(QLabel('Inputs:'), inputs)
        self.tx_fields_layout.addRow(QLabel('Outputs:'), outputs)
        self.tx_fields_layout.addRow(QLabel('LockTime:'), self.locktime_edit)

        form.addRow('Tx ID:', self.tx_id)
        form.addRow(self.tx_fields_layout)
        form.addRow('Metadata:', self.tx_properties)

        self.adjust_field_widgets()

        self.setLayout(form)

    def set_tx(self, tx):
        self.version_edit.setText(str(tx.nVersion))

        for i in tx.vin:
            self.add_input(i)

        for o in tx.vout:
            self.add_output(o)

        self.locktime_edit.set_locktime(tx.nLockTime)

        for name, w in self.field_widgets:
            # We already handle these four.
            if name in ['nVersion', 'vin', 'vout', 'nLockTime']:
                continue
            if not name in [field[0] for field in tx.fields]:
                continue
            value = getattr(tx, name)
            w.setText(str(value))

        self.tx_properties.set_tx(tx)

        self.tx_id.setText(bitcoin.core.b2lx(tx.GetHash()))

    def clear(self):
        self.tx_id.clear()
        self.tx_properties.clear()
        for name, w in self.field_widgets:
            w.clear()

    def add_input(self, i):
        self.inputs_tree.add_input(i)

    def add_output(self, o):
        self.outputs_tree.add_output(o)

    def on_option_changed(self, key):
        if key != 'chainparams':
            return
        self.adjust_field_widgets()

    def adjust_field_widgets(self):
        """Add widgets and adjust visibility for tx field widgets."""
        tx_fields = chainparams.get_tx_fields()
        for i, field in enumerate(tx_fields):
            name = field[0]
            # Create a new widget for the tx field.
            if name not in [j[0] for j in self.field_widgets]:
                widget = QLineEdit()
                widget.setReadOnly(True)
                if name == 'Timestamp':
                    widget = TimestampWidget()
                label = QLabel(''.join([name, ':']))
                # Add the widget to our list and to the layout.
                self.field_widgets.insert(i, (name, widget))
                self.tx_fields_layout.insertRow(i, label, widget)

            # Make sure the existing widget for the tx field is visible.
            else:
                w = self.field_widgets[i][1]
                l = self.tx_fields_layout.labelForField(w)
                w.show()
                l.show()

        # Hide unnecessary widgets
        tx_field_names = [i[0] for i in tx_fields]
        for i, (name, w) in enumerate(self.field_widgets):
            if name not in tx_field_names:
                l = self.tx_fields_layout.labelForField(w)
                w.hide()
                l.hide()

        self.clear()

