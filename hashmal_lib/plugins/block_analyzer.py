from PyQt4.QtGui import *
from PyQt4.QtCore import *
import bitcoin
from bitcoin.core import CBlockHeader, CBlock, x, b2x, lx, b2lx
from base import BaseDock, Plugin
from hashmal_lib.gui_utils import Separator

def make_plugin():
    return Plugin(BlockAnalyzer)

class BlockHeaderWidget(QWidget):
    """Model and View showing a block header."""
    def __init__(self, parent=None):
        super(BlockHeaderWidget, self).__init__(parent)
        self.model = QStandardItemModel()
        self.model.setColumnCount(1)
        self.model.setHorizontalHeaderLabels(['Block Header'])
        self.model.setVerticalHeaderLabels(['Version', 'PrevBlockHash', 'MerkleRootHash', 'Time', 'Bits', 'Nonce'])

        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.verticalHeader().setResizeMode(QHeaderView.ResizeToContents)
        self.view.verticalHeader().setHighlightSections(False)
        self.view.horizontalHeader().setResizeMode(QHeaderView.Stretch)
        self.view.horizontalHeader().setHighlightSections(False)

        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self.view)
        self.setLayout(vbox)

    def clear(self):
        for i in range(6):
            self.model.setItem(i, 0, QStandardItem(''))

    def set_block_header(self, block):
        self.clear()
        if not isinstance(block, CBlockHeader):
            return
        items = map(lambda x: QStandardItem(x), [
                str(block.nVersion),
                b2lx(block.hashPrevBlock),
                b2lx(block.hashMerkleRoot),
                str(block.nTime),
                str(block.nBits),
                str(block.nNonce)
        ])
        rows = range(6)
        for row, item in zip(rows, items):
            self.model.setItem(row, 0, item)

class BlockTxsWidget(QWidget):
    """Model and View showing a block's transactions."""
    def __init__(self, parent=None):
        super(BlockTxsWidget, self).__init__(parent)
        self.model = QStandardItemModel()
        self.model.setColumnCount(1)

        self.view = QListView()
        self.view.setModel(self.model)

        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self.view)
        self.setLayout(vbox)

    def clear(self):
        self.model.setRowCount(0)

    def set_block(self, block):
        self.clear()
        if not isinstance(block, CBlock):
            return
        txids = [b2lx(i.GetHash()) for i in block.vtx]
        items = map(lambda x: QStandardItem(x), txids)
        for item in items:
            self.model.appendRow(item)

class BlockWidget(QWidget):
    """Displays the deserialized fields of a block."""
    def __init__(self, parent=None):
        super(BlockWidget, self).__init__(parent)
        self.header_widget = BlockHeaderWidget()
        self.header_widget.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.txs_widget = BlockTxsWidget()

        form = QFormLayout()
        form1 = QFormLayout()
        form2 = QFormLayout()
        for i in [form, form1, form2]:
            i.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form1.addRow('Header:', self.header_widget)
        form2.addRow('Transactions:', self.txs_widget)
        vbox = QHBoxLayout()
        vbox.addLayout(form1)
        vbox.addLayout(form2)
        form.addRow(vbox)

        self.setLayout(form)

    def clear(self):
        self.header_widget.clear()
        self.txs_widget.clear()

    def set_block(self, block_header, block):
        self.clear()
        self.header_widget.set_block_header(block_header)
        self.txs_widget.set_block(block)


class BlockAnalyzer(BaseDock):

    tool_name = 'Block Analyzer'
    description = 'Deserializes raw blocks.'
    is_large = True

    def init_data(self):
        self.block = None

    def create_layout(self):
        self.block_widget = BlockWidget()
        self.block_widget.header_widget.view.selectionModel().selectionChanged.connect(self.select_block_field)
        self.raw_block_edit = QPlainTextEdit()
        self.raw_block_edit.textChanged.connect(self.check_raw_block)

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
            self.handler.add_plugin_actions(self, menu, 'raw_transaction', raw_tx)

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

