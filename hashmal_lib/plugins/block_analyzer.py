from io import BytesIO

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from bitcoin.core import x, b2x
from bitcoin.core.serialize import VarIntSerializer

from base import BaseDock, Plugin, Category, augmenter
from item_types import ItemAction
from hashmal_lib.gui_utils import Separator
from hashmal_lib.widgets.block import BlockWidget
from hashmal_lib.core import BlockHeader, Block

def make_plugin():
    return Plugin(BlockAnalyzer, category=Category.Block)

def deserialize_block_or_header(raw):
    """Deserialize hex-encoded block/block header.

    Returns:
        Two-tuple of (block, block_header)
    """
    try:
        raw = x(raw)
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

class BlockAnalyzer(BaseDock):

    tool_name = 'Block Analyzer'
    description = 'Deserializes raw blocks.'
    is_large = True

    def init_data(self):
        self.header = None
        self.block = None

    @augmenter
    def item_actions(self, *args):
        return [
            ItemAction(self.tool_name, 'Block', 'Deserialize', self.deserialize_item),
            ItemAction(self.tool_name, 'Block Header', 'Deserialize', self.deserialize_item)
        ]

    def create_layout(self):
        self.raw_block_invalid = QLabel('Cannot parse block or block header.')
        self.raw_block_invalid.setProperty('hasError', True)
        self.raw_block_invalid.hide()
        self.block_widget = BlockWidget()
        self.block_widget.header_widget.view.selectionModel().selectionChanged.connect(self.on_header_selection)
        self.block_widget.txs_widget.view.selectionModel().selectionChanged.connect(self.on_tx_selection)
        self.raw_block_edit = QPlainTextEdit()
        self.raw_block_edit.setWhatsThis('Enter a serialized raw block or block header here. If you have a raw block or header stored in the Variables tool, you can enter the variable name preceded by a "$", and the variable value will be substituted automatically after pressing the space key.')
        self.raw_block_edit.textChanged.connect(self.check_raw_block)
        self.handler.substitute_variables(self.raw_block_edit)
        self.raw_block_edit.setTabChangesFocus(True)
        self.setFocusProxy(self.raw_block_edit)

        self.raw_block_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.raw_block_edit.customContextMenuRequested.connect(self.raw_block_context_menu)

        self.block_widget.txs_widget.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.block_widget.txs_widget.view.customContextMenuRequested.connect(self.txs_context_menu)
        
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel('Raw Block (Or Block Header):'))
        vbox.addWidget(self.raw_block_edit)
        vbox.addWidget(self.raw_block_invalid)
        vbox.addWidget(Separator())
        vbox.addWidget(self.block_widget, stretch=1)
        return vbox

    def raw_block_context_menu(self, pos):
        menu = self.raw_block_edit.createStandardContextMenu()
        self.handler.add_plugin_actions(self, menu, str(self.raw_block_edit.toPlainText()))
        menu.exec_(self.raw_block_edit.viewport().mapToGlobal(pos))

    def check_raw_block(self):
        txt = str(self.raw_block_edit.toPlainText())
        # Variable substitution
        if txt.startswith('$'):
            return
        self.block, self.header = deserialize_block_or_header(txt)
        show_invalid_msg = True if self.header is None and txt else False
        self.raw_block_invalid.setVisible(show_invalid_msg)

        # Clears the widget if block_header is None.
        self.block_widget.set_block(self.header, self.block)

    def deserialize_item(self, item):
        self.needsFocus.emit()
        self.raw_block_edit.setPlainText(item.raw())

    def txs_context_menu(self, position):
        try:
            selected = self.block_widget.txs_widget.view.selectedIndexes()[0]
        except IndexError:
            return
        menu = QMenu()
        if self.block:
            r = selected.row()
            tx = self.block.vtx[r]
            raw_tx = b2x(tx.serialize())
            self.handler.add_plugin_actions(self, menu, raw_tx)

        menu.exec_(self.block_widget.txs_widget.view.viewport().mapToGlobal(position))

    def select_block_text(self, start, length):
        """Select an area of the raw block textedit."""
        cursor = QTextCursor(self.raw_block_edit.document())
        cursor.setPosition(start)
        cursor.setPosition(start + length, QTextCursor.KeepAnchor)
        self.raw_block_edit.setTextCursor(cursor)

    def on_header_selection(self, selected, deselected):
        if not self.header or not len(selected.indexes()):
            return
        index = selected.indexes()[0]
        row = index.row()
        header = [i[2] * 2 for i in self.header.fields]

        start = sum(header[0:row])
        self.select_block_text(start, header[row])

    def on_tx_selection(self, selected, deselected):
        if not self.block or not len(selected.indexes()):
            return
        index = selected.indexes()[0]
        row = index.row()

        def tx_len(i):
            return len(self.block.vtx[i].serialize()) * 2

        start = BlockHeader.header_length() * 2 + sum(tx_len(i) for i in range(row))
        # Account for VarInt.
        _buf = BytesIO()
        VarIntSerializer.stream_serialize(len(self.block.vtx), _buf)
        start += len(_buf.getvalue()) * 2

        length = len(self.block.vtx[row].serialize()) * 2
        self.select_block_text(start, length)

    def on_option_changed(self, key):
        if key == 'chainparams':
            self.raw_block_edit.textChanged.emit()

