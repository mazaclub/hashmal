
import os

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4 import QtCore

from core.script import Script
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
                if self.gui.dock_handler.variables.get_key(var_name):
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

