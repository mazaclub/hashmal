from functools import partial
from pkg_resources import iter_entry_points
from collections import OrderedDict
import sys
import __builtin__

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from gui_utils import required_plugins, default_plugins, add_shortcuts, hashmal_entry_points
import plugins
from plugins.base import Category


class Augmentation(object):
    """Model of an augmentation.

    Attributes:
        - augmenter_plugin: Plugin instance that has the augmenter.
        - hook_name: Augmentation hook name.
        - requester: Class name of object that requested augmentation.
        - data: Data passed to the augmenter.
        - callback: Function to call after augmenting.
        - has_run: Whether the augmentation has been done.
        - is_enabled: Whether the augmentation can be done.
    """
    def __init__(self, augmenter_plugin, hook_name, requester=None, data=None, callback=None):
        self.augmenter_plugin = augmenter_plugin
        self.hook_name = hook_name
        self.requester = requester
        self.data = data
        self.callback = callback

        self.has_run = False
        self.is_enabled = True

    def __str__(self):
        return '%s.%s' % (self.augmenter_plugin.name, self.hook_name)

class Augmentations(list):
    """Container for Augmentation instances."""
    def get(self, plugin_name, hook_name):
        for i in self:
            if i.augmenter_plugin.name == plugin_name and i.hook_name == hook_name:
                return i
        return None

    def for_plugin(self, plugin_name):
        """Return an Augmentations instance with augmenters in plugin_name."""
        return Augmentations(filter(lambda i: i.augmenter_plugin.name == plugin_name, self))

    def disabled(self):
        """Return an Augmentations instance with disabled augmentations."""
        return Augmentations(filter(lambda i: i.is_enabled == False, self))


