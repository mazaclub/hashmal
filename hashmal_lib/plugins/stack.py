import bitcoin
from bitcoin.core.script import CScript, OPCODE_NAMES
from bitcoin.core.scripteval import EvalScript

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from hashmal_lib.core import Transaction
from hashmal_lib.core.stack import Stack
from hashmal_lib.gui_utils import monospace_font, floated_buttons
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
        self.stack = Stack()
        self.step_counter = -1
        self.tx = None
        self.inIdx = 0

    def init_actions(self):
        set_as_spending = ('Set as spending transaction', self.set_spending_tx)
        self.advertised_actions['raw_transaction'] = [set_as_spending]

    def reset_step_counter(self):
        self.step_counter = -1

    def reset(self):
        self.reset_step_counter()
        self.stack_view.clear()
        self.stack_log.clear()
        self.stack_result.clear()
        self.stack_result.setProperty('hasError', False)
        self.style().polish(self.stack_result)
        # Clear selected step.
        cursor = QTextCursor(self.tx_script.document())
        cursor.setPosition(0)
        self.tx_script.setTextCursor(cursor)

    def create_layout(self):
        form = QFormLayout()

        tabs = QTabWidget()
        tabs.addTab(self.create_main_tab(), 'Stack')
        tabs.addTab(self.create_tx_tab(), 'Transaction')
        self.setFocusProxy(tabs)
        form.addRow(tabs)

        return form

    def create_main_tab(self):
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapAllRows)

        # Raw script input.
        self.tx_script = QPlainTextEdit()
        self.tx_script.textChanged.connect(self.reset_step_counter)
        self.tx_script.setFont(monospace_font)
        # Result of the latest script op.
        self.stack_result = QLineEdit()
        self.stack_result.setReadOnly(True)

        # Visualization of stack.
        self.stack_view = QListWidget()
        # Log of script ops.
        self.stack_log = QTreeWidget()
        self.stack_log.setColumnCount(3)
        self.stack_log.setHeaderLabels(['Step', 'Op', 'Result'])
        self.stack_log.header().setDefaultSectionSize(50)
        self.stack_log.header().setResizeMode(0, QHeaderView.Fixed)
        self.stack_log.header().setResizeMode(1, QHeaderView.ResizeToContents)
        self.stack_log.header().setResizeMode(2, QHeaderView.Stretch)
        self.stack_log.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        # Controls
        self.step_button = QPushButton('Step')
        self.step_button.setToolTip('Evaluate the next operation')
        self.step_button.clicked.connect(self.do_step)
        self.reset_button = QPushButton('Reset')
        self.reset_button.setToolTip('Reset the current evaluation')
        self.reset_button.clicked.connect(self.reset)
        self.do_button = QPushButton('Evaluate')
        self.do_button.setToolTip('Evaluate the entire script')
        self.do_button.clicked.connect(self.do_evaluate)


        form.addRow('Script:', self.tx_script)
        form.addRow('Stack:', self.stack_view)
        form.addRow('Stack log:', self.stack_log)
        form.addRow(self.stack_result)

        btn_hbox = floated_buttons([self.step_button, self.reset_button, self.do_button], left=True)
        form.addRow(btn_hbox)

        w = QWidget()
        w.setLayout(form)
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
        while 1:
            if not self.do_step():
                break
        cursor = QTextCursor(self.tx_script.document())
        cursor.setPosition(0)
        self.tx_script.setTextCursor(cursor)

    def do_step(self):
        """Returns whether another step can be done."""
        if self.step_counter == -1:
            txt = str(self.tx_script.toPlainText())
            scr = CScript(txt.decode('hex'))
            # So we can show the opcode in the stack log
            self.script_ops = [i for i in scr.raw_iter()]
            self.stack.set_script(scr, self.tx, self.inIdx)
            self.stack_iterator = self.stack.step()
            self.stack_log.clear()
            self.step_counter += 1

        step_again = False
        try:
            self.step_counter += 1
            stack_state, action = self.stack_iterator.next()
            new_stack = [i.encode('hex') for i in reversed(stack_state)]
            self.stack_view.clear()
            self.stack_view.addItems(new_stack)

            op_name = OPCODE_NAMES.get(self.script_ops[self.step_counter - 1][0], 'PUSHDATA')
            self.highlight_step(self.script_ops[self.step_counter - 1])
            item = QTreeWidgetItem(map(lambda i: str(i), [self.step_counter, op_name, action]))
            item.setTextAlignment(0, Qt.AlignLeft)
            item.setToolTip(1, 'Step {} operation'.format(self.step_counter))
            item.setToolTip(2, 'Result of step {}'.format(self.step_counter))
            self.stack_log.insertTopLevelItem(0, item)
            self.stack_result.setText(action)
            self.stack_result.setProperty('hasError', False)
            step_again = True
        except StopIteration:
            self.stack_result.setText('End of script.')
        except Exception as e:
            self.stack_result.setText(str(e))
            self.stack_result.setProperty('hasError', True)
        finally:
            self.style().polish(self.stack_result)

        return step_again
