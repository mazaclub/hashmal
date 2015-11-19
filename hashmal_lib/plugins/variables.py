from collections import OrderedDict, namedtuple

from bitcoin.core import x, lx, b2x, b2lx
from bitcoin.base58 import CBase58Data

from PyQt4.QtGui import *
from PyQt4 import QtCore

from base import BaseDock, Plugin
from hashmal_lib.core import Transaction, Block
from hashmal_lib.gui_utils import floated_buttons, HBox
from hashmal_lib.items import *

def make_plugin():
    return Plugin(Variables)

VariableType = namedtuple('VariableType', ('name', 'category', 'classify'))
"""Variable type.

Attributes:
    name (str): Human-readable name.
    category (str): Category; for plugin context menus. (e.g. hashmal_lib.items.RAW_TX)
    classify (function): Function returning whether a value has this variable type.
"""

def is_hex(x):
    try:
        i = int(x, 16)
        return True
    except Exception:
        return False

def is_raw_tx(x):
    try:
        t = Transaction.deserialize(x.decode('hex'))
        return True
    except Exception:
        return False

def is_raw_block(x):
    try:
        b = Block.deserialize(x.decode('hex'))
        return True
    except Exception:
        return False

_var_types = [
    VariableType('None', None, lambda x: False),
    VariableType('Hex', None, is_hex),
    VariableType('Text', None, lambda x: x.startswith('"') and x.endswith('"')),
    VariableType('64 Hex Digits', None, lambda x: is_hex(x) and (len(x) == 66 if x.startswith('0x') else len(x) == 64)),
    VariableType('Raw Transaction', RAW_TX, is_raw_tx),
    VariableType('Raw Block', RAW_BLOCK, is_raw_block),
]

variable_types = OrderedDict()
for var_type in _var_types:
    variable_types.update({var_type.name: var_type})

def classify_data(value):
    """Determine what to categorize a value as.

    Returns a list of variable_types keys.
    """
    var_types = []
    for var_type in variable_types.values():
        if var_type.classify(value):
            var_types.append(var_type.name)

    return var_types

