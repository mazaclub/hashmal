from functools import partial
from pkg_resources import iter_entry_points
from collections import OrderedDict
import logging
import sys
import __builtin__

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from hashmal_lib.core import chainparams
from gui_utils import required_plugins, default_plugins, add_shortcuts, hashmal_entry_points
import plugins
from plugins.base import Category
from augment import Augmentations


class PluginHandler(QWidget):
    """Handles loading/unloading plugins and managing their UI widgets."""
    pluginsLoaded = pyqtSignal()
    def __init__(self, main_window):
        super(PluginHandler, self).__init__(main_window)
        self.gui = main_window
        self.config = main_window.config
        self.loaded_plugins = []
        self.config.optionChanged.connect(self.on_option_changed)
        # Whether the initial plugin loading is done.
        self.plugins_loaded = False
        # Augmentations waiting until all plugins load.
        self.waiting_augmentations = []
        # Augmentations collection.
        self.augmentations = Augmentations()
        # Menus for plugin categories.
        self.category_menus = []

    def get_plugin(self, plugin_name):
        for plugin in self.loaded_plugins:
            if plugin.name == plugin_name:
                return plugin
        return None

    def plugin_is_enabled(self, plugin_name):
        plugin = self.get_plugin(plugin_name)
        if plugin:
            return plugin.ui.is_enabled
        return False

    def create_menu(self, menu):
        """Add plugins to menu."""
        _categories = OrderedDict()
        for c in sorted([x[0] for x in Category.categories()]):
            _categories[c] = []
        for plugin in self.loaded_plugins:
            if not plugin.has_gui:
                continue
            _categories[plugin.category.name].append(plugin)

        shortcuts = add_shortcuts(_categories.keys())
        # Dict with keys that have ampersands for keyboard shortcuts.
        categories = OrderedDict()
        for k, v in zip(shortcuts, _categories.values()):
            categories[k] = v
        for i in categories.keys():
            plugins = categories[i]
            if len(plugins) == 0:
                continue
            category_menu = menu.addMenu(i)
            self.category_menus.append(category_menu)
            for plugin in sorted(plugins, key = lambda x: x.name):
                category_menu.addAction(plugin.ui.toggleViewAction())

        self.hide_unused_category_menus()

    def hide_unused_category_menus(self):
        """Hide the menus for categories that have no enabled plugins."""
        # {category_name: is_in_use, ...}
        active_categories = dict((i.name, False) for i in Category.categories())
        # Determine which categories are in use.
        for plugin in self.loaded_plugins:
            if not plugin.has_gui or not plugin.ui.is_enabled:
                continue
            active_categories[plugin.category.name] = True

        for menu in self.category_menus:
            category_name = str(menu.title()).replace('&','')
            menu.menuAction().setVisible(active_categories[category_name])

    def load_plugin(self, plugin_maker, name):
        plugin_instance = plugin_maker()

        tool_name = plugin_instance.ui_class.tool_name
        plugin_instance.name = tool_name if tool_name else name
        plugin_instance.instantiate_ui(self)
        # Only required plugins can be Core plugins.
        if plugin_instance.category == Category.Core and tool_name not in required_plugins:
            return
        # Don't load plugins with unknown category metadata.
        if plugin_instance.category not in Category.categories():
            return

        self.loaded_plugins.append(plugin_instance)

    def load_plugins(self):
        """Load plugins from entry points."""
        if __builtin__.use_local_modules:
            for i in hashmal_entry_points['hashmal.plugin']:
                plugin_name = i[:i.find(' = ')]
                module_name, plugin_maker_name = i[i.find('plugins.') + 8:].split(':')
                module = getattr(plugins, module_name)
                plugin_maker = getattr(module, plugin_maker_name)
                self.load_plugin(plugin_maker, plugin_name)
        else:
            for entry_point in iter_entry_points(group='hashmal.plugin'):
                plugin_maker = entry_point.load()
                self.load_plugin(plugin_maker, entry_point.name)

        # Fail if core plugins aren't present.
        for req in required_plugins:
            if req not in [i.name for i in self.loaded_plugins]:
                print('Required plugin "{}" not found.\nTry running setup.py.'.format(req))
                sys.exit(1)

        self.update_enabled_plugins()
        self.enable_required_plugins()
        self.plugins_loaded = True
        for i in self.waiting_augmentations:
            self.do_augment_hook(*i)
        self.pluginsLoaded.emit()

    def set_plugin_enabled(self, plugin_name, is_enabled):
        """Enable or disable a plugin and its UI."""
        plugin = self.get_plugin(plugin_name)
        if plugin is None:
            return

        # Do not disable required plugins.
        if not is_enabled and plugin_name in required_plugins:
            return

        plugin.ui.is_enabled = is_enabled
        if plugin.has_gui:
            self.set_dock_signals(plugin.ui, is_enabled)
            plugin.ui.setEnabled(is_enabled)
            if not is_enabled:
                plugin.ui.setVisible(False)

        if is_enabled:
            # Run augmentations that were disabled.
            for i in self.augmentations.get_disabled_augmentations(plugin.name):
                i.is_enabled = True
                self.do_augment(i)
        else:
            # Undo augmentations that ran.
            for i in self.augmentations.get_completed_augmentations(plugin.name):
                i.is_enabled = False
                self.undo_augment(i)
        self.assign_dock_shortcuts()
        self.hide_unused_category_menus()

    def bring_to_front(self, dock):
        """Activate a dock by ensuring it is visible and raising it."""
        if not dock.is_enabled:
            return
        dock.setVisible(True)
        dock.raise_()
        dock.setFocus()
        dock.visibilityChanged.emit(True)

    def set_dock_signals(self, dock, do_connect):
        """Connect or disconnect Qt signals to/from a dock."""
        try:
            dock.needsFocus.disconnect()
            dock.visibilityChanged.disconnect()
        except TypeError:
            pass

        if do_connect:
            dock.needsFocus.connect(partial(self.bring_to_front, dock))
            dock.visibilityChanged.connect(lambda is_visible, dock=dock: self.gui.on_dock_visibility_changed(dock, is_visible))
        dock.blockSignals(not do_connect)

    def assign_dock_shortcuts(self):
        """Assign shortcuts to visibility-toggling actions."""
        favorites = self.gui.config.get_option('favorite_plugins', [])
        for plugin in self.loaded_plugins:
            if not plugin.has_gui:
                continue
            ui = plugin.ui
            # Keyboard shortcut
            shortcut = 'Alt+' + str(1 + favorites.index(plugin.name)) if plugin.name in favorites else ''
            ui.toggleViewAction().setShortcut(shortcut)
            ui.toggleViewAction().setEnabled(ui.is_enabled)
            ui.toggleViewAction().setVisible(ui.is_enabled)

    def add_plugin_actions(self, instance, menu, data):
        """Add the relevant actions to a context menu.

        Args:
            instance: Instance of class that is requesting actions.
            menu (QMenu): Context menu to add actions to.
            data: Data to call the action(s) with.

        """

        items_plugin = self.get_plugin('Item Types')
        items = items_plugin.instantiate_item(data, allow_multiple=True)
        if not items:
            return

        menu_has_separator = False
        # Add the item's own actions.
        for item in items:
            for label, func in item.actions:
                menu.addAction(label, func)

        # Add actions for other plugins.
        for item in items:
            # Get actions for other plugins.
            actions = items_plugin.get_item_actions(item.name)
            if not actions:
                continue

            # Separator between the item's own actions and plugin actions.
            if not menu_has_separator:
                menu.addSeparator()
                menu_has_separator = True

            # Add a menu for relevant plugins in sorted order.
            for plugin_name in sorted(actions.keys()):
                if plugin_name == instance.tool_name:
                    continue
                plugin_menu = menu.addMenu(plugin_name)

                # Add the plugin's actions to its menu.
                plugin_actions = actions[plugin_name]
                for label, func in plugin_actions:
                    plugin_menu.addAction(label, partial(func, item))

    def do_augment_hook(self, class_name, hook_name, data=None, callback=None, undo_callback=None):
        """Consult plugins that can augment hook_name."""
        # Don't hook until initial plugin loading is done.
        if not self.plugins_loaded:
            augmentation = (class_name, hook_name, data, callback, undo_callback)
            if not augmentation in self.waiting_augmentations:
                self.waiting_augmentations.append(augmentation)
            return
        for plugin in self.loaded_plugins:
            if hook_name in plugin.augmenters():
                augmentation = self.augmentations.get_augmentation(plugin, hook_name, class_name, data=data, callback=callback, undo_callback=undo_callback)

                # Don't hook disabled plugins.
                if plugin.name not in self.config.get_option('enabled_plugins', default_plugins):
                    augmentation.is_enabled = False
                    continue

                # Call the augmenter method.
                self.do_augment(augmentation)

    def do_augment(self, augmentation):
        """Call the augmenter for an Augmentation."""
        self.augmentations.do_augment(augmentation)

    def undo_augment(self, augmentation):
        """Undo an Augmentation."""
        self.augmentations.undo_augment(augmentation)

    # TODO access data retrievers from Plugin, not UI
    def get_data_retrievers(self):
        """Get a list of plugins that claim to be able to retrieve blockchain data."""
        retrievers = []
        for plugin in self.loaded_plugins:
            dock = plugin.ui
            if not dock.is_enabled: continue
            if hasattr(dock, 'retrieve_blockchain_data'):
                retrievers.append(plugin)
        return retrievers

    # TODO access data retrievers from Plugin, not UI
    def download_blockchain_data(self, data_type, identifier, callback=None):
        """Download blockchain data with the pre-chosen plugin.

        Args:
            data_type (str): Type of data (e.g. 'raw_transaction').
            identifier (str): Data identifier (e.g. transaction ID).
            callback (function): If supplied, download will be asynchronous.
        """
        # Check if data is cached.
        cached_data = self.gui.download_controller.get_cache_data(identifier)
        if cached_data is not None:
            return cached_data

        plugin_name = self.config.get_option('data_retriever', 'Blockchain')
        plugin = self.get_plugin(plugin_name)
        if not plugin or not hasattr(plugin.ui, 'retrieve_blockchain_data'):
            plugin = self.get_plugin('Blockchain')
        if not data_type in plugin.ui.supported_blockchain_data_types():
            raise Exception('Plugin "%s" does not support downloading "%s" data.' % (plugin.name, data_type))
        return plugin.ui.retrieve_blockchain_data(data_type, identifier, callback)

    def evaluate_current_script(self):
        """Evaluate the script being edited with the Stack Evaluator tool."""
        script_hex = self.gui.script_editor.get_data('Hex')
        if not script_hex: return
        self.get_plugin('Stack Evaluator').ui.evaluate_script(script_hex)

    def do_default_layout(self):
        last_small = last_large = None
        for plugin in self.loaded_plugins:
            if not plugin.has_gui:
                continue
            dock = plugin.ui
            # Large docks go to the bottom.
            if dock.is_large:
                self.gui.addDockWidget(Qt.BottomDockWidgetArea, dock)
                if last_large:
                    self.gui.tabifyDockWidget(last_large, dock)
                last_large = dock
            # Small docks go to the right.
            else:
                self.gui.addDockWidget(Qt.RightDockWidgetArea, dock)
                if last_small:
                    self.gui.tabifyDockWidget(last_small, dock)
                last_small = dock
            dock.setVisible(False)

        self.get_plugin('Variables').ui.setVisible(True)
        self.get_plugin('Stack Evaluator').ui.setVisible(True)

    def hide_disabled_plugins(self):
        """Hide plugins that are disabled.

        Only needed after a layout containing disabled plugins is loaded.
        """
        for plugin in self.loaded_plugins:
            if not plugin.has_gui or plugin.ui.is_enabled:
                continue
            plugin.ui.setVisible(False)

    def enable_required_plugins(self):
        """Ensure that all required plugins are enabled."""
        enabled_plugins = self.config.get_option('enabled_plugins', default_plugins)
        needs_save = False
        for i in required_plugins:
            if i not in enabled_plugins:
                enabled_plugins.append(i)
                needs_save = True
        if needs_save:
            self.config.set_option('enabled_plugins', enabled_plugins)

    def update_enabled_plugins(self):
        """Enable or disable plugin docks according to config file."""
        enabled_plugins = self.config.get_option('enabled_plugins', default_plugins)
        for plugin in self.loaded_plugins:
            is_enabled = plugin.name in enabled_plugins
            self.set_plugin_enabled(plugin.name, is_enabled)

    def substitute_variables(self, widget):
        """Substitute variable names when entered in a widget."""
        getter, setter = 'text', 'setText'
        if isinstance(widget, QPlainTextEdit):
            getter, setter = 'toPlainText', 'setPlainText'

        def on_text_changed():
            txt = str(getattr(widget, getter)())
            if txt.startswith('$') and txt != txt.rstrip():
                var_value = self.get_plugin('Variables').ui.get_key(txt[1:].rstrip())
                if var_value:
                    # Substitute variable value.
                    getattr(widget, setter)(var_value)

        widget.textChanged.connect(on_text_changed)

    def get_tx_field_help(self, field, section=None):
        """Get the help text for a transaction field."""
        chainparams_plugin = self.get_plugin('Chainparams')
        return chainparams_plugin.get_field_help(chainparams.active_preset.name, field, section)

    def on_option_changed(self, key):
        if key == 'enabled_plugins':
            self.update_enabled_plugins()
        elif self.loaded_plugins and key == 'favorite_plugins':
            self.assign_dock_shortcuts()

    def debug(self, plugin_name, message):
        if self.plugin_is_enabled(plugin_name):
            self.gui.log_message(plugin_name, message, logging.DEBUG)

    def info(self, plugin_name, message):
        if self.plugin_is_enabled(plugin_name):
            self.gui.log_message(plugin_name, message, logging.INFO)

    def warning(self, plugin_name, message):
        if self.plugin_is_enabled(plugin_name):
            self.gui.log_message(plugin_name, message, logging.WARNING)

    def error(self, plugin_name, message):
        if self.plugin_is_enabled(plugin_name):
            self.gui.log_message(plugin_name, message, logging.ERROR)

