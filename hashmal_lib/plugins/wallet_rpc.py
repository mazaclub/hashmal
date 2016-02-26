import json
import urllib
import shlex

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from hashmal_lib.plugins import BaseDock, Plugin, Category
from hashmal_lib.gui_utils import floated_buttons
from hashmal_lib.downloader import Downloader

known_methods = [
    'getblock',
    'getrawtransaction'
]

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

class RPCProfileModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super(RPCProfileModel, self).__init__(parent)
        self.profile = None

    def clear(self):
        self.set_profile(None)

    def set_profile(self, profile):
        self.beginResetModel()
        self.profile = profile
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 1

    def columnCount(self, parent=QModelIndex()):
        return 4

    def data(self, index, role = Qt.DisplayRole):
        if not index.isValid() or not self.profile:
            return None

        data = None
        c = index.column()
        if c == 0:
            if role in [Qt.DisplayRole, Qt.ToolTipRole, Qt.EditRole]:
                data = self.profile.user
        elif c == 1:
            if role in [Qt.DisplayRole, Qt.ToolTipRole, Qt.EditRole]:
                data = self.profile.password
        elif c == 2:
            if role in [Qt.DisplayRole, Qt.ToolTipRole, Qt.EditRole]:
                data = self.profile.host
        elif c == 3:
            if role in [Qt.DisplayRole, Qt.ToolTipRole, Qt.EditRole]:
                data = self.profile.port

        return data

    def setData(self, index, value, role = Qt.EditRole):
        if not index.isValid() or not self.profile:
            return False

        c = index.column()
        val = str(value.toString()) if type(value) is QVariant else value
        if c == 0:
            self.profile.user = val
            return True
        elif c == 1:
            self.profile.password = val
            return True
        elif c == 2:
            self.profile.host = val
            return True
        elif c == 3:
            self.profile.port = val
            return True
        return False

class RPCDownloader(Downloader):
    finished = pyqtSignal(str, str, str, name='finished')
    def __init__(self, profile, method_name, params):
        super(RPCDownloader, self).__init__()
        self.profile = profile
        self.method_name = method_name
        self.params = params

    @pyqtSlot()
    def download(self):
        postdata = json.dumps({'method': self.method_name, 'params': self.params, 'id': 'jsonrpc'})
        result = ''
        error = ''

        try:
            connection = urllib.urlopen(self.profile.as_url(), postdata)
            respdata = connection.read()
            connection.close()
        except Exception as e:
            error = str(e)
        else:
            r = json.loads(respdata)
            res = r.get('result', '')
            err = r.get('error', '')
            if res:
                if type(res) not in (str, unicode):
                    res = json.dumps(res, indent=2)
                else:
                    res = res.strip('"')
                result = res
            if err:
                if type(err) not in (str, unicode):
                    err = json.dumps(err, indent=2)
                else:
                    err = err.strip('"')
                error = err

        for i in [result, error]:
            if i is None: i = ''
        self.finished.emit(self.method_name, result, error)


