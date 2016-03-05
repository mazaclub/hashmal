from collections import OrderedDict

from PyQt4.QtGui import *
from PyQt4.QtCore import *


class Downloader(QObject):
    """Abstract downloader class that plugins can subclass."""
    finished = pyqtSignal()

    @pyqtSlot()
    def download(self):
        """Abstract method.

        Subclasses should overload this method and emit finished() with their results.
        """
        self.finished.emit()

class DownloadController(QObject):
    """Manages creation of QThreads for downloading."""
    def __init__(self, config, parent=None):
        super(DownloadController, self).__init__(parent)
        self.config = config
        # Cache for downloaded data.
        self.data_cache = OrderedDict()
        self.max_data_values = self.config.get_option('max_download_cache_items', 10000)

    def add_cache_data(self, key, value):
        if self.get_cache_data(key) == value:
            return
        self.data_cache[key] = value
        while len(self.data_cache) > self.max_data_values:
            self.data_cache.popitem(last=False)

    def get_cache_data(self, key, default=None):
        return self.data_cache.get(key, default)

    def do_download(self, downloader, callback):
        """Execute a download in a separate QThread."""
        self.downloader = downloader
        self.downloader_thread = thread = QThread()
        downloader.moveToThread(thread)
        thread.started.connect(downloader.download)

        downloader.finished.connect(callback)
        downloader.finished.connect(thread.quit)
        downloader.finished.connect(downloader.deleteLater)
        thread.finished.connect(thread.deleteLater)

        thread.start()

