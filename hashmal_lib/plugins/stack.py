import bitcoin

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from hashmal_lib.core import Transaction, Script
from hashmal_lib.core.stack import Stack, ScriptExecution, ExecutionData
from hashmal_lib.gui_utils import monospace_font, floated_buttons, AmountEdit, HBox, ReadOnlyCheckBox
from hashmal_lib.widgets import ScriptExecutionWidget
from base import BaseDock, Plugin, Category, augmenter
from item_types import ItemAction

def make_plugin():
    return Plugin(StackEval)

class ScriptExecutionDelegate(QStyledItemDelegate):
    """Delegate for drawing script execution views."""
    def paint(self, painter, option, index):
        self.apply_style(option, index)
        return super(ScriptExecutionDelegate, self).paint(painter, option, index)

    def apply_style(self, option, index):
        is_root = not index.parent().isValid()
        col = index.column()

        # Log column
        if col == 3:
            # Human-readable representation of stack item
            if not is_root:
                txt = index.data(Qt.DisplayRole).toString().trimmed()

                # Variable name
                if txt.startsWith('$'):
                    color = QColor(QSettings().value('color/variables', 'darkMagenta'))
                    option.palette.setColor(QPalette.Text, color)
                # String literal
                elif txt.startsWith('"') and txt.endsWith('"'):
                    color = QColor(QSettings().value('color/strings', 'gray'))
                    option.palette.setColor(QPalette.Text, color)

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

    @augmenter
    def item_actions(self, *args):
        return ItemAction(self.tool_name, 'Transaction', 'Set as spending transaction', self.set_spending_item)

    def init_data(self):
        self.tx = None
        self.inIdx = 0
        self.execution = ScriptExecution()

    def reset(self):
        self.tx_script.clear()
        self.clear_execution()

    def clear_execution(self):
        self.execution_widget.clear()
        for i in [self.script_passed, self.script_verified]:
            i.setChecked(False)
            i.setProperty('hasSuccess', False)
            self.style().polish(i)

    def create_layout(self):
        vbox = QVBoxLayout()

        tabs = QTabWidget()
        tabs.addTab(self.create_main_tab(), 'Stack')
        tabs.addTab(self.create_tx_tab(), 'Transaction')
        tabs.addTab(self.create_block_tab(), 'Block')
        self.setFocusProxy(tabs)
        vbox.addWidget(tabs)

        return vbox

    def create_main_tab(self):
        self.execution_widget = ScriptExecutionWidget(self.execution)
        # For variable substitution
        self.execution_widget.model.plugin_handler = self.handler

        self.execution_delegate = ScriptExecutionDelegate()
        self.execution_widget.view.setItemDelegate(self.execution_delegate)

        # Raw script input.
        self.tx_script = QPlainTextEdit()
        self.tx_script.setWhatsThis('Enter a raw script here to evaluate it.')
        self.tx_script.setFont(monospace_font)
        self.tx_script.setTabChangesFocus(True)

        self.clear_button = QPushButton('Clear')
        self.clear_button.setToolTip('Clear the current script.')
        self.clear_button.clicked.connect(self.reset)
        self.do_button = QPushButton('&Evaluate')
        self.do_button.setToolTip('Evaluate the entire script.')
        self.do_button.clicked.connect(self.do_evaluate)
        btn_hbox = floated_buttons([self.clear_button, self.do_button], left=True)

        vbox = QVBoxLayout()
        vbox.addWidget(QLabel('Script:'))
        vbox.addWidget(self.tx_script)
        vbox.addLayout(btn_hbox)
        vbox.addWidget(self.execution_widget, stretch=1)

        self.next_button = QPushButton('Next')
        self.next_button.setToolTip('Step forward in script execution.')
        self.next_button.clicked.connect(self.execution_widget.select_next)
        self.prev_button = QPushButton('Previous')
        self.prev_button.setToolTip('Step backward in script execution.')
        self.prev_button.clicked.connect(self.execution_widget.select_prev)

        controls_hbox = floated_buttons([self.prev_button, self.next_button], left=True)
        vbox.addLayout(controls_hbox)

        self.script_passed = ReadOnlyCheckBox('Passed')
        self.script_passed.setToolTip('Whether the script passed')
        self.script_passed.setWhatsThis('This box is checked if the script finished with a nonzero top stack value.')
        self.script_verified = ReadOnlyCheckBox('Verified')
        self.script_verified.setToolTip('Whether the script was verified with an input script')
        self.script_verified.setWhatsThis('This box is checked if the script was verified with a transaction\'s input script.')
        pass_hbox = HBox(QLabel('Script: '), self.script_passed, self.script_verified)
        pass_hbox.addStretch(1)
        vbox.addLayout(pass_hbox)

        w = QWidget()
        w.setLayout(vbox)
        return w

    def create_tx_tab(self):
        form = QFormLayout()

        # Spending transaction
        self.tx_edit = QPlainTextEdit()
        self.tx_edit.setWhatsThis('Enter a serialized transaction here. If you have a raw transaction stored in the Variables tool, you can enter the variable name preceded by a "$", and the variable value will be substituted automatically.')
        self.tx_edit.setFont(monospace_font)
        self.tx_edit.textChanged.connect(self.set_tx)
        self.tx_edit.setTabChangesFocus(True)
        # Input with scriptSig to include
        self.input_idx = QSpinBox()
        self.input_idx.setEnabled(False)
        self.input_idx.valueChanged.connect(self.set_input_index)
        self.input_idx.setToolTip('Input in the containing transaction with the relevant scriptSig.')
        self.input_idx.setWhatsThis('Use this to specify the input you want to simulate.')
        in_idx_box = QHBoxLayout()
        in_idx_box.addWidget(QLabel('Input containing scriptSig:'))
        in_idx_box.addWidget(self.input_idx)
        in_idx_box.addStretch(1)


        desc = QLabel(' '.join(['You can specify the transaction that contains the script you\'re testing.',
                        'This allows you to evaluate whether an input spends successfully.']))
        desc.setWordWrap(True)
        form.addRow(desc)
        form.addRow('Raw Transaction:', self.tx_edit)
        form.addRow('Spending Input:', self.input_idx)

        w = QWidget()
        w.setLayout(form)
        return w

    def create_block_tab(self):
        form = QFormLayout()

        desc = QLabel(''.join(['For most purposes, this tab can be ignored.\n\n'
                        'You can simulate the block that contains the script you\'re testing. ',
                        'This allows you to use certain opcodes like CHECKLOCKTIMEVERIFY, which require ',
                        'data about the block a transaction is in.']))
        desc.setWordWrap(True)
        form.addRow(desc)

        self.block_height_edit = AmountEdit()
        self.block_height_edit.setToolTip('Height of the block your script is in')
        self.block_height_edit.setWhatsThis('Use this to simulate the height of the block that your script is in.')

        self.block_time_edit = AmountEdit()
        self.block_time_edit.setToolTip('Timestamp of the block your script is in')
        self.block_time_edit.setWhatsThis('Use this to simulate the timestamp of the block that your script is in.')

        form.addRow('Block height:', self.block_height_edit)
        form.addRow('Block time:', self.block_time_edit)

        w = QWidget()
        w.setLayout(form)
        return w

    def set_spending_item(self, item):
        """Called from other tools to set the spending transaction."""
        self.needsFocus.emit()
        self.tx_edit.setPlainText(item.raw())

    def set_tx(self):
        """Set the spending transaction and (en|dis)able the input index box."""
        txt = str(self.tx_edit.toPlainText())
        # Variable substition
        if txt.startswith('$'):
            var_value = self.handler.get_plugin('Variables').ui.get_key(txt[1:])
            if var_value:
                self.tx_edit.setPlainText(var_value)
                return
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

    def do_evaluate(self):
        self.clear_execution()
        try:
            scr = Script(str(self.tx_script.toPlainText()).decode('hex'))
        except Exception as e:
            self.status_message('Error decoding script: %s' % str(e), error=True)
            return
        exec_data = None
        if not self.block_height_edit.property('hasError').toBool() and not self.block_time_edit.property('hasError').toBool():
            exec_data = ExecutionData(self.block_height_edit.get_amount(), self.block_time_edit.get_amount())
        self.execution_widget.evaluate(scr, self.tx, self.inIdx, execution_data=exec_data)
        passed = True if self.execution_widget.execution.script_passed else False
        verified = self.execution_widget.execution.script_verified
        self.script_passed.setChecked(passed)
        self.script_verified.setChecked(verified)
        for widget in [self.script_passed, self.script_verified]:
            widget.setProperty('hasSuccess', widget.isChecked())
            self.style().polish(widget)

