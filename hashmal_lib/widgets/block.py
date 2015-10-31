from PyQt4.QtGui import *
from PyQt4.QtCore import *

from bitcoin.core import CBlockHeader, CBlock, x, b2x, lx, b2lx

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

