from PyQt4.QtGui import *
from PyQt4.QtCore import *
import bitcoin
from bitcoin.core import CBlockHeader, CBlock, x, b2x, lx, b2lx
from base import BaseDock, Plugin, Category
from hashmal_lib.gui_utils import Separator
from hashmal_lib.widgets.block import BlockWidget
from hashmal_lib.items import *
from hashmal_lib.core import BlockHeader, Block

def make_plugin():
    return Plugin(BlockAnalyzer)

class BlockAnalyzer(BaseDock):

    tool_name = 'Block Analyzer'
    description = 'Deserializes raw blocks.'
    category = Category.Block
    is_large = True

    def init_data(self):
        self.header = None
        self.block = None

    def init_actions(self):
        deserialize = ('Deserialize', self.deserialize_raw)
        self.advertised_actions[RAW_BLOCK] = self.advertised_actions[RAW_BLOCK_HEADER] = [deserialize]

    def create_layout(self):
        self.raw_block_invalid = QLabel('Cannot parse block or block header.')
        self.raw_block_invalid.setProperty('hasError', True)
        self.raw_block_invalid.hide()
        self.block_widget = BlockWidget()
        self.block_widget.header_widget.view.selectionModel().selectionChanged.connect(self.select_block_field)
        self.raw_block_edit = QPlainTextEdit()
        self.raw_block_edit.setWhatsThis('Enter a serialized raw block or block header here. If you have a raw block or header stored in the Variables tool, you can enter the variable name preceded by a "$", and the variable value will be substituted automatically.')
        self.raw_block_edit.textChanged.connect(self.check_raw_block)
        self.setFocusProxy(self.raw_block_edit)

        self.block_widget.txs_widget.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.block_widget.txs_widget.view.customContextMenuRequested.connect(self.txs_context_menu)
        
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form.addRow('Raw Block (Or Block Header):', self.raw_block_edit)
        form.addRow(self.raw_block_invalid)
        form.addRow(Separator())
        form.addRow(self.block_widget)
        return form

    def check_raw_block(self):
        txt = str(self.raw_block_edit.toPlainText())
        # Variable substitution
        if txt.startswith('$'):
            var_value = self.handler.get_plugin('Variables').dock.get_key(txt[1:])
            if var_value:
                self.raw_block_edit.setPlainText(var_value)
            return
        self.block, self.header = self.deserialize(txt)
        self.raw_block_invalid.setVisible(self.header is None)

        # Clears the widget if block_header is None.
        self.block_widget.set_block(self.header, self.block)

    def deserialize_raw(self, txt):
        """This is for context menus."""
        self.needsFocus.emit()
        self.raw_block_edit.setPlainText(txt)
        self.check_raw_block()

    def deserialize(self, raw):
        """Deserialize hex-encoded block/block header.

        Returns:
            Two-tuple of (block, block_header)
        """
        raw = x(raw)
        try:
            if len(raw) == BlockHeader.header_length():
                block_header = BlockHeader.deserialize(raw)
                return (None, block_header)
            else:
                # We don't use block.get_header() in case the header is
                # correct but the rest of the block isn't.
                block_header = BlockHeader.deserialize(raw[0:BlockHeader.header_length()])
                block = Block.deserialize(raw)
                return (block, block_header)
        except Exception as e:
            return (None, None)

    def txs_context_menu(self, position):
        menu = QMenu()
        if self.block:
            selected = self.block_widget.txs_widget.view.selectedIndexes()[0]
            r = selected.row()
            tx = self.block.vtx[r]
            raw_tx = b2x(tx.serialize())
            self.handler.add_plugin_actions(self, menu, RAW_TX, raw_tx)

        menu.exec_(self.block_widget.txs_widget.view.viewport().mapToGlobal(position))

    def select_block_field(self, selected, deselected):
        if len(self.raw_block_edit.toPlainText()) < BlockHeader.header_length() * 2:
            return
        if not len(selected.indexes()):
            return
        index = selected.indexes()[0]
        row = index.row()
        header = [i[2] * 2 for i in self.header.fields]

        start = sum(header[0:row])
        length = header[row]

        cursor = QTextCursor(self.raw_block_edit.document())
        cursor.setPosition(start)
        cursor.setPosition(start + length, QTextCursor.KeepAnchor)
        self.raw_block_edit.setTextCursor(cursor)

    def on_option_changed(self, key):
        if key == 'chainparams':
            self.raw_block_edit.textChanged.emit()

