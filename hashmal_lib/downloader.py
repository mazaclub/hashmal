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

