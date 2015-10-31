
import os

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4 import QtCore

from hashmal_lib.core.script import Script, transform_human
from hashmal_lib.gui_utils import monospace_font

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


def transform_human_script(text, main_window):
    """Transform user input into something Script can read.

    Main window is needed for tool integration."""
    variables = main_window.plugin_handler.get_plugin('Variables').dock.data
    return transform_human(text, variables)

class ScriptHighlighter(QSyntaxHighlighter):
    """Highlights variables, etc. with colors from QSettings."""
    def __init__(self, gui, script_edit):
        super(ScriptHighlighter, self).__init__(script_edit)
        self.gui = gui
        self.editor = script_edit

    def highlightBlock(self, text):
        """Use the ScriptEdit's context attribute to highlight."""
        if len(self.editor.context) == 0:
            return

        settings = self.gui.qt_settings
        offset = self.currentBlock().position()
        for start, end, value, match_type in self.editor.context:
            start = start - offset
            end = end - offset
            idx = start
            length = end - start
            fmt = QTextCharFormat()
            if match_type == 'Variable':
                length += 1 # account for '$' prefix
                var_name = str(text[idx+1: idx+length]).strip()
                if self.gui.plugin_handler.get_plugin('Variables').dock.get_key(var_name):
                    fmt.setForeground( QColor(settings.value('color/variables', 'darkMagenta')) )
            elif match_type == 'String literal':
                fmt.setForeground( QColor(settings.value('color/strings', 'gray')) )
            self.setFormat(idx, length, fmt)
        return

class MyScriptEdit(ScriptEdit):
    """Main script editor.

    Requires the main window as an argument so it can integrate tools.
    """
    def __init__(self, gui=None):
        super(MyScriptEdit, self).__init__(gui)
        self.gui = gui
        self.highlighter = ScriptHighlighter(self.gui, self)

    def contextMenuEvent(self, e):
        menu = self.createStandardContextMenu()
        menu.addAction('Copy Hex', self.copy_hex)
        menu.exec_(e.globalPos())

    def set_data(self, text, fmt):
        script = None
        if fmt == 'Hex' and len(text) % 2 == 0:
            try:
                script = Script(text.decode('hex'))
            except Exception:
                pass
        elif fmt == 'Human':
            txt, self.context = transform_human_script(text, self.gui)
            script = Script.from_human(txt)
        self.script = script

