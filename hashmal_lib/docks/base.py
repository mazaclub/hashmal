from PyQt4.QtGui import QDockWidget, QWidget, QVBoxLayout
from PyQt4 import QtCore


class BaseDock(QDockWidget):
    """Base class for docks."""
    needsUpdate = QtCore.pyqtSignal()
    statusMessage = QtCore.pyqtSignal(str, bool, name='statusMessage')
    def __init__(self, handler):
        super(BaseDock, self).__init__('', handler)
        self.handler = handler
        self.tool_name = ''
        self.description = ''

        self.init_metadata()
        self.init_data()
        my_layout = self.create_layout()
        self.main_widget = QWidget()
        self.main_widget.setLayout(my_layout)
        self.needsUpdate.connect(self.refresh_data)
        self.setWidget(self.main_widget)

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
        """Returns the main layout for our widget."""
        return QVBoxLayout()

    def refresh_data(self):
        """Synchronize."""
        pass

    def update_script_view(self, txt):
        """Called on widgets that have script views."""
        pass

    def status_message(self, msg, error=False):
        msg = ''.join([ '[%s] --> %s' % (self.tool_name, msg) ])
        self.statusMessage.emit(msg, error)
