import __builtin__

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from hashmal_lib.plugins.base import Category
from gui_utils import Separator, required_plugins, default_plugins, hashmal_builtin_plugins

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
            if role in [Qt.DisplayRole, Qt.EditRole]:
                data = plugin.category.name
            elif role in [Qt.ToolTipRole]:
                data = plugin.category.description
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
        return self.plugin_for_row(index.row())

    def plugin_for_row(self, row):
        plugin = sorted(self.plugins, key=lambda i: i.name)[row]
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

class PluginsProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super(PluginsProxyModel, self).__init__(parent)
        self.name_filter = QRegExp()
        self.hide_core_plugins = True
        self.hide_builtin_plugins = False
        self.hide_gui_plugins = False
        self.hide_nongui_plugins = False

    def set_name_filter(self, regexp):
        self.name_filter = regexp
        self.invalidateFilter()

    def set_hide_core_plugins(self, do_hide):
        self.hide_core_plugins = do_hide
        self.invalidateFilter()

    def set_hide_builtin_plugins(self, do_hide):
        self.hide_builtin_plugins = do_hide
        self.invalidateFilter()

    def set_hide_gui_plugins(self, do_hide):
        self.hide_gui_plugins = do_hide
        self.invalidateFilter()

    def set_hide_nongui_plugins(self, do_hide):
        self.hide_nongui_plugins = do_hide
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        plugin = self.sourceModel().plugin_for_row(source_row)

        if self.hide_core_plugins:
            if plugin.category == Category.Core:
                return False
        if self.hide_builtin_plugins:
            builtin_plugin_names = [i[0] for i in hashmal_builtin_plugins]
            if plugin.name in builtin_plugin_names:
                return False
        if self.hide_gui_plugins and plugin.has_gui:
            return False
        if self.hide_nongui_plugins and not plugin.has_gui:
            return False
        if self.name_filter:
            idx = self.sourceModel().index(source_row, 0, source_parent)
            name = str(self.sourceModel().data(idx).toString())
            if self.name_filter.indexIn(name) == -1:
                return False
        return True


class FavoritesModel(QAbstractTableModel):
    """Models favorite plugins."""
    def __init__(self, gui, parent=None):
        super(FavoritesModel, self).__init__(parent)
        self.plugin_handler = gui.plugin_handler
        self.config = gui.config
        self.config.optionChanged.connect(self.on_option_changed)
        self.favorite_plugins = self.config.get_option('favorite_plugins', [])

    def rowCount(self, parent = QModelIndex()):
        return len(self.favorite_plugins)

    def columnCount(self, parent = QModelIndex()):
        return 1

    def headerData(self, section, orientation, role = Qt.DisplayRole):
        data = None
        if orientation == Qt.Horizontal and section == 0:
            if role in [Qt.DisplayRole, Qt.ToolTipRole]:
                data = 'Favorite Plugins'
        else:
            if section < len(self.favorite_plugins):
                if role == Qt.DisplayRole:
                    data = '+'.join(['Alt', str(section + 1)])
                elif role == Qt.ToolTipRole:
                    data = 'Plugin shortcut'

        return data

    def data(self, index, role = Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.favorite_plugins):
            return None
        data = None
        plugin_name = self.favorite_plugins[index.row()]
        if role in [Qt.DisplayRole, Qt.ToolTipRole, Qt.EditRole]:
            data = plugin_name

        return data

    def setData(self, index, value, role = Qt.EditRole):
        if not index.isValid():
            return False
        if index.column() != 0:
            return False
        plugin_name = str(value.toString())
        if plugin_name in self.favorite_plugins:
            return self.move_plugin_name(plugin_name, index.row())
        return False

    def move_plugin_name(self, plugin_name, row):
        # Make sure plugin exists.
        if not self.plugin_handler.get_plugin(plugin_name):
            return False
        # If we're replacing an item, remove it.
        try:
            old_row = self.favorite_plugins.index(plugin_name)
            self.favorite_plugins.pop(old_row)
        except ValueError:
            pass
        self.favorite_plugins.insert(row, plugin_name)
        self.config.set_option('favorite_plugins', self.favorite_plugins)
        return True

    def remove_plugin(self, plugin_name):
        if plugin_name in self.favorite_plugins:
            self.favorite_plugins.remove(plugin_name)
            self.config.set_option('favorite_plugins', self.favorite_plugins)
            return True
        return False

    def supportedDropActions(self):
        return Qt.MoveAction

    def flags(self, index):
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if not index.isValid():
            return flags | Qt.ItemIsDropEnabled
        return flags | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled

    def mimeTypes(self):
        return ['text/plain']

    def mimeData(self, indexes):
        mime_data = QMimeData()
        text = self.data(indexes[0])
        mime_data.setText(text)
        return mime_data

    def dropMimeData(self, data, action, row, column, parent):
        r = self.rowCount()
        c = 0
        if parent.isValid():
            r = parent.row()
            c = parent.column()
        if action != Qt.MoveAction:
            return False
        if c != 0:
            return False

        if not data.hasText():
            return False

        text = str(data.text())
        if r >= 0:
            idx = self.index(r, c)
            self.setData(idx, QVariant(text))
            return True
        return False

    def on_option_changed(self, key):
        if key == 'favorite_plugins':
            new_favorites = self.config.get_option('favorite_plugins', [])
            self.beginResetModel()
            self.favorite_plugins = new_favorites
            self.endResetModel()

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

        # Set tooltips.
        tooltip = self.manager.model.data(self.manager.model.index(index.row(), 1), Qt.ToolTipRole).toString()
        self.category_label.setToolTip(tooltip)
        tooltip = 'This plugin has a GUI' if self.has_gui.isChecked() else 'This plugin has no GUI'
        self.has_gui.setToolTip(tooltip)

