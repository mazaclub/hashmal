
from collections import OrderedDict

from PyQt4.QtGui import *
from PyQt4 import QtCore

from base import BaseDock

class Variables(BaseDock):
    def __init__(self, handler):
        super(Variables, self).__init__(handler)

    def init_metadata(self):
        self.tool_name = 'Variables'
        self.description = 'Variables records data for later access.'

    def init_data(self):
        self.data = OrderedDict()

    def create_layout(self):
        vbox = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels([ 'Key', 'Value' ])
        self.table.horizontalHeader().setResizeMode(QHeaderView.Stretch)

        vbox.addWidget(self.table)

        add_var_hbox = QHBoxLayout()
        self.new_var_key = QLineEdit()
        self.new_var_value = QLineEdit()
        add_var_hbox.addWidget(self.new_var_key)
        add_var_hbox.addWidget(QLabel(' = '))
        add_var_hbox.addWidget(self.new_var_value)
        add_var_btn = QPushButton('Add')
        add_var_btn.clicked.connect(self.add_new_var)
        add_var_hbox.addWidget(add_var_btn)

        vbox.addLayout(add_var_hbox)
        return vbox

    def refresh_data(self):
        self.table.clearContents()
        self.table.setRowCount(0)
        for k, v in self.data.items():
            self.table.insertRow(0)
            item_key = QTableWidgetItem(k)
            item_value = QTableWidgetItem(str(v))
            self.table.setItem(0, 0, item_key)
            self.table.setItem(0, 1, item_value)

    def add_new_var(self):
        k = str(self.new_var_key.text())
        v = str(self.new_var_value.text())
        if k == '' or v == '':
            return
        self.data[k] = v
        self.needsUpdate.emit()
