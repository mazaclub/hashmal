from collections import OrderedDict
import requests

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from bitcoin.core import lx

from hashmal_lib.gui_utils import floated_buttons
from hashmal_lib.core import BlockHeader
from hashmal_lib.downloader import Downloader
from base import BaseDock, Plugin, Category

def make_plugin():
    return Plugin(Blockchain)

known_data_types = OrderedDict()
known_data_types.update({'Transaction': 'raw_tx'})
known_data_types.update({'Block Header': 'raw_header'})

class BlockExplorer(object):
    """Blockchain API base class.

    Attributes:
        name (str): Identifying name.
        domain (str): Base URL.
        routes (dict): URL routes for data (e.g. {'raw_tx': '/tx/'}).
        parsers (dict): Lambdas for parsing request responses.

    """
    name = ''
    domain = ''
    routes = None
    parsers = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if self.routes is None:
            self.routes = {}
        if self.parsers is None:
            self.parsers = {}

    def request(self, url):
        r = requests.get(url)
        r.raise_for_status()
        return r.json()

    def get_data(self, data_type, identifier):
        if not self.routes.get(data_type) or not self.parsers.get(data_type):
            return
        s = [self.domain]
        s.append(self.routes[data_type])
        s.append(identifier)
        s = ''.join(s)
        res = self.request(s)
        return self.parsers[data_type](res)

def header_from_insight_block(d):
    version = int(d['version'])
    prev_block = lx(d['previousblockhash'])
    merkle_root = lx(d['merkleroot'])
    time = int(d['time'])
    bits = int(d['bits'], 16)
    nonce = int(d['nonce'])
    return BlockHeader(version, prev_block, merkle_root, time, bits, nonce).as_hex()

insight_explorer = type('insight_explorer', (BlockExplorer,), dict(name='insight',domain='https://insight.bitpay.com',
                routes = {'raw_tx':'/api/rawtx/', 'raw_header':'/api/block/'},
                parsers = {'raw_tx':lambda d: d.get('rawtx'), 'raw_header': header_from_insight_block}))
known_explorers = {'Bitcoin': [insight_explorer()]}

class BlockchainDownloader(Downloader):
    finished = pyqtSignal(str, str, str, str, name='finished')
    def __init__(self, explorer, data_type, identifier):
        super(BlockchainDownloader, self).__init__()
        if data_type == 'raw_transaction':
            data_type = 'raw_tx'
        self.explorer = explorer
        self.data_type = data_type
        self.identifier = identifier

    @pyqtSlot()
    def download(self):
        raw = ''
        error = ''
        try:
            raw = self.explorer.get_data(self.data_type, self.identifier)
        except Exception as e:
            error = '{}: {}'.format(str(e.__class__.__name__), str(e))

        if not raw:
            raw = ''
        self.finished.emit(self.data_type, self.identifier, raw, error)

