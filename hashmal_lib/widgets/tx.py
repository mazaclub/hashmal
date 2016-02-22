import datetime
import time
import decimal
from decimal import Decimal
from collections import OrderedDict

import bitcoin
from bitcoin.core import COutPoint, CTxIn, CTxOut, lx, x, b2x, b2lx, CMutableOutPoint, CMutableTxIn, CMutableTxOut
from PyQt4.QtGui import *
from PyQt4 import QtCore
from PyQt4.QtCore import *

from hashmal_lib.gui_utils import Amount, monospace_font, HBox, floated_buttons, RawRole, ReadOnlyCheckBox
from hashmal_lib.core import chainparams
from hashmal_lib.core.script import Script
from hashmal_lib.core import Transaction
from hashmal_lib import config

class InputsModel(QAbstractTableModel):
    """Model of a transaction's inputs."""
    def __init__(self, parent=None):
        super(InputsModel, self).__init__(parent)
        self.vin = []

    def rowCount(self, parent=QModelIndex()):
        return len(self.vin)

    def columnCount(self, parent=QModelIndex()):
        return 4

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation != Qt.Horizontal: return QVariant(None)
        headers = [
            {Qt.DisplayRole: 'Prev Tx', Qt.ToolTipRole: 'Previous Transaction Hash'},
            {Qt.DisplayRole: 'Prev Output', Qt.ToolTipRole: 'Previous Transaction Output'},
            {Qt.DisplayRole: 'scriptSig', Qt.ToolTipRole: 'Input script'},
            {Qt.DisplayRole: 'Sequence', Qt.ToolTipRole: 'Input sequence'}
        ]
        try:
            data = QVariant(headers[section][role])
            return data
        except (IndexError, KeyError):
            return QVariant(None)

    def data(self, index, role = Qt.DisplayRole):
        if not index.isValid() or not self.vin: return QVariant(None)
        if role not in [Qt.DisplayRole, Qt.ToolTipRole, Qt.EditRole, RawRole]:
            return None
        tx_input = self.vin[index.row()]
        col = index.column()
        data = None
        if col == 0:
            data = b2lx(tx_input.prevout.hash)
        elif col == 1:
            data = tx_input.prevout.n
            if role == Qt.DisplayRole:
                data = str(data)
        elif col == 2:
            if role == RawRole:
                data = Script(tx_input.scriptSig).get_hex()
            else:
                data = Script(tx_input.scriptSig).get_human()
        elif col == 3:
            data = tx_input.nSequence
            if role == Qt.DisplayRole:
                data = str(data)

        return QVariant(data)

    def setData(self, index, value, role = Qt.EditRole):
        if not index.isValid() or not self.vin: return False
        tx_input = self.vin[index.row()]
        col = index.column()
        if col == 0:
            tx_input.prevout.hash = lx(str(value.toString()))
        elif col == 1:
            tx_input.prevout.n, _ = value.toUInt()
        elif col == 2:
            tx_input.scriptSig = x(Script.from_human(str(value.toString())).get_hex())
        elif col == 3:
            tx_input.nSequence, _ = value.toUInt()
        self.dataChanged.emit(self.index(index.row(), col), self.index(index.row(), col))
        return True

    def set_tx(self, tx):
        """Reset the model to reflect tx."""
        self.beginResetModel()
        self.vin = []
        for i in tx.vin:
            self.vin.append(CMutableTxIn.from_txin(i))
        self.endResetModel()

    def add_input(self, tx_input=None, input_index=None):
        """Add an input at input_index, or append one if input_index is None."""
        if tx_input is None:
            tx_input = CMutableTxIn()
        elif tx_input.__class__ == CTxIn:
            tx_input = CMutableTxIn.from_txin(tx_input)

        if input_index is None:
            input_index = len(self.vin)
        self.beginInsertRows(QModelIndex(), input_index, input_index)
        self.vin.insert(input_index, tx_input)
        self.endInsertRows()

    def get_inputs(self):
        return list(self.vin)

    def removeRows(self, row, count, parent=QModelIndex()):
        self.beginRemoveRows(QModelIndex(), row, row + count - 1)
        for i in range(row, row + count):
            self.vin.pop(row)
        self.endRemoveRows()
        return True

    def clear(self):
        self.set_tx(Transaction())

