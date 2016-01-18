from collections import OrderedDict, namedtuple
from functools import partial

from bitcoin.core import x, lx, b2x, b2lx
from bitcoin.base58 import CBase58Data

from PyQt4.QtGui import *
from PyQt4 import QtCore

from base import BaseDock, Plugin, augmenter
from item_types import ItemAction, item_types
from hashmal_lib.core import Transaction, Block, BlockHeader
from hashmal_lib.gui_utils import floated_buttons, HBox
from hashmal_lib.core.utils import is_hex

def make_plugin():
    return Plugin(Variables)

VariableType = namedtuple('VariableType', ('name', 'classify'))
"""Variable type.

Attributes:
    name (str): Human-readable name.
    classify (function): Function returning whether a value has this variable type.
"""

_var_types = [
    VariableType('None', lambda x: False),
    VariableType('Hex', is_hex),
    VariableType('Text', lambda x: x.startswith('"') and x.endswith('"')),
    VariableType('64 Hex Digits', lambda x: is_hex(x) and (len(x) == 66 if x.startswith('0x') else len(x) == 64)),
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
        self.reverse_lookup = {}
        for k, v in self.vars_data.items():
            self.reverse_lookup[v] = k
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
        self.reverse_lookup[value] = key
        self.endInsertRows()

    def remove_key(self, key):
        row = self.vars_data.keys().index(key)
        self.beginRemoveRows( QtCore.QModelIndex(), row, row )
        value = self.vars_data[key]
        del self.reverse_lookup[value]
        del self.vars_data[key]
        self.endRemoveRows()

    def key_for_value(self, value):
        return self.reverse_lookup.get(value)

    def invalidate_cache(self):
        self.classification_cache.clear()

class VarsProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super(VarsProxyModel, self).__init__(parent)
        self.category_filter = 'None'
        self.key_filter = ''

    def set_category_filter(self, text):
        self.category_filter = text
        self.invalidateFilter()

    def set_key_filter(self, text):
        self.key_filter = text
        self.invalidateFilter()

    def keyForIndex(self, index, role=QtCore.Qt.DisplayRole):
        idx = self.mapToSource(index)
        data_idx = self.sourceModel().createIndex(idx.row(), 0, role)
        return self.sourceModel().data(data_idx, role)

    def valueForIndex(self, index, role=QtCore.Qt.DisplayRole):
        idx = self.mapToSource(index)
        data_idx = self.sourceModel().createIndex(idx.row(), 1, role)
        return self.sourceModel().data(data_idx, role)

    def filterAcceptsRow(self, source_row, source_parent):
        if self.category_filter and self.category_filter != 'None':
            categories = self.sourceModel().dataAt(source_row, 1, QtCore.Qt.UserRole).toList()
            if self.category_filter not in categories:
                return False
        if self.key_filter:
            idx = self.sourceModel().index(source_row, 0, source_parent)
            key = str(self.sourceModel().data(idx).toString())
            if self.key_filter not in key:
                return False
        return True


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
        self.dataChanged.connect(self.hide_unused_category_names)

    @augmenter
    def item_actions(self, args):
        # Since we know that the Item Types has been instantiated now, add variable types for known item_types
        # and connect to itemTypesChanged.
        for i in sorted(item_types, key = lambda item_type: item_type.name):
            var_type = VariableType(i.name, lambda x, item=i: item.coerce_item(x) is not None)
            variable_types.update({var_type.name: var_type})
        self.on_var_types_changed()
        self.handler.get_plugin('Item Types').ui.itemTypesChanged.connect(self.on_item_types_changed)
        return (
            ItemAction(self.tool_name, 'Transaction', 'Store raw tx as...', self.store_tx_as_variable),
            ItemAction(self.tool_name, 'Block', 'Store raw block as...', self.store_block_as_variable),
            ItemAction(self.tool_name, 'Block Header', 'Store raw header as...', self.store_block_header_as_variable),
        )

    def init_data(self):
        self.data = OrderedDict(self.option('data', {}))
        self.auto_save = self.option('auto_save', False)
        self.filters = variable_types.keys()

    def create_layout(self):
        form = QFormLayout()

        self.model = VarsModel(self.data)
        self.proxy_model = VarsProxyModel()
        self.proxy_model.setSourceModel(self.model)

        self.view = QTableView()
        self.view.setWhatsThis('This table displays the variables you have defined.')
        self.view.setModel(self.proxy_model)
        self.view.setSortingEnabled(True)
        self.view.sortByColumn(0, QtCore.Qt.AscendingOrder)
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

        form.addRow(self.create_filters_box())
        form.addRow(self.view)

        # Controls for adding/removing variables

        self.new_var_key = QLineEdit()
        self.new_var_key.setPlaceholderText('Key')
        self.new_var_key.setWhatsThis('Enter the name to give the new variable here.')
        self.setFocusProxy(self.new_var_key)
        self.new_var_value = QLineEdit()
        self.new_var_value.setPlaceholderText('Value')
        self.new_var_value.setWhatsThis('Enter the value to give the new variable here.')
        add_var_btn = QPushButton('&Add')
        add_var_btn.clicked.connect(self.add_new_var)
        add_var_hbox = HBox(self.new_var_key, QLabel(':'), self.new_var_value, add_var_btn)

        self.auto_save_check = QCheckBox('Automatically save')
        self.auto_save_check.setWhatsThis('If this box is checked, then your stored variables will automatically be saved whenever one is added or deleted.')
        self.auto_save_check.setChecked(self.auto_save)
        def change_auto_save(is_checked):
            is_checked = True if is_checked else False
            self.auto_save = is_checked
            self.set_option('auto_save', self.auto_save)
        self.auto_save_check.stateChanged.connect(change_auto_save)
        self.save_button = QPushButton('Save')
        self.save_button.clicked.connect(self.save_variables)
        self.save_button.setToolTip('Save variables to config file')
        self.save_button.setWhatsThis('This button will save your stored variables in the Hashmal config file.')

        form.addRow('Add:', add_var_hbox)
        form.addRow(floated_buttons([self.auto_save_check, self.save_button]))
        return form

    def create_filters_box(self):
        form = QFormLayout()

        # Filtering by variable name.
        self.filter_key = QLineEdit()
        self.filter_key.setWhatsThis('Use this to filter the displayed variables by their names.')
        self.filter_key.setPlaceholderText('Filter by key')
        def filter_by_key():
            s = str(self.filter_key.text())
            self.proxy_model.set_key_filter(s)
        self.filter_key.textChanged.connect(filter_by_key)

        # Filtering by data category.
        self.filter_category = QComboBox()
        self.filter_category.setWhatsThis('Use this to filter the displayed variables by their value types.')
        self.filter_category.addItems(self.filters)
        def filter_by_category():
            s = str(self.filter_category.currentText())
            self.proxy_model.set_category_filter(s)
        self.filter_category.currentIndexChanged.connect(filter_by_category)

        form.addRow('Key:', self.filter_key)
        form.addRow('Category:', self.filter_category)

        self.filter_group = QGroupBox('Filters')
        self.filter_group.setLayout(form)
        return self.filter_group

    def is_valid_key(self, key):
        return isinstance(key, str) and key and key.isalnum()

    def fill_fields(self, key, value):
        """Fill the input widgets with key and value."""
        self.new_var_key.setText(key)
        self.new_var_value.setText(value)

    def _make_unique_key(self, key):
        """Create a unique key with a given prefix."""
        if self.get_key(key):
            offset = 1
            original = key
            while self.get_key(key):
                key = ''.join([original, str(offset)])
                offset += 1
        return key

    def store_tx_as_variable(self, item):
        """Prompt to store a tx as a value."""
        key = self._make_unique_key('rawtx')
        self.fill_fields(key, item.raw())
        self.needsFocus.emit()

    def store_block_as_variable(self, item):
        """Prompt to store a block as a value."""
        key = self._make_unique_key('rawblock')
        self.fill_fields(key, item.raw())
        self.needsFocus.emit()

    def store_block_header_as_variable(self, item):
        """Prompt to store a block header as a value."""
        key = self._make_unique_key('rawheader')
        self.fill_fields(key, item.raw())
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

    def key_for_value(self, value, strict=True):
        """Reverse-lookup a key.

        If strict is True, only one representation will be checked.
        """
        if strict:
            return self.model.key_for_value(value)
        formats = [value]
        if isinstance(value, str):
            if value.startswith('0x'):
                formats.append(value[2:])
            elif value.startswith('"') and value.endswith('"'):
                formats.append(value[1:-1])
        for i in formats:
            key = self.model.key_for_value(i)
            if key:
                return key

    def save_variables(self):
        self.set_option('data', self.data)
        if not self.auto_save:
            self.status_message('Saved variables to config file.')

    def context_menu(self, position):
        menu = QMenu()

        def copy_key(index):
            text = self.proxy_model.keyForIndex(index).toString()
            QApplication.clipboard().setText(str(text))

        def copy_value(index):
            text = self.proxy_model.valueForIndex(index).toString()
            QApplication.clipboard().setText(str(text))

        def delete_key(index):
            name = self.proxy_model.keyForIndex(index).toString()
            self.remove_key(str(name))

        menu.addAction('Copy Key', lambda: copy_key(self.view.currentIndex()))
        menu.addAction('Copy Value', lambda: copy_value(self.view.currentIndex()))
        menu.addAction('Delete', lambda: delete_key(self.view.currentIndex()))

        idx = self.proxy_model.mapToSource(self.view.currentIndex())
        data_value = str(self.model.valueForIndex(idx).toString())
        self.handler.add_plugin_actions(self, menu, data_value)

        menu.exec_(self.view.viewport().mapToGlobal(position))

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

    def hide_unused_category_names(self):
        filters = list(self.filters)
        used_categories = set()
        for i in range(self.model.rowCount()):
            categories = [str(x.toString()) for x in self.model.dataAt(i, 1, QtCore.Qt.UserRole).toList()]
            used_categories.update(categories)
        filters = filter(lambda x: x in used_categories, filters)
        filters.insert(0, 'None')
        self.filter_category.clear()
        self.filter_category.addItems(filters)

    def on_var_types_changed(self):
        self.filters = variable_types.keys()
        self.model.invalidate_cache()
        self.hide_unused_category_names()

    def on_item_types_changed(self, new_item_types):
        changed = False
        for i in new_item_types:
            if i.name in variable_types.keys():
                continue
            changed = True
            var_type = VariableType(i.name, lambda x, item=i: item.coerce_item(x) is not None)
            variable_types.update({var_type.name: var_type})
        if changed:
            self.on_var_types_changed()

    def on_option_changed(self, key):
        if key == 'chainparams':
            self.model.invalidate_cache()
            self.proxy_model.invalidateFilter()
