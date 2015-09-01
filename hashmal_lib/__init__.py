import sys

from PyQt4.QtGui import QApplication

from main_window import HashmalMain


class HashmalGui(object):
    def __init__(self):
        super(HashmalGui, self).__init__()
        self.app = QApplication(sys.argv)

    def main(self):
        self.main_window = HashmalMain(self.app)
        self.main_window.show()
        sys.exit(self.app.exec_())

