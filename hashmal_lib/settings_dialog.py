from PyQt4.QtGui import *
from PyQt4.QtCore import *

from hashmal_lib.core import chainparams
from gui_utils import floated_buttons, Amount, monospace_font, Separator

class ChainparamsComboBox(QComboBox):
    """ComboBox for selecting chainparams presets.

    Separated from SettingsDialog so it can be used elsewhere.
    """
    paramsChanged = pyqtSignal()
    def __init__(self, config, parent=None):
        super(ChainparamsComboBox, self).__init__(parent)
        self.config = config

        preset_names = [i.name for i in chainparams.presets_list]
        self.addItems(preset_names)
        self.set_index()

        self.currentIndexChanged.connect(self.change_params)
        self.config.optionChanged.connect(self.check_config)

    def set_index(self):
        preset_names = [i.name for i in chainparams.presets_list]
        active_params = self.config.get_option('chainparams', 'Bitcoin')
        # The config file might have changed to have a nonexistent preset.
        try:
            self.setCurrentIndex(preset_names.index(active_params))
        except ValueError:
            self.setCurrentIndex(preset_names.index('Bitcoin'))

    def check_config(self, key):
        if key != 'chainparams':
            return
        self.set_index()

    def change_params(self):
        new_name = str(self.currentText())
        chainparams.set_to_preset(new_name)
        self.config.set_option('chainparams', new_name)
        self.paramsChanged.emit()

class LayoutChanger(QWidget):
    current_layout = 'default'
    def __init__(self, main_window, parent=None):
        super(LayoutChanger, self).__init__(parent)
        self.gui = main_window
        self.qt_settings = main_window.qt_settings
        self.load_layout_names()
        self.create_layout()
        self.gui.layoutsChanged.connect(self.refresh_layout_combobox)
        self.layout_combo.setCurrentIndex(self.layout_names.indexOf('default'))

    def load_layout_names(self):
        self.qt_settings.beginGroup('toolLayout')
        self.layout_names = self.qt_settings.childGroups()
        self.qt_settings.endGroup()

    def create_layout(self):
        # QComboBox for loading/deleting/saving a layout.
        self.layout_combo = layout_combo = QComboBox()
        layout_combo.addItems(self.layout_names)
        # Load layout
        self.load_button = load_button = QPushButton('Load')
        load_button.setToolTip('Load the selected layout')
        load_button.clicked.connect(lambda: self.load_layout(str(layout_combo.currentText())))
        # Delete layout
        self.delete_button = delete_button = QPushButton('Delete')
        delete_button.setToolTip('Delete the selected layout')
        delete_button.clicked.connect(lambda: self.delete_layout(str(layout_combo.currentText())))
        # Save layout button
        self.save_button = save_button = QPushButton('Save')
        save_button.setToolTip('Save current layout as the selected layout')
        save_button.clicked.connect(lambda: self.save_layout(str(layout_combo.currentText())))

        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.addWidget(layout_combo)
        hbox.addWidget(load_button)
        hbox.addWidget(save_button)
        hbox.addWidget(delete_button)

        self.setLayout(hbox)

    def save_layout(self, name='default'):
        key = '/'.join(['toolLayout', name])
        LayoutChanger.current_layout = name
        self.qt_settings.setValue(key + '/state', self.gui.saveState())
        self.qt_settings.setValue(key + '/geometry', self.gui.saveGeometry())
        self.gui.show_status_message('Saved layout "{}".'.format(name))
        self.gui.layoutsChanged.emit()

    def load_layout(self, name='default'):
        key = '/'.join(['toolLayout', name])
        LayoutChanger.current_layout = name
        pos = self.gui.pos()
        self.gui.restoreState(self.qt_settings.value(key + '/state').toByteArray())
        self.gui.restoreGeometry(self.qt_settings.value(key + '/geometry').toByteArray())
        self.gui.move(pos)
        self.gui.show_status_message('Loaded layout "{}".'.format(name))
        self.gui.layoutsChanged.emit()

    def delete_layout(self, name):
        key = '/'.join(['toolLayout', name])
        if LayoutChanger.current_layout == name:
            LayoutChanger.current_layout = 'default'
        self.qt_settings.remove(key)
        self.gui.show_status_message('Deleted layout "{}".'.format(name))
        self.gui.layoutsChanged.emit()

    def refresh_layout_combobox(self):
        # Skip if things aren't set up yet.
        if not getattr(self, 'layout_combo', None):
            return
        self.load_layout_names()
        self.layout_combo.clear()
        self.layout_combo.addItems(self.layout_names)
        self.layout_combo.setCurrentIndex(self.layout_names.indexOf(LayoutChanger.current_layout))


