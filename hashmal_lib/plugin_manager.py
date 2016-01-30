import __builtin__

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from gui_utils import Separator, required_plugins, default_plugins

class PluginsModel(QAbstractTableModel):
    def __init__(self, gui, parent=None):
        super(PluginsModel, self).__init__(parent)
        self.gui = gui
        self.plugins = gui.plugin_handler.loaded_plugins
        self.config = gui.config
        self.config.optionChanged.connect(self.on_option_changed)
        self.enabled_plugins = self.config.get_option('enabled_plugins', default_plugins)
        self.favorite_plugins = self.config.get_option('favorite_plugins', [])

    def columnCount(self, parent=QModelIndex()):
        return 6

    def rowCount(self, parent=QModelIndex()):
        return len(self.plugins)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Vertical:
            return QVariant(None)

        headers = [
                {Qt.DisplayRole: 'Plugin', Qt.ToolTipRole: 'Plugin Name'},
                {Qt.DisplayRole: 'Category', Qt.ToolTipRole: 'Plugin Category'},
                {Qt.DisplayRole: 'Enabled', Qt.ToolTipRole: 'Whether the plugin is enabled'},
                {Qt.DisplayRole: 'Favorite', Qt.ToolTipRole: 'Whether the plugin is a favorite'},
                {Qt.DisplayRole: 'GUI', Qt.ToolTipRole: 'Whether the plugin has a graphical user interface'},
                {Qt.DisplayRole: 'Description', Qt.ToolTipRole: 'Plugin description'}
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
            if role in [Qt.DisplayRole, Qt.ToolTipRole, Qt.EditRole]:
                data = plugin.name
        elif col == 1:
            category_name, category_desc = plugin.ui.category
            if role in [Qt.DisplayRole, Qt.EditRole]:
                data = category_name
            elif role in [Qt.ToolTipRole]:
                data = category_desc
        elif col == 2:
            is_enabled = plugin.name in self.enabled_plugins
            if role in [Qt.DisplayRole]:
                data = 'Yes' if is_enabled else 'No'
            elif role == Qt.CheckStateRole:
                data = Qt.Checked if is_enabled else Qt.Unchecked
            elif role == Qt.EditRole:
                data = is_enabled
        elif col == 3:
            is_favorite = plugin.name in self.favorite_plugins
            if role in [Qt.DisplayRole]:
                data = 'Yes' if is_favorite else 'No'
            elif role == Qt.CheckStateRole:
                data = Qt.Checked if is_favorite else Qt.Unchecked
            elif role == Qt.EditRole:
                data = is_favorite
        elif col == 4:
            has_gui = plugin.has_gui
            if role in [Qt.DisplayRole]:
                data = 'Yes' if has_gui else 'No'
            elif role == Qt.EditRole:
                data = has_gui
        elif col == 5:
            if role in [Qt.DisplayRole, Qt.EditRole]:
                data = plugin.ui.description

        return QVariant(data)

    def setData(self, index, value, role = Qt.EditRole):
        if not index.isValid():
            return False

        col = index.column()
        plugin = self.plugin_for_index(index)

        if col == 2:
            is_checked = value.toBool()
            enabled = self.enabled_plugins
            name = plugin.name
            is_enabled = name in enabled

            # No need to do anything.
            if (is_checked and is_enabled) or (not is_checked and not is_enabled):
                return False
            # Enable plugin.
            elif is_checked and not is_enabled:
                enabled.append(name)
            # Disable plugin.
            elif not is_checked and is_enabled:
                enabled.remove(name)

            self.config.set_option('enabled_plugins', enabled)
            return True
        elif col == 3:
            is_checked = value.toBool()
            favorites = self.favorite_plugins
            name = plugin.name
            in_favorites = name in favorites

            # No need to do anything.
            if (is_checked and in_favorites) or (not is_checked and not in_favorites):
                return False
            # Add to favorites.
            elif is_checked and not in_favorites:
                favorites.append(name)
            # Remove from favorites.
            elif not is_checked and in_favorites:
                favorites.remove(name)

            self.config.set_option('favorite_plugins', favorites)
            return True

        return True

    def plugin_for_index(self, index):
        if not index.isValid():
            return None
        plugin = sorted(self.plugins, key=lambda i: i.name)[index.row()]
        return plugin

    def on_option_changed(self, key):
        if key == 'enabled_plugins':
            new_enabled = self.config.get_option('enabled_plugins', default_plugins)
            # Update view if necessary.
            if self.enabled_plugins != new_enabled:
                self.enabled_plugins = new_enabled
                self.dataChanged.emit(QModelIndex(), QModelIndex())
        elif key == 'favorite_plugins':
            new_favorites = self.config.get_option('favorite_plugins', [])
            if self.favorite_plugins != new_favorites:
                self.favorite_plugins = new_favorites
                self.dataChanged.emit(QModelIndex(), QModelIndex())

class PluginDetails(QWidget):
    """Widget with details and controls for a plugin."""

    def __init__(self, manager, parent=None):
        super(PluginDetails, self).__init__(parent)
        self.manager = manager

        self.name_label = QLineEdit()
        self.category_label = QLineEdit()
        self.desc_edit = QTextEdit()
        self.name_label.setToolTip('Plugin name')
        self.desc_edit.setToolTip('Plugin description')
        self.desc_edit.setReadOnly(True)
        self.desc_edit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        for i in [self.name_label, self.category_label, self.desc_edit]:
            i.setReadOnly(True)
        self.plugin_is_enabled = QCheckBox('Enabled')
        self.plugin_is_enabled.setToolTip('Whether this plugin is enabled')
        self.plugin_is_favorite = QCheckBox('Favorite')
        self.plugin_is_favorite.setToolTip('Favorite plugins are assigned keyboard shortcuts in the Tools menu')
        self.has_gui = QCheckBox('GUI')
        self.has_gui.setToolTip('Whether this plugin has a graphical user interface')
        self.has_gui.setEnabled(False)

        self.mapper = QDataWidgetMapper()
        self.mapper.setModel(self.manager.model)
        self.mapper.setSubmitPolicy(QDataWidgetMapper.AutoSubmit)
        self.mapper.addMapping(self.name_label, 0)
        self.mapper.addMapping(self.category_label, 1)
        self.mapper.addMapping(self.plugin_is_enabled, 2)
        self.mapper.addMapping(self.plugin_is_favorite, 3)
        self.mapper.addMapping(self.has_gui, 4)
        self.mapper.addMapping(self.desc_edit, 5)

        form = QFormLayout()
        form.setContentsMargins(0,6,0,0)
        form.addRow('Plugin Name:', self.name_label)
        form.addRow('Category:', self.category_label)
        form.addRow(self.plugin_is_enabled)
        form.addRow(self.plugin_is_favorite)
        form.addRow(self.has_gui)
        form.addRow(self.desc_edit)
        self.setLayout(form)

    def set_index(self, index):
        """Set the mapper's index."""
        self.mapper.setCurrentIndex(index.row())
        plugin = self.manager.model.plugin_for_index(index)

        self.plugin_is_enabled.setEnabled(not plugin.name in required_plugins)
        self.plugin_is_favorite.setEnabled(plugin.has_gui)

class PluginManager(QDialog):
    """GUI for the plugin system."""
    def __init__(self, main_window):
        super(PluginManager, self).__init__(main_window)
        self.gui = main_window
        self.config = self.gui.config
        self.create_layout()
        self.setWindowTitle('Plugin Manager')
        self.view.setFocus()

    def sizeHint(self):
        return QSize(500, 400)

    def create_layout(self):
        vbox = QVBoxLayout()

        self.model = PluginsModel(self.gui)
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)

        self.view = QTableView()
        self.view.setModel(self.proxy_model)
        self.view.setSortingEnabled(True)
        self.view.setAlternatingRowColors(True)
        self.view.setWordWrap(True)

        self.view.horizontalHeader().setResizeMode(0, QHeaderView.Stretch)
        self.view.horizontalHeader().setResizeMode(1, QHeaderView.ResizeToContents)
        self.view.horizontalHeader().setHighlightSections(False)
        for i in [4, 5]:
            self.view.horizontalHeader().setSectionHidden(i, True)
        self.view.verticalHeader().setDefaultSectionSize(22)
        self.view.verticalHeader().setVisible(False)

        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.selectionModel().selectionChanged.connect(self.update_details_area)
        self.view.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.view.sortByColumn(0, Qt.AscendingOrder)

        self.plugin_details = PluginDetails(self)

        filter_edit = QLineEdit()
        def filter_view():
            regexp = QRegExp(str(filter_edit.text()), Qt.CaseInsensitive)
            self.proxy_model.setFilterRegExp(regexp)
        filter_edit.textChanged.connect(filter_view)
        filter_label = QLabel('&Find:')
        filter_label.setBuddy(filter_edit)
        filter_box = QHBoxLayout()
        filter_box.addWidget(filter_label)
        filter_box.addWidget(filter_edit, stretch=1)

        is_local = QLabel('Hashmal is being run locally.\n\nInstall Hashmal to use third-party plugins.\n')
        is_local.setVisible(__builtin__.use_local_modules)

        vbox.addWidget(is_local)
        vbox.addLayout(filter_box)
        vbox.addWidget(self.view)
        vbox.addWidget(Separator())
        vbox.addWidget(self.plugin_details)
        self.setLayout(vbox)

        self.view.selectRow(0)

    def update_details_area(self, selected, deselected):
        """Update the plugin details area when selection changes."""
        selected = self.proxy_model.mapSelectionToSource(selected)
        try:
            index = selected.indexes()[0]
        except IndexError:
            return
        self.plugin_details.set_index(index)