class InputsTree(QWidget):
    """Model and View showing a transaction's inputs."""
    def __init__(self, parent=None):
        super(InputsTree, self).__init__(parent)
        self.model = InputsModel()
        self.view = QTableView()
        self.view.setAlternatingRowColors(True)
        self.view.setModel(self.model)
        self.view.horizontalHeader().setStretchLastSection(False)
        self.view.horizontalHeader().setResizeMode(0, QHeaderView.Interactive)
        self.view.horizontalHeader().setResizeMode(1, QHeaderView.ResizeToContents)
        self.view.horizontalHeader().setResizeMode(2, QHeaderView.Stretch)
        self.view.horizontalHeader().setResizeMode(3, QHeaderView.Interactive)
        self.view.horizontalHeader().setHighlightSections(False)
        self.view.verticalHeader().setDefaultSectionSize(22)
        self.view.verticalHeader().setVisible(False)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.customContextMenu)
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self.view)
        self.setLayout(vbox)

    def clear(self):
        self.model.clear()

    def copy_prev_tx(self):
        """Copy the previous transaction ID to clipboard."""
        idx = self.view.selectedIndexes()[0]
        data = self.model.data(idx)
        QApplication.clipboard().setText(data.toString())

    def copy_script(self):
        """Copy the scriptSig to clipboard."""
        idx = self.view.selectedIndexes()[2]
        data = self.model.data(idx)
        QApplication.clipboard().setText(data.toString())

    def copy_script_hex(self):
        """Copy the scriptSig to clipboard as hex."""
        idx = self.view.selectedIndexes()[2]
        data = self.model.data(idx, RawRole)
        QApplication.clipboard().setText(data.toString())

    def context_menu(self):
        menu = QMenu()
        copy = menu.addMenu('Copy')
        copy.addAction('Previous Transaction ID', self.copy_prev_tx)
        copy.addAction('Input Script', self.copy_script)
        copy.addAction('Input Script (Hex)', self.copy_script_hex)

        def copy_serialized():
            row = self.view.selectedIndexes()[0].row()
            inp = self.model.tx.vin[row]
            data = b2x(inp.serialize())
            QApplication.clipboard().setText(data)
        copy.addAction('Serialized Input', copy_serialized)
        return menu

    def customContextMenu(self, pos):
        if len(self.view.selectedIndexes()) == 0:
            return
        menu = self.context_menu()
        menu.exec_(self.view.viewport().mapToGlobal(pos))

    def add_input(self, i):
        self.model.add_input(i)
        return

    def get_inputs(self):
        return self.model.get_inputs()