class SettingsDialog(QDialog):
    """Configuration interface.

    Handles loading/saving window layouts as well.
    """
    def __init__(self, main_window):
        super(SettingsDialog, self).__init__(main_window)
        self.gui = main_window
        self.config = main_window.config
        self.qt_settings = main_window.qt_settings
        self.layout_changer = LayoutChanger(self.gui)
        if not self.qt_settings.contains('toolLayout/default/state'):
            self.layout_changer.save_layout()

        self.setup_layout()
        self.setWindowTitle('Settings')

    def sizeHint(self):
        return QSize(375, 270)

    def setup_layout(self):
        vbox = QVBoxLayout()
        tabs = QTabWidget()
        qt_tab = self.create_qt_tab()
        editor_tab = self.create_editor_tab()
        general_tab = self.create_general_tab()
        chainparams_tab = self.create_chainparams_tab()
        tabs.addTab(general_tab, '&General')
        tabs.addTab(qt_tab, '&Window Settings')
        tabs.addTab(editor_tab, '&Editor')
        tabs.addTab(chainparams_tab, '&Chainparams')

        close_button = QPushButton('Close')
        close_button.clicked.connect(self.close)
        close_box = floated_buttons([close_button])

        vbox.addWidget(tabs)
        vbox.addLayout(close_box)
        self.setLayout(vbox)

    def create_qt_tab(self):
        self.layout_changer.layout().setStretch(0, 1)
        self.layout_changer.save_button.setVisible(False)
        # QLineEdit for saving a layout
        layout_name_edit = QLineEdit()
        layout_name_edit.setText('default')
        # Save layout button
        save_button = QPushButton('Save')
        save_button.clicked.connect(lambda: self.layout_changer.save_layout(str(layout_name_edit.text())))

        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form.setVerticalSpacing(10)

        form.addRow('Layout:', self.layout_changer)

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

    def create_editor_tab(self):
        form = QFormLayout()
        font_db = QFontDatabase()

        editor_font = self.gui.script_editor.font()

        editor_font_combo = QComboBox()
        editor_font_combo.addItems(font_db.families())
        editor_font_combo.setCurrentIndex(font_db.families().indexOf(editor_font.family()))

        editor_font_size = QSpinBox()
        editor_font_size.setRange(5, 24)
        editor_font_size.setValue(editor_font.pointSize())

        def change_font_family(idx):
            family = editor_font_combo.currentText()
            editor_font.setFamily(family)
            self.change_editor_font(editor_font)

        def change_font_size(value):
            editor_font.setPointSize(value)
            self.change_editor_font(editor_font)

        def reset_font():
            editor_font_combo.setCurrentIndex(font_db.families().indexOf(monospace_font.family()))
            editor_font_size.setValue(monospace_font.pointSize())

        editor_font_combo.currentIndexChanged.connect(change_font_family)
        editor_font_size.valueChanged.connect(change_font_size)

        reset_font_button = QPushButton('Reset to Default')
        reset_font_button.clicked.connect(reset_font)

        font_group = QGroupBox('Font')
        font_form = QFormLayout()
        font_form.addRow('Family:', editor_font_combo)
        font_form.addRow('Size:', editor_font_size)
        font_form.addRow(floated_buttons([reset_font_button]))
        font_group.setLayout(font_form)


        vars_color = ColorButton('variables', QColor('darkMagenta'))
        strs_color = ColorButton('strings', QColor('gray'))

        colors_group = QGroupBox('Colors')
        colors_form = QFormLayout()
        colors_form.addRow('Variables:', floated_buttons([vars_color], True))
        colors_form.addRow('String literals:', floated_buttons([strs_color], True))
        colors_group.setLayout(colors_form)

        form.addRow(font_group)
        form.addRow(colors_group)

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
        amnt_format.currentIndexChanged.connect(set_amount_format)
        amnt_format.setToolTip('Format that transaction amounts are shown in')


        data_retriever = QComboBox()
        retrievers = self.gui.plugin_handler.get_data_retrievers()
        retriever_names = [i.name for i in retrievers]
        data_retriever.addItems(retriever_names)

        current_data_retriever = self.config.get_option('data_retriever', 'Blockchain')
        try:
            idx = retriever_names.index(current_data_retriever)
            data_retriever.setCurrentIndex(idx)
        except ValueError:
            idx = retriever_names.index('Blockchain')
            data_retriever.setCurrentIndex(idx)

        def set_retriever(idx):
            new_retriever = retriever_names[idx]
            self.config.set_option('data_retriever', new_retriever)
        data_retriever.currentIndexChanged.connect(set_retriever)
        data_retriever.setToolTip('Plugin used to download blockchain data')

        form.addRow('Amount format:', amnt_format)
        form.addRow('Data Retriever:', data_retriever)

        w = QWidget()
        w.setLayout(form)
        return w

    def create_chainparams_tab(self):
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)

        desc = ''.join(['ChainParams define some basic rules of the blockchain.',
                        ' Notably, these rules include the format of transactions.'])
        desc_label = QLabel(desc)
        desc_label.setWordWrap(True)

        self.params_combo = ChainparamsComboBox(self.config)

        self.params_combo.paramsChanged.connect(self.change_chainparams)

        self.format_list = QListWidget()
        for name, _, _, _ in chainparams.get_tx_fields():
            self.format_list.addItem(name)

        form.addRow(desc_label)
        form.addRow('Params:', self.params_combo)
        form.addRow(Separator())
        form.addRow('Tx Format:', self.format_list)

        w = QWidget()
        w.setLayout(form)
        return w

    def change_editor_font(self, font):
        self.gui.script_editor.setFont(font)
        self.qt_settings.setValue('editor/font', font.toString())

    def change_chainparams(self):
        self.format_list.clear()
        for name, _, _, _ in chainparams.get_tx_fields():
            self.format_list.addItem(name)

class ColorButton(QPushButton):
    """Represents a color visually."""
    def __init__(self, name, default_color, parent=None):
        super(ColorButton, self).__init__(parent)
        self.name = name
        self.color = QColor(QSettings().value('color/' + name, default_color.name()))
        self.clicked.connect(self.show_color_dialog)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(0, 0, self.size().width(), self.size().height(), self.color)

    def show_color_dialog(self):
        new_color = QColorDialog.getColor(self.color)
        if not new_color.isValid(): return
        self.color = new_color
        QSettings().setValue('color/' + self.name, self.color.name())
