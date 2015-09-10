
import os

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4 import QtCore

from core.script import Script
from docks.base import BaseDock
from script_widget import transform_human, ScriptEdit


def transform_human_script(text, main_window):
    """Transform user input into something Script can read.

    Main window is needed for tool integration."""
    variables = main_window.dock_handler.variables.data
    return transform_human(text, variables)

class ScriptHighlighter(QSyntaxHighlighter):
    """Highlights variables, etc. with colors from QSettings."""
    def __init__(self, gui, script_edit):
        super(ScriptHighlighter, self).__init__(script_edit)
        self.gui = gui

    def highlightBlock(self, text):
        from_index = 0
        settings = self.gui.qt_settings
        for word in str(text).split():
            idx = text.indexOf(word, from_index)
            from_index = idx + len(word)
            fmt = QTextCharFormat()
            # Highlight variable names.
            if word.startswith('$'):
                if self.gui.dock_handler.variables.get_key(word[1:]):
                    fmt.setForeground( QColor(settings.value('color/variables', 'darkMagenta')) )
            self.setFormat(idx, len(word), fmt)

class MyScriptEdit(ScriptEdit):
    """Main script editor.

    Requires the main window as an argument so it can integrate tools.
    """
    def __init__(self, gui=None):
        super(MyScriptEdit, self).__init__(gui)
        self.gui = gui
        self.highlighter = ScriptHighlighter(self.gui, self.document())

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