class OutputsModel(QAbstractTableModel):
    """Model of a transaction's outputs."""
    def __init__(self, parent=None):
        super(OutputsModel, self).__init__(parent)
        self.vout = []
        self.amount_format = config.get_config().get_option('amount_format', 'coins')

    def rowCount(self, parent=QModelIndex()):
        return len(self.vout)

    def columnCount(self, parent=QModelIndex()):
        return 2

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation != Qt.Horizontal: return QVariant(None)
        headers = [
            {Qt.DisplayRole: 'Value', Qt.ToolTipRole: 'Output amount'},
            {Qt.DisplayRole: 'scriptPubKey', Qt.ToolTipRole: 'Output script'}
        ]
        try:
            data = QVariant(headers[section][role])
            return data
        except (IndexError, KeyError):
            return QVariant(None)

    def data(self, index, role = Qt.DisplayRole):
        if not index.isValid() or not self.vout: return QVariant(None)
        if role not in [Qt.DisplayRole, Qt.ToolTipRole, Qt.EditRole, RawRole]:
            return None
        tx_out = self.vout[index.row()]
        col = index.column()
        data = None
        if col == 0:
            if role in [Qt.EditRole, RawRole]:
                data = tx_out.nValue
            elif role in [Qt.ToolTipRole]:
                data = ' '.join([str(tx_out.nValue), 'satoshis'])
            else:
                data = self.format_amount(tx_out.nValue)
        elif col == 1:
            if role == RawRole:
                data = Script(tx_out.scriptPubKey).get_hex()
            else:
                data = Script(tx_out.scriptPubKey).get_human()

        return QVariant(data)

    def setData(self, index, value, role = Qt.EditRole):
        if not index.isValid() or not self.vout: return False
        tx_out = self.vout[index.row()]
        col = index.column()
        if col == 0:
            tx_out.nValue, _ = value.toULongLong()
        elif col == 1:
            tx_out.scriptPubKey = x(Script.from_human(str(value.toString())).get_hex())
        self.dataChanged.emit(self.index(index.row(), col), self.index(index.row(), col))
        return True

    def set_tx(self, tx):
        """Reset the model to reflect tx."""
        self.beginResetModel()
        self.vout = []
        for o in tx.vout:
            self.vout.append(CMutableTxOut.from_txout(o))
        self.endResetModel()

    def add_output(self, tx_out=None, output_index=None):
        """Add an output at output_index, or append one if output_index is None."""
        if tx_out is None:
            tx_out = CMutableTxOut()
        elif tx_out.__class__ == CTxOut:
            tx_out = CMutableTxOut.from_txout(tx_out)

        if output_index is None:
            output_index = len(self.vout)
        self.beginInsertRows(QModelIndex(), output_index, output_index)
        self.vout.insert(output_index, tx_out)
        self.endInsertRows()

    def get_outputs(self):
        return list(self.vout)

    def removeRows(self, row, count, parent=QModelIndex()):
        self.beginRemoveRows(QModelIndex(), row, row + count - 1)
        for i in range(row, row + count):
            self.vout.pop(row)
        self.endRemoveRows()
        return True

    def clear(self):
        self.set_tx(Transaction())

    def format_amount(self, satoshis):
        if self.amount_format == 'satoshis':
            return str(satoshis)
        elif self.amount_format == 'coins':
            amount = Decimal(satoshis) / pow(10, 8)
            amount = amount.quantize(Decimal('0.00000001'), rounding=decimal.ROUND_DOWN)
            return '{:f}'.format(amount)

    def amount_format_changed(self):
        """Refreshes TxOut amounts with the new format."""
        self.dataChanged.emit(QModelIndex(), QModelIndex())

