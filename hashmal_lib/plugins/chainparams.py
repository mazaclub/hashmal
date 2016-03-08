
from PyQt4 import QtCore

from hashmal_lib.core import chainparams
from base import Plugin, BasePluginUI, Category

def make_plugin():
    p = Plugin(ChainParams)
    p.has_gui = False
    p.get_field_help = get_field_help
    return p

# Transaction field help info.

_bitcoin_tx_fields = list(chainparams._bitcoin_tx_fields)
_bitcoin_prevout_fields = list(chainparams._bitcoin_prevout_fields)
_bitcoin_txin_fields = list(chainparams._bitcoin_txin_fields)
_bitcoin_txout_fields = list(chainparams._bitcoin_txout_fields)

btc_field_help = {}
btc_field_help['prevout'] = {}
btc_field_help['input'] = {}
btc_field_help['output'] = {}
for i, field in enumerate(_bitcoin_tx_fields):
    info = ''
    if i == 0:
        info = 'Transaction version'
    elif i == 3:
        info = 'Transaction lock time'
    btc_field_help[field] = info

for i, field in enumerate(_bitcoin_prevout_fields):
    info = ''
    if i == 0:
        info = 'Previous transaction hash'
    elif i == 1:
        info = 'Previous transaction output'
    btc_field_help['prevout'][field] = info

for i, field in enumerate(_bitcoin_txin_fields):
    info = ''
    if i == 0:
        info = 'Previous outpoint'
    elif i == 1:
        info = 'Input script'
    elif i == 2:
        info = 'Input sequence'
    btc_field_help['input'][field] = info

for i, field in enumerate(_bitcoin_txout_fields):
    info = ''
    if i == 0:
        info = 'Output amount'
    elif i == 1:
        info = 'Output script'
    btc_field_help['output'][field] = info

clams_field_help = {
    ('Timestamp', b'<i', 4, 0): 'Timestamp',
    ('ClamSpeech', 'bytes', None, b''): 'CLAMspeech text',
}

frc_field_help = {
    ('RefHeight', b'<i', 4, 0): 'Reference height',
}

ppc_field_help = {
    ('Timestamp', b'<i', 4, 0): 'Timestamp',
}

transaction_field_help = {
    'Bitcoin': btc_field_help,
    'Clams': clams_field_help,
    'Freicoin': frc_field_help,
    'Peercoin': ppc_field_help,
}

def get_field_help(params_name, field, section=None):
    d = transaction_field_help.get(params_name, {})
    if section:
        d = d.get(section, {})
    value = d.get(field, None)
    if value is None and params_name != 'Bitcoin':
        return get_field_help('Bitcoin', field, section)
    return value

class ChainParamsObject(QtCore.QObject):
    """This class exists so that a signal can be emitted when chainparams presets change."""
    paramsPresetsChanged = QtCore.pyqtSignal()

class ChainParams(BasePluginUI):
    """For augmentation purposes, we use this plugin to help with chainparams presets."""
    tool_name = 'Chainparams'
    description = 'Chainparams allows plugins to add chainparams presets for Hashmal to use.'
    category = Category.Core

    def __init__(self, *args):
        super(ChainParams, self).__init__(*args)
        self.chainparams_object = ChainParamsObject()
        self.paramsPresetsChanged = self.chainparams_object.paramsPresetsChanged
        self.augment('chainparams_presets', callback=self.on_chainparams_augmented, undo_callback=self.undo_chainparams_augmented)
        self.augment('transaction_field_help', callback=self.on_tx_field_help_augmented, undo_callback=self.undo_tx_field_help_augmented)

    def add_params_preset(self, preset):
        try:
            chainparams.add_preset(preset)
            self.paramsPresetsChanged.emit()
        except Exception as e:
            self.error(str(e))

    def remove_params_preset(self, preset):
        try:
            chainparams.remove_preset(preset)
            self.paramsPresetsChanged.emit()
        except Exception as e:
            self.error(str(e))

    def on_chainparams_augmented(self, data):
        # Assume data is iterable.
        try:
            for i in data:
                self.add_params_preset(i)
            return
        # data is not an iterable.
        except Exception:
            self.add_params_preset(data)

    def undo_chainparams_augmented(self, data):
        # Assume data is iterable.
        try:
            for i in data:
                self.remove_params_preset(i)
            return
        # data is not an iterable.
        except Exception:
            self.remove_params_preset(data)

    def on_tx_field_help_augmented(self, data):
        global transaction_field_help
        for params_name, params_dict in data.items():
            existing_dict = transaction_field_help.get(params_name)
            # Create new chainparams preset dict.
            if not existing_dict:
                transaction_field_help[params_name] = params_dict
                continue

    def undo_tx_field_help_augmented(self, data):
        global transaction_field_help
        for params_name in data.keys():
            del transaction_field_help[params_name]