class OptionsWidget(QWidget):
    """Plugin view options."""
    def __init__(self, plugin_manager, parent=None):
        super(OptionsWidget, self).__init__(parent)
        self.plugin_manager = plugin_manager
        self.proxy_model = plugin_manager.proxy_model

        # General

        self.hide_core_plugins = QCheckBox('Hide Core plugins')
        self.hide_core_plugins.setToolTip('A "core plugin" refers to required Hashmal functionality implemented as a plugin')
        self.hide_core_plugins.setChecked(self.option('hide_core_plugins', True))
        self.hide_core_plugins.stateChanged.connect(self.change_hide_core_plugins)

        self.hide_builtin_plugins = QCheckBox('Hide built-in plugins')
        self.hide_builtin_plugins.setToolTip('Hide plugins that are included with Hashmal')
        self.hide_builtin_plugins.setChecked(self.option('hide_builtin_plugins', False))
        self.hide_builtin_plugins.stateChanged.connect(self.change_hide_builtin_plugins)

        general_vbox = QVBoxLayout()
        general_vbox.addWidget(self.hide_core_plugins)
        general_vbox.addWidget(self.hide_builtin_plugins)
        general_group = self.make_section('General', general_vbox)

        # Graphical plugins

        self.hide_gui_plugins = QCheckBox('Hide graphical plugins')
        self.hide_gui_plugins.setToolTip('Hide plugins that have graphical interfaces')
        self.hide_gui_plugins.setChecked(self.option('hide_gui_plugins', False))
        self.hide_gui_plugins.stateChanged.connect(self.change_hide_gui_plugins)

        self.hide_nongui_plugins = QCheckBox('Hide non-graphical plugins')
        self.hide_nongui_plugins.setToolTip('Hide plugins that do not have graphical interfaces')
        self.hide_nongui_plugins.setChecked(self.option('hide_nongui_plugins', False))
        self.hide_nongui_plugins.stateChanged.connect(self.change_hide_nongui_plugins)

        gui_vbox = QVBoxLayout()
        gui_vbox.addWidget(self.hide_gui_plugins)
        gui_vbox.addWidget(self.hide_nongui_plugins)
        gui_group = self.make_section('Graphical Plugins', gui_vbox)


        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(general_group)
        vbox.addWidget(gui_group)
        vbox.addStretch()
        self.setLayout(vbox)

    def make_section(self, title, layout):
        group = QGroupBox(title)
        group.setFlat(True)
        group.setLayout(layout)
        return group

    def option(self, key, default=None):
        return self.plugin_manager.option(key, default)

    def set_option(self, key, value):
        return self.plugin_manager.set_option(key, value)

    def change_hide_core_plugins(self, state):
        do_hide = True if state == Qt.Checked else False
        self.set_option('hide_core_plugins', do_hide)
        self.proxy_model.set_hide_core_plugins(do_hide)

    def change_hide_builtin_plugins(self, state):
        do_hide = True if state == Qt.Checked else False
        self.set_option('hide_builtin_plugins', do_hide)
        self.proxy_model.set_hide_builtin_plugins(do_hide)

    def change_hide_gui_plugins(self):
        do_hide = self.hide_gui_plugins.isChecked()
        self.set_option('hide_gui_plugins', do_hide)
        self.proxy_model.set_hide_gui_plugins(do_hide)

    def change_hide_nongui_plugins(self):
        do_hide = self.hide_nongui_plugins.isChecked()
        self.set_option('hide_nongui_plugins', do_hide)
        self.proxy_model.set_hide_nongui_plugins(do_hide)

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
        return QSize(750, 550)

    def options(self):
        return self.config.get_option('Plugin Manager', {})

    def option(self, key, default=None):
        return self.options().get(key, default)

    def set_option(self, key, value):
        options = self.options()
        options[key] = value
        self.config.set_option('Plugin Manager', options)

    def create_layout(self):
        plugins_page = self.create_plugins_page()
        favorites_page = self.create_favorites_page()
        self.pages = [plugins_page, favorites_page]
        self.stacked_widget = QStackedWidget()
        for i in self.pages:
            self.stacked_widget.addWidget(i)

        self.selector = QComboBox()
        self.selector.addItems(['Plugins', 'Favorites'])
        self.selector.currentIndexChanged.connect(self.stacked_widget.setCurrentIndex)
        selector_hbox = QHBoxLayout()
        selector_hbox.setContentsMargins(0, 0, 0, 0)
        selector_hbox.addWidget(self.selector)
        selector_hbox.addStretch(1)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow('View: ', selector_hbox)
        vbox = QVBoxLayout()
        vbox.addLayout(form)
        vbox.addWidget(self.stacked_widget)
        self.setLayout(vbox)

        self.view.selectRow(0)

    def create_plugins_page(self):
        self.model = PluginsModel(self.gui)
        self.proxy_model = PluginsProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.set_hide_core_plugins(self.option('hide_core_plugins', True))

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

        self.options_widget = OptionsWidget(self)
        self.plugin_details = PluginDetails(self)

        filter_edit = QLineEdit()
        def filter_view():
            regexp = QRegExp(str(filter_edit.text()), Qt.CaseInsensitive)
            self.proxy_model.set_name_filter(regexp)
        filter_edit.textChanged.connect(filter_view)
        filter_label = QLabel('&Find:')
        filter_label.setBuddy(filter_edit)
        filter_box = QHBoxLayout()
        filter_box.addWidget(filter_label)
        filter_box.addWidget(filter_edit, stretch=1)

        is_local = QLabel('Hashmal is being run locally.\n\nInstall Hashmal to use third-party plugins.\n')
        is_local.setVisible(__builtin__.use_local_modules)

        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(is_local)
        vbox.addLayout(filter_box)
        vbox.addWidget(self.view, stretch=1)
        vbox.addWidget(Separator())
        vbox.addWidget(self.plugin_details)

        hbox = QHBoxLayout()
        hbox.setContentsMargins(0,0,0,0)
        hbox.addWidget(self.options_widget)
        hbox.addLayout(vbox, stretch=1)
        w = QWidget()
        w.setLayout(hbox)
        return w

    def create_favorites_page(self):
        self.favorites_model = FavoritesModel(self.gui)
        self.favorites_view = view = QTableView()
        view.setModel(self.favorites_model)
        view.horizontalHeader().setResizeMode(0, QHeaderView.Stretch)
        view.setAlternatingRowColors(True)
        for i in [view.horizontalHeader(), view.verticalHeader()]:
            i.setHighlightSections(False)
        view.setSelectionMode(QAbstractItemView.SingleSelection)
        view.setDragEnabled(True)
        view.setAcceptDrops(True)
        view.setDropIndicatorShown(True)
        view.setContextMenuPolicy(Qt.CustomContextMenu)
        view.customContextMenuRequested.connect(self.favorites_view_context_menu)
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self.favorites_view)
        w = QWidget()
        w.setLayout(vbox)
        return w

    def favorites_view_context_menu(self, pos):
        menu = QMenu()
        indexes = self.favorites_view.selectedIndexes()
        if not len(indexes):
            return
        idx = indexes[0]
        def remove_highlighted_plugin():
            plugin_name = self.favorites_model.data(idx)
            self.favorites_model.remove_plugin(plugin_name)
        menu.addAction('Remove', remove_highlighted_plugin)

        menu.exec_(self.favorites_view.viewport().mapToGlobal(pos))

    def update_details_area(self, selected, deselected):
        """Update the plugin details area when selection changes."""
        selected = self.proxy_model.mapSelectionToSource(selected)
        try:
            index = selected.indexes()[0]
        except IndexError:
            return
        self.plugin_details.set_index(index)

