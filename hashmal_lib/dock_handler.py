from PyQt4.QtGui import *
from PyQt4 import QtCore


from pkg_resources import iter_entry_points

class DockHandler(QWidget):
    """Handles the many available dock widgets."""
    def __init__(self, parent):
        super(DockHandler, self).__init__(parent)
        self.gui = parent
        self.dock_widgets = {}

    def create_docks(self):
        self.loaded_plugins = {}
        for entry_point in iter_entry_points(group='hashmal.plugin'):
            plugin_maker = entry_point.load()
            self.loaded_plugins[entry_point.name] = plugin_maker()

#        from pprint import pprint
#        pprint(self.loaded_plugins)

        for name, plugin in self.loaded_plugins.items():
            for dock in plugin.docks:
                dock_instance = dock(self)
                self.dock_widgets[dock_instance.tool_name] = dock_instance

#        pprint(self.dock_widgets)

        for name, dock in self.dock_widgets.items():
            dock.statusMessage.connect(self.gui.show_status_message)

    def bring_to_front(self, dock):
        """Activate a dock by ensuring it is visible and raising it."""
        dock.setVisible(True)
        dock.raise_()

    def evaluate_current_script(self):
        """Evaluate the script being edited with the Stack Evaluator tool."""
        script_hex = self.gui.script_editor.get_data('Hex')
        if not script_hex: return
        self.bring_to_front(self.dock_widgets['Stack Evaluator'])
        self.dock_widgets['Stack Evaluator'].tx_script.setPlainText(script_hex)
        self.dock_widgets['Stack Evaluator'].setVisible(True)
        self.dock_widgets['Stack Evaluator'].do_evaluate()

    def set_stack_spending_tx(self, txt):
        """Set the spending transaction in the Stack Evaluator tool."""
        self.bring_to_front(self.dock_widgets['Stack Evaluator'])
        self.dock_widgets['Stack Evaluator'].set_spending_tx(txt)

    def deserialize_tx(self, tx):
        """Deserialize a raw transaction."""
        self.bring_to_front(self.dock_widgets['Transaction Deserializer'])
        self.dock_widgets['Transaction Deserializer'].raw_tx_edit.setPlainText(tx)
        self.dock_widgets['Transaction Deserializer'].deserialize()

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

