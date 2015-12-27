import bitcoin
from bitcoin.core.script import CScript, OPCODE_NAMES
from bitcoin.core.scripteval import EvalScript

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from hashmal_lib.core import Transaction, Script
from hashmal_lib.core.stack import Stack, ScriptExecution
from hashmal_lib.gui_utils import monospace_font, floated_buttons
from hashmal_lib.items import *
from hashmal_lib.widgets import ScriptExecutionWidget
from base import BaseDock, Plugin, Category

def make_plugin():
    return Plugin(StackEval)

class StackEval(BaseDock):

    tool_name = 'Stack Evaluator'
    description = '\n'.join([
            'Stack Evaluator steps through scripts, showing you what\'s happening as it happens.',
            '<b>Please read this warning from the source of python-bitcoinlib, which Stack Evaluator uses to evaluate scripts:</b>',
            '"Be warned that there are highly likely to be consensus bugs in this code; it is unlikely to match Satoshi Bitcoin exactly. Think carefully before using this module."'
    ])
    is_large = True
    category = Category.Script

    def __init__(self, handler):
        super(StackEval, self).__init__(handler)
        self.widget().setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

    def init_data(self):
        self.tx = None
        self.inIdx = 0
        self.execution = ScriptExecution()

    def init_actions(self):
        set_as_spending = ('Set as spending transaction', self.set_spending_tx)
        self.advertised_actions[RAW_TX] = [set_as_spending]

    def reset(self):
#        self.stack_result.clear()
#        self.stack_result.setProperty('hasError', False)
#        self.style().polish(self.stack_result)
        # Clear selected step.
        cursor = QTextCursor(self.tx_script.document())
        cursor.setPosition(0)
        self.tx_script.setTextCursor(cursor)

    def create_layout(self):
        vbox = QVBoxLayout()

        tabs = QTabWidget()
        tabs.addTab(self.create_main_tab(), 'Stack')
        tabs.addTab(self.create_tx_tab(), 'Transaction')
        self.setFocusProxy(tabs)
        vbox.addWidget(tabs)

        return vbox

    def create_main_tab(self):
        self.execution_widget = ScriptExecutionWidget(self.execution)

        # Raw script input.
        self.tx_script = QPlainTextEdit()
        self.tx_script.setWhatsThis('Enter a raw script here to evaluate it.')
        # TODO
#        self.tx_script.textChanged.connect(self.reset_step_counter)
        self.tx_script.setFont(monospace_font)

        vbox = QVBoxLayout()
        vbox.addWidget(QLabel('Script:'))
        vbox.addWidget(self.tx_script)
        vbox.addWidget(self.execution_widget, stretch=1)

        self.do_button = QPushButton('Evaluate')
        self.do_button.setToolTip('Evaluate the entire script')
        self.do_button.clicked.connect(self.do_evaluate)

        btn_hbox = floated_buttons([self.do_button], left=True)
        vbox.addLayout(btn_hbox)

        w = QWidget()
        w.setLayout(vbox)
        return w

    def create_tx_tab(self):
        form = QFormLayout()

        # Spending transaction
        self.tx_edit = QPlainTextEdit()
        self.tx_edit.setFont(monospace_font)
        self.tx_edit.textChanged.connect(self.set_tx)
        # Input with scriptSig to include
        self.input_idx = QSpinBox()
        self.input_idx.setEnabled(False)
        self.input_idx.valueChanged.connect(self.set_input_index)
        self.input_idx.setToolTip('Input in the containing transaction with the relevant scriptSig.')
        in_idx_box = QHBoxLayout()
        in_idx_box.addWidget(QLabel('Input containing scriptSig:'))
        in_idx_box.addWidget(self.input_idx)
        in_idx_box.addStretch(1)


        desc = QLabel(' '.join(['You can specify the transaction that contains the script you\'re testing.',
                        'This allows you to evaluate whether an input is spent successfully.']))
        desc.setWordWrap(True)
        form.addRow(desc)
        form.addRow('Raw Transaction:', self.tx_edit)
        form.addRow('Input to spend:', self.input_idx)

        w = QWidget()
        w.setLayout(form)
        return w

    def set_spending_tx(self, txt):
        """Called from other tools to set the spending transaction."""
        if not txt:
            return
        self.needsFocus.emit()
        self.tx_edit.setPlainText(txt)

    def set_tx(self):
        """Set the spending transaction and (en|dis)able the input index box."""
        txt = str(self.tx_edit.toPlainText())
        try:
            assert txt
            self.tx = Transaction.deserialize(txt.decode('hex'))
            self.tx_edit.setToolTip(''.join(['Tx ID: ', bitcoin.core.b2lx(self.tx.GetHash())]))
            self.input_idx.setRange(0, len(self.tx.vin) - 1)
            self.input_idx.setEnabled(True)
        except Exception:
            self.tx = None
            self.tx_edit.setToolTip('')
            self.input_idx.setEnabled(False)

    def set_input_index(self, idx):
        self.inIdx = idx

    def highlight_step(self, op):
        """Highlights the relevant text in the input widget."""
        opcode, data, byte_index = op
        if data is None:
            data = ''

        pos = byte_index * 2
        length = 2 + 2 * len(data)
        cursor = QTextCursor(self.tx_script.document())
        cursor.setPosition(pos)
        cursor.setPosition(pos + length, QTextCursor.KeepAnchor)
        self.tx_script.setTextCursor(cursor)

    def do_evaluate(self):
        scr = Script(str(self.tx_script.toPlainText()).decode('hex'))
        self.execution_widget.evaluate(scr)
        return
        # TODO
        while 1:
            if not self.do_step():
                break
        cursor = QTextCursor(self.tx_script.document())
        cursor.setPosition(0)
        self.tx_script.setTextCursor(cursor)

