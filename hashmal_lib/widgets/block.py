from PyQt4.QtGui import *
from PyQt4.QtCore import *

from bitcoin.core import CBlockHeader, b2x, b2lx

from hashmal_lib.gui_utils import monospace_font
from hashmal_lib.core import BlockHeader, Block

class BlockHeaderModel(QAbstractTableModel):
    """Model of a block header."""
    def __init__(self, header=None, parent=None):
        super(BlockHeaderModel, self).__init__(parent)
        self.vertical_header = []
        self.set_header(header)

    def rowCount(self, parent=QModelIndex()):
        return len(self.header.fields) if self.header else len(self.vertical_header)

    def columnCount(self, parent=QModelIndex()):
        return 1

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role not in [Qt.DisplayRole, Qt.EditRole]: return None
        if orientation != Qt.Vertical or section >= len(self.vertical_header): return None
        return self.vertical_header[section]

    def setHeaderData(self, section, orientation, value, role=Qt.EditRole):
        if orientation != Qt.Vertical: return False
        try:
            self.vertical_header.insert(section, value)
        except Exception:
            return False
        self.headerDataChanged.emit(orientation, 0, section)
        return True

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not self.header: return None
        if role == Qt.FontRole:
            return monospace_font
        if role not in [Qt.DisplayRole, Qt.ToolTipRole, Qt.EditRole]:
            return None

        field_name = self.header.fields[index.row()][0]
        field = self.header.fields[index.row()]
        data = getattr(self.header, field[0])
        if field[1] == 'bytes':
            data = b2lx(data)
        else:
            data = str(data)
        return data

    def set_header(self, header):
        """Reset the model to reflect blk."""
        if header.__class__ not in [BlockHeader, CBlockHeader] or header is None:
            return self.clear()
        self.beginResetModel()
        self.header = BlockHeader.from_header(header)

        self.vertical_header = []
        field_names = [i[0] for i in self.header.fields]
        for i, field in enumerate(self.header.fields):
            self.setHeaderData(i, Qt.Vertical, field[0])
        self.endResetModel()

    def clear(self):
        self.beginResetModel()
        self.header = None
        self.endResetModel()

class BlockHeaderWidget(QWidget):
    """Model and View showing a block header."""
    def __init__(self, parent=None):
        super(BlockHeaderWidget, self).__init__(parent)
        self.model = BlockHeaderModel()

        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.verticalHeader().setResizeMode(QHeaderView.ResizeToContents)
        self.view.verticalHeader().setHighlightSections(False)
        self.view.horizontalHeader().setResizeMode(QHeaderView.Stretch)
        self.view.horizontalHeader().setHighlightSections(False)
        self.view.horizontalHeader().setVisible(False)

        self.model.modelReset.connect(lambda: self.view.verticalHeader().resizeSections(QHeaderView.ResizeToContents))
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.context_menu)

        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self.view)
        self.setLayout(vbox)

    def context_menu(self, pos):
        if len(self.view.selectedIndexes()) == 0:
            return
        menu = QMenu()
        copy = menu.addMenu('Copy')
        copy.addAction('Serialized header', self.copy_serialized)

        menu.exec_(self.view.viewport().mapToGlobal(pos))

    def copy_serialized(self):
        data = b2x(self.model.header.serialize())
        QApplication.clipboard().setText(data)

    def clear(self):
        self.model.clear()

    def set_block_header(self, block):
        self.model.set_header(block)

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
        self.model.clear()

    def set_block(self, block):
        self.clear()
        if not isinstance(block, Block):
            return
        txids = [b2lx(i.GetHash()) for i in block.vtx]
        items = map(lambda x: QStandardItem(x), txids)
        for item in items:
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.model.appendRow(item)

class BlockWidget(QWidget):
    """Displays the deserialized fields of a block."""
    def __init__(self, parent=None):
        super(BlockWidget, self).__init__(parent)
        self.header_widget = BlockHeaderWidget()
        self.header_widget.view.setWhatsThis('The header of the block is displayed here.')
        self.header_widget.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.txs_widget = BlockTxsWidget()
        self.txs_widget.view.setWhatsThis('The transactions in the block are displayed here.\n\nRight-click a transaction ID to access the transaction it represents.')

        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)

        form = QFormLayout()
        form.setContentsMargins(0,0,0,0)
        form1 = QFormLayout()
        form2 = QFormLayout()
        for i in [form, form1, form2]:
            i.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form1.addRow('Header:', self.header_widget)
        form1.setContentsMargins(0,0,5,0)
        form2.addRow('Transactions:', self.txs_widget)
        form2.setContentsMargins(5,0,0,0)
        w = QWidget()
        w.setLayout(form1)
        splitter.addWidget(w)
        w = QWidget()
        w.setLayout(form2)
        splitter.addWidget(w)

        hbox = QHBoxLayout()
        hbox.addWidget(splitter)
        form.addRow(hbox)

        self.setLayout(form)

    def clear(self):
        self.header_widget.clear()
        self.txs_widget.clear()

    def set_block(self, block_header, block):
        self.clear()
        self.header_widget.set_block_header(block_header)
        self.txs_widget.set_block(block)

