
import os

import pyparsing
from pyparsing import Word, QuotedString, ZeroOrMore

from PyQt4.QtGui import *
from PyQt4.QtCore import *
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
            val = main_window.dock_handler.variables.get_key(t[1:])
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

class ScriptHighlighter(QSyntaxHighlighter):
    def __init__(self, gui, script_edit):
        super(ScriptHighlighter, self).__init__(script_edit)
        self.gui = gui

    def highlightBlock(self, text):
        from_index = 0
        for word in str(text).split():
            idx = text.indexOf(word, from_index)
            from_index = idx + len(word)
            fmt = QTextCharFormat()
            # Highlight variable names.
            if word.startswith('$'):
                if self.gui.dock_handler.variables.get_key(word[1:]):
                    fmt.setForeground(Qt.darkMagenta)
            self.setFormat(idx, len(word), fmt)

class MyScriptEdit(QTextEdit):
    def __init__(self, gui=None):
        super(MyScriptEdit, self).__init__(gui)
        self.gui = gui
        self.current_format = 'Human'
        self.script = Script()
        self.textChanged.connect(self.on_text_changed)
        self.setFont(monospace_font)
        self.highlighter = ScriptHighlighter(self.gui, self.document())

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
            txt = transform_human(text, self.gui)
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

