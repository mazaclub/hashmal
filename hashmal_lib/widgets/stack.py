import bitcoin
from bitcoin.core.script import CScript
from bitcoin.core.scripteval import EvalScript

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from hashmal_lib.core import Transaction, opcodes
from hashmal_lib.core.script import Script, transform_human
from hashmal_lib.core.utils import is_hex
from hashmal_lib.core.stack import Stack, ScriptExecution
from hashmal_lib.gui_utils import monospace_font, floated_buttons
from hashmal_lib.items import *


class ScriptExecutionItem(object):
    """Base class for Tree View items."""
    def __init__(self, data, parent=None):
        self.parent_item = parent
        self.item_data = data
        self.children = []

    def appendChild(self, item):
        self.children.append(item)

    def child(self, row):
        return self.children[row]

    def childCount(self):
        return len(self.children)

    def columnCount(self):
        return len(self.item_data)

    def data(self, column, role = Qt.DisplayRole):
        try:
            return self.item_data[column]
        except IndexError:
            return None

    def parent(self):
        return self.parent_item

    def row(self):
        if self.parent_item:
            return self.parent_item.children.index(self)

        return 0

class TopLevelScriptItem(ScriptExecutionItem):
    """Tree View item for script execution steps."""
    def __init__(self, data, parent=None):
        super(TopLevelScriptItem, self).__init__(data, parent)
        self.stack_data = Script(self.item_data[2]).get_human()
        # Convert log data representations to human-readable ones.
        log_data = self.item_data[3].split()
        for i, word in enumerate(log_data):
            if is_hex(word) and len(word) % 2 == 0 and all(ord(c) < 128 and ord(c) > 31 for c in word.decode('hex')):
                log_data[i] = ''.join(['"', word.decode('hex'), '"'])
        self.log_data = ' '.join(log_data)

        self.op_name = opcodes.opcode_names.get(self.item_data[1], 'PUSHDATA')

    def data(self, column, role = Qt.DisplayRole):
        item_data = super(TopLevelScriptItem, self).data(column, role)
        if column == 1:
            return self.op_name
        elif column == 2:
            return self.stack_data
        elif column == 3:
            return self.log_data
        return item_data

class SubLevelScriptItem(ScriptExecutionItem):
    """Tree View item for the state of a script execution step."""
    def __init__(self, data, parent=None):
        super(SubLevelScriptItem, self).__init__(data, parent)
        self.op_data = ''.join(['    ', self.item_data[2]])
        self.log_data = ''.join(['    ', self.item_data[3]])

    def data(self, column, role = Qt.DisplayRole):
        if column == 2 and role == Qt.DisplayRole:
            return self.op_data
        elif column == 3 and role == Qt.DisplayRole:
            return self.log_data
        return super(SubLevelScriptItem, self).data(column, role)

class ScriptExecutionModel(QAbstractItemModel):
    """Model of a script's execution."""
    def __init__(self, execution, parent=None):
        super(ScriptExecutionModel, self).__init__(parent)
        self.execution = execution
        self.plugin_handler = None
        self.rootItem = ScriptExecutionItem(('Step', 'Op', 'Stack', 'Log'))
        self.header_tooltips = ['Step Number', 'Operation', 'Stack State', 'Description']
        self.setup_data(self.execution, self.rootItem)

    def columnCount(self, parent = QModelIndex()):
        if parent.isValid():
            return parent.internalPointer().columnCount()
        return self.rootItem.columnCount()

    def rowCount(self, parent = QModelIndex()):
        if parent.column() > 0:
            return 0
        if parent.isValid():
            return parent.internalPointer().childCount()
        return self.rootItem.childCount()

    def index(self, row, column, parent = QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if parent.isValid():
            parent_item = parent.internalPointer()
        else:
            parent_item = self.rootItem

        child_item = parent_item.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)
        return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        item = index.internalPointer()
        parent_item = item.parent()

        if parent_item == self.rootItem:
            return QModelIndex()
        return self.createIndex(parent_item.row(), 0, parent_item)

    def headerData(self, section, orientation, role = Qt.DisplayRole):
        if orientation != Qt.Horizontal:
            return None

        if role == Qt.DisplayRole:
            return self.rootItem.data(section)
        elif role == Qt.ToolTipRole:
            try:
                return self.header_tooltips[section]
            except IndexError:
                return None

    def data(self, index, role = Qt.DisplayRole):
        if not index.isValid():
            return None

        if role not in [Qt.DisplayRole, Qt.EditRole, Qt.ToolTipRole]:
            return None

        item = index.internalPointer()
        return item.data(index.column(), role)

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def setup_data(self, execution, parent):
        self.beginResetModel()
        for count, step in enumerate(execution.steps):
            step_item = TopLevelScriptItem((count, step.last_op, step.stack, step.log), parent)
            # Loop through stack items.
            scr = Script(step.stack).get_human().split()
            for i, data in enumerate(step.stack):
                human = scr[i]
                # Variable name
                if self.plugin_handler:
                    key = self.plugin_handler.get_plugin('Variables').dock.key_for_value(human, strict=False)
                    if key:
                        human = '$' + key

                stack_data = data
                try:
                    stack_data = stack_data.encode('hex')
                except Exception:
                    stack_data = str(stack_data)
                data_item = SubLevelScriptItem([i, '', stack_data, human], step_item)
                step_item.appendChild(data_item)
            parent.appendChild(step_item)
        self.endResetModel()

    def evaluate(self, execution=None):
        if execution:
            self.execution = execution
        self.rootItem = ScriptExecutionItem(('Step', 'Op', 'Stack', 'Log'))
        self.setup_data(self.execution, self.rootItem)

    def clear(self):
        self.evaluate(ScriptExecution())

