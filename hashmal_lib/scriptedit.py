
import os

import pyparsing
from pyparsing import Word, QuotedString, ZeroOrMore

from PyQt4.QtGui import *
from PyQt4 import QtCore

from core.script import Script
from docks.base import BaseDock
from gui_utils import monospace_font

def transform_human(text, main_window):
    """Transform user input into something Script can read.

    Main window is needed for tool integration."""
    # these are parseActions for pyparsing.
    def str_literal_to_hex(s, loc, toks):
        for i, t in enumerate(toks):
            toks[i] = ''.join(['0x', t.encode('hex')])
        return toks
    def var_name_to_value(s, loc, toks):
        for i, t in enumerate(toks):
            val = main_window.dock_handler.variables.get_key(t.strip('$'))
            if val:
                toks[i] = val
        return toks
    # ^ parseActions for pyparsing end here.
    str_literal = QuotedString('"')
    str_literal.setParseAction(str_literal_to_hex)
    var_name = pyparsing.Combine(Word('$') + Word(pyparsing.alphas))
    var_name.setParseAction(var_name_to_value)

    s = text
    s = var_name.transformString(s)
    s = str_literal.transformString(s)
    return s

known_script_formats = ['Human', 'Hex']

class MyScriptEdit(QPlainTextEdit):
    def __init__(self, editor=None):
        super(MyScriptEdit, self).__init__(editor)
        self.editor = editor
        self.current_format = known_script_formats[0]
        self.script = Script()
        self.textChanged.connect(self.on_text_changed)
        self.setFont(monospace_font)

    def on_text_changed(self):
        txt = str(self.toPlainText())
        self.set_data(txt, self.current_format)

    def copy_hex(self):
        txt = self.get_data('Hex')
        QApplication.clipboard().setText(txt)

    def contextMenuEvent(self, e):
        menu = self.createStandardContextMenu()
        menu.addAction('Copy Hex', self.copy_hex)
        menu.exec_(e.globalPos())

    def set_format(self, fmt):
        self.current_format = fmt
        self.setPlainText(self.get_data())

    def set_data(self, text, fmt):
        script = None
        if fmt == 'Hex' and len(text) % 2 == 0:
            try:
                script = Script(text.decode('hex'))
            except Exception:
                pass
        elif fmt == 'Human':
            txt = transform_human(text, self.editor.gui)
            script = Script.from_human(txt)
        self.script = script

    def get_data(self, fmt=None):
        if fmt is None:
            fmt = self.current_format
        if not self.script: return ''
        if fmt == 'Hex':
            return self.script.get_hex()
        elif fmt == 'Human':
            return self.script.get_human()


class ScriptEditor(QWidget):
    changesSaved = QtCore.pyqtSignal(bool, name='changesSaved')
    def __init__(self, main_window):
        super(ScriptEditor, self).__init__()
        self.gui = main_window

        self.filename = ''
        self.last_saved = ''

        self.setLayout(self.create_layout())
        self.on_text_changed()

    def create_layout(self):
        vbox = QVBoxLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(known_script_formats)
        self.script_edit = MyScriptEdit(self)
        self.script_edit.textChanged.connect(self.on_text_changed)

        self.format_combo.currentIndexChanged.connect(lambda index: self.script_edit.set_format(known_script_formats[index]))

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel('Format: '))
        hbox.addWidget(self.format_combo)
        hbox.addStretch(1)
        vbox.addLayout(hbox)
        vbox.addWidget(self.script_edit)
        return vbox

    def on_text_changed(self):
        s = str(self.script_edit.toPlainText())
        if s == self.last_saved and self.filename:
            self.set_changes_saved(True)
        else:
            self.set_changes_saved(False)

    def set_changes_saved(self, saved):
        self.changesSaved.emit(saved)

    def load(self, filename):
        if os.path.exists(filename):
            self.filename = filename
            with open(self.filename,'r') as file:
                self.script_edit.setPlainText(file.read())
        else:
            self.script_edit.clear()
        self.last_saved = str(self.script_edit.toPlainText())
        self.on_text_changed()

    def save(self):
        with open(self.filename, 'w') as file:
            file.write(str(self.script_edit.toPlainText()))
        self.last_saved = str(self.script_edit.toPlainText())
        self.on_text_changed()