class OutputsTree(QWidget):
    """Model and View showing a transaction's outputs."""
    def __init__(self, parent=None):
        super(OutputsTree, self).__init__(parent)
        self.model = OutputsModel()
        self.view = QTableView()
        self.view.setAlternatingRowColors(True)
        self.view.setModel(self.model)
        self.view.horizontalHeader().setResizeMode(0, QHeaderView.Interactive)
        self.view.horizontalHeader().setResizeMode(1, QHeaderView.Stretch)
        self.view.horizontalHeader().setHighlightSections(False)
        self.view.verticalHeader().setDefaultSectionSize(22)
        self.view.verticalHeader().setVisible(False)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.customContextMenu)
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self.view)
        self.setLayout(vbox)
        config.get_config().optionChanged.connect(self.on_option_changed)

    def clear(self):
        self.model.clear()

    def copy_script(self):
        """Copy the scriptPubKey to clipboard."""
        idx = self.view.selectedIndexes()[1]
        data = self.model.data(idx)
        QApplication.clipboard().setText(data.toString())

    def copy_script_hex(self):
        """Copy the scriptPubKey to clipboard as hex."""
        idx = self.view.selectedIndexes()[1]
        data = self.model.data(idx, RawRole)
        QApplication.clipboard().setText(data.toString())

    def copy_amount(self):
        """Copy the output amount to clipboard."""
        idx = self.view.selectedIndexes()[0]
        data = self.model.data(idx)
        QApplication.clipboard().setText(data.toString())

    def context_menu(self):
        menu = QMenu()
        copy = menu.addMenu('Copy')
        copy.addAction('Amount', self.copy_amount)
        copy.addAction('Output Script', self.copy_script)
        copy.addAction('Output Script (Hex)', self.copy_script_hex)
        def copy_serialized():
            row = self.view.selectedIndexes()[0].row()
            out = self.model.tx.vout[row]
            data = b2x(out.serialize())
            QApplication.clipboard().setText(data)
        copy.addAction('Serialized Output', copy_serialized)
        return menu

    def customContextMenu(self, pos):
        if len(self.view.selectedIndexes()) == 0:
            return
        menu = self.context_menu()
        menu.exec_(self.view.viewport().mapToGlobal(pos))

    def add_output(self, o):
        self.model.add_output(o)

    def get_outputs(self):
        return self.model.get_outputs()

    def on_option_changed(self, key):
        if key == 'amount_format':
            self.model.amount_format = config.get_config().get_option('amount_format', 'coins')
            self.model.amount_format_changed()

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
        if not str(timestamp_str).isdigit():
            self.timestamp_raw.setText(str(int(time.time())))
            return
        timestamp = int(timestamp_str)
        date_time = datetime.datetime.utcfromtimestamp(timestamp)
        self.timestamp_human.setText(' '.join([date_time.strftime('%Y-%m-%d %H:%M:%S'), 'UTC']))
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

        self.is_final = ReadOnlyCheckBox('Is Final')
        self.is_final.setToolTip('True if all inputs have a Sequence of 0xffffffff')
        self.is_coinbase = ReadOnlyCheckBox('Is Coinbase')
        self.is_coinbase.setToolTip('True if the tx generates new coins via mining')
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
        self.field_widgets = OrderedDict()

        form = QFormLayout()

        self.tx_id = QLineEdit()
        self.tx_id.setReadOnly(True)
        self.tx_id.setToolTip('Transaction ID')
        self.tx_id.setWhatsThis('The ID (hash) of the transaction is displayed here.')

        self.version_edit = QLineEdit()
        self.version_edit.setReadOnly(True)
        self.inputs_tree = inputs = InputsTree()
        self.outputs_tree = outputs = OutputsTree()
        self.locktime_edit = LockTimeWidget()

        self.field_widgets.update({'nVersion': self.version_edit})
        self.field_widgets.update({'vin': self.inputs_tree})
        self.field_widgets.update({'vout': self.outputs_tree})
        self.field_widgets.update({'nLockTime': self.locktime_edit})

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

        self.inputs_tree.model.set_tx(tx)
        self.outputs_tree.model.set_tx(tx)

        self.locktime_edit.set_locktime(tx.nLockTime)

        for name, w in self.field_widgets.items():
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
        for w in self.field_widgets.values():
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
            if name not in self.field_widgets.keys():
                widget = QLineEdit()
                widget.setReadOnly(True)
                if name == 'Timestamp':
                    widget = TimestampWidget()
                label = QLabel(''.join([name, ':']))
                # Add the widget to our dict and to the layout.
                self.field_widgets[name] = widget
                self.tx_fields_layout.insertRow(i, label, widget)

            # Make sure the existing widget for the tx field is visible.
            else:
                w = self.field_widgets[name]
                l = self.tx_fields_layout.labelForField(w)
                w.show()
                l.show()

        # Hide unnecessary widgets
        tx_field_names = [i[0] for i in tx_fields]
        for name, w in self.field_widgets.items():
            if name not in tx_field_names:
                l = self.tx_fields_layout.labelForField(w)
                w.hide()
                l.hide()


