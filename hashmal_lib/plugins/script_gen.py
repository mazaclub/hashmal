from collections import namedtuple
import functools

import bitcoin
from bitcoin.base58 import CBase58Data
from bitcoin.core.key import CPubKey

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from base import BaseDock, Plugin, Category, augmenter
from item_types import Item, ItemAction
from hashmal_lib.core import Script
from hashmal_lib.core.utils import is_hex, push_script, format_hex_string
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
            - 'pubkey': Public key.

"""

def format_variable_value(value, var_type):
    """Returns a 2-tuple of (is_valid, formatted_value)."""
    if var_type == 'address':
        try:
            h160 = CBase58Data(value).to_bytes()
        except Exception:
            # Check if value is a hash160.
            if is_hex(value) and len(format_hex_string(value, with_prefix=False)) == 40:
                h160 = format_hex_string(value, with_prefix=False).decode('hex')
            else:
                return False, 'Error: Could not decode address.'
        return True, '0x' + h160.encode('hex')
    elif var_type == 'pubkey':
        if not is_hex(value):
            return False, 'Error: Pubkey must be hex.'
        key_hex = format_hex_string(value, with_prefix=False)
        pub = CPubKey(key_hex.decode('hex'))
        if not pub.is_fullyvalid:
            return False, 'Error: Pubkey is invalid.'
        return True, '0x' + key_hex
    elif var_type == 'text':
        try:
            return True, '0x' + value.encode('hex')
        except Exception as e:
            return False, 'Error: ' + str(e)

    return True, value

def template_to_script(template, variables):
    text = template.text
    _vars = {}
    for k, v in variables.items():
        var_type = template.variables[k]
        is_valid, formatted_value = format_variable_value(v, var_type)
        if not is_valid:
            return formatted_value
        _vars[k] = formatted_value

    # Replace the <variable> occurrences with their values.
    for k, v in _vars.items():
        old = ''.join(['<', k, '>'])
        text = text.replace(old, v)
    return text

def is_template_script(script, template):
    """Returns whether script complies with template."""
    iterator = script.human_iter()
    text = template.text.split()
    index = 0
    used_variables = []
    while 1:
        try:
            s = next(iterator)
            txt = text[index]
            # Check variable value.
            if txt.startswith('<') and txt.endswith('>'):
                var_type = template.variables[txt[1:-1]]
                is_valid, _ = format_variable_value(s, var_type)
                if not is_valid:
                    return False
                else:
                    used_variables.append(txt[1:-1])
            elif s != txt:
                return False
            index += 1
        except StopIteration:
            break
        except Exception:
            return False
            break

    # Fail if there are not values for all expected variables.
    if not all(i in used_variables for i in template.variables.keys()):
        return False
    return True

class ScriptTemplateItem(Item):
    name = 'Script Matching Template'
    @classmethod
    def coerce_item(cls, data):
        if not isinstance(data, Script):
            try:
                data = Script.from_human(data)
            except Exception:
                return None
        for i in known_templates:
            if is_template_script(data, i):
                return cls(data, i)

    def __init__(self, value, template=''):
        super(ScriptTemplateItem, self).__init__(value)
        self.template = template
        # Populate variables dict.
        variables = {}
        iterator = self.value.human_iter()
        text = self.template.text.split()
        index = 0
        while 1:
            try:
                s = next(iterator)
                txt = text[index]
                if txt.startswith('<') and txt.endswith('>'):
                    variables[txt[1:-1]] = s
                index += 1
            except Exception:
                break
        self.variables = variables

        # Actions for copying all variables.
        for k, v in self.variables.items():
            label = ' '.join(['Copy', k])
            copy_func = functools.partial(QApplication.clipboard().setText, v)
            self.actions.append((label, copy_func))

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
        self.clear_button = QPushButton('Clear')
        self.clear_button.clicked.connect(self.clear_fields)
        for var_name in self.template.variables.keys():
            label = QLabel(''.join([var_name.capitalize(), ':']))
            var_input = QLineEdit()
            var_input.setFont(monospace_font)
            var_input.setToolTip('Value for template variable "%s"' % var_name)
            form.addRow(label, var_input)
            self.variable_widgets[var_name] = var_input
        form.addRow(floated_buttons([self.clear_button], left=True))
        scroller.setLayout(form)
        while self.layout().count() > 0:
            self.layout().takeAt(0)
        self.layout().addWidget(scroller)

    def get_script(self):
        text = self.template.text
        variables = {}
        for var_name, v in self.variable_widgets.items():
            variables.update({var_name: str(v.text())})

        return template_to_script(self.template, variables)

    def clear_fields(self):
        for _, v in self.variable_widgets.items():
            v.clear()

    def set_template(self, template):
        var_values = [(key, self.variable_widgets[key].text()) for key in self.variable_widgets.keys()]
        self.template = template
        self.variable_widgets = {}
        self.create_layout()
        # Fill in fields with names matching the old template's fields.
        for name, value in var_values:
            w = self.variable_widgets.get(name)
            if w:
                w.setText(value)

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
    # P2PK
    ScriptTemplate('Pay-To-Public-Key',
        '<recipient> OP_CHECKSIG',
        {'recipient': 'pubkey'}),
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

    @augmenter
    def item_types(self, *args):
        return ScriptTemplateItem

    @augmenter
    def item_actions(self, *args):
        return ItemAction(self.tool_name, 'Script Matching Template', 'Edit', self.set_completed_item)

    def create_layout(self):
        # ComboBox for selecting which template to use.
        self.template_combo = QComboBox()
        self.template_combo.setWhatsThis('Use this to select a template for script generation.')
        self.template_combo.addItems([i.name for i in known_templates])
        self.setFocusProxy(self.template_combo)

        template = known_templates[0]
        self.template_widget = TemplateWidget(template)

        self.template_combo.currentIndexChanged.connect(self.change_template)

        # Generated script
        self.script_output = QPlainTextEdit()
        self.script_output.setWhatsThis('The generated script is displayed here in human-readable format.')
        self.script_output.setReadOnly(True)
        self.script_output.setFont(monospace_font)
        self.script_output.setContextMenuPolicy(Qt.CustomContextMenu)
        self.script_output.customContextMenuRequested.connect(self.context_menu)

        self.generate_button = QPushButton('Generate')
        self.generate_button.clicked.connect(self.generate)
        self.generate_button.setToolTip('Generate script')
        self.generate_button.setWhatsThis('Clicking this button will generate a script based on the chosen template.')

        vbox = QVBoxLayout()
        vbox.addWidget(QLabel('Select a template:'))
        vbox.addWidget(self.template_combo)
        vbox.addWidget(self.template_widget)

        btn_hbox = floated_buttons([self.generate_button])
        vbox.addLayout(btn_hbox)

        vbox.addWidget(QLabel('Generated script:'))
        vbox.addWidget(self.script_output)

        return vbox

    def context_menu(self, pos):
        menu = self.script_output.createStandardContextMenu()
        self.handler.add_plugin_actions(self, menu, str(self.script_output.toPlainText()))

        menu.exec_(self.script_output.viewport().mapToGlobal(pos))

    def change_template(self, index):
        name = str(self.template_combo.currentText())
        template = known_templates[0]
        for i in known_templates:
            if i.name == name:
                template = i
        self.template_widget.set_template(template)
        self.script_output.setPlainText(template.text)

    def set_completed_item(self, item):
        """Deserialize a completed template."""
        idx = known_templates.index(item.template)
        self.template_combo.setCurrentIndex(idx)
        for k, v in item.variables.items():
            self.template_widget.variable_widgets[k].setText(v)
        self.generate()
        self.needsFocus.emit()

    def generate(self):
        new_script = self.template_widget.get_script()
        self.script_output.setPlainText(new_script)
        if new_script.startswith('Error'):
            self.error(new_script)
        else:
            script_type = str(self.template_combo.currentText())
            self.info('Generated %s script.' % script_type)

    def on_templates_augmented(self, arg):
        self.template_combo.clear()
        self.template_combo.addItems([i.name for i in known_templates])
