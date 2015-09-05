from PyQt4.QtGui import *
from PyQt4.QtCore import QSettings, QSize, QVariant

from gui_utils import floated_buttons, Amount

class SettingsDialog(QDialog):
    """Shows info about tools and manages their layout."""
    def __init__(self, main_window):
        super(SettingsDialog, self).__init__(main_window)
        self.gui = main_window
        self.config = main_window.config
        self.qt_settings = main_window.qt_settings
        if not self.qt_settings.contains('/'.join(['toolLayout', 'default'])):
            self.save_layout()

        # load saved layouts
        self.qt_settings.beginGroup('toolLayout')
        self.layout_names = self.qt_settings.childKeys()
        self.qt_settings.endGroup()

        self.setup_layout()
        self.setWindowTitle('Settings')

    def sizeHint(self):
        return QSize(375, 270)

    def setup_layout(self):
        vbox = QVBoxLayout()
        tabs = QTabWidget()
        qt_tab = self.create_qt_tab()
        general_tab = self.create_general_tab()
        tabs.addTab(qt_tab, 'Window Settings')
        tabs.addTab(general_tab, 'General')

        close_button = QPushButton('Close')
        close_button.clicked.connect(self.close)
        close_box = floated_buttons([close_button])

        vbox.addWidget(tabs)
        vbox.addLayout(close_box)
        self.setLayout(vbox)

    def create_qt_tab(self):
        # QComboBox for loading/deleting a layout
        layout_combo = QComboBox()
        layout_combo.addItems(self.layout_names)
        # Load layout
        load_button = QPushButton('Load')
        load_button.setToolTip('Load the selected layout')
        load_button.clicked.connect(lambda: self.load_layout(str(layout_combo.currentText())))
        # Delete layout
        delete_button = QPushButton('Delete')
        delete_button.setToolTip('Delete the selected layout')
        delete_button.clicked.connect(lambda: self.delete_layout(str(layout_combo.currentText())))

        # QLineEdit for saving a layout
        layout_name_edit = QLineEdit()
        # Save layout button
        save_button = QPushButton('Save')
        save_button.clicked.connect(lambda: self.save_layout(str(layout_name_edit.text())))

        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form.setVerticalSpacing(10)

        hbox = QHBoxLayout()
        hbox.setSpacing(10)
        hbox.addWidget(layout_combo, stretch=1)
        hbox.addWidget(load_button)
        hbox.addWidget(delete_button)

        form.addRow('Layout:', hbox)

        hbox = QHBoxLayout()
        hbox.setSpacing(10)
        hbox.addWidget(layout_name_edit, stretch=1)
        hbox.addWidget(save_button)

        form.addRow('Save current layout as:', hbox)

        save_on_quit = QCheckBox('Save the current layout as default when quitting Hashmal.')
        save_on_quit.setChecked(self.qt_settings.value('saveLayoutOnExit', defaultValue=QVariant(False)).toBool())
        save_on_quit.stateChanged.connect(lambda checked: self.qt_settings.setValue('saveLayoutOnExit', True if checked else False))
        form.addRow(save_on_quit)

        w = QWidget()
        w.setLayout(form)
        return w

    def create_general_tab(self):
        form = QFormLayout()

        amnt_format = QComboBox()
        amnt_format.addItems(Amount.known_formats())
        current_format = self.config.get_option('amount_format', 'satoshis')
        try:
            amnt_format.setCurrentIndex(Amount.known_formats().index(current_format))
        except Exception:
            amnt_format.setCurrentIndex(0)
        def set_amount_format():
            new_format = str(amnt_format.currentText())
            self.config.set_option('amount_format', new_format)
            self.gui.dock_handler.amount_format_changed()
        amnt_format.currentIndexChanged.connect(set_amount_format)
        amnt_format.setToolTip('Format that transaction amounts are shown in')

        form.addRow('Amount format:', amnt_format)

        w = QWidget()
        w.setLayout(form)
        return w

    def save_layout(self, name='default'):
        key = '/'.join(['toolLayout', name])
        self.qt_settings.setValue(key, self.gui.saveState())
        self.gui.show_status_message('Saved layout "{}".'.format(name))

    def load_layout(self, name='default'):
        key = '/'.join(['toolLayout', name])
        self.gui.restoreState(self.qt_settings.value(key).toByteArray())
        self.gui.show_status_message('Loaded layout "{}".'.format(name))

    def delete_layout(self, name):
        if name == 'default':
            self.gui.show_status_message('Cannot delete the default layout.', True)
            return
        key = '/'.join(['toolLayout', name])
        self.qt_settings.remove(key)
        self.gui.show_status_message('Deleted layout "{}".'.format(name))

