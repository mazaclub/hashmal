import unittest
from collections import OrderedDict

from PyQt4.QtTest import QTest
from PyQt4.QtCore import Qt

from bitcoin.core import b2lx

from hashmal_lib.core import chainparams, Script
from hashmal_lib.plugins import script_gen
from .gui_test import PluginTest


chainparams.set_to_preset('Bitcoin')

class ScriptGenBaseTest(unittest.TestCase):
    def setUp(self):
        super(ScriptGenBaseTest, self).setUp()
        templates = OrderedDict()
        for i in script_gen.known_templates:
            templates[i.name] = i
        self.templates = templates

class ScriptGenTest(ScriptGenBaseTest):
    def test_is_template_script(self):
        scr = Script.from_human('OP_DUP OP_HASH160 0x0000000000000000000000000000000000000000 OP_EQUALVERIFY OP_CHECKSIG')
        self.assertTrue(script_gen.is_template_script(scr, self.templates['Pay-To-Public-Key-Hash Output']))

        scr = Script.from_human('OP_DUP OP_HASH160 0x0000000000000000000000000000000000000000 OP_EQUAL OP_CHECKSIG')
        self.assertFalse(script_gen.is_template_script(scr, self.templates['Pay-To-Public-Key-Hash Output']))

        scr = Script.from_human('OP_DUP OP_HASH160 0x00000000000000000000000000000000000000 OP_EQUALVERIFY OP_CHECKSIG')
        self.assertFalse(script_gen.is_template_script(scr, self.templates['Pay-To-Public-Key-Hash Output']))

        scr = Script.from_human('0x03569988948d05ddf970d610bc52f0d47fb21ec307a35d3cbeba6d11accfcd3c6a OP_CHECKSIG')
        self.assertTrue(script_gen.is_template_script(scr, self.templates['Pay-To-Public-Key']))

        scr = Script.from_human('0x3045022100f89cffc794d3c43bbaec99f61d0bb2eb72ea1df4be407f375e98f7039caab83d02204b24170189348f82d9af3049aadc1160904e7ef0ba3bc96f3fd241053f0b6de101 0x028f917ac4353d2027ef1be2d02b4dd657ef2ecf67191760c957e79f198b3579c6')
        self.assertTrue(script_gen.is_template_script(scr, self.templates['Signature Script']))

        scr = Script.from_human('0x304402200a156e3e5617cc1d795dfe0c02a5c7dab3941820f194eabd6107f81f25e0519102204d8c585635e03c9137b239893701dc280e25b162011e6474d0c9297d2650b46901 0x51210208b5b58fd9bf58f1d71682887182e7abd428756264442eec230dd021c193f8d9210245af4f2b1ae21c9310a3211f8d5debb296175e20b3a14b173ff30428e03d502d52ae')
        self.assertTrue(script_gen.is_template_script(scr, self.templates['Pay-To-Script-Hash Signature Script']))

        scr = Script.from_human('OP_0 0x304402200a156e3e5617cc1d795dfe0c02a5c7dab3941820f194eabd6107f81f25e0519102204d8c585635e03c9137b239893701dc280e25b162011e6474d0c9297d2650b46901 0x51210208b5b58fd9bf58f1d71682887182e7abd428756264442eec230dd021c193f8d9210245af4f2b1ae21c9310a3211f8d5debb296175e20b3a14b173ff30428e03d502d52ae')
        self.assertTrue(script_gen.is_template_script(scr, self.templates['Pay-To-Script-Hash Multisig Signature Script']))

