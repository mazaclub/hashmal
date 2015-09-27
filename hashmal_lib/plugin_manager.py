

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from gui_utils import Separator

class PluginsModel(QAbstractTableModel):
    def __init__(self, gui, parent=None):
        super(PluginsModel, self).__init__(parent)
        self.gui = gui
        self.plugins = gui.plugin_handler.loaded_plugins
        self.config = gui.config
        self.config.optionChanged.connect(self.on_option_changed)
        self.disabled_plugins = self.config.get_option('disabled_plugins', [])

    def columnCount(self, parent=QModelIndex()):
        return 2

    def rowCount(self, parent=QModelIndex()):
        return len(self.plugins)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Vertical:
            return QVariant(None)
        if role not in [Qt.DisplayRole, Qt.ToolTipRole]:
            return QVariant(None)

        data = None
        if section == 0:
            if role == Qt.DisplayRole:
                data = 'Enabled?'
            elif role == Qt.ToolTipRole:
                data = 'Whether the plugin is enabled'
        elif section == 1:
            if role == Qt.DisplayRole:
                data = 'Name'
            elif role == Qt.ToolTipRole:
                data = 'Plugin Name'

        return QVariant(data)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant(None)
        if role not in [Qt.CheckStateRole, Qt.DisplayRole, Qt.ToolTipRole]:
            return QVariant(None)

        data = None
        col = index.column()
        plugin = self.plugin_for_index(index)

        if col == 0:
            is_enabled = plugin.name not in self.disabled_plugins
            if role in [Qt.CheckStateRole]:
                data = is_enabled
            elif role in [Qt.DisplayRole]:
                data = 'Yes' if is_enabled else 'No'
        elif col == 1:
            if role in [Qt.DisplayRole, Qt.ToolTipRole]:
                data = plugin.name

        return QVariant(data)

    def plugin_for_index(self, index):
        if not index.isValid():
            return None
        plugin = sorted(self.plugins, key=lambda i: i.name)[index.row()]
        return plugin

    def on_option_changed(self, key):
        if key == 'disabled_plugins':
            self.disabled_plugins = self.config.get_option('disabled_plugins', [])

class ToolWidget(QWidget):
    """Widget with details and controls for a tool."""

    def __init__(self, manager, dock=None, parent=None):
        super(ToolWidget, self).__init__(parent)
        self.manager = manager
        # Changing tool_is_favorite only does something if this is True.
        self.is_ready = False

        self.tool_name_edit = QLineEdit()
        self.tool_desc_edit = QTextEdit()
        self.tool_name_edit.setToolTip('Window title of the plugin\'s tool')
        self.tool_desc_edit.setToolTip('Tool description')
        for i in [self.tool_name_edit, self.tool_desc_edit]:
            i.setReadOnly(True)
        self.tool_is_favorite = QCheckBox('Favorite tool')
        self.tool_is_favorite.setToolTip('Favorite tools are assigned keyboard shortcuts in the Tools menu')
        self.tool_is_favorite.stateChanged.connect(self.set_favorite)

        form = QFormLayout()
        form.setContentsMargins(0,6,0,0)
        form.addRow('Tool Name:', self.tool_name_edit)
        form.addRow(self.tool_is_favorite)
        form.addRow(self.tool_desc_edit)
        self.setLayout(form)

        if dock is not None:
            self.set_tool(dock)

    def set_tool(self, dock):
        self.is_ready = False
        self.tool_name_edit.setText(dock.tool_name)
        desc = []
        for i in dock.description.split('\n'):
            desc.append('<p>{}</p>'.format(i))
        self.tool_desc_edit.setHtml(''.join(desc))

        is_in_favorites = dock.tool_name in self.manager.config.get_option('favorite_tools', [])
        self.tool_is_favorite.setChecked(is_in_favorites)
        self.is_ready = True

    def set_favorite(self, is_checked):
        if not self.is_ready:
            return
        is_checked = True if is_checked else False
        fav_tools = self.manager.config.get_option('favorite_tools', [])
        tool_name = str(self.tool_name_edit.text())
        in_favorites = tool_name in fav_tools

        # No need to do anything.
        if (is_checked and in_favorites) or (not is_checked and not in_favorites):
            return
        # Add to favorites.
        elif is_checked and not in_favorites:
            fav_tools.append(tool_name)
        # Remove from favorites.
        elif not is_checked and in_favorites:
            fav_tools.remove(tool_name)

        self.manager.config.set_option('favorite_tools', fav_tools)

class PluginManager(QDialog):
    def __init__(self, main_window):
        super(PluginManager, self).__init__(main_window)
        self.gui = main_window
        self.config = self.gui.config
        self.create_layout()
        self.setWindowTitle('Plugin Manager')

    def sizeHint(self):
        return QSize(500, 400)

    def create_layout(self):
        vbox = QVBoxLayout()

        self.model = PluginsModel(self.gui)

        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(True)
        self.view.setWordWrap(True)
        self.view.horizontalHeader().setResizeMode(0, QHeaderView.ResizeToContents)
        self.view.horizontalHeader().setResizeMode(1, QHeaderView.Stretch)
        self.view.horizontalHeader().setHighlightSections(False)
        self.view.verticalHeader().setDefaultSectionSize(22)
        self.view.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.selectionModel().selectionChanged.connect(self.update_details_area)

        details_area = self.create_details_area()

        vbox.addWidget(self.view)
        vbox.addWidget(Separator())
        vbox.addWidget(details_area)
        self.setLayout(vbox)

        self.view.selectRow(0)

    def create_details_area(self):
        self.details_plugin_name = QLabel()

        self.tool_widget = ToolWidget(self)

        form = QFormLayout()
        form.addRow('Plugin:', self.details_plugin_name)
        form.addRow(self.tool_widget)

        w = QWidget()
        w.setLayout(form)

        return w

    def update_details_area(self, selected, deselected):
        """Update the plugin details area."""
        index = selected.indexes()[0]
        plugin = self.model.plugin_for_index(index)
        if str(self.details_plugin_name.text()) == plugin.name:
            return
        self.details_plugin_name.setText(plugin.name)
        self.tool_widget.set_tool(plugin.dock)

