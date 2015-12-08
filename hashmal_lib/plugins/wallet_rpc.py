import json
import urllib
import shlex
from collections import namedtuple

from PyQt4.QtGui import *
from PyQt4.QtCore import *

import hashmal_lib
from hashmal_lib.plugins import BaseDock, Plugin, Category
from hashmal_lib.gui_utils import floated_buttons
from hashmal_lib.items import *

RPCMethod = namedtuple('RPCMethod', ('method', 'get_result_type'))
"""RPC method.

An RPCMethod instance is not necessary for a given RPC method to be used.
This class is just for special cases.

get_result_type is a function that takes the parameters used in a call, and returns
the kind of data the result is. This way, context menus can have relevant actions (e.g. Deserialize transaction).
"""

known_methods = [
            RPCMethod('getblock', lambda params: RAW_BLOCK if len(params) > 1 and params[1] == False else None), # non-verbose
            RPCMethod('getrawtransaction', lambda params: RAW_TX if len(params) == 1 or (len(params) > 1 and params[1] == 0) else None) # non-verbose
]

known_methods_dict = dict((i.method, i) for i in known_methods)

def make_plugin():
    return Plugin(WalletRPC)

class RPCProfile(object):
    user = 'rpcUser'
    password = 'rpcPassword'
    host = 'localhost'
    port = '8332'
    def __init__(self, kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def as_dict(self):
        return {
            'user': self.user,
            'password': self.password,
            'host': self.host,
            'port': self.port
        }

    def as_url(self):
        return 'http://%s:%s@%s:%s/' % (
                    self.user,
                    self.password,
                    self.host,
                    self.port)


class WalletRPC(BaseDock):
    tool_name = 'Wallet RPC'
    description = 'Wallet RPC allows you to communicate with a full client to retrieve blockchain data.'
    category = Category.Data
    is_large = True
    def __init__(self, *args):
        super(WalletRPC, self).__init__(*args)
        self.augment('rpc_methods', {'known_rpc_methods': known_methods}, callback=self.on_methods_augmented)

    def init_data(self):
        self.profile = RPCProfile(self.options())

    def create_layout(self):
        vbox = QVBoxLayout()
        tabs = QTabWidget()
        tabs.addTab(self.create_rpc_tab(), 'RPC')
        tabs.addTab(self.create_settings_tab(), 'Settings')
        self.setFocusProxy(tabs)

        vbox.addWidget(tabs)
        return vbox

    def create_settings_tab(self):
        form = QFormLayout()

        self.user_edit = QLineEdit()
        self.user_edit.setText(self.profile.user)
        self.pass_edit = QLineEdit()
        self.pass_edit.setText(self.profile.password)
        self.host_edit = QLineEdit()
        self.host_edit.setText(self.profile.host)
        self.port_edit = QSpinBox()
        self.port_edit.setRange(0, 65535)
        self.port_edit.setValue(int(self.profile.port))

        for i in [self.user_edit, self.pass_edit, self.host_edit]:
            i.textChanged.connect(self.update_profile)
        self.port_edit.valueChanged.connect(self.update_profile)

        save_profile_button = QPushButton('Save')
        save_profile_button.clicked.connect(self.save_rpc_options)

        form.addRow('RPC Username:', self.user_edit)
        form.addRow('RPC Password:', self.pass_edit)
        form.addRow('RPC Host:', self.host_edit)
        form.addRow('RPC Port:', self.port_edit)
        form.addRow(floated_buttons([save_profile_button]))

        w = QWidget()
        w.setLayout(form)
        return w

    def create_rpc_tab(self):
        form = QFormLayout()

        self.method_edit = QLineEdit()
        self.method_edit.setWhatsThis('Enter the RPC method you want to use here. Some methods have auto-completion support, but any method that a node accepts can be entered here.')
        method_completer = QCompleter([i.method for i in known_methods])
        method_completer.setCompletionMode(QCompleter.InlineCompletion)
        self.method_edit.setCompleter(method_completer)

        self.params_edit = QLineEdit()
        param_desc = QLabel('Params syntax is the same as when using a wallet\'s command-line tool (e.g. bitcoin-cli) from a shell.')

        self.result_edit = QPlainTextEdit()
        self.result_edit.setWhatsThis('The response from a node is displayed here.')
        self.result_edit.setReadOnly(True)
        self.result_edit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.result_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.result_edit.customContextMenuRequested.connect(self.context_menu)

        do_button = QPushButton('&Download')
        do_button.clicked.connect(self.call_rpc)

        form.addRow('&Method:', self.method_edit)
        form.addRow(param_desc)
        form.addRow('&Params:', self.params_edit)
        form.addRow('Result:', self.result_edit)
        form.addRow(floated_buttons([do_button]))

        w = QWidget()
        w.setLayout(form)
        return w

    def supported_blockchain_data_types(self):
        """Get the types of data this plugin can retrieve."""
        return ['raw_transaction', 'raw_block', 'raw_header', 'block_hash']

    def retrieve_blockchain_data(self, data_type, identifier):
        """Signifies that this plugin is a data retriever."""
        params = [identifier]
        method_name = ''
        if data_type == 'raw_transaction':
            method_name = 'getrawtransaction'
            params.append(0)
        elif data_type in ('raw_block', 'raw_header'):
            method_name = 'getblock'
            params.append(False)
        elif data_type == 'block_hash':
            method_name = 'getblockhash'
        else:
            raise Exception('Unsupported data type "%s"' % data_type)


        result = None
        try:
            result = self.do_rpc(method_name, params)
            # Truncate block to header
            if data_type == 'raw_header':
                result = result[:160]
        except Exception as e:
            result = str(e)
        return result

    def call_rpc(self):
        """Call do_rpc() with text from widgets."""
        method_name = str(self.method_edit.text())
        method = known_methods_dict.get(method_name)

        params = shlex.split(str(self.params_edit.text()))
        # Parse JSON strings.
        for i, item in enumerate(params):
            try:
                as_json = json.loads(item)
                params[i] = as_json
            except Exception:
                pass

        result = None
        error = False
        try:
            result = self.do_rpc(method_name, params)
        except Exception as e:
            result = str(e)
            error = True
        self.result_edit.setProperty('data_type', None)

        if not error and method:
            self.result_edit.setProperty('data_type', method.get_result_type(params))

        self.result_edit.setPlainText(result)
        self.result_edit.setProperty('hasError', True if error else False)
        self.style().polish(self.result_edit)

    def do_rpc(self, method_name, params):
        """Call the full client.

        Returns:
            Result or raises an exception with an error.
        """
        postdata = json.dumps({'method': method_name, 'params': params, 'id': 'jsonrpc'})

        try:
            connection = urllib.urlopen(self.profile.as_url(), postdata)
            respdata = connection.read()
            connection.close()
        except Exception as e:
            return str(e)
        else:
            r = json.loads(respdata)
            result = r.get('result', '')
            error = r.get('error', '')
            if result:
                if type(result) not in (str, unicode):
                    result = json.dumps(result, indent=2)
                else:
                    result = result.strip('"')
            if error:
                raise Exception('%s\n(Error code: %s' % (error['message'].strip('"'), error['code']))
            return result

    def context_menu(self, position):
        menu = self.result_edit.createStandardContextMenu()

        data_type = str(self.result_edit.property('data_type').toString())
        if data_type:
            txt = str(self.result_edit.toPlainText())
            self.handler.add_plugin_actions(self, menu, data_type, txt)

        menu.exec_(self.result_edit.mapToGlobal(position))

    def update_profile(self):
        self.profile.user = str(self.user_edit.text())
        self.profile.password = str(self.pass_edit.text())
        self.profile.host = str(self.host_edit.text())
        self.profile.port = self.port_edit.value()

    def save_rpc_options(self):
        options = self.profile.as_dict()
        self.save_options(options)
        self.status_message('Saved RPC options.')

    def on_methods_augmented(self, data):
        self.method_edit.setCompleter()
        completer = QCompleter([i.method for i in data])
        completer.setCompletionMode(QCompleter.InlineCompletion)
        self.method_edit.setCompleter(completer)
