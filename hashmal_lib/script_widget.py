"""Classes for displaying a Script."""

import pyparsing
from pyparsing import Word, QuotedString, ZeroOrMore, OneOrMore, Combine

import bitcoin
from bitcoin.core.script import OPCODE_NAMES

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from gui_utils import monospace_font
from core.script import Script, transform_human


class ScriptEdit(QTextEdit):
    """Script editor.

    Keeps an internal Script instance that it updates
    with its text, and uses to convert formats.
    """
    def __init__(self, parent=None):
        super(ScriptEdit, self).__init__(parent)
        self.current_format = 'Human'
        self.script = Script()
        self.textChanged.connect(self.on_text_changed)
        self.setFont(monospace_font)
        # For tooltips
        self.context = []

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
            txt, self.context = transform_human(text)
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

    def event(self, e):
        if e.type() == QEvent.ToolTip:
            cursor = self.cursorForPosition(e.pos())
            context = self.get_tooltip(cursor.position())
            if not context:
                QToolTip.hideText()
            else:
                QToolTip.showText(e.globalPos(), context)
            return True
        return super(ScriptEdit, self).event(e)

    def get_tooltip(self, index):
        """Returns the contextual tip for the word at index."""
        if index < 0 or len(self.toPlainText()) < index:
            return ''
        for start, end, value, match_type in self.context:
            if index >= start and index < end:
                return '{} ({})'.format(value, match_type)
