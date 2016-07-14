from PyQt4.QtGui import *
from PyQt4.QtCore import *

from txsc.script_compiler import CompilationFailedError

from hashmal_lib.core.script import Script, get_asm_context, get_txscript_context
from hashmal_lib.gui_utils import monospace_font, settings_color

known_script_formats = ('ASM', 'Hex', 'TxScript',)

class ScriptEdit(QPlainTextEdit):
    """Script editor.

    Keeps an internal Script instance that it updates
    with its text, and uses to convert formats.
    """
    def __init__(self, parent=None):
        super(ScriptEdit, self).__init__(parent)
        self.setTabStopWidth(40)
        self.needs_compilation = False
        self.current_format = 'ASM'
        self.script = Script()
        self.textChanged.connect(self.on_text_changed)
        self.setFont(monospace_font)
        # For tooltips
        self.context = []

    def on_text_changed(self):
        text = str(self.toPlainText())
        if text:
            # Get ASM context after every text change.
            if self.current_format == 'ASM':
                try:
                    self.context = get_asm_context(text)
                except Exception:
                    pass
            elif self.current_format == 'TxScript':
                try:
                    self.context = get_txscript_context(text)
                except Exception:
                    pass
        self.needs_compilation = True

    def compile_input(self):
        text = str(self.toPlainText())
        self.set_data(text, self.current_format)

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
        self.context = []
        if fmt == 'Hex' and len(text) % 2 == 0:
            script = Script(text.decode('hex'))
        elif fmt == 'ASM':
            self.context = get_asm_context(text)
            script = Script.from_asm(text)
        elif fmt == 'TxScript':
            self.context = get_txscript_context(text)
            script = Script.from_txscript(text)
        self.script = script

    def get_data(self, fmt=None):
        if self.needs_compilation:
            self.compile_input()
            self.needs_compilation = False

        if fmt is None:
            fmt = self.current_format
        if not self.script: return ''
        if fmt == 'Hex':
            return self.script.get_hex()
        elif fmt == 'ASM':
            return self.script.get_asm()
        # TODO: Inform user that TxScript is not a target language.
        elif fmt == 'TxScript':
            pass
        return ''

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


class ScriptHighlighter(QSyntaxHighlighter):
    """Highlights variables, etc. with colors from QSettings."""
    def __init__(self, gui, script_edit):
        super(ScriptHighlighter, self).__init__(script_edit.document())
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
                if self.gui.plugin_handler.get_plugin('Variables').ui.get_key(var_name):
                    fmt.setForeground(settings_color(settings, 'variables'))
            elif match_type == 'String literal':
                fmt.setForeground(settings_color(settings, 'strings'))
            elif match_type == 'Hex string':
                fmt.setForeground(settings_color(settings, 'hexstrings'))
            elif match_type == 'Comment':
                fmt.setForeground(settings_color(settings, 'comments'))
            elif match_type == 'Type name':
                fmt.setForeground(settings_color(settings, 'typenames'))
            elif match_type == 'Number':
                fmt.setForeground(settings_color(settings, 'numbers'))
            elif match_type.startswith('Keyword'):
                fmt.setForeground(settings_color(settings, 'keywords'))
            elif match_type.startswith('Conditional'):
                fmt.setForeground(settings_color(settings, 'conditionals'))
            elif match_type.startswith('Boolean operator'):
                fmt.setForeground(settings_color(settings, 'booleanoperators'))
            self.setFormat(idx, length, fmt)
        return

class ScriptCompilationLog(QPlainTextEdit):
    """Compilation log display for a script editor."""
    def __init__(self, editor):
        super(ScriptCompilationLog, self).__init__(editor)
        self.editor = editor
        self.setReadOnly(True)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)
        self.hide()

    def sizeHint(self):
        return QSize(self.editor.width(), self.editor.height() / 4)

    def target_x(self):
        """Get the x coordinate that this widget's rect should have."""
        return self.editor.height() * 0.75

    def target_height(self):
        """Get the height that this widget's rect should have."""
        return self.editor.height() * 0.25

    def set_message(self, text):
        """Set the displayed message."""
        self.clear()
        self.appendPlainText(text)
        if text:
            self.show()
        else:
            self.hide()

