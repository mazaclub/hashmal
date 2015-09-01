
import os
import time

from PyQt4.QtGui import *
from PyQt4 import QtCore

from dock_handler import DockHandler
from settings_dialog import SettingsDialog
from scriptedit import ScriptEditor
from help_widgets import QuickTips, ToolInfo
from gui_utils import script_file_filter, hashmal_style

class HashmalMain(QMainWindow):

    def __init__(self, app):
        super(HashmalMain, self).__init__()
        self.app = app
        self.app.setStyleSheet(hashmal_style)
        self.changes_saved = True

        QtCore.QCoreApplication.setOrganizationName('mazaclub')
        QtCore.QCoreApplication.setApplicationName('hashmal')
        self.settings = QtCore.QSettings()

        self.setDockNestingEnabled(True)
        self.dock_handler = DockHandler(self)
        self.dock_handler.create_docks()
        self.dock_handler.do_default_layout()

        self.script_editor = ScriptEditor()
        self.script_editor.changesSaved.connect(self.on_changes_saved)
        self.setCentralWidget(self.script_editor)

        self.create_menubar()
        self.create_default_script()
        self.statusBar().setVisible(True)
        self.statusBar().messageChanged.connect(self.change_status_bar)

        self.restoreState(self.settings.value('toolLayout/default').toByteArray())

        if self.settings.value('quickTipsOnStart', defaultValue=QtCore.QVariant(True)).toBool():
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

    def on_changes_saved(self, saved):
        title = ''.join(['Hashmal - ', self.script_editor.filename])
        if not saved:
            title = ''.join([title, ' *'])
        self.setWindowTitle(title)
        self.changes_saved = saved

    def closeEvent(self, event):
        # Save layout if configured to.
        if self.settings.value('saveLayoutOnExit', defaultValue=QtCore.QVariant(False)).toBool():
            self.settings.setValue('toolLayout/default', self.saveState())

        if self.changes_saved or (not self.script_editor.filename and not str(self.script_editor.script_edit.toPlainText())):
            event.accept()
            return
        result = QMessageBox.question(self, 'Save Changes',
                    'Do you want to save your changes to ' + self.script_editor.filename + ' before closing?',
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
        filename = self.script_editor.filename
        if not filename:
            filename = str(QFileDialog.getSaveFileName(self, 'Save script', filter=script_file_filter))
            if not filename: return

        if not filename.endswith('.coinscript'):
            filename += '.coinscript'

        self.script_editor.filename = filename
        self.script_editor.save()

    def save_script_as(self):
        filename = str(QFileDialog.getSaveFileName(self, 'Save script as', filter=script_file_filter))
        if not filename: return

        if not filename.endswith('.coinscript'):
            filename += '.coinscript'
        self.script_editor.filename = filename
        self.script_editor.save()

    def open_script(self):
        filename = str(QFileDialog.getOpenFileName(self, 'Open script', '.', filter=script_file_filter))
        if not filename:
            return
        # Confirm discarding changes if an unsaved file is open.
        if (self.script_editor.filename
            and str(self.script_editor.script_edit.toPlainText())
            and filename != self.script_editor.filename
            and not self.changes_saved):
            result = QMessageBox.question(self, 'Save Changes',
                        'Do you want to save your changes to ' + self.script_editor.filename + ' before closing?',
                        QMessageBox.Yes | QMessageBox.No)
            if result == QMessageBox.Yes:
                self.save_script()

        self.load_script(filename)

    def load_script(self, filename):
        self.setWindowTitle('Hashmal - ' + filename)
        self.script_editor.load(filename)

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

        btn_box = QHBoxLayout()
        close_button = QPushButton('Close')
        close_button.clicked.connect(d.close)
        btn_box.addStretch(1)
        btn_box.addWidget(close_button)

        vbox.addWidget(about_label)
        vbox.addLayout(btn_box)
        d.setLayout(vbox)
        d.setWindowTitle('About Hashmal')
        d.exec_()

    def do_quick_tips(self):
        QuickTips(self).exec_()
