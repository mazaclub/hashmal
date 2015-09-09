from collections import namedtuple
import requests

from PyQt4.QtGui import *
from PyQt4 import QtCore

from hashmal_lib.gui_utils import floated_buttons
from base import BaseDock

ApiType = namedtuple('ApiType', ('name', 'default_domain', 'rawtx_route', 'rawtx_parse'))
"""Structure of a blockchain API."""

insight_api = ApiType('insight', 'https://insight.bitpay.com', '/api/rawtx/', lambda d: d.get('rawtx'))
known_api_types = [insight_api]

class BApi(object):
    """Blockchain API."""
    def __init__(self, api_type, domain=''):
        self.api_type = api_type
        self.domain = domain

    def request(self, url):
        r = requests.get(url)
        r.raise_for_status()
        return r.json()

    def get_raw_tx(self, txid):
        """Download a raw transaction."""
        s = [self.domain]
        s.append(self.api_type.rawtx_route)
        s.append(txid)
        s = ''.join(s)
        d = self.request(s)
        return self.api_type.rawtx_parse(d)

    def api_name(self):
        return self.api_type.name

class Blockchain(BaseDock):

    def init_metadata(self):
        self.tool_name = 'Blockchain'
        self.description = 'Blockchain allows you to download data from block explorers.'

    def init_data(self):
        config_apis = self.config.get_option('blockchain_apis', {})
        if not config_apis:
            config_apis['insight'] = 'https://insight.bitpay.com'
        self.config.set_option('blockchain_apis', config_apis)

        config_api_type = self.config.get_option('blockchain_api', 'insight')
        for i in known_api_types:
            if i.name == config_api_type:
                api_type = i

        domain = config_apis.get(config_api_type, api_type.default_domain)
        self.api = BApi(api_type, domain)

    def create_layout(self):
        """Two tabs:

        Download: Interface for actually downloading data.
        API Settings: Settings for where to get data.
        """
        vbox = QVBoxLayout()

        tabs = QTabWidget()
        tabs.addTab(self.create_download_tab(), 'Download')
        tabs.addTab(self.create_api_tab(), 'API Settings')

        vbox.addWidget(tabs)
        return vbox

    def create_api_tab(self):
        form = QFormLayout()

        config_apis = self.config.get_option('blockchain_apis')
        config_domain = config_apis.get(self.api.api_name(), self.api.api_type.default_domain)

        api_domain_edit = QLineEdit()
        api_domain_edit.setText(config_domain)
        reset_domain_button = QPushButton('Reset to Default')
        reset_domain_button.setToolTip('Reset domain to the API\'s default')
        save_domain_button = QPushButton('Save Domain')
        save_domain_button.setToolTip('Save domain to use with this API')

        api_type_combo = QComboBox()
        api_type_combo.addItems([i.name for i in known_api_types])

        def change_api_type(idx):
            new_api = known_api_types[idx]
            self.set_api_type(new_api)
            api_domain_edit.setText(self.api.domain)
        api_type_combo.currentIndexChanged.connect(change_api_type)

        def change_api_domain():
            txt = str(api_domain_edit.text())
            if not txt: return
            self.set_api_domain(txt)

        def reset_api_domain():
            default = self.api.api_type.default_domain
            api_domain_edit.setText(default)
            change_api_domain()

        reset_domain_button.clicked.connect(reset_api_domain)
        save_domain_button.clicked.connect(change_api_domain)

        form.addRow('API:', api_type_combo)
        form.addRow('Domain:', api_domain_edit)
        form.addRow(floated_buttons([reset_domain_button, save_domain_button]))

        w = QWidget()
        w.setLayout(form)
        return w

    def create_download_tab(self):
        form = QFormLayout()
        
        self.tx_id_edit = QLineEdit()
        self.raw_tx_edit = QTextEdit()
        self.raw_tx_edit.setReadOnly(True)
        self.raw_tx_edit.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.raw_tx_edit.customContextMenuRequested.connect(self.context_menu)
        self.download_button = QPushButton('Download')
        self.download_button.clicked.connect(self.do_download)

        form.addRow('Tx ID:', self.tx_id_edit)
        form.addRow(floated_buttons([self.download_button]))
        form.addRow('Raw Tx:', self.raw_tx_edit)

        w = QWidget()
        w.setLayout(form)
        return w

    def context_menu(self, position):
        menu = QMenu()
        def set_as_spending():
            self.handler.set_stack_spending_tx(str(self.raw_tx_edit.toPlainText()))
        def deserialize():
            self.handler.deserialize_tx(str(self.raw_tx_edit.toPlainText()))
        text_exists = True if self.raw_tx_edit.toPlainText() else False
        menu.addAction('Deserialize', deserialize).setEnabled(text_exists)
        menu.addAction('Set as transaction in Stack Evaluator', set_as_spending).setEnabled(text_exists)
        menu.exec_(self.raw_tx_edit.viewport().mapToGlobal(position))

    def do_download(self):
        self.download_button.setEnabled(False)
        txid = str(self.tx_id_edit.text())
        self.raw_tx_edit.setText('Downloading...')
        try:
            raw = self.api.get_raw_tx(txid)
        except Exception as e:
            self.raw_tx_edit.clear()
            self.status_message(str(e), True)
            return
        else:
            self.raw_tx_edit.setText(raw)
            self.status_message('Downloaded transaction %s' % txid)
        finally:
            self.download_button.setEnabled(True)

    def download_raw_tx(txid):
        """This is for use by other widgets."""
        return self.api.get_raw_tx(txid)

    def set_api_type(self, api):
        """Set the base API type and save."""
        self.api.api_type = new_api
        # save change
        self.config.set_option('blockchain_api', self.api.api_name())
        # update domain
        domains = self.config.get_option('blockchain_apis', {})
        self.api.domain = domains.get(self.api.api_name(), api.default_domain)

    def set_api_domain(self, domain):
        """Set the domain for an API type and save."""
        self.api.domain = domain
        # save change
        config_apis = self.config.get_option('blockchain_apis', {})
        config_apis[self.api.api_name()] = domain
        self.config.set_option('blockchain_apis', config_apis)