class ScriptGenGUITest(ScriptGenBaseTest, PluginTest):
    plugin_name = 'Script Generator'
    def setUp(self):
        super(ScriptGenGUITest, self).setUp()
        self.ui.template_combo.setCurrentIndex(0)
        self.ui.template_widget.clear_fields()

    def _set_widget_values(self, template, templates_vars):
        self.ui.template_combo.setCurrentIndex(self.templates.values().index(template))
        for template_vars in templates_vars:
            for var_name, var_value in template_vars.items():
                self.ui.template_widget.variable_widgets[var_name].setText(var_value)

    def test_create_p2pkh_script(self):
        template = self.templates['Pay-To-Public-Key-Hash Output']
        templates_vars = [
                {'Recipient': '1111111111111111111114oLvT2'},
                {'Recipient': '0' * 40},
                {'Recipient': '0x' + '0' * 40}
        ]
        expected = 'OP_DUP OP_HASH160 0x0000000000000000000000000000000000000000 OP_EQUALVERIFY OP_CHECKSIG'

        self._set_widget_values(template, templates_vars)

        QTest.mouseClick(self.ui.generate_button, Qt.LeftButton)
        script_out = str(self.ui.script_output.toPlainText())
        self.assertEqual(expected, script_out)

    def test_create_p2pk_script(self):
        template = self.templates['Pay-To-Public-Key']
        templates_vars = [
                {'Recipient': '0x03569988948d05ddf970d610bc52f0d47fb21ec307a35d3cbeba6d11accfcd3c6a'},
                {'Recipient': '03569988948d05ddf970d610bc52f0d47fb21ec307a35d3cbeba6d11accfcd3c6a'}
        ]
        expected = '0x03569988948d05ddf970d610bc52f0d47fb21ec307a35d3cbeba6d11accfcd3c6a OP_CHECKSIG'

        self._set_widget_values(template, templates_vars)

        QTest.mouseClick(self.ui.generate_button, Qt.LeftButton)
        script_out = str(self.ui.script_output.toPlainText())
        self.assertEqual(expected, script_out)

    def test_op_return_script(self):
        template = self.templates['Null Output']
        templates_vars = [{'Text': 'testing'}]
        expected = 'OP_RETURN 0x74657374696e67'

        self._set_widget_values(template, templates_vars)

        QTest.mouseClick(self.ui.generate_button, Qt.LeftButton)
        script_out = str(self.ui.script_output.toPlainText())
        self.assertEqual(expected, script_out)

    def test_create_p2sh_sig_script(self):
        template = self.templates['Pay-To-Script-Hash Signature Script']
        templates_vars = [
                {'Signature': '0x304402200a156e3e5617cc1d795dfe0c02a5c7dab3941820f194eabd6107f81f25e0519102204d8c585635e03c9137b239893701dc280e25b162011e6474d0c9297d2650b46901',
                'RedeemScript': 'OP_1 0x0208b5b58fd9bf58f1d71682887182e7abd428756264442eec230dd021c193f8d9 0x0245af4f2b1ae21c9310a3211f8d5debb296175e20b3a14b173ff30428e03d502d OP_2 OP_CHECKMULTISIG'},
                {'Signature': '0x304402200a156e3e5617cc1d795dfe0c02a5c7dab3941820f194eabd6107f81f25e0519102204d8c585635e03c9137b239893701dc280e25b162011e6474d0c9297d2650b46901',
                'RedeemScript': '0x51210208b5b58fd9bf58f1d71682887182e7abd428756264442eec230dd021c193f8d9210245af4f2b1ae21c9310a3211f8d5debb296175e20b3a14b173ff30428e03d502d52ae'}
        ]
        expected = '0x304402200a156e3e5617cc1d795dfe0c02a5c7dab3941820f194eabd6107f81f25e0519102204d8c585635e03c9137b239893701dc280e25b162011e6474d0c9297d2650b46901 0x51210208b5b58fd9bf58f1d71682887182e7abd428756264442eec230dd021c193f8d9210245af4f2b1ae21c9310a3211f8d5debb296175e20b3a14b173ff30428e03d502d52ae'

        self._set_widget_values(template, templates_vars)

        QTest.mouseClick(self.ui.generate_button, Qt.LeftButton)
        script_out = str(self.ui.script_output.toPlainText())
        self.assertEqual(expected, script_out)
