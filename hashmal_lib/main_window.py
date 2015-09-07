
import os
import time

from PyQt4.QtGui import *
from PyQt4 import QtCore

from config import Config
from dock_handler import DockHandler
from settings_dialog import SettingsDialog
from scriptedit import MyScriptEdit
from help_widgets import QuickTips, ToolInfo
from gui_utils import script_file_filter, hashmal_style, floated_buttons, monospace_font

known_script_formats = ['Human', 'Hex']

class HashmalMain(QMainWindow):

    def __init__(self, app):
        super(HashmalMain, self).__init__()
        self.app = app
        self.app.setStyleSheet(hashmal_style)
        self.changes_saved = True

        self.config = Config()

        QtCore.QCoreApplication.setOrganizationName('mazaclub')
        QtCore.QCoreApplication.setApplicationName('hashmal')
        self.qt_settings = QtCore.QSettings()

        self.setDockNestingEnabled(True)
        self.dock_handler = DockHandler(self)
        self.dock_handler.create_docks()
        self.dock_handler.do_default_layout()

        # Filename of script being edited.
        self.filename = ''
        # The last text that we saved.
        self.last_saved = ''
        self.create_script_editor()
        # Set up script editor font.
        script_font = self.qt_settings.value('editor/font', defaultValue=QtCore.QVariant('default')).toString()
        if script_font == 'default':
            font = monospace_font
        else:
            font = QFont()
            font.fromString(script_font)
        self.script_editor.setFont(font)

        self.create_menubar()
        self.create_default_script()
        self.statusBar().setVisible(True)
        self.statusBar().messageChanged.connect(self.change_status_bar)

        self.restoreState(self.qt_settings.value('toolLayout/default').toByteArray())

        if self.qt_settings.value('quickTipsOnStart', defaultValue=QtCore.QVariant(True)).toBool():
            QtCore.QTimer.singleShot(500, self.do_quick_tips)

    def sizeHint(self):
        return QtCore.QSize(800, 500)

    def create_default_script(self):
        filename = os.path.expanduser('Untitled.coinscript')
        self.load_script(filename)

    def create_menubar(self):
        menubar = QMenuBar()

        file_menu = menubar.addMenu('&File')
        file_menu.addAction('&New', self.new_script).setShortcut(QKeySequence.New)
        file_menu.addAction('Save As...', self.save_script_as).setShortcut(QKeySequence.SaveAs)
        file_menu.addAction('&Open', self.open_script).setShortcut(QKeySequence.Open)
        file_menu.addAction('&Save', self.save_script).setShortcut(QKeySequence.Save)
        file_menu.addAction('&Quit', self.close)

        # Script actions
        script_menu = menubar.addMenu('&Script')
        script_menu.addAction('&Evaluate', self.dock_handler.evaluate_current_script)
        script_menu.addAction('&Copy Hex', self.script_editor.copy_hex)

        # Settings and tool toggling
        tools_menu = menubar.addMenu('&Tools')
        tools_menu.addAction('&Settings', lambda: SettingsDialog(self).exec_())
        tools_menu.addSeparator()
        for i in sorted(self.dock_handler.dock_widgets):
            tools_menu.addAction(i.toggleViewAction())

        help_menu = menubar.addMenu('&Help')
        help_menu.addAction('&About', self.do_about)
        help_menu.addAction('&Tool Info', lambda: ToolInfo(self).exec_())
        help_menu.addAction('&Quick Tips', self.do_quick_tips)

        self.setMenuBar(menubar)

    def show_status_message(self, msg, error=False):
        self.statusBar().showMessage(msg, 3000)
        if error:
            self.statusBar().setProperty('hasError', True)
        else:
            self.statusBar().setProperty('hasError', False)
        self.style().polish(self.statusBar())

    def change_status_bar(self, new_msg):
        # Unset hasError if an error is removed.
        if not new_msg and self.statusBar().property('hasError'):
            self.statusBar().setProperty('hasError', False)
        self.style().polish(self.statusBar())

    def on_text_changed(self):
        s = str(self.script_editor.toPlainText())
        saved = False
        if s == self.last_saved and self.filename:
            saved = True
        self.on_changes_saved(saved)

    def on_changes_saved(self, saved):
        title = ''.join(['Hashmal - ', self.filename])
        if not saved:
            title = ''.join([title, ' *'])
        self.setWindowTitle(title)
        self.changes_saved = saved

    def closeEvent(self, event):
        # Save layout if configured to.
        if self.qt_settings.value('saveLayoutOnExit', defaultValue=QtCore.QVariant(False)).toBool():
            self.qt_settings.setValue('toolLayout/default', self.saveState())

        if self.changes_saved or (not self.filename and not str(self.script_editor.toPlainText())):
            event.accept()
            return
        result = QMessageBox.question(self, 'Save Changes',
                    'Do you want to save your changes to ' + self.filename + ' before closing?',
                    QMessageBox.Yes | QMessageBox.No)
        if result == QMessageBox.Yes:
            self.save_script()
        event.accept()

    def new_script(self, filename=''):
        if not filename:
            base_name = ''.join(['Untitled-', str(time.time()), '.coinscript'])
            filename = os.path.expanduser(base_name)
        self.load_script(filename)

    def save_script(self):
        filename = self.filename
        if not filename:
            filename = str(QFileDialog.getSaveFileName(self, 'Save script', filter=script_file_filter))
            if not filename: return

        if not filename.endswith('.coinscript'):
            filename += '.coinscript'

        self.filename = filename
        with open(self.filename, 'w') as file:
            file.write(str(self.script_editor.toPlainText()))
        self.last_saved = str(self.script_editor.toPlainText())
        self.on_text_changed()

    def save_script_as(self):
        filename = str(QFileDialog.getSaveFileName(self, 'Save script as', filter=script_file_filter))
        if not filename: return

        if not filename.endswith('.coinscript'):
            filename += '.coinscript'
        self.filename = filename
        self.save_script()

    def open_script(self):
        filename = str(QFileDialog.getOpenFileName(self, 'Open script', '.', filter=script_file_filter))
        if not filename:
            return
        # Confirm discarding changes if an unsaved file is open.
        if (self.filename
            and str(self.script_editor.toPlainText())
            and filename != self.filename
            and not self.changes_saved):
            result = QMessageBox.question(self, 'Save Changes',
                        'Do you want to save your changes to ' + self.filename + ' before closing?',
                        QMessageBox.Yes | QMessageBox.No)
            if result == QMessageBox.Yes:
                self.save_script()

        self.load_script(filename)

    def load_script(self, filename):
        self.setWindowTitle('Hashmal - ' + filename)
        if os.path.exists(filename):
            self.filename = filename
            with open(self.filename,'r') as file:
                self.script_editor.setPlainText(file.read())
        else:
            self.script_editor.clear()
        self.last_saved = str(self.script_editor.toPlainText())
        self.on_text_changed()


    def create_script_editor(self):
        vbox = QVBoxLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(known_script_formats)
        self.script_editor = MyScriptEdit(self)
        self.script_editor.textChanged.connect(self.on_text_changed)

        self.format_combo.currentIndexChanged.connect(lambda index: self.script_editor.set_format(known_script_formats[index]))

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel('Format: '))
        hbox.addWidget(self.format_combo)
        hbox.addStretch(1)
        vbox.addLayout(hbox)
        vbox.addWidget(self.script_editor)

        w = QWidget()
        w.setLayout(vbox)
        self.setCentralWidget(w)

    def do_about(self):
        d = QDialog(self)
        vbox = QVBoxLayout()
        about_label = QLabel()
        about_label.setWordWrap(True)

        txt = []
        txt.append(' '.join([
                'Hashmal is an IDE for Bitcoin transaction scripts.',
                'Its purpose is to make it easier to write, evaluate, and learn about transaction scripts.'
        ]))
        txt.append('Hashmal is intended for cryptocurrency developers and power users.')
        txt.append('Use at own risk!')
        txt = '\n\n'.join(txt)

        about_label.setText(txt)

        close_button = QPushButton('Close')
        close_button.clicked.connect(d.close)
        btn_box = floated_buttons([close_button])

        vbox.addWidget(about_label)
        vbox.addLayout(btn_box)
        d.setLayout(vbox)
        d.setWindowTitle('About Hashmal')
        d.exec_()

    def do_quick_tips(self):
        QuickTips(self).exec_()