class WalletRPC(BaseDock):
    tool_name = 'Wallet RPC'
    description = 'Wallet RPC allows you to communicate with a full client to retrieve blockchain data.'
    category = Category.Data
    is_large = True
    def __init__(self, *args):
        super(WalletRPC, self).__init__(*args)
        self.augment('rpc_methods', None, callback=self.on_methods_augmented)

    def set_profile(self, profile):
        self.profile = profile
        self.profile_model.set_profile(self.profile)
        self.mapper.toFirst()

    def load_profile(self, name):
        profiles = self.options().get('profiles', {})
        if not profiles.get(name):
            self.error('Cannot load nonexistent profile "%s".' % name)
            return
        profile = RPCProfile(profiles.get(name, {}))
        self.set_profile(profile)
        self.debug('Loaded RPC profile "%s".' % name)

    def save_profile(self, name):
        options = self.options()
        profiles = options.get('profiles', {})
        profiles[name] = self.profile.as_dict()
        options['profiles'] = profiles
        self.save_options(options)
        self.load_profile_names()
        self.debug('Saved RPC profile "%s".' % name)

    def delete_profile(self, name):
        if name == 'default':
            self.error('Cannot delete default profile.')
            return
        options = self.options()
        profiles = options.get('profiles', {})
        if profiles.get(name):
            del profiles[name]
            options['profiles'] = profiles
            self.save_options(options)
            self.name_combo.setCurrentIndex(self.profile_names.index('default'))
            self.load_profile_names()
            self.debug('Deleted RPC profile "%s".' % name)
        else:
            self.error('Cannot delete nonexistent profile "%s".')

    def load_profile_names(self):
        profiles = self.options().get('profiles', {})
        self.profile_names = profiles.keys()
        current_profile = str(self.name_combo.currentText())
        self.name_combo.clear()
        self.name_combo.addItems(self.profile_names)
        # Setting the current index also has the effect of re-loading the selected profile.
        self.name_combo.setCurrentIndex(self.profile_names.index(current_profile))

    def init_data(self):
        profiles = self.options().get('profiles', {})
        self.profile = RPCProfile(profiles.get('default', {}))
        self.profile_names = profiles.keys()
        # Save default profile if no profiles exist.
        if not self.profile_names:
            self.profile_names = ['default']
            options = self.options()
            options['profiles'] = {'default': self.profile.as_dict()}
            self.save_options(options)

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
        self.profile_model = RPCProfileModel()
        self.profile_model.set_profile(self.profile)

        # Profiles
        self.name_combo = QComboBox()
        self.name_combo.addItems(self.profile_names)
        self.name_combo.setEditable(True)
        self.name_combo.setCurrentIndex(self.profile_names.index('default'))

        self.save_button = QPushButton('Save')
        self.save_button.clicked.connect(lambda: self.save_profile(str(self.name_combo.currentText())))
        self.delete_button = QPushButton('Delete')
        self.delete_button.clicked.connect(lambda: self.delete_profile(str(self.name_combo.currentText())))
        hbox = QHBoxLayout()
        hbox.addWidget(self.name_combo, stretch=1)
        for i in [self.save_button, self.delete_button]:
            hbox.addWidget(i)
        form.addRow(hbox)

        # Profile variables
        self.user_edit = QLineEdit()
        self.user_edit.setText(self.profile.user)
        self.pass_edit = QLineEdit()
        self.pass_edit.setText(self.profile.password)
        self.host_edit = QLineEdit()
        self.host_edit.setText(self.profile.host)
        self.port_edit = QSpinBox()
        self.port_edit.setRange(0, 65535)
        self.port_edit.setValue(int(self.profile.port))

        self.mapper = QDataWidgetMapper()
        self.mapper.setModel(self.profile_model)
        self.mapper.setSubmitPolicy(QDataWidgetMapper.AutoSubmit)
        self.mapper.addMapping(self.user_edit, 0)
        self.mapper.addMapping(self.pass_edit, 1)
        self.mapper.addMapping(self.host_edit, 2)
        self.mapper.addMapping(self.port_edit, 3)

        form.addRow('RPC Username:', self.user_edit)
        form.addRow('RPC Password:', self.pass_edit)
        form.addRow('RPC Host:', self.host_edit)
        form.addRow('RPC Port:', self.port_edit)

        self.mapper.toFirst()
        self.load_profile_names()
        self.name_combo.currentIndexChanged.connect(lambda: self.load_profile(str(self.name_combo.currentText())))

        w = QWidget()
        w.setLayout(form)
        return w

    def create_rpc_tab(self):
        form = QFormLayout()

        self.method_edit = QLineEdit()
        self.method_edit.setWhatsThis('Enter the RPC method you want to use here. Some methods have auto-completion support, but any method that a node accepts can be entered here.')
        method_completer = QCompleter(known_methods)
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


        result, err = self.do_rpc(method_name, params, async=False)
        if err:
            if 'Connection refused' in err:
                raise Exception('RPC connection refused.')
            raise Exception(err)
        # Truncate block to header
        if data_type == 'raw_header':
            result = result[:160]
        return result

    def call_rpc(self):
        """Call do_rpc() with text from widgets."""
        method_name = str(self.method_edit.text())

        params = shlex.split(str(self.params_edit.text()))
        # Parse JSON strings.
        for i, item in enumerate(params):
            try:
                as_json = json.loads(item)
                params[i] = as_json
            except Exception:
                pass

        self.do_rpc(method_name, params)

    def do_rpc(self, method_name, params, async=True):
        """Call the full client.

        Returns:
            Result or raises an exception with an error.
        """
        if async:
            downloader = RPCDownloader(self.profile, method_name, params)
            self.download_async(downloader, self.set_result)
        else:
            postdata = json.dumps({'method': method_name, 'params': params, 'id': 'jsonrpc'})
            result = ''
            error = ''

            try:
                connection = urllib.urlopen(self.profile.as_url(), postdata)
                respdata = connection.read()
                connection.close()
            except Exception as e:
                error = str(e)
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
                    if type(error) not in (str, unicode):
                        error = json.dumps(error, indent=2)
                    else:
                        error = error.strip('"')
            return result, error

    def set_result(self, method_name, result, error):
        self.result_edit.setPlainText(error if error else result)
        self.result_edit.setProperty('hasError', True if error else False)
        self.style().polish(self.result_edit)

    def context_menu(self, position):
        menu = self.result_edit.createStandardContextMenu()

        # Add plugin actions if there's no error.
        if not self.result_edit.property('hasError').toBool():
            txt = str(self.result_edit.toPlainText())
            self.handler.add_plugin_actions(self, menu, txt)

        menu.exec_(self.result_edit.mapToGlobal(position))

    def on_methods_augmented(self, data):
        if type(data) is type(''):
            known_methods.append(data)
        else:
            known_methods.extend(data)
        self.method_edit.setCompleter()
        completer = QCompleter(known_methods)
        completer.setCompletionMode(QCompleter.InlineCompletion)
        self.method_edit.setCompleter(completer)