class ScriptLineNumberArea(QWidget):
    def __init__(self, editor):
        super(ScriptLineNumberArea, self).__init__(editor)
        self.editor = editor
        self.current_line = None

    def set_current_line(self, number):
        """Set the line number that the cursor is on."""
        self.current_line = number
        self.update()

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        return self.editor.paint_line_number_area(event)

class ScriptEditor(ScriptEdit):
    """Main script editor.

    Requires the main window as an argument so it can integrate tools.
    """
    def __init__(self, gui, parent=None):
        super(ScriptEditor, self).__init__(gui)
        self.gui = gui
        self.highlighter = ScriptHighlighter(self.gui, self)
        self.message_display = ScriptCompilationLog(self)
        self.line_number_area = ScriptLineNumberArea(self)

        vbox = QVBoxLayout()
        vbox.setContentsMargins(0,0,0,0)
        vbox.addStretch()
        vbox.addWidget(self.message_display)
        self.setLayout(vbox)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.on_update_request)
        self.cursorPositionChanged.connect(self.set_current_line)
        self.update_line_number_area_width()

    def contextMenuEvent(self, e):
        menu = self.createStandardContextMenu()
        menu.addAction('Copy Hex', self.copy_hex)
        menu.exec_(e.globalPos())

    def rehighlight(self):
        self.highlighter.rehighlight()

    def insertFromMimeData(self, source):
        """Rehighlight the script after pasting."""
        super(ScriptEditor, self).insertFromMimeData(source)
        self.rehighlight()

    @pyqtProperty(str)
    def asmText(self):
        return self.get_data(fmt='ASM')

    @asmText.setter
    def asmText(self, value):
        self.setText(str(value))

    def set_data(self, text, fmt):
        try:
            super(ScriptEditor, self).set_data(text, fmt)
        except CompilationFailedError as e:
            msg = '\n'.join([e.message, e.exception_message])
            self.message_display.set_message(msg)
        except Exception as e:
            self.message_display.set_message(str(e))
        else:
            self.message_display.set_message('')

    # http://doc.qt.io/qt-4.8/qt-widgets-codeeditor-codeeditor-cpp.html
    def line_number_area_width(self):
        digits = 1
        maximum = max(1, self.blockCount())
        while maximum >= 10:
            maximum /= 10
            digits += 1

        space = 3 + self.fontMetrics().width(QChar('9')) * digits
        return space

    def update_line_number_area_width(self):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0);

    def on_update_request(self, rect, dy):
        """Handle updateRequest for the line number and message areas."""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
            self.message_display.update(0, rect.y() + self.message_display.target_x(), self.width(), self.message_display.target_height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

    def resizeEvent(self, event):
        """Handle resizeEvent for the line number and message areas."""
        super(ScriptEditor, self).resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))
        self.message_display.setGeometry(QRect(cr.left(), cr.top() + self.message_display.target_x(), cr.width(), self.message_display.target_height()))

    # http://doc.qt.io/qt-4.8/qt-widgets-codeeditor-codeeditor-cpp.html
    def paint_line_number_area(self, event):
        """Handle paintEvent for ScriptLineNumberArea."""
        painter = QPainter(self.line_number_area)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                line_num = block_number + 1
                number = QString.number(line_num)

                painter.setPen(Qt.black)
                font = painter.font()
                # Make the current line's number bold.
                if line_num == self.line_number_area.current_line:
                    font.setWeight(QFont.Bold)
                    painter.setFont(font)
                # Offset width to keep text away from the edge.
                width = self.line_number_area.width() - 2
                painter.drawText(0, top, width, self.fontMetrics().height(),
                                 Qt.AlignRight | Qt.AlignVCenter, number)
                font.setWeight(QFont.Normal)
                painter.setFont(font)

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def set_current_line(self):
        """Set the line of text that the cursor is on.

        This causes the line number area to be repainted.
        """
        self.line_number_area.set_current_line(self.textCursor().blockNumber() + 1)
