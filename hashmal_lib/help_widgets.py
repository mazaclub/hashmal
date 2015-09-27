from PyQt4.QtGui import *
from PyQt4 import QtCore

from gui_utils import floated_buttons

class QuickTips(QDialog):
    def __init__(self, main_window):
        super(QuickTips, self).__init__(main_window)
        self.gui = main_window

        vbox = QVBoxLayout()
        general_tips_text = '''
<ul>
<li>See <i>Tools > Plugin Manager</i> in the menubar for details on what each tool does.</li>
<li>The Plugin Manager also allows you to set "favorite tools" - which have keyboard shortcuts.</li>
<li>You can manage tool layouts via <i>Tools > Settings</i> in the menubar.</li>
</ul>
'''

        editor_tips_text = '''
<ul>
<li>When typing opcodes, you can omit the "OP_" prefix for opcodes other than OP_1, OP_2, ...OP_16. For example, "DUP" and "OP_DUP" do the same thing.</li>
<li>Put text in double quotation marks to ensure that it\'s treated as text that needs to be hex-encoded.</li>
</ul>

<p>See <a href="https://github.com/mazaclub/hashmal/wiki">https://github.com/mazaclub/hashmal/wiki</a> for detailed help.</p>
'''
        general_tips = QLabel(general_tips_text)
        general_tips.setWordWrap(True)
        vbox.addWidget(QLabel('<b>General Tips:</b>'))
        vbox.addWidget(general_tips)

        editor_tips = QLabel(editor_tips_text)
        editor_tips.setWordWrap(True)
        vbox.addWidget(QLabel('<b>Editor Tips:</b>'))
        vbox.addWidget(editor_tips)

        does_show_on_startup = self.gui.qt_settings.value('quickTipsOnStart', defaultValue=QtCore.QVariant(True)).toBool()
        show_on_startup = QCheckBox('Show this dialog on startup.')
        show_on_startup.setChecked(does_show_on_startup)
        show_on_startup.stateChanged.connect(lambda checked: self.gui.qt_settings.setValue('quickTipsOnStart', True if checked else False))
        vbox.addWidget(show_on_startup)

        close_button = QPushButton('Close')
        close_button.clicked.connect(self.close)
        btn_hbox = floated_buttons([close_button])
        vbox.addLayout(btn_hbox)

        self.setLayout(vbox)
        self.setWindowTitle('Quick Tips')

    def sizeHint(self):
        return QtCore.QSize(375, 270)


