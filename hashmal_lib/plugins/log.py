from collections import namedtuple
import logging
import datetime

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from hashmal_lib.plugins import BaseDock, Plugin

def make_plugin():
    return Plugin(Log)

log_level_names = {
    logging.DEBUG: 'DEBUG',
    logging.INFO: 'INFO',
    logging.WARNING: 'WARNING',
    logging.ERROR: 'ERROR',
    logging.CRITICAL: 'CRITICAL',
}

LogItem = namedtuple('LogItem', ('timestamp', 'level', 'plugin', 'message'))

class LogProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super(LogProxyModel, self).__init__(parent)
        self.min_level = logging.ERROR

    def set_min_level(self, level):
        self.min_level = level
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        level = self.sourceModel().data(self.sourceModel().index(source_row, LogModel.LEVEL), Qt.EditRole)
        if level >= self.min_level:
            return True
        return False

class LogModel(QAbstractTableModel):
    """Model for recent log messages."""
    TIME = 0
    LEVEL = 1
    PLUGIN = 2
    MESSAGE = 3

    def __init__(self, config, parent=None):
        super(LogModel, self).__init__(parent)
        self.config = config
        self.messages = []
        self.max_items = 100

    def columnCount(self, parent=QModelIndex()):
        return 4

    def rowCount(self, parent=QModelIndex()):
        return len(self.messages)

    def headerData(self, section, orientation, role = Qt.DisplayRole):
        if orientation != Qt.Horizontal:
            return None
        if role not in [Qt.DisplayRole, Qt.EditRole, Qt.ToolTipRole]:
            return None

        data = None
        if section == 0:
            data = 'Time'
        elif section == 1:
            data = 'Level'
        elif section == 2:
            data = 'Plugin'
        elif section == 3:
            data = 'Message'

        return data

    def data(self, index, role = Qt.DisplayRole):
        if not index.isValid():
            return None

        # Tinted background.
        if role == Qt.BackgroundColorRole:
            sibling = index.sibling(index.row(), self.LEVEL)
            level, ok = sibling.data(Qt.EditRole).toInt()
            if not ok:
                return
            if level == logging.WARNING:
                color = QColor(255, 255, 0)
                color.setAlphaF(0.256)
                return color
            if level == logging.ERROR:
                color = QColor(255, 0, 0)
                color.setAlphaF(0.25)
                return color
            return

        data = None
        c = index.column()
        item = self.messages[index.row()]
        if c == self.TIME:
            if role in [Qt.DisplayRole, Qt.ToolTipRole, Qt.EditRole]:
                data = datetime.datetime.fromtimestamp(item.timestamp).strftime('%D %H:%M')
            elif role == Qt.EditRole:
                data = item.timestamp
                # String for keyboard copy-paste convenience.
                if role != Qt.EditRole:
                    data = str(data)
        elif c == self.LEVEL:
            if role in [Qt.DisplayRole, Qt.ToolTipRole]:
                data = log_level_names.get(item.level)
            elif role == Qt.EditRole:
                data = item.level
        elif c == self.PLUGIN:
            if role in [Qt.DisplayRole, Qt.ToolTipRole, Qt.EditRole]:
                data = item.plugin
        elif c == self.MESSAGE:
            if role in [Qt.DisplayRole, Qt.ToolTipRole, Qt.EditRole]:
                data = item.message

        return data

    def add_log_message(self, item):
        # TODO use insertRows
        self.beginResetModel()
        self.messages.append(item)
        self.endResetModel()

        self.limit_max_items()

    def limit_max_items(self):
        if len(self.messages) > self.max_items:
            self.beginResetModel()
            self.messages = self.messages[:self.max_items]
            self.endResetModel()

    def set_max_items(self, max_items):
        self.max_items = max_items
        self.limit_max_items()

class Log(BaseDock):
    tool_name = 'Log'
    description = 'Contains a log of recent events.'

    def create_layout(self):
        self.model = LogModel(self.config)
        self.proxy_model = LogProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.view = QTableView()
        self.view.setModel(self.proxy_model)
        self.view.verticalHeader().setVisible(False)
        self.view.horizontalHeader().setHighlightSections(False)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.horizontalHeader().setResizeMode(LogModel.LEVEL, QHeaderView.ResizeToContents)
        self.view.horizontalHeader().setResizeMode(LogModel.MESSAGE, QHeaderView.Stretch)
        self.view.setToolTip('Log messages')
        self.view.setWhatsThis('Log messages are displayed here.\n\nYou can change the minimum priority of messages that are displayed via the Settings dialog.')

        self.update_log_level()

        desc = QLabel('Log messages are shown here.')

        max_items = QSpinBox()
        max_items.setRange(1, 500)
        max_items.setToolTip('Maximum log items stored')
        max_items.setWhatsThis('Use this to change the maximum number of messages stored here.')
        max_items.setValue(self.option('max_items', 100))
        def change_max_items(i):
            self.set_option('max_items', i)
            self.model.set_max_items(i)
        max_items.valueChanged.connect(change_max_items)

        self.model.set_max_items(max_items.value())

        form = QFormLayout()
        form.setContentsMargins(0,0,0,0)
        form.addRow('Max messages stored:', max_items)

        vbox = QVBoxLayout()
        vbox.addWidget(desc)
        vbox.addLayout(form)
        vbox.addWidget(self.view, stretch=1)

        return vbox

    def add_log_message(self, time, level, plugin, message):
        item = LogItem(time, level, plugin, message)
        self.model.add_log_message(item)

    def update_log_level(self):
        level_str = self.config.get_option('log_level', 'Error').upper()
        if level_str not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            level_str = 'ERROR'
        level = getattr(logging, level_str)
        self.proxy_model.set_min_level(level)

    def on_option_changed(self, key):
        if key == 'log_level':
            self.update_log_level()