class StackWidget(QListWidget):
    """List view of a stack."""
    def __init__(self, *args):
        super(StackWidget, self).__init__(*args)
        self.setAlternatingRowColors(True)
        self.script = Script()

    @pyqtProperty(str)
    def human(self):
        return self.script.get_human()

    @human.setter
    def human(self, value):
        self.clear()
        s = []
        self.script = Script.from_human(str(value))
        iterator = self.script.human_iter()
        while 1:
            try:
                s.append(next(iterator))
            except Exception:
                break
        s.reverse()
        self.addItems(s)

class ScriptExecutionWidget(QWidget):
    """Model and view showing a script's execution."""
    def __init__(self, execution, parent=None):
        super(ScriptExecutionWidget, self).__init__(parent)

        self.execution = execution
        self.model = ScriptExecutionModel(execution)
        self.view = QTreeView()
        self.view.setModel(self.model)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.selectionModel().currentRowChanged.connect(self.on_selection_changed)
        self.view.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        self.view.setAlternatingRowColors(True)
        self.view.setWhatsThis('This view displays the steps of the script\'s execution.')

        self.error_edit = QLineEdit('')
        self.error_edit.setProperty('hasError', True)
        self.error_edit.hide()

        self.stack_label = QLabel('Stack:')
        self.stack_list = StackWidget()
        self.stack_list.setWhatsThis('The selected stack or stack item is shown here.')
        self.log_label = QLabel('Log:')
        self.log_edit = QLineEdit()
        self.log_edit.setWhatsThis('The result of the selected step, or the selected stack item in human-readable form, is shown here.')
        for i in [self.error_edit, self.log_edit]:
            i.setReadOnly(True)

        self.mapper = QDataWidgetMapper()
        self.mapper.setModel(self.model)
        self.mapper.addMapping(self.stack_list, 2, 'human')
        self.mapper.addMapping(self.log_edit, 3)

        self.widgets_form = form = QFormLayout()
        form.addRow(self.error_edit)
        form.addRow(self.stack_label, self.stack_list)
        form.addRow(self.log_label, self.log_edit)

        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self.view, stretch=1)
        vbox.addLayout(form)
        self.setLayout(vbox)

    def evaluate(self, tx_script, txTo=None, inIdx=0, flags=None):
        """Evaluate a script."""
        if flags is None:
            flags = ()
        self.execution.evaluate(tx_script, txTo, inIdx, flags)
        self.model.evaluate(self.execution)
        if self.execution.error:
            self.error_edit.setText(str(self.execution.error))
            self.error_edit.show()
        else:
            self.error_edit.clear()
            self.error_edit.hide()

    def on_selection_changed(self, selected, deselected):
        try:
            idx = selected
            is_root = not idx.parent().isValid()
            self.change_labels(is_root)
            self.mapper.setRootIndex(idx.parent())
            self.mapper.setCurrentIndex(idx.row())
        except Exception as e:
            self.mapper.setCurrentIndex(0)

    def change_labels(self, is_root):
        """Change the widget labels depending on what is being viewed."""
        if is_root:
            self.log_label.setText('Log:')
            self.stack_label.setText('Stack:')
        else:
            self.log_label.setText('Text:')
            self.stack_label.setText('Data: ')

    def select_next(self):
        """Select the next execution step or stack item."""
        try:
            index = self.view.selectionModel().selectedIndexes()[0]
            next_row = index.row() + 1
            next_index = self.model.index(next_row, index.column(), index.parent())
        except IndexError:
            next_index = self.model.index(self.model.rowCount() - 1, 0)
        finally:
            if not next_index.isValid():
                return
            self.view.selectionModel().select(next_index, QItemSelectionModel.SelectCurrent | QItemSelectionModel.Rows)
            self.on_selection_changed(next_index, None)

    def select_prev(self):
        """Select the previous execution step or stack item."""
        try:
            index = self.view.selectionModel().selectedIndexes()[0]
            prev_row = max(0, index.row() - 1)
            prev_index = self.model.index(prev_row, index.column(), index.parent())
        except IndexError:
            prev_index = self.model.index(0, 0)
        finally:
            if not prev_index.isValid():
                return
            self.view.selectionModel().select(prev_index, QItemSelectionModel.SelectCurrent | QItemSelectionModel.Rows)
            self.on_selection_changed(prev_index, None)

    def clear(self):
        self.model.clear()
