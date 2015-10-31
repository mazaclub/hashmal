from collections import OrderedDict


from PyQt4.QtGui import *
from PyQt4 import QtCore

from base import BaseDock, Plugin
from hashmal_lib.core import Transaction
from hashmal_lib.gui_utils import floated_buttons, HBox

def make_plugin():
    return Plugin(Variables)

class VarsModel(QtCore.QAbstractTableModel):
    """Model for stored variables."""
    def __init__(self, data, parent=None):
        super(VarsModel, self).__init__(parent)
        self.vars_data = data

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

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.DisplayRole and role != QtCore.Qt.UserRole:
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
                data = self.classify_data(self.vars_data[key])

        return QtCore.QVariant(data)

    def classify_data(self, value):
        """Determine what to categorize a value as."""
        # If the value is not hex, assume text
        try:
            i = int(value, 16)
        except ValueError:
            return 'Text'

        # See if it's a raw transaction.
        try:
            t = Transaction.deserialize(value.decode('hex'))
            return 'Raw Transaction'
        except Exception:
            pass

        # Use the generic 'Hex' category if nothing else matches.
        return 'Hex'

    def set_key(self, key, value):
        self.beginInsertRows( QtCore.QModelIndex(), self.rowCount(), self.rowCount() )
        self.vars_data[key] = value
        self.endInsertRows()

    def remove_key(self, key):
        row = self.vars_data.keys().index(key)
        self.beginRemoveRows( QtCore.QModelIndex(), row, row )
        del self.vars_data[key]
        self.endRemoveRows()

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

    def init_data(self):
        self.data = OrderedDict(self.option('data', {}))
        self.auto_save = self.option('auto_save', False)
        self.filters = ['None', 'Hex', 'Raw Transaction', 'Text']

    def init_actions(self):
        store_as = ('Store raw tx as...', self.store_as_variable)
        self.advertised_actions['raw_transaction'] = [store_as]

    def create_layout(self):
        form = QFormLayout()

        self.model = VarsModel(self.data)

        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.horizontalHeader().setResizeMode(1, QHeaderView.Stretch)
        self.view.horizontalHeader().setHighlightSections(False)
        self.view.verticalHeader().setDefaultSectionSize(22)
        self.view.verticalHeader().setVisible(False)
        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.context_menu)
        self.view.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding))
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setAlternatingRowColors(True)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(self.filters)
        self.filter_combo.currentIndexChanged.connect(self.filter_table)

        form.addRow('Filter:', self.filter_combo)
        form.addRow(self.view)

        # Controls for adding/removing variables

        self.new_var_key = QLineEdit()
        self.setFocusProxy(self.new_var_key)
        self.new_var_value = QLineEdit()
        add_var_btn = QPushButton('Set')
        add_var_btn.clicked.connect(self.add_new_var)
        add_var_hbox = HBox(self.new_var_key, QLabel(':'), self.new_var_value, add_var_btn)

        self.del_var_key = QLineEdit()
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

            if filter_str == str(self.model.dataAt(i, 1, QtCore.Qt.UserRole).toString()):
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

        def copy():
            index = self.view.currentIndex()
            text = self.model.data(index).toString()
            QApplication.clipboard().setText(str(text))
        menu.addAction('Copy', copy)

        def delete():
            index = self.view.currentIndex()
            row = index.row()
            name = self.model.dataAt(row, 0).toString()
            self.remove_key(str(name))
        menu.addAction('Delete', delete)

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
