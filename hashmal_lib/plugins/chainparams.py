
from PyQt4 import QtCore

from hashmal_lib.core import chainparams
from base import Plugin, BasePluginUI

def make_plugin():
    p = Plugin(ChainParams)
    p.has_gui = False
    return p

class ChainParamsObject(QtCore.QObject):
    """This class exists so that a signal can be emitted when chainparams presets change."""
    paramsPresetsChanged = QtCore.pyqtSignal()

class ChainParams(BasePluginUI):
    """For augmentation purposes, we use this plugin to help with chainparams presets."""
    tool_name = 'Chainparams'
    description = 'Chainparams allows plugins to add chainparams presets for Hashmal to use.'

    def __init__(self, *args):
        super(ChainParams, self).__init__(*args)
        self.chainparams_object = ChainParamsObject()
        self.paramsPresetsChanged = self.chainparams_object.paramsPresetsChanged
        self.augment('chainparams_presets', None, callback=self.on_chainparams_augmented)

    def add_params_preset(self, preset):
        try:
            chainparams.add_preset(preset)
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
