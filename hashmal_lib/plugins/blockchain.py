from collections import namedtuple, OrderedDict
import requests

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from hashmal_lib.gui_utils import floated_buttons
from base import BaseDock, Plugin

def make_plugin():
    return Plugin(Blockchain)

class BlockExplorer(object):
    """Blockchain API base class."""
    name = ''
    domain = ''
    raw_tx_route = None

    parse_raw_tx_lambda = None
    """If parse_raw_tx_lambda is not None, it will be used
    instead of parse_raw_tx().
    """

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def request(self, url):
        r = requests.get(url)
        r.raise_for_status()
        return r.json()

    def get_raw_tx(self, txid):
        """Download a raw transaction."""
        s = [self.domain]
        s.append(self.raw_tx_route)
        s.append(txid)
        s = ''.join(s)
        res = self.request(s)
        # If present, use the lambda.
        if self.parse_raw_tx_lambda is not None:
            return self.parse_raw_tx_lambda(res)
        return self.parse_raw_tx(res)

    def parse_raw_tx(self, res):
        """Abstract method.

        This does not need to be implemented in a subclass if the
        'parse_raw_tx_lambda' argument is passed to their constructor.

        Args:
            res: Response from raw_tx_route request.

        Returns:
            Hex-encoded raw transaction.
        """
        pass

insight_explorer = BlockExplorer(name='insight',domain='https://insight.bitpay.com',
                raw_tx_route='/api/rawtx/', parse_raw_tx_lambda = lambda d: d.get('rawtx'))

known_explorers = {'Bitcoin': [insight_explorer]}

class Downloader(QObject):
    """Asynchronous downloading via QThreads."""
    start = pyqtSignal()
    finished = pyqtSignal(str, str, str, name='finished')
    def __init__(self, explorer, txid):
        super(Downloader, self).__init__()
        self.explorer = explorer
        self.txid = txid
        self.start.connect(self.download)

    @pyqtSlot()
    def download(self):
        raw_tx = ''
        error = ''
        try:
            raw_tx = self.explorer.get_raw_tx(self.txid)
        except Exception as e:
            error = '{}: {}'.format(str(e.__class__.__name__), str(e))
        self.finished.emit(self.txid, raw_tx, error)

class Blockchain(BaseDock):

    tool_name = 'Blockchain'
    description = 'Blockchain allows you to download data from block explorers.'
    is_large = True

    def __init__(self, handler):
        super(Blockchain, self).__init__(handler)
        self.augment('block_explorers', {'known_explorers': self.known_explorers}, callback=self.on_explorers_augmented)

    def init_data(self):
        self.known_explorers = OrderedDict(known_explorers)
        config_explorer = self.config.get_option('block_explorer', 'Bitcoin:insight')
        chain, explorer_name = config_explorer.split(':')
        explorer = (dict((i.name, i) for i in self.known_explorers.get(chain, []))).get(explorer_name)
        if not explorer:
            chain = 'Bitcoin'
            explorer = self.known_explorers['Bitcoin'][0]
        self.chain = chain
        self.explorer = explorer
        # Cache of recently downloaded txs
        self.recent_transactions = OrderedDict()

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

        vbox.addWidget(tabs)
        return vbox

    def create_explorer_tab(self):
        form = QFormLayout()

        set_default_button = QPushButton('Save as default')
        set_default_button.setToolTip('Save this block explorer as default')

        def set_default():
            chain = str(chain_combo.currentText())
            txt = str(explorer_combo.currentText())
            self.config.set_option('block_explorer', ':'.join([chain, txt]))
        set_default_button.clicked.connect(set_default)


        self.chain_combo = chain_combo = QComboBox()
        chain_combo.addItems(self.known_explorers.keys())
        chain_combo.setCurrentIndex(self.known_explorers.keys().index(self.chain))

        chain_combo.currentIndexChanged.connect(self.on_chain_combo_changed)

        self.explorer_combo = explorer_combo = QComboBox()
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

        cache_size = int(self.config.get_option('blockchain_cache_size', 25))

        cache_size_box = QSpinBox()
        cache_size_box.setRange(0, 100)
        cache_size_box.setValue(cache_size)
        cache_size_box.setToolTip('Number of recent raw transactions to keep in memory')

        def change_cache_size():
            new_size = cache_size_box.value()
            self.config.set_option('blockchain_cache_size', new_size)
        cache_size_box.valueChanged.connect(change_cache_size)

        form.addRow('Transaction cache size:', cache_size_box)

        w = QWidget()
        w.setLayout(form)
        return w


    def create_download_tab(self):
        form = QFormLayout()
        
        self.tx_id_edit = QLineEdit()
        self.raw_tx_edit = QTextEdit()
        self.raw_tx_edit.setReadOnly(True)
        self.raw_tx_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.raw_tx_edit.customContextMenuRequested.connect(self.context_menu)
        self.download_button = QPushButton('Download')
        self.download_button.clicked.connect(self.do_download)
        self.download_button.setEnabled(False)

        def validate_txid(txt):
            valid = len(str(txt)) == 64
            self.download_button.setEnabled(valid)
        self.tx_id_edit.textChanged.connect(validate_txid)

        form.addRow('Tx ID:', self.tx_id_edit)
        form.addRow(floated_buttons([self.download_button]))
        form.addRow('Raw Tx:', self.raw_tx_edit)

        w = QWidget()
        w.setLayout(form)
        return w

    def context_menu(self, position):
        menu = self.raw_tx_edit.createStandardContextMenu(position)

        txt = str(self.raw_tx_edit.toPlainText())
        if txt:
            self.handler.add_plugin_actions(self, menu, 'raw_transaction', txt)

        menu.exec_(self.raw_tx_edit.viewport().mapToGlobal(position))

    def update_cache(self, txid, rawtx):
        self.recent_transactions[txid] = rawtx
        while len(self.recent_transactions.keys()) > int(self.config.get_option('blockchain_cache_size', 25)):
            self.recent_transactions.popitem(False)

    def make_downloader(self, txid):
        self.downloader_thread = QThread()
        self.downloader = Downloader(self.explorer, txid)
        self.downloader.moveToThread(self.downloader_thread)
        self.downloader.finished.connect(self.downloader_thread.quit)

    def do_download(self):
        self.download_button.setEnabled(False)
        txid = str(self.tx_id_edit.text())

        cached_tx = self.recent_transactions.get(txid)
        if cached_tx:
            self.set_result(txid, cached_tx, '')
            return

        self.raw_tx_edit.setText('Downloading...')
        self.make_downloader(txid)
        self.downloader.finished.connect(self.set_result)
        self.downloader_thread.start()
        self.downloader.start.emit()

    def set_result(self, txid, rawtx, error):
        """Set result of tx downloader thread."""
        if error:
            self.status_message(error, True)
            self.raw_tx_edit.clear()
        elif not rawtx:
            self.status_message('Unknown error. Failed to retrieve transaction.', True)
            self.raw_tx_edit.clear()
        else:
            self.raw_tx_edit.setText(rawtx)
            self.update_cache(txid, rawtx)
            self.status_message('Downloaded transaction %s' % txid)

        self.download_button.setEnabled(True)

    def download_raw_tx(self, txid):
        """This is for use by other widgets."""
        if self.recent_transactions.get(txid):
            return self.recent_transactions.get(txid)

        rawtx = self.explorer.get_raw_tx(txid)
        if rawtx:
            self.update_cache(txid, rawtx)
        return rawtx

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
        config_explorer = self.config.get_option('block_explorer', 'Bitcoin:insight')
        chain, explorer_name = config_explorer.split(':')

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