class Blockchain(BaseDock):

    tool_name = 'Blockchain'
    description = 'Blockchain allows you to download data from block explorers.'
    is_large = True
    category = Category.Data

    def __init__(self, handler):
        super(Blockchain, self).__init__(handler)
        self.augment('block_explorers', {'known_explorers': self.known_explorers}, callback=self.on_explorers_augmented)
        self.data_group.button(0).setChecked(True)

    def init_data(self):
        self.known_explorers = OrderedDict(known_explorers)
        chain = self.option('chain', 'Bitcoin')
        explorer_name = self.option('explorer', 'insight')
        explorer = (dict((i.name, i) for i in self.known_explorers.get(chain, []))).get(explorer_name)
        if not explorer:
            chain = 'Bitcoin'
            explorer = self.known_explorers['Bitcoin'][0]
        self.chain = chain
        self.explorer = explorer
        # Cache of recently downloaded txs
        self.recent_data = OrderedDict()

    def create_layout(self):
        """Two tabs:

        Download: Interface for actually downloading data.
        Block Explorer: Settings for where to get data.
        """
        vbox = QVBoxLayout()

        tabs = QTabWidget()
        tabs.addTab(self.create_download_tab(), 'Download')
        tabs.addTab(self.create_explorer_tab(), 'Block Explorer')
        tabs.addTab(self.create_options_tab(), 'Settings')
        self.setFocusProxy(tabs)

        vbox.addWidget(tabs)
        return vbox

    def create_explorer_tab(self):
        form = QFormLayout()

        set_default_button = QPushButton('Save as default')
        set_default_button.setToolTip('Save this block explorer as default')

        def set_default():
            chain = str(chain_combo.currentText())
            txt = str(explorer_combo.currentText())
            self.set_option('chain', chain)
            self.set_option('explorer', txt)
        set_default_button.clicked.connect(set_default)


        self.chain_combo = chain_combo = QComboBox()
        chain_combo.setWhatsThis('Use this to select which cryptocurrency\'s block explorers you want to use.')
        chain_combo.addItems(self.known_explorers.keys())
        chain_combo.setCurrentIndex(self.known_explorers.keys().index(self.chain))

        chain_combo.currentIndexChanged.connect(self.on_chain_combo_changed)

        self.explorer_combo = explorer_combo = QComboBox()
        explorer_combo.setWhatsThis('Use this to select which block explorer you want to use.')
        explorer_names_list = [i.name for i in self.known_explorers[self.chain]]
        explorer_combo.addItems(explorer_names_list)
        explorer_combo.setCurrentIndex(explorer_names_list.index(self.explorer.name))

        explorer_combo.currentIndexChanged.connect(self.on_explorer_combo_changed)

        form.addRow('Chain:', chain_combo)
        form.addRow('Explorer:', explorer_combo)
        form.addRow(floated_buttons([set_default_button]))

        w = QWidget()
        w.setLayout(form)
        return w

    def create_options_tab(self):
        form = QFormLayout()

        cache_size = int(self.option('cache_size', 25))

        cache_size_box = QSpinBox()
        cache_size_box.setWhatsThis('Use this to change the number of recent downloaded data items that are kept in memory for quicker access to them.')
        cache_size_box.setRange(0, 100)
        cache_size_box.setValue(cache_size)
        cache_size_box.setToolTip('Number of recent raw transactions/blocks to keep in memory')

        def change_cache_size():
            new_size = cache_size_box.value()
            self.set_option('cache_size', new_size)
        cache_size_box.valueChanged.connect(change_cache_size)

        form.addRow('Transaction cache size:', cache_size_box)

        w = QWidget()
        w.setLayout(form)
        return w


    def create_download_tab(self):
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapAllRows)

        self.data_group = QButtonGroup()
        self.data_box = QGroupBox()
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0,0,0,6)
        for i, data_type in enumerate(known_data_types.keys()):
            btn = QRadioButton(data_type)
            self.data_group.addButton(btn, i)
            hbox.addWidget(btn)
        hbox.addStretch(1)
        self.data_box.setLayout(hbox)

        self.id_edit = QLineEdit()
        self.id_edit.setWhatsThis('Enter an identifier here, such as a transaction ID or block hash.')
        self.raw_edit = QTextEdit()
        self.raw_edit.setReadOnly(True)
        self.raw_edit.setWhatsThis('The result of a download is displayed here.')
        self.raw_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.raw_edit.customContextMenuRequested.connect(self.context_menu)
        self.download_button = QPushButton('&Download')
        self.download_button.clicked.connect(self.do_download)
        self.download_button.setEnabled(False)

        def validate_identifier(txt):
            valid = len(str(txt)) == 64
            self.download_button.setEnabled(valid)
        self.id_edit.textChanged.connect(validate_identifier)

        form.addRow(self.data_box)
        form.addRow('Identifier (Transaction ID or Block Hash):', self.id_edit)
        form.addRow(floated_buttons([self.download_button]))
        form.addRow('Result:', self.raw_edit)

        self.data_group.buttonClicked.connect(lambda: self.raw_edit.clear())

        w = QWidget()
        w.setLayout(form)
        return w

    def context_menu(self, position):
        menu = self.raw_edit.createStandardContextMenu(position)

        txt = str(self.raw_edit.toPlainText())
        if txt:
            self.handler.add_plugin_actions(self, menu, txt)

        menu.exec_(self.raw_edit.viewport().mapToGlobal(position))

    def update_cache(self, identifier, raw):
        self.recent_data[identifier] = raw
        while len(self.recent_data.keys()) > int(self.option('cache_size', 25)):
            self.recent_data.popitem(False)

    def do_download(self):
        self.download_button.setEnabled(False)
        identifier = str(self.id_edit.text())
        data_type = known_data_types[str(self.data_group.checkedButton().text())]

        cached_data = self.recent_data.get(identifier)
        if cached_data:
            self.set_result(data_type, identifier, cached_data, '')
            return

        self.raw_edit.setText('Downloading...')

        downloader = BlockchainDownloader(self.explorer, data_type, identifier)
        self.download_async(downloader, self.set_result)

    def set_result(self, data_type, identifier, raw, error):
        """Set result of tx downloader thread."""
        if error:
            self.error(error)
            self.raw_edit.clear()
        elif not raw:
            self.error('Unknown error. Failed to retrieve transaction.')
            self.raw_edit.clear()
        else:
            self.raw_edit.setText(raw)
            self.update_cache(identifier, raw)
            # Get human-friendly name for data type.
            word = 'data'
            for k, v in known_data_types.items():
                if v == data_type:
                    word = k
            self.info('Downloaded %s %s.' % (word.lower(), identifier))

        self.download_button.setEnabled(True)

    def supported_blockchain_data_types(self):
        """Get the types of data this plugin can retrieve."""
        return ['raw_transaction', 'raw_header']

    def retrieve_blockchain_data(self, data_type, identifier, callback=None):
        """Signifies that this plugin is a data retriever."""
        if callback:
            # Callback with the data as an argument.
            cb = lambda datatype, ident, raw, err: callback(str(raw))
            downloader = BlockchainDownloader(self.explorer, data_type, identifier)
            self.download_async(downloader, cb)
        elif data_type == 'raw_transaction':
            return self.download_raw_tx(identifier)
        elif data_type == 'raw_header':
            return self.download_block_header(identifier)
        else:
            raise Exception('Unsupported data type "%s"' % data_type)

    def download_raw_tx(self, txid):
        """This is for use by other widgets."""
        if self.recent_data.get(txid):
            return self.recent_data.get(txid)

        rawtx = self.explorer.get_data('raw_tx', txid)
        if rawtx:
            self.update_cache(txid, rawtx)
        return rawtx

    def download_block_header(self, blockhash):
        """This is for use by other widgets."""
        if self.recent_data.get(blockhash):
            return self.recent_data.get(blockhash)

        rawheader = self.explorer.get_data('raw_header', blockhash)
        if rawheader:
            self.update_cache(blockhash, rawheader)
        return rawheader

    def on_explorer_combo_changed(self, idx):
        new_explorer = self.known_explorers[self.chain][idx]
        self.set_explorer(new_explorer)

    def set_explorer(self, new_explorer):
        """Set the block explorer."""
        self.explorer = new_explorer

    def on_chain_combo_changed(self, idx):
        new_chain = self.known_explorers.keys()[idx]
        self.set_chain(new_chain)

    def set_chain(self, new_chain):
        """Set the current chain and update the explorer combo box."""
        self.chain = new_chain
        self.explorer_combo.currentIndexChanged.disconnect(self.on_explorer_combo_changed)
        self.explorer_combo.clear()
        explorer_names_list = [i.name for i in self.known_explorers[self.chain]]
        self.explorer_combo.addItems(explorer_names_list)
        self.explorer_combo.currentIndexChanged.connect(self.on_explorer_combo_changed)

        index = 0
        if self.explorer.name in explorer_names_list:
            index = explorer_names_list.index(self.explorer.name)
        self.explorer_combo.setCurrentIndex(index)
        self.explorer_combo.currentIndexChanged.emit(index)

    def on_explorers_augmented(self, arg):
        """Update combo boxes after augmentation."""
        chain = self.option('chain', 'Bitcoin')
        explorer_name = self.option('explorer', 'insight')

        explorer = (dict((i.name, i) for i in self.known_explorers.get(chain, []))).get(explorer_name)
        if not explorer:
            chain = 'Bitcoin'
            explorer = self.known_explorers['Bitcoin'][0]
        self.chain = chain
        self.explorer = explorer

        self.chain_combo.currentIndexChanged.disconnect(self.on_chain_combo_changed)
        self.chain_combo.clear()
        self.chain_combo.addItems(self.known_explorers.keys())
        self.chain_combo.setCurrentIndex(self.known_explorers.keys().index(self.chain))
        self.chain_combo.currentIndexChanged.connect(self.on_chain_combo_changed)
        self.set_chain(self.chain)
