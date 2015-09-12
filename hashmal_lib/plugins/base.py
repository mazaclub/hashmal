from PyQt4.QtGui import QDockWidget, QWidget, QVBoxLayout
from PyQt4 import QtCore

from hashmal_lib import config

class Plugin(object):
    """A plugin.

    A module's make_plugin() function should return
    an instance of this class.
    """
    def __init__(self, dock_widgets):
        self.docks = dock_widgets

class BaseDock(QDockWidget):
    """Base class for docks."""
    needsUpdate = QtCore.pyqtSignal()
    statusMessage = QtCore.pyqtSignal(str, bool, name='statusMessage')
    def __init__(self, handler):
        super(BaseDock, self).__init__('', handler)
        self.handler = handler
        self.tool_name = ''
        self.description = ''
        self.config = config.get_config()
        # If True, dock will be placed on the bottom by default.
        # Otherwise, dock will be placed on the right.
        self.is_large = False

        self.init_metadata()
        self.init_data()
        my_layout = self.create_layout()
        self.main_widget = QWidget()
        self.main_widget.setLayout(my_layout)
        self.needsUpdate.connect(self.refresh_data)
        self.setWidget(self.main_widget)

        self.config.optionChanged.connect(self.on_option_changed)

        self.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea | QtCore.Qt.BottomDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.setObjectName(self.tool_name)
        self.setWindowTitle(self.tool_name)
        self.setWhatsThis(self.description)

    def init_metadata(self):
        """Initialize metadata (e.g. tool description)."""
        pass

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

    def on_option_changed(self, key):
        """Called when a config option changes."""
        pass

    def status_message(self, msg, error=False):
        """Show a message on the status bar.

        Args:
            msg (str): Message to be displayed.
            error (bool): Whether to display msg as an error.
        """
        msg = ''.join([ '[%s] --> %s' % (self.tool_name, msg) ])
        self.statusMessage.emit(msg, error)
