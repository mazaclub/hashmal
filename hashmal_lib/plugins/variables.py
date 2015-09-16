from collections import OrderedDict

from bitcoin.core import CTransaction

from PyQt4.QtGui import *
from PyQt4 import QtCore

from base import BaseDock, Plugin
from hashmal_lib.gui_utils import floated_buttons

def make_plugin():
    return Plugin([Variables])

class Variables(BaseDock):
    def __init__(self, handler):
        super(Variables, self).__init__(handler)
        self.needsUpdate.emit()

    def init_metadata(self):
        self.tool_name = 'Variables'
        self.description = 'Variables records data for later access.'

    def init_data(self):
        data = self.config.get_option('variables', {})
        self.data = OrderedDict(data)
        self.filters = ['None', 'Hex', 'Raw Transaction', 'Text']

    def init_actions(self):
        store_as = ('Store raw tx as...', self.store_as_variable)
        self.advertised_actions['raw_transaction'] = [store_as]

    def create_layout(self):
        form = QFormLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels([ 'Key', 'Value' ])
        self.table.verticalHeader().setDefaultSectionSize(25)
        self.table.horizontalHeader().setResizeMode(QHeaderView.Stretch)
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.context_menu)
        self.table.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding))

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(self.filters)
        self.filter_combo.currentIndexChanged.connect(self.filter_table)

        form.addRow('Filter:', self.filter_combo)
        form.addRow(self.table)

        add_var_hbox = QHBoxLayout()
        self.new_var_key = QLineEdit()
        self.new_var_value = QLineEdit()
        add_var_hbox.addWidget(self.new_var_key)
        add_var_hbox.addWidget(QLabel(':'))
        add_var_hbox.addWidget(self.new_var_value)
        add_var_btn = QPushButton('Add')
        add_var_btn.clicked.connect(self.add_new_var)
        add_var_hbox.addWidget(add_var_btn)

        self.del_var_key = QLineEdit()
        del_var_button = QPushButton('Delete')
        del_var_button.clicked.connect(self.remove_var)
        del_var_hbox = QHBoxLayout()
        del_var_hbox.addWidget(self.del_var_key)
        del_var_hbox.addWidget(del_var_button)

        self.save_button = QPushButton('Save')
        self.save_button.clicked.connect(self.save_variables)
        self.save_button.setToolTip('Save variables to config file')

        form.addRow('Add:', add_var_hbox)
        form.addRow('Delete:', del_var_hbox)
        form.addRow(floated_buttons([self.save_button]))
        return form

    def is_valid_key(self, key):
        return isinstance(key, str) and key and key.isalnum()

    def filter_table(self):
        filter_str = str(self.filter_combo.currentText())
        for i in range(self.table.rowCount()):
            if filter_str == 'None':
                self.table.showRow(i)
                continue

            item = self.table.item(i, 1)
            if filter_str == item.data(QtCore.Qt.UserRole).toString():
                self.table.showRow(i)
            else:
                self.table.hideRow(i)

    def classify_data(self, value):
        """Determine what to categorize a value as."""
        # If the value is not hex, assume text
        try:
            i = int(value, 16)
        except ValueError:
            return 'Text'

        # See if it's a raw transaction.
        try:
            t = CTransaction.deserialize(value.decode('hex'))
            return 'Raw Transaction'
        except Exception:
            pass

        # Use the generic 'Hex' category if nothing else matches.
        return 'Hex'

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

        Used by scriptedit for substituting values.
        """
        return self.data.get(key)

    def set_key(self, key, value):
        """Store a new variable."""
        self.data[key] = value
        self.needsUpdate.emit()

    def remove_key(self, key):
        """Remove a key."""
        if self.data.get(key):
            del self.data[key]
        self.needsUpdate.emit()

    def save_variables(self):
        self.config.set_option('variables', self.data)
        self.status_message('Saved variables to config file.')

    def context_menu(self, position):
        menu = QMenu()

        def copy():
            item = self.table.currentItem()
            QApplication.clipboard().setText(str(item.text()))
        menu.addAction('Copy', copy)

        def delete():
            row = self.table.currentRow()
            name = str(self.table.item(row, 0).text())
            del self.data[name]
            self.needsUpdate.emit()
        menu.addAction('Delete', delete)

        menu.exec_(self.table.viewport().mapToGlobal(position))

    def refresh_data(self):
        self.table.clearContents()
        self.table.setRowCount(0)
        for k, v in self.data.items():
            self.table.insertRow(0)
            item_key = QTableWidgetItem(k)
            item_value = QTableWidgetItem(str(v))
            item_value.setData(QtCore.Qt.UserRole, self.classify_data(str(v)))
            self.table.setItem(0, 0, item_key)
            self.table.setItem(0, 1, item_value)
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
        self.status_message('Set variable %s to %s'.format(k, v))
        self.new_var_key.clear()
        self.new_var_value.clear()

    def remove_var(self):
        k = str(self.del_var_key.text())
        self.remove_key(k)
        self.del_var_key.clear()
