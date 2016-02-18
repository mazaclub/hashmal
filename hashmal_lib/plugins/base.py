from functools import wraps
from collections import namedtuple

from PyQt4.QtGui import QDockWidget, QWidget, QVBoxLayout
from PyQt4 import QtCore

from hashmal_lib import config

PluginCategory = namedtuple('PluginCategory', ('name', 'description'))
class Category(object):
    """Plugin category.

    Use one of the below class attributes for a dock's category attribute
    e.g. 'category = Category.Script'.
    """
    General = PluginCategory('General', 'General or uncategorized plugin.')
    Block = PluginCategory('Blocks', 'Plugin that involves blocks and/or block headers.')
    Data = PluginCategory('Data', 'Plugin that retrieves blockchain data.')
    Key = PluginCategory('Keys', 'Plugin that involves keys, addresses, etc.')
    Script = PluginCategory('Scripts', 'Plugin that involves scripts.')
    Tx = PluginCategory('Transactions', 'Plugin that involves transactions.')

    @classmethod
    def categories(cls):
        category_list = []
        for i in dir(cls):
            attr = getattr(cls, i)
            if attr.__class__.__name__ == 'PluginCategory':
                category_list.append(attr)
        return category_list

known_augmenters = []

def augmenter(func):
    """Decorator for augmenters.

    Augmenters allow plugins to augment one another.
    """
    func_name = func.__name__
    if func_name not in known_augmenters:
        known_augmenters.append(func_name)

    @wraps(func)
    def func_wrapper(*args):
        return func(*args)
    return func_wrapper


class Plugin(object):
    """A plugin.

    A module's make_plugin() function should return
    an instance of this class.
    """
    def __init__(self, ui_class):
        self.ui_class = ui_class
        self.ui = None
        # name is set when the entry point is loaded.
        self.name = ''
        # If False, plugin has no dedicated GUI.
        self.has_gui = True

    def instantiate_ui(self, plugin_handler):
        instance = self.ui_class(plugin_handler)
        self.ui = instance

    def augmenters(self):
        return self.ui.augmenters if self.ui else None

    def get_augmenter(self, hook_name):
        return getattr(self.ui, hook_name) if self.ui else None

class BasePluginUI(object):
    """Base class for plugin user interfaces."""
    tool_name = ''
    description = ''
    category = Category.General

    def __init__(self, handler):
        self.handler = handler
        self.config = config.get_config()
        self.config.optionChanged.connect(self.on_option_changed)
        self.is_enabled = True

        self.augmenters = []
        for name in dir(self):
            if name in known_augmenters:
                self.augmenters.append(name)

    def on_option_changed(self, key):
        """Called when a config option changes."""
        pass

    def options(self):
        """Return the config dict for this plugin."""
        return self.config.get_option(self.tool_name, {})

    def option(self, key, default=None):
        """Return a config option for this plugin."""
        options = self.options()
        return options.get(key, default)

    def set_option(self, key, value):
        """Set a plugin-specific config option."""
        options = self.options()
        options[key] = value
        self.save_options(options)

    def save_options(self, options):
        """Save options to config file."""
        self.config.set_option(self.tool_name, options)

    def augment(self, target, data, callback=None):
        """Ask other plugins if they have anything to contribute.

        Allows plugins to enhance other plugins.
        """
        return self.handler.do_augment_hook(self.__class__.__name__, target, data, callback)

    def info(self, msg):
        """Log an info message."""
        self.handler.info(self.tool_name, msg)

    def warning(self, msg):
        """Log a warning message."""
        self.handler.warning(self.tool_name, msg)

    def error(self, msg):
        """Log an error message."""
        self.handler.error(self.tool_name, msg)

class BaseDock(BasePluginUI, QDockWidget):
    """Base class for docks.

    Optional methods:
        retrieve_blockchain_data(data_type, identifier): Signifies that
            this dock is a data retriever, and can be used when the user
            wants to download blockchain data such as transactions.

        supported_blockchain_data_types(): Returns the types of blockchain
            data this class can retrieve.
    """
    needsFocus = QtCore.pyqtSignal()
    needsUpdate = QtCore.pyqtSignal()

    # If True, dock will be placed on the bottom by default.
    # Otherwise, dock will be placed on the right.
    is_large = False

    def __init__(self, handler):
        # We use explicit initialization methods so we don't have trouble with multiple inheritance.
        BasePluginUI.__init__(self, handler)
        QDockWidget.__init__(self, '', handler)

        self.init_data()
        my_layout = self.create_layout()
        self.main_widget = QWidget()
        self.main_widget.setLayout(my_layout)
        self.needsUpdate.connect(self.refresh_data)
        self.toggleViewAction().triggered.connect(self.visibility_toggled)
        self.setWidget(self.main_widget)

        self.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea | QtCore.Qt.BottomDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.setObjectName(self.tool_name)
        self.setWindowTitle(self.tool_name)

    def init_data(self):
        """Initialize attributes such as data containers."""
        pass

    def create_layout(self):
        """Returns the main layout for our widget.

        Subclasses should override this to return their layout.
        """
        return QVBoxLayout()

    def refresh_data(self):
        """Synchronize. Called when needsUpdate is emitted."""
        pass

    def visibility_toggled(self):
        """Called when toggleViewAction() is triggered so this dock can get focus."""
        if self.isVisible():
            self.needsFocus.emit()

    def download_async(self, downloader, callback):
        """Execute a downloader.Downloader subclass in a separate thread and call callback with the results."""
        self.handler.gui.download_controller.do_download(downloader, callback)
