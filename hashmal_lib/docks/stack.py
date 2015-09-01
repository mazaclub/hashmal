import bitcoin
from bitcoin.core import CMutableTransaction
from bitcoin.core.script import CScript, OPCODE_NAMES
from bitcoin.core.scripteval import EvalScript

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from hashmal_lib.core.stack import Stack
from hashmal_lib.gui_utils import monospace_font
from base import BaseDock


class StackEval(BaseDock):

    def __init__(self, handler):
        super(StackEval, self).__init__(handler)
        self.widget().setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

    def init_metadata(self):
        self.tool_name = 'Stack View'
        self.description = '\n'.join([
                'Stack View steps through scripts, showing you what\'s happening as it happens.',
                '<b>Please read this warning from the source of python-bitcoinlib, which Stack View uses to evaluate scripts:</b>',
                '"Be warned that there are highly likely to be consensus bugs in this code; it is unlikely to match Satoshi Bitcoin exactly. Think carefully before using this module."'
        ])

    def init_data(self):
        self.stack = Stack()
        self.step_counter = -1

    def reset_step_counter(self):
        self.step_counter = -1

    def create_layout(self):
        vbox = QVBoxLayout()
        self.tx_script = QPlainTextEdit()
        self.tx_script.textChanged.connect(self.reset_step_counter)
        self.tx_script.setFont(monospace_font)
        self.stack_result = QLineEdit()
        self.stack_result.setReadOnly(True)

        self.stack_view = QListWidget()
        self.stack_log = QTreeWidget()
        self.stack_log.setColumnCount(3)
        self.stack_log.setHeaderLabels(['Step', 'Op', 'Result'])
        self.stack_log.header().setDefaultSectionSize(50)
        self.stack_log.header().setResizeMode(0, QHeaderView.Fixed)
        self.stack_log.header().setResizeMode(1, QHeaderView.ResizeToContents)
        self.stack_log.header().setResizeMode(2, QHeaderView.Stretch)
        self.stack_log.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)

        def reset():
            self.reset_step_counter()
            self.stack_view.clear()
            self.stack_log.clear()
            self.stack_result.clear()
            self.stack_result.setProperty('hasError', False)
            self.style().polish(self.stack_result)

        self.step_button = QPushButton('Step')
        self.step_button.setToolTip('Evaluate the next operation')
        self.step_button.clicked.connect(self.do_step)
        self.reset_button = QPushButton('Reset')
        self.reset_button.setToolTip('Reset the current evaluation')
        self.reset_button.clicked.connect(reset)
        self.do_button = QPushButton('Evaluate')
        self.do_button.setToolTip('Evaluate the entire script')
        self.do_button.clicked.connect(self.do_evaluate)

        vbox.addWidget(QLabel('Script:'))
        vbox.addWidget(self.tx_script)
        vbox.addWidget(QLabel('Stack:'))
        vbox.addWidget(self.stack_view)
        vbox.addWidget(QLabel('Stack log:'))
        vbox.addWidget(self.stack_log, stretch=1)
        vbox.addWidget(self.stack_result)

        btn_hbox = QHBoxLayout()
        btn_hbox.addWidget(self.step_button)
        btn_hbox.addWidget(self.reset_button)
        btn_hbox.addWidget(self.do_button)
        btn_hbox.addStretch(1)
        vbox.addLayout(btn_hbox)
        return vbox

    def do_evaluate(self):
        while 1:
            if not self.do_step():
                break

    def do_step(self):
        """Returns whether another step can be done."""
        if self.step_counter == -1:
            txt = str(self.tx_script.toPlainText())
            scr = CScript(txt.decode('hex'))
            # So we can show the opcode in the stack log
            self.script_ops = [i[0] for i in scr.raw_iter()]
            self.stack.set_script(scr)
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

            op_name = OPCODE_NAMES.get(self.script_ops[self.step_counter - 1], 'PUSHDATA')
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
