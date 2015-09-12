import bitcoin
from bitcoin.base58 import CBase58Data

from PyQt4.QtGui import *

from base import BaseDock, Plugin
from hashmal_lib.core.utils import push_script
from hashmal_lib.gui_utils import monospace_font, floated_buttons

def make_plugin():
    return Plugin([ScriptGenerator])

class ScriptTemplate(QWidget):
    """Template for a script.

    Attributes:
        name (str): Template name.
        text (str): Template text with variable names in brackets.
        variables (dict): Variable names and types.
            Variable types can be any of the following:
                - 'address': Base58 address.

    """
    def __init__(self, name, text, variables):
        super(ScriptTemplate, self).__init__()
        self.name = name
        self.text = text
        # {var_name: var_type, ...}
        self.variables = variables
        # {var_name: input_widget, ...}
        self.variable_widgets = {}
        self.create_layout()

    def create_layout(self):
        form = QFormLayout()
        for var_name in self.variables.keys():
            label = QLabel(''.join([var_name.capitalize(), ':']))
            var_input = QLineEdit()
            var_input.setFont(monospace_font)
            form.addRow(label, var_input)
            self.variable_widgets[var_name] = var_input
        self.setLayout(form)

    def get_script(self):
        text = self.text
        variables = {}
        for var_name, v in self.variable_widgets.items():
            var = str(v.text())
            var_type = self.variables[var_name]
            # Convert input to appropriate format.
            if var_type == 'address':
                try:
                    h160 = CBase58Data(var).to_bytes()
                except Exception:
                    return 'Error: Could not decode <{}> address.'.format(var_name)
                var = ''.join(['0x', h160.encode('hex')])
            elif var_type == 'text':
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

class ScriptGenerator(BaseDock):
    def __init__(self, handler):
        super(ScriptGenerator, self).__init__(handler)
        self.template_combo.currentIndexChanged.emit(0)
        self.widget().setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

    def init_metadata(self):
        self.tool_name = 'Script Generator'
        self.description = 'Generates scripts from templates.'

    def init_data(self):
        # This list contains both ScriptTemplate instances and strings.
        # The strings are treated as separators in the selection ComboBox.
        self.templates = []
        # {name: ScriptTemplate, ...}
        self.template_widgets = {}
        # Output scripts
        output_templates = [
                # P2PKH
                ('Pay-To-Public-Key-Hash Output',
                'OP_DUP OP_HASH160 <recipient> OP_EQUALVERIFY OP_CHECKSIG',
                {'recipient': 'address'}),
                # P2SH
                ('Pay-To-Script-Hash Output',
                'OP_HASH160 <recipient> OP_EQUAL',
                {'recipient': 'address'}),
                # OP_RETURN
                ('Null Output',
                'OP_RETURN <text>',
                {'text': 'text'})
        ]
        # Organize by template type.
        templates = [output_templates]
        for template_type in templates:
            for name, text, variables in template_type:
                w = ScriptTemplate(name, text, variables)
                self.templates.append(w)
                self.template_widgets[name] = w
            # Add a separator. (We use '-' but the actual character doesn't matter.)
            self.templates.append('-')

    def create_layout(self):
        # ComboBox for selecting which template to use.
        self.template_combo = QComboBox()
        for i in self.templates:
            if isinstance(i, str):
                self.template_combo.insertSeparator(self.template_combo.count())
            else:
                self.template_combo.addItem(i.name)

        # StackedWidget showing input widgets for the currently selected template.
        self.template_stack = QStackedWidget()
        for i in self.templates:
            if isinstance(i, str):
                # separator
                continue
            self.template_stack.addWidget(i)

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
        vbox.addWidget(self.template_stack)

        vbox.addWidget(QLabel('Generated script:'))
        vbox.addWidget(self.script_output)

        btn_hbox = floated_buttons([self.generate_button])
        vbox.addLayout(btn_hbox)

        return vbox

    def change_template(self, index):
        new_template = str(self.template_combo.currentText())
        self.template_stack.currentWidget().clear_fields()
        self.template_stack.setCurrentWidget(self.template_widgets[new_template])
        self.script_output.setPlainText(self.template_stack.currentWidget().text)

    def generate(self):
        w = self.template_stack.currentWidget()
        new_script = w.get_script()
        self.script_output.setPlainText(new_script)
        if new_script.startswith('Error'):
            self.status_message(new_script, True)
        else:
            script_type = str(self.template_combo.currentText())
            self.status_message('Generated %s script.' % script_type)
