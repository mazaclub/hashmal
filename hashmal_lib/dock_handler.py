from functools import partial

from PyQt4.QtGui import *
from PyQt4 import QtCore


from pkg_resources import iter_entry_points

class DockHandler(QWidget):
    """Loads plugins and handles the many available dock widgets."""
    def __init__(self, parent):
        super(DockHandler, self).__init__(parent)
        self.gui = parent
        self.dock_widgets = {}

    def create_docks(self):
        self.loaded_plugins = {}
        # Load plugins.
        for entry_point in iter_entry_points(group='hashmal.plugin'):
            plugin_maker = entry_point.load()
            self.loaded_plugins[entry_point.name] = plugin_maker()

        # Instantiate dock widgets from plugins.
        for name, plugin in self.loaded_plugins.items():
            for dock in plugin.docks:
                dock_instance = dock(self)
                self.dock_widgets[dock_instance.tool_name] = dock_instance

        for name, dock in self.dock_widgets.items():
            dock.needsFocus.connect(partial(self.bring_to_front, dock))
            dock.statusMessage.connect(self.gui.show_status_message)

    def bring_to_front(self, dock):
        """Activate a dock by ensuring it is visible and raising it."""
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
        for name, dock in self.dock_widgets.items():
            if dock.__class__ == instance.__class__:
                continue

            dock_actions = dock.get_actions(category)
            if dock_actions:
                dock_menu = menu.addMenu(name)
                for action_name, action_receiver in dock_actions:
                    dock_menu.addAction(action_name, partial(action_receiver, data))

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

