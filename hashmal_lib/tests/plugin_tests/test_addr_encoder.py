import unittest

from PyQt4.QtTest import QTest
from PyQt4.QtCore import Qt

from hashmal_lib.plugins import addr_encoder
from .gui_test import PluginTest

class AddrEncoderTest(PluginTest):
    plugin_name = 'Address Encoder'
    def setUp(self):
        super(AddrEncoderTest, self).setUp()
        self.ui.address_line.clear()
        self.ui.hash_line.clear()
        self.ui.addr_version.setValue(0)

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
