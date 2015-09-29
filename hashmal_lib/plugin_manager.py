

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from gui_utils import Separator, required_plugins

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

        headers = [
                {Qt.DisplayRole: 'Plugin', Qt.ToolTipRole: 'Plugin Name'},
                {Qt.DisplayRole: 'Enabled?', Qt.ToolTipRole: 'Whether the plugin is enabled'}
        ]

        data = None
        try:
            data = QVariant(headers[section][role])
            return data
        except (IndexError, KeyError):
            pass

        return QVariant(data)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant(None)

        data = None
        col = index.column()
        plugin = self.plugin_for_index(index)

        if col == 0:
            if role in [Qt.DisplayRole, Qt.ToolTipRole]:
                data = plugin.name
        elif col == 1:
            is_enabled = plugin.name not in self.disabled_plugins
            if role in [Qt.DisplayRole]:
                data = 'Yes' if is_enabled else 'No'

        return QVariant(data)

    def plugin_for_index(self, index):
        if not index.isValid():
            return None
        plugin = sorted(self.plugins, key=lambda i: i.name)[index.row()]
        return plugin

    def on_option_changed(self, key):
        if key == 'disabled_plugins':
            new_disabled = self.config.get_option('disabled_plugins', [])
            # Update view if necessary.
            if self.disabled_plugins != new_disabled:
                self.disabled_plugins = new_disabled
                self.dataChanged.emit(QModelIndex(), QModelIndex())

class PluginDetails(QWidget):
    """Widget with details and controls for a plugin."""

    def __init__(self, manager, parent=None):
        super(PluginDetails, self).__init__(parent)
        self.manager = manager
        # Changing plugin_is_favorite only updates shortcuts if this is True.
        self.is_ready = False

        self.name_label = QLabel()
        self.desc_edit = QTextEdit()
        self.name_label.setToolTip('Plugin name')
        self.desc_edit.setToolTip('Plugin description')
        self.desc_edit.setReadOnly(True)
        self.plugin_is_enabled = QCheckBox('Enabled plugin')
        self.plugin_is_enabled.setToolTip('Whether this plugin is enabled')
        self.plugin_is_enabled.stateChanged.connect(self.set_enabled)
        self.plugin_is_favorite = QCheckBox('Favorite plugin')
        self.plugin_is_favorite.setToolTip('Favorite plugins are assigned keyboard shortcuts in the Tools menu')
        self.plugin_is_favorite.stateChanged.connect(self.set_favorite)

        form = QFormLayout()
        form.setContentsMargins(0,6,0,0)
        form.addRow('Plugin Name:', self.name_label)
        form.addRow(self.plugin_is_enabled)
        form.addRow(self.plugin_is_favorite)
        form.addRow(self.desc_edit)
        self.setLayout(form)

    def set_plugin(self, plugin):
        """Set the plugin that this widget needs to represent."""
        self.is_ready = False
        self.name_label.setText(plugin.name)
        desc = []
        for i in plugin.dock.description.split('\n'):
            desc.append('<p>{}</p>'.format(i))
        self.desc_edit.setHtml(''.join(desc))

        is_in_favorites = plugin.name in self.manager.config.get_option('favorite_plugins', [])
        self.plugin_is_favorite.setChecked(is_in_favorites)
        if plugin.name in required_plugins:
            self.plugin_is_enabled.setEnabled(False)
        else:
            self.plugin_is_enabled.setEnabled(True)
            self.plugin_is_enabled.setChecked(plugin.dock.is_enabled)
        self.is_ready = True

    def set_enabled(self, is_checked):
        if not self.is_ready:
            return
        is_checked = True if is_checked else False
        disabled = self.manager.config.get_option('disabled_plugins', [])
        name = str(self.name_label.text())
        is_enabled = name not in disabled

        # No need to do anything.
        if (is_checked and is_enabled) or (not is_checked and not is_enabled):
            return
        # Enable plugin.
        elif is_checked and not is_enabled:
            disabled.remove(name)
        # Disable plugin.
        elif not is_checked and is_enabled:
            disabled.append(name)

        self.manager.config.set_option('disabled_plugins', disabled)

    def set_favorite(self, is_checked):
        if not self.is_ready:
            return
        is_checked = True if is_checked else False
        favorites = self.manager.config.get_option('favorite_plugins', [])
        name = str(self.name_label.text())
        in_favorites = name in favorites

        # No need to do anything.
        if (is_checked and in_favorites) or (not is_checked and not in_favorites):
            return
        # Add to favorites.
        elif is_checked and not in_favorites:
            favorites.append(name)
        # Remove from favorites.
        elif not is_checked and in_favorites:
            favorites.remove(name)

        self.manager.config.set_option('favorite_plugins', favorites)

class PluginManager(QDialog):
    """GUI for the plugin system."""
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
        self.view.horizontalHeader().setResizeMode(0, QHeaderView.Stretch)
        self.view.horizontalHeader().setResizeMode(1, QHeaderView.ResizeToContents)
        self.view.horizontalHeader().setHighlightSections(False)
        self.view.verticalHeader().setDefaultSectionSize(22)
        self.view.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.selectionModel().selectionChanged.connect(self.update_details_area)
        self.view.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        details_area = self.create_details_area()

        vbox.addWidget(self.view)
        vbox.addWidget(Separator())
        vbox.addWidget(details_area)
        self.setLayout(vbox)

        self.view.selectRow(0)

    def create_details_area(self):
        self.plugin_details = PluginDetails(self)
        return self.plugin_details

    def update_details_area(self, selected, deselected):
        """Update the plugin details area when selection changes."""
        index = selected.indexes()[0]
        plugin = self.model.plugin_for_index(index)
        if str(self.plugin_details.name_label.text()) == plugin.name:
            return
        self.plugin_details.set_plugin(plugin)

