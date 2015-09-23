from PyQt4.QtGui import *
from PyQt4 import QtCore

from gui_utils import floated_buttons

class QuickTips(QDialog):
    def __init__(self, main_window):
        super(QuickTips, self).__init__(main_window)
        self.gui = main_window

        vbox = QVBoxLayout()
        tips_text = '''
<ul>
<li>See <i>Help > Tool Info</i> in the menubar for details on what each tool does.</li>
<li>You can manage tool layouts via <i>Tools > Settings</i> in the menubar.</li>
<li>When typing opcodes, you can omit the "OP_" prefix for opcodes other than OP_1, OP_2, ...OP_16. For example, "DUP" and "OP_DUP" do the same thing.</li>
<li>You can quickly evaluate the script you\'re working on via <i>Script > Evaluate</i> in the menubar.</li>
<li>Put text in double quotation marks to ensure that it\'s treated as text that needs to be hex-encoded.</li>
</ul>

<p>See <a href="https://github.com/mazaclub/hashmal/wiki">https://github.com/mazaclub/hashmal/wiki</a> for detailed help.</p>
'''
        tips = QLabel(tips_text)
        tips.setWordWrap(True)
        vbox.addWidget(QLabel('<b>Quick Tips:</b>'))
        vbox.addWidget(tips)

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


class ToolInfo(QDialog):
    def __init__(self, main_window):
        super(ToolInfo, self).__init__(main_window)
        self.gui = main_window

        tool_combo = QComboBox()
        tool_combo.addItems( [i for i in sorted(self.gui.dock_handler.dock_widgets.keys())] )

        tool_info = QTextEdit()
        tool_info.setReadOnly(True)

        def show_tool_info():
            # Create HTML paragraphs from description.
            tool = self.gui.dock_handler.dock_widgets[str(tool_combo.currentText())]
            s = []
            for i in tool.description.split('\n'):
                s.append('<p>{}</p>'.format(i))
            tool_info.setHtml(''.join(s))
        tool_combo.currentIndexChanged.connect(show_tool_info)
        # For some reason this has to be done twice.
        tool_combo.setCurrentIndex(1)
        tool_combo.setCurrentIndex(0)

        close_button = QPushButton('Close')
        close_button.clicked.connect(self.close)

        vbox = QVBoxLayout()

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel('Tool:'))
        hbox.addWidget(tool_combo, stretch=1)

        btn_hbox = floated_buttons([close_button])

        vbox.addLayout(hbox)
        vbox.addWidget(QLabel('Info:'))
        vbox.addWidget(tool_info)
        vbox.addLayout(btn_hbox)
        self.setLayout(vbox)

        self.setWindowTitle('Tool Info')

    def sizeHint(self):
        return QtCore.QSize(375, 270)
