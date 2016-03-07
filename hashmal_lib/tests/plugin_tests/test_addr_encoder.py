import unittest
import sys
import __builtin__

from PyQt4.QtGui import QApplication
from PyQt4.QtTest import QTest
from PyQt4.QtCore import Qt

from hashmal_lib.core import chainparams
from hashmal_lib.main_window import HashmalMain
from hashmal_lib.plugins import addr_encoder

__builtin__.use_local_modules = True

chainparams.set_to_preset('Bitcoin')

app = QApplication(sys.argv)

class AddrEncoderTest(unittest.TestCase):
    def setUp(self):
        super(AddrEncoderTest, self).setUp()
        self.gui = HashmalMain(app)
        self.ui = self.gui.plugin_handler.get_plugin('Address Encoder').ui

    def test_encode_hex_bytes(self):
        self.ui.hash_line.setText('00' * 20)
        self.ui.addr_version.setValue(0)
        QTest.mouseClick(self.ui.encode_button, Qt.LeftButton)
        self.assertEqual('1111111111111111111114oLvT2', str(self.ui.address_line.text()))

    def test_decode_address(self):
        self.ui.address_line.setText('1111111111111111111114oLvT2')
        self.ui.addr_version.setValue(100)
        QTest.mouseClick(self.ui.decode_button, Qt.LeftButton)
        self.assertEqual('00' * 20, str(self.ui.hash_line.text()))
        self.assertEqual(0, self.ui.addr_version.value())
