from functools import partial

from PyQt4.QtGui import *
from PyQt4 import QtCore


from pkg_resources import iter_entry_points

class DockHandler(QWidget):
    """Handles the many available dock widgets."""
    def __init__(self, main_window, plugin_handler):
        super(DockHandler, self).__init__(main_window)
        self.gui = main_window
        self.plugin_handler = plugin_handler
        self.dock_widgets = {}
        self.gui.config.optionChanged.connect(self.on_option_changed)

    def create_docks(self):
        """Instantiate dock widgets from plugins."""
        for plugin in self.plugin_handler.loaded_plugins:
            plugin.instantiate_dock(self)
            self.dock_widgets.update({ plugin.dock.tool_name: plugin.dock })

    def set_dock_signals(self, dock, do_connect):
        if do_connect:
            dock.needsFocus.connect(partial(self.bring_to_front, dock))
            dock.statusMessage.connect(self.gui.show_status_message)
        else:
            dock.needsFocus.disconnect()
            dock.statusMessage.disconnect()

    def set_dock_enabled(self, tool_name, is_enabled):
        """Enable or disable a dock."""
        dock = self.dock_widgets.get(tool_name)
        if not dock:
            return

        self.set_dock_signals(dock, is_enabled)
        dock.is_enabled = is_enabled
        self.assign_dock_shortcuts()

    def assign_dock_shortcuts(self):
        fav_tools = self.gui.config.get_option('favorite_tools', [])
        for tool_name, dock in self.dock_widgets.items():
            # Keyboard shortcut
            shortcut = 'Alt+' + str(1 + fav_tools.index(tool_name)) if tool_name in fav_tools else ''
            dock.toggleViewAction().setShortcut(shortcut)
            dock.toggleViewAction().setEnabled(dock.is_enabled)

    def bring_to_front(self, dock):
        """Activate a dock by ensuring it is visible and raising it."""
        if not dock.is_enabled:
            return
        dock.setVisible(True)
        dock.raise_()

    def add_plugin_actions(self, instance, menu, category, data):
        """Add the relevant actions to a context menu.

        Args:
            instance: Instance of class that is requesting actions.
            menu (QMenu): Context menu to add actions to.
            category (str): Category of actions (e.g. raw_transaction).
            data: Data to call the action(s) with.

        """
        separator_added = False
        for name, dock in self.dock_widgets.items():
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
                dock_menu = menu.addMenu(name)
                for action_name, action_receiver in dock_actions:
                    dock_menu.addAction(action_name, partial(action_receiver, data))

    def do_augment_hook(self, class_name, hook_name, *args):
        for dock in self.dock_widgets.values():
            if class_name == dock.__class__.__name__:
                continue
            cls = dock.__class__
            if cls.augmenters is None:
                cls.augmenters = []
            if hook_name in cls.augmenters:
                # Call the augmenter method.
                method_name = cls.augmenters.index(hook_name)
                func = getattr(dock, method_name)
                return func(*args)

    def get_dock(self, dock_name, raise_if_none=False):
        dock = self.dock_widgets.get(dock_name)
        if dock and not dock.is_enabled:
            dock = None

        if dock is None and raise_if_none:
            raise Exception('Unknown dock "{}".'.format(dock_name))
        return dock

    def evaluate_current_script(self):
        """Evaluate the script being edited with the Stack Evaluator tool."""
        script_hex = self.gui.script_editor.get_data('Hex')
        if not script_hex: return
        self.bring_to_front(self.dock_widgets['Stack Evaluator'])
        self.dock_widgets['Stack Evaluator'].tx_script.setPlainText(script_hex)
        self.dock_widgets['Stack Evaluator'].setVisible(True)
        self.dock_widgets['Stack Evaluator'].do_evaluate()

    def do_default_layout(self):

        last_small = last_large = None
        for name, dock in self.dock_widgets.items():
            # Large docks go to the bottom.
            if dock.is_large:
                self.gui.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dock)
                if last_large:
                    self.gui.tabifyDockWidget(last_large, dock)
                last_large = dock
            # Small docks go to the right.
            else:
                self.gui.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
                if last_small:
                    self.gui.tabifyDockWidget(last_small, dock)
                last_small = dock
            dock.setVisible(False)

        self.dock_widgets['Variables'].setVisible(True)
        self.dock_widgets['Stack Evaluator'].setVisible(True)

    def on_option_changed(self, key):
        if self.dock_widgets and key == 'favorite_tools':
            self.assign_dock_shortcuts()
