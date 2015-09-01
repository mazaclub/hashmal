from PyQt4.QtGui import *
from PyQt4 import QtCore

from docks.addr_encoder import AddrEncoder
from docks.variables import Variables
from docks.stack import StackEval
from docks.script_gen import ScriptGenerator

class DockHandler(QWidget):
    """Handles the many available dock widgets."""
    def __init__(self, parent):
        super(DockHandler, self).__init__(parent)
        self.gui = parent
        self.dock_widgets = []

    def create_docks(self):
        self.addr_encoder = AddrEncoder(self)
        self.variables = Variables(self)
        self.stack_eval = StackEval(self)
        self.script_generator = ScriptGenerator(self)

        self.dock_widgets.extend([
                    self.addr_encoder,
                    self.variables,
                    self.stack_eval,
                    self.script_generator])
        self.dock_widgets.sort(key = lambda i: i.tool_name)
        for i in self.dock_widgets:
            i.statusMessage.connect(self.gui.show_status_message)

    def evaluate_current_script(self):
        script_hex = self.gui.script_editor.script_edit.get_data('Hex')
        if not script_hex: return
        self.stack_eval.tx_script.setPlainText(script_hex)
        self.stack_eval.setVisible(True)
        self.stack_eval.do_evaluate()

    def do_default_layout(self):
        self.gui.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.variables)
        self.variables.setVisible(False)
        self.gui.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.stack_eval)

        self.gui.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.addr_encoder)
        self.addr_encoder.setVisible(False)
        self.gui.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.script_generator)
