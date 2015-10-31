from collections import namedtuple

import bitcoin
from bitcoin.base58 import CBase58Data

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from base import BaseDock, Plugin, Category
from hashmal_lib.core.utils import push_script
from hashmal_lib.gui_utils import monospace_font, floated_buttons

def make_plugin():
    return Plugin(ScriptGenerator)

ScriptTemplate = namedtuple('ScriptTemplate', ('name', 'text', 'variables'))
"""Template for a script.

Attributes:
    name (str): Template name.
    text (str): Template text with variable names in brackets.
    variables (dict): Variable names and types.
        Variable types can be any of the following:
            - 'address': Base58 address.

"""

class TemplateWidget(QWidget):
    def __init__(self, template):
        super(TemplateWidget, self).__init__()
        self.template = template
        # {var_name: input_widget, ...}
        self.variable_widgets = {}
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

    def create_layout(self):
        form = QFormLayout()
        scroller = QScrollArea()
        for var_name in self.template.variables.keys():
            label = QLabel(''.join([var_name.capitalize(), ':']))
            var_input = QLineEdit()
            var_input.setFont(monospace_font)
            form.addRow(label, var_input)
            self.variable_widgets[var_name] = var_input
        scroller.setLayout(form)
        while self.layout().count() > 0:
            self.layout().takeAt(0)
        self.layout().addWidget(scroller)

    def get_script(self):
        text = self.template.text
        variables = {}
        for var_name, v in self.variable_widgets.items():
            var = str(v.text())
            var_type = self.template.variables[var_name]
            # Convert input to appropriate format.
            if var_type == 'address':
                try:
                    h160 = CBase58Data(var).to_bytes()
                except Exception:
                    return 'Error: Could not decode <{}> address.'.format(var_name)
                var = ''.join(['0x', h160.encode('hex')])
            elif var_type == 'text':
#                var = ''.join(['"', var, '"'])
                var = var.encode('hex')
            variables[var_name] = var

        # Replace the <variable> occurrences with their values.
        for k, v in variables.items():
            old = ''.join(['<', k, '>'])
            text = text.replace(old, v)

        return text

    def clear_fields(self):
        for _, v in self.variable_widgets.items():
            v.clear()

    def set_template(self, template):
        self.template = template
        self.variable_widgets = {}
        self.create_layout()

# Standard output scripts by default.
known_templates = [
    # P2PKH
    ScriptTemplate('Pay-To-Public-Key-Hash Output',
        'OP_DUP OP_HASH160 <recipient> OP_EQUALVERIFY OP_CHECKSIG',
        {'recipient': 'address'}),
    # P2SH
    ScriptTemplate('Pay-To-Script-Hash Output',
        'OP_HASH160 <recipient> OP_EQUAL',
        {'recipient': 'address'}),
    # OP_RETURN
    ScriptTemplate('Null Output',
        'OP_RETURN <text>',
        {'text': 'text'})
]

class ScriptGenerator(BaseDock):

    tool_name = 'Script Generator'
    description = 'Generates scripts from templates.'
    category = Category.Script

    def __init__(self, handler):
        super(ScriptGenerator, self).__init__(handler)
        self.augment('script_templates', {'known_templates': known_templates}, callback=self.on_templates_augmented)
        self.template_combo.currentIndexChanged.emit(0)
        self.widget().setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

    def create_layout(self):
        # ComboBox for selecting which template to use.
        self.template_combo = QComboBox()
        self.template_combo.addItems([i.name for i in known_templates])
        self.setFocusProxy(self.template_combo)

        template = known_templates[0]
        self.template_widget = TemplateWidget(template)

        self.template_combo.currentIndexChanged.connect(self.change_template)

        # Generated script
        self.script_output = QPlainTextEdit()
        self.script_output.setReadOnly(True)
        self.script_output.setFont(monospace_font)

        self.generate_button = QPushButton('Generate')
        self.generate_button.clicked.connect(self.generate)

        vbox = QVBoxLayout()
        vbox.addWidget(QLabel('Select a template:'))
        vbox.addWidget(self.template_combo)
        vbox.addWidget(self.template_widget)

        vbox.addWidget(QLabel('Generated script:'))
        vbox.addWidget(self.script_output)

        btn_hbox = floated_buttons([self.generate_button])
        vbox.addLayout(btn_hbox)

        return vbox

    def change_template(self, index):
        name = str(self.template_combo.currentText())
        template = known_templates[0]
        for i in known_templates:
            if i.name == name:
                template = i
        self.template_widget.set_template(template)
        self.script_output.setPlainText(template.text)

    def generate(self):
        new_script = self.template_widget.get_script()
        self.script_output.setPlainText(new_script)
        if new_script.startswith('Error'):
            self.status_message(new_script, True)
        else:
            script_type = str(self.template_combo.currentText())
            self.status_message('Generated %s script.' % script_type)

    def on_templates_augmented(self, arg):
        self.template_combo.clear()
        self.template_combo.addItems([i.name for i in known_templates])
