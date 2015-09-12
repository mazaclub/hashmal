from PyQt4.QtGui import *
from PyQt4 import QtCore

from plugins.addr_encoder import AddrEncoder
from plugins.blockchain import Blockchain
from plugins.variables import Variables
from plugins.stack import StackEval
from plugins.script_gen import ScriptGenerator
from plugins.tx_builder import TxBuilder
from plugins.tx_deserializer import TxDeserializer

class DockHandler(QWidget):
    """Handles the many available dock widgets."""
    def __init__(self, parent):
        super(DockHandler, self).__init__(parent)
        self.gui = parent
        self.dock_widgets = []

    def create_docks(self):
        self.addr_encoder = AddrEncoder(self)
        self.blockchain = Blockchain(self)
        self.variables = Variables(self)
        self.stack_eval = StackEval(self)
        self.script_generator = ScriptGenerator(self)
        self.tx_builder = TxBuilder(self)
        self.tx_deserializer = TxDeserializer(self)

        self.dock_widgets.extend([
                    self.addr_encoder,
                    self.blockchain,
                    self.variables,
                    self.stack_eval,
                    self.script_generator,
                    self.tx_builder,
                    self.tx_deserializer
                    ])
        self.dock_widgets.sort(key = lambda i: i.tool_name)
        for i in self.dock_widgets:
            i.statusMessage.connect(self.gui.show_status_message)

    def bring_to_front(self, dock):
        """Activate a dock by ensuring it is visible and raising it."""
        dock.setVisible(True)
        dock.raise_()

    def evaluate_current_script(self):
        """Evaluate the script being edited with the Stack Evaluator tool."""
        script_hex = self.gui.script_editor.get_data('Hex')
        if not script_hex: return
        self.bring_to_front(self.stack_eval)
        self.stack_eval.tx_script.setPlainText(script_hex)
        self.stack_eval.setVisible(True)
        self.stack_eval.do_evaluate()

    def set_stack_spending_tx(self, txt):
        """Set the spending transaction in the Stack Evaluator tool."""
        self.bring_to_front(self.stack_eval)
        self.stack_eval.set_spending_tx(txt)

    def deserialize_tx(self, tx):
        """Deserialize a raw transaction."""
        self.bring_to_front(self.tx_deserializer)
        self.tx_deserializer.raw_tx_edit.setPlainText(tx)
        self.tx_deserializer.deserialize()

    def do_default_layout(self):
        # Generally, small widgets go to the right.

        self.gui.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.script_generator)
        self.gui.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.variables)
        self.gui.tabifyDockWidget(self.script_generator, self.variables)
        self.variables.setVisible(False)

        self.gui.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.addr_encoder)
        self.gui.tabifyDockWidget(self.variables, self.addr_encoder)
        self.addr_encoder.setVisible(False)

        # Large widgets generally go to the bottom.

        self.gui.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.stack_eval)
        self.gui.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.tx_builder)
        self.gui.tabifyDockWidget(self.stack_eval, self.tx_builder)
        self.tx_builder.setVisible(False)

        self.gui.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.tx_deserializer)
        self.gui.tabifyDockWidget(self.tx_builder, self.tx_deserializer)
        self.tx_deserializer.setVisible(False)

        self.gui.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.blockchain)
        self.gui.tabifyDockWidget(self.tx_deserializer, self.blockchain)
        self.blockchain.setVisible(False)