class PluginHandler(QWidget):
    """Handles loading/unloading plugins and managing their dock widgets."""
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

    def get_plugin(self, plugin_name):
        for plugin in self.loaded_plugins:
            if plugin.name == plugin_name:
                return plugin
        return None

    def create_menu(self, menu):
        """Add plugins to menu."""
        _categories = OrderedDict()
        for c in sorted([x[0] for x in Category.categories()]):
            _categories[c] = []
        for plugin in self.loaded_plugins:
            _categories[plugin.dock.category[0]].append(plugin)

        shortcuts = add_shortcuts(_categories.keys())
        categories = OrderedDict()
        for k, v in zip(shortcuts, _categories.values()):
            categories[k] = v
        for i in categories.keys():
            plugins = categories[i]
            if len(plugins) == 0:
                continue
            category_menu = menu.addMenu(i)
            for plugin in sorted(plugins, key = lambda x: x.name):
                category_menu.addAction(plugin.dock.toggleViewAction())

    def load_plugin(self, plugin_maker, name):
        plugin_instance = plugin_maker()

        dock_tool_name = plugin_instance.dock_class.tool_name
        plugin_instance.name = dock_tool_name if dock_tool_name else name
        plugin_instance.instantiate_dock(self)
        # Don't load plugins with unknown category metadata.
        if plugin_instance.dock.category not in Category.categories():
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
        self.plugins_loaded = True
        for i in self.waiting_augmentations:
            self.do_augment_hook(*i)

    def set_plugin_enabled(self, plugin_name, is_enabled):
        """Enable or disable a plugin and its dock."""
        plugin = self.get_plugin(plugin_name)
        if plugin is None:
            return

        # Do not disable required plugins.
        if not is_enabled and plugin_name in required_plugins:
            return

        dock = plugin.dock
        self.set_dock_signals(dock, is_enabled)
        dock.is_enabled = is_enabled

        if not is_enabled:
            dock.setVisible(False)
        else:
            # Run augmentations that were disabled.
            for i in self.augmentations.disabled().for_plugin(plugin.name):
                if not i.has_run:
                    i.is_enabled = True
                    self.do_augment(i)
        self.assign_dock_shortcuts()

    def bring_to_front(self, dock):
        """Activate a dock by ensuring it is visible and raising it."""
        if not dock.is_enabled:
            return
        dock.setVisible(True)
        dock.raise_()
        dock.setFocus()

    def set_dock_signals(self, dock, do_connect):
        if do_connect:
            dock.needsFocus.connect(partial(self.bring_to_front, dock))
            dock.statusMessage.connect(self.gui.show_status_message)
        else:
            try:
                dock.needsFocus.disconnect()
                dock.statusMessage.disconnect()
            except TypeError:
                pass

    def assign_dock_shortcuts(self):
        """Assign shortcuts to visibility-toggling actions."""
        favorites = self.gui.config.get_option('favorite_plugins', [])
        for plugin in self.loaded_plugins:
            dock = plugin.dock
            # Keyboard shortcut
            shortcut = 'Alt+' + str(1 + favorites.index(plugin.name)) if plugin.name in favorites else ''
            dock.toggleViewAction().setShortcut(shortcut)
            dock.toggleViewAction().setEnabled(dock.is_enabled)
            dock.toggleViewAction().setVisible(dock.is_enabled)

    def add_plugin_actions(self, instance, menu, category, data):
        """Add the relevant actions to a context menu.

        Args:
            instance: Instance of class that is requesting actions.
            menu (QMenu): Context menu to add actions to.
            category (str): Category of actions (e.g. RAW_TX, defined in hashmal_lib.items).
            data: Data to call the action(s) with.

        """
        separator_added = False
        # Add the caller's actions first.
        dock_actions = instance.get_actions(category, local=True)
        if dock_actions:
            for action_name, action_receiver in dock_actions:
                menu.addAction(action_name, partial(action_receiver, data))
        # Then add other plugins' actions.
        for plugin in self.loaded_plugins:
            dock = plugin.dock
            if not dock.is_enabled:
                continue
            if dock.__class__ == instance.__class__:
                continue

            dock_actions = dock.get_actions(category)
            if dock_actions:
                # Add the separator before plugin actions.
                if not separator_added:
                    menu.addSeparator()
                    separator_added = True
                dock_menu = menu.addMenu(plugin.name)
                for action_name, action_receiver in dock_actions:
                    dock_menu.addAction(action_name, partial(action_receiver, data))

    def do_augment_hook(self, class_name, hook_name, data, callback=None):
        """Consult plugins that can augment hook_name."""
        # Don't hook until initial plugin loading is done.
        if not self.plugins_loaded:
            augmentation = (class_name, hook_name, data, callback)
            if not augmentation in self.waiting_augmentations:
                self.waiting_augmentations.append(augmentation)
            return
        for plugin in self.loaded_plugins:
            dock = plugin.dock
            if hook_name in dock.augmenters:

                # Set up augmentations.
                for i in dock.augmenters:
                    augmentation = self.augmentations.get(plugin.name, i)
                    if augmentation is None:
                        augmentation = Augmentation(plugin, i, requester=class_name, data=data, callback=callback)
                        self.augmentations.append(augmentation)

                augmentation = self.augmentations.get(plugin.name, hook_name)
                if augmentation is None:
                    continue

                # Don't hook disabled plugins.
                if plugin.name not in self.config.get_option('enabled_plugins', default_plugins):
                    augmentation.is_enabled = False
                    continue

                # Call the augmenter method.
                self.do_augment(augmentation)

    def do_augment(self, augmentation):
        """Call the augmenter for an Augmentation."""
        # Don't run augmentations that have been run, aren't enabled,
        # or are from the same class that wants augmenting.
        if (
            augmentation.has_run or
            not augmentation.is_enabled or
            augmentation.requester == augmentation.augmenter_plugin.dock.__class__.__name__
        ): return
        dock = augmentation.augmenter_plugin.dock
        func = getattr(dock, augmentation.hook_name)
        data = func(augmentation.data)
        if augmentation.callback:
            augmentation.callback(data)
        augmentation.has_run = True

    def get_data_retrievers(self):
        """Get a list of plugins that claim to be able to retrieve blockchain data."""
        retrievers = []
        for plugin in self.loaded_plugins:
            dock = plugin.dock
            if not dock.is_enabled: continue
            if hasattr(dock, 'retrieve_blockchain_data'):
                retrievers.append(plugin)
        return retrievers

    def download_blockchain_data(self, data_type, identifier):
        """Download blockchain data with the pre-chosen plugin.

        Args:
            data_type (str): Type of data (e.g. RAW_TX, defined in hashmal_lib.items).
            identifier (str): Data identifier (e.g. transaction ID).
        """
        plugin_name = self.config.get_option('data_retriever', 'Blockchain')
        plugin = self.get_plugin(plugin_name)
        if not plugin or not hasattr(plugin.dock, 'retrieve_blockchain_data'):
            plugin = self.get_plugin('Blockchain')
        if not data_type in plugin.dock.supported_blockchain_data_types():
            raise Exception('Plugin "%s" does not support downloading "%s" data.' % (plugin.name, data_type))
        return plugin.dock.retrieve_blockchain_data(data_type, identifier)

    def evaluate_current_script(self):
        """Evaluate the script being edited with the Stack Evaluator tool."""
        script_hex = self.gui.script_editor.get_data('Hex')
        if not script_hex: return
        self.bring_to_front(self.get_plugin('Stack Evaluator').dock)
        self.get_plugin('Stack Evaluator').dock.tx_script.setPlainText(script_hex)
        self.get_plugin('Stack Evaluator').dock.do_evaluate()

    def do_default_layout(self):
        last_small = last_large = None
        for plugin in self.loaded_plugins:
            dock = plugin.dock
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

        self.get_plugin('Variables').dock.setVisible(True)
        self.get_plugin('Stack Evaluator').dock.setVisible(True)

    def update_enabled_plugins(self):
        """Enable or disable plugin docks according to config file."""
        enabled_plugins = self.config.get_option('enabled_plugins', default_plugins)
        for plugin in self.loaded_plugins:
            is_enabled = plugin.name in enabled_plugins
            self.set_plugin_enabled(plugin.name, is_enabled)

    def on_option_changed(self, key):
        if key == 'enabled_plugins':
            self.update_enabled_plugins()
        elif self.loaded_plugins and key == 'favorite_plugins':
            self.assign_dock_shortcuts()