class VarsModel(QtCore.QAbstractTableModel):
    """Model for stored variables."""
    def __init__(self, data, parent=None):
        super(VarsModel, self).__init__(parent)
        self.vars_data = data
        self.classification_cache = {}

    def columnCount(self, parent = QtCore.QModelIndex()):
        return 2

    def rowCount(self, parent = QtCore.QModelIndex()):
        return len(self.vars_data)

    def headerData(self, section, orientation, role = QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Vertical:
            return QtCore.QVariant(None)

        data = None
        if section == 0:
            if role == QtCore.Qt.DisplayRole:
                data = 'Key'
            elif role == QtCore.Qt.ToolTipRole:
                data = 'Variable name'
        elif section == 1:
            if role == QtCore.Qt.DisplayRole:
                data = 'Value'
            elif role == QtCore.Qt.ToolTipRole:
                data = 'Variable value'

        return QtCore.QVariant(data)

    def flags(self, index):
        return (QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsEnabled)

    def dataAt(self, row, column, role = QtCore.Qt.DisplayRole):
        index = self.createIndex(row, column)
        return self.data(index, role)

    def keyForIndex(self, index, role=QtCore.Qt.DisplayRole):
        return self.dataAt(index.row(), 0, role)

    def valueForIndex(self, index, role=QtCore.Qt.DisplayRole):
        return self.dataAt(index.row(), 1, role)

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if role not in [QtCore.Qt.DisplayRole, QtCore.Qt.UserRole]:
            return QtCore.QVariant(None)
        data = None
        r = index.row()
        c = index.column()
        key = self.vars_data.keys()[r]

        if c == 0:
            data = key
        elif c == 1:
            if role == QtCore.Qt.DisplayRole:
                data = self.vars_data[key]
            elif role == QtCore.Qt.UserRole:
                value = self.vars_data[key]
                cached = self.classification_cache.get(value, None)
                if cached is None:
                    data = classify_data(value)
                    self.classification_cache[value] = data
                else:
                    data = cached

        return QtCore.QVariant(data)

    def set_key(self, key, value):
        self.beginInsertRows( QtCore.QModelIndex(), self.rowCount(), self.rowCount() )
        self.vars_data[key] = value
        self.endInsertRows()

    def remove_key(self, key):
        row = self.vars_data.keys().index(key)
        self.beginRemoveRows( QtCore.QModelIndex(), row, row )
        del self.vars_data[key]
        self.endRemoveRows()

    def invalidate_cache(self):
        self.classification_cache.clear()

class Variables(BaseDock):

    tool_name = 'Variables'
    description = 'Variables records data for later access.'

    dataChanged = QtCore.pyqtSignal()
    def __init__(self, handler):
        super(Variables, self).__init__(handler)
        def maybe_save():
            if self.auto_save:
                self.save_variables()
        self.dataChanged.connect(maybe_save)
        self.augment('variable_types', variable_types, callback=self.on_var_types_augmented)

    def init_data(self):
        self.data = OrderedDict(self.option('data', {}))
        self.auto_save = self.option('auto_save', False)
        self.filters = variable_types.keys()

    def init_actions(self):
        store_as = ('Store raw tx as...', self.store_as_variable)
        self.advertised_actions[RAW_TX] = [store_as]

        def copy_h160(x):
            h160 = CBase58Data(x).encode('hex')
            QApplication.clipboard().setText(h160)
        copy_hash160 = ('Copy RIPEMD-160 Hash', copy_h160)
        self.local_actions['address'] = [copy_hash160]

        def copy_txid(rawtx):
            txid = b2lx(Transaction.deserialize(x(rawtx)).GetHash())
            QApplication.clipboard().setText(txid)
        copy_tx_id = ('Copy Transaction ID', copy_txid)
        self.local_actions[RAW_TX] = [copy_tx_id]

        def copy_blockhash(rawblock):
            blockhash = b2lx(Block.deserialize(x(rawblock)).GetHash())
            QApplication.clipboard().setText(blockhash)
        copy_block_hash = ('Copy Block Hash', copy_blockhash)
        self.local_actions[RAW_BLOCK] = [copy_block_hash]

    def create_layout(self):
        form = QFormLayout()

        self.model = VarsModel(self.data)

        self.view = QTableView()
        self.view.setWhatsThis('This table displays the variables you have defined.')
        self.view.setModel(self.model)
        self.view.horizontalHeader().setResizeMode(1, QHeaderView.Stretch)
        self.view.horizontalHeader().setHighlightSections(False)
        self.view.verticalHeader().setDefaultSectionSize(22)
        self.view.verticalHeader().setVisible(False)
        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.context_menu)
        self.view.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding))
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setAlternatingRowColors(True)

        self.filter_combo = QComboBox()
        self.filter_combo.setWhatsThis('Use this to filter the displayed variables by their values.')
        self.filter_combo.addItems(self.filters)
        self.filter_combo.currentIndexChanged.connect(self.filter_table)

        form.addRow('Filter:', self.filter_combo)
        form.addRow(self.view)

        # Controls for adding/removing variables

        self.new_var_key = QLineEdit()
        self.new_var_key.setWhatsThis('Enter the name to give the new variable here.')
        self.setFocusProxy(self.new_var_key)
        self.new_var_value = QLineEdit()
        self.new_var_value.setWhatsThis('Enter the value to give the new variable here.')
        add_var_btn = QPushButton('Set')
        add_var_btn.clicked.connect(self.add_new_var)
        add_var_hbox = HBox(self.new_var_key, QLabel(':'), self.new_var_value, add_var_btn)

        self.del_var_key = QLineEdit()
        self.del_var_key.setWhatsThis('Enter the name of the variable you want to delete here.')
        del_var_button = QPushButton('Delete')
        del_var_button.clicked.connect(self.remove_var)
        del_var_hbox = HBox(self.del_var_key, del_var_button)

        self.auto_save_check = QCheckBox('Automatically save')
        self.auto_save_check.setChecked(self.auto_save)
        def change_auto_save(is_checked):
            is_checked = True if is_checked else False
            self.auto_save = is_checked
            self.set_option('auto_save', self.auto_save)
        self.auto_save_check.stateChanged.connect(change_auto_save)
        self.save_button = QPushButton('Save')
        self.save_button.clicked.connect(self.save_variables)
        self.save_button.setToolTip('Save variables to config file')

        form.addRow('Add:', add_var_hbox)
        form.addRow('Delete:', del_var_hbox)
        form.addRow(floated_buttons([self.auto_save_check, self.save_button]))
        return form

    def is_valid_key(self, key):
        return isinstance(key, str) and key and key.isalnum()

    def filter_table(self):
        filter_str = str(self.filter_combo.currentText())
        for i in range(self.model.rowCount()):
            if filter_str == 'None':
                self.view.showRow(i)
                continue

            if filter_str in self.model.dataAt(i, 1, QtCore.Qt.UserRole).toList():
                self.view.showRow(i)
            else:
                self.view.hideRow(i)


    def store_as_variable(self, value):
        """Prompt to store a value."""
        key = 'rawtx'
        if self.get_key(key):
            offset = 1
            while self.get_key(key):
                key = ''.join(['rawtx', str(offset)])
                offset += 1
        self.new_var_key.setText(key)
        self.new_var_value.setText(value)
        self.needsFocus.emit()

    def get_key(self, key):
        """Get a value for a key.

        Used by scriptedit for highlighting variable keys.
        """
        return self.data.get(key)

    def set_key(self, key, value):
        """Store a new variable."""
        self.model.set_key(key, value)
        self.dataChanged.emit()

    def remove_key(self, key):
        """Remove a key."""
        try:
            self.model.remove_key(key)
        except ValueError:
            self.status_message('No variable named "{}"'.format(key), True)
        self.dataChanged.emit()

    def save_variables(self):
        self.set_option('data', self.data)
        if not self.auto_save:
            self.status_message('Saved variables to config file.')

    def context_menu(self, position):
        menu = QMenu()

        def copy_key(index):
            text = self.model.keyForIndex(index).toString()
            QApplication.clipboard().setText(str(text))

        def copy_value(index):
            text = self.model.valueForIndex(index).toString()
            QApplication.clipboard().setText(str(text))

        def delete_key(index):
            name = self.model.keyForIndex(index).toString()
            self.remove_key(str(name))

        menu.addAction('Copy Key', lambda: copy_key(self.view.currentIndex()))
        menu.addAction('Copy Value', lambda: copy_value(self.view.currentIndex()))
        menu.addAction('Delete', lambda: delete_key(self.view.currentIndex()))

        idx = self.view.currentIndex()
        row = idx.row()
        idx = self.model.createIndex(row, 1)
        data_value = str(self.model.data(idx).toString())
        # Add context menu actions for all applicable variable types.
        data_categories = map(lambda x: variable_types[str(x.toString())], self.model.data(idx, role=QtCore.Qt.UserRole).toList())
        for i in data_categories:
            self.handler.add_plugin_actions(self, menu, i.category, data_value)

        menu.exec_(self.view.viewport().mapToGlobal(position))

    def refresh_data(self):
        self.filter_table()

    def add_new_var(self):
        k = str(self.new_var_key.text())
        v = str(self.new_var_value.text())
        if not self.is_valid_key(k):
            self.status_message('Key names must be alphanumeric.', True)
            return
        if v == '':
            self.status_message('Value must not be empty.', True)
            return
        self.set_key(k, v)
        self.status_message('Set variable {} to {}'.format(k, v))
        self.new_var_key.clear()
        self.new_var_value.clear()

    def remove_var(self):
        k = str(self.del_var_key.text())
        self.remove_key(k)
        self.del_var_key.clear()

    def on_var_types_augmented(self, arg):
        self.filters = variable_types.keys()
        self.filter_combo.clear()
        self.filter_combo.addItems(self.filters)
        self.model.invalidate_cache()
