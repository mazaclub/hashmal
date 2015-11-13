from PyQt4.QtGui import *
from PyQt4.QtCore import *
import bitcoin
from bitcoin.core import CBlockHeader, CBlock, x, b2x, lx, b2lx
from base import BaseDock, Plugin, Category
from hashmal_lib.gui_utils import Separator
from hashmal_lib.widgets.block import BlockWidget
from hashmal_lib.items import *

def make_plugin():
    return Plugin(BlockAnalyzer)

class BlockAnalyzer(BaseDock):

    tool_name = 'Block Analyzer'
    description = 'Deserializes raw blocks.'
    category = Category.Block
    is_large = True

    def init_data(self):
        self.block = None

    def init_actions(self):
        deserialize = ('Deserialize', self.deserialize_raw)
        self.advertised_actions[RAW_BLOCK] = self.advertised_actions[RAW_BLOCK_HEADER] = [deserialize]

    def create_layout(self):
        self.block_widget = BlockWidget()
        self.block_widget.header_widget.view.selectionModel().selectionChanged.connect(self.select_block_field)
        self.raw_block_edit = QPlainTextEdit()
        self.raw_block_edit.textChanged.connect(self.check_raw_block)
        self.setFocusProxy(self.raw_block_edit)

        self.block_widget.txs_widget.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.block_widget.txs_widget.view.customContextMenuRequested.connect(self.txs_context_menu)
        
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form.addRow('Raw Block (Or Block Header):', self.raw_block_edit)
        form.addRow(Separator())
        form.addRow(self.block_widget)
        return form

    def check_raw_block(self):
        txt = str(self.raw_block_edit.toPlainText())
        self.block, block_header = self.deserialize(txt)

        # Clears the widget if block_header is None.
        self.block_widget.set_block(block_header, self.block)

    def deserialize_raw(self, txt):
        """This is for context menus."""
        self.needsFocus.emit()
        self.raw_block_edit.setPlainText(txt)
        self.check_raw_block()

    def deserialize(self, raw):
        """Deserialize hex-encoded block/block header."""
        only_header = False
        if len(raw) == 160:
            only_header = True

        block = None
        block_header = None

        try:
            if only_header:
                block_header = CBlockHeader.deserialize(x(raw))
            else:
                # We don't use block.get_header() in case the header is
                # correct but the rest of the block isn't.
                block_header = CBlockHeader.deserialize(x(raw[0:160]))
                block = CBlock.deserialize(x(raw))
        except Exception:
            pass

        return (block, block_header)

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
        if len(self.raw_block_edit.toPlainText()) < 160:
            return
        index = selected.indexes()[0]
        row = index.row()
        header = [8, 64, 64, 8, 8, 8]

        start = sum(header[0:row])
        length = header[row]

        cursor = QTextCursor(self.raw_block_edit.document())
        cursor.setPosition(start)
        cursor.setPosition(start + length, QTextCursor.KeepAnchor)
        self.raw_block_edit.setTextCursor(cursor)

