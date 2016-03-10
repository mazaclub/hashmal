"""Item types.

This module makes it easier for individual plugins and
parts of Hashmal to use consistent metadata.
"""
from collections import namedtuple, defaultdict

from bitcoin.core import x, b2x, b2lx
from PyQt4.QtCore import pyqtSignal, QObject
from PyQt4.QtGui import QApplication

from hashmal_lib.core import Transaction, BlockHeader, Block
from base import Plugin, BasePluginUI, Category

class Item(object):
    """A value and metadata."""
    name = ''
    @classmethod
    def coerce_item(cls, data):
        """Attempt to coerce data into an item of this type."""
        return None

    def __init__(self, value):
        self.value = value
        # Actions that this item supports without the need of any plugins.
        # List of 2-tuples: (label, func)
        self.actions = []

    def __str__(self):
        return str(self.value)

    def raw(self):
        """Returns the raw representation of this item, if applicable."""
        pass

# This named tuple should be used by plugins when augmenting item actions.
ItemAction = namedtuple('ItemAction', ('plugin_name', 'item_type', 'label', 'func'))

# List of Item subclasses.
item_types = []
# List of ItemAction instances.
item_actions = []

def instantiate_item(data, allow_multiple=False):
    """Attempt to instantiate an item with the value of data.

    If allow_multiple is True, a list of compatible items
    will be returned.
    """
    items = []
    for i in item_types:
        instance = i.coerce_item(data)
        if instance is not None:
            if not allow_multiple:
                return instance
            items.append(instance)
    return items

def get_actions(name):
    """Get actions for an item type.

    Returns:
        A list of dicts of the form:
            {plugin_name: [(action_label, action_function), ...]}
    """
    actions = defaultdict(list)
    for i in item_actions:
        if i.item_type == name:
            actions[i.plugin_name].append( (i.label, i.func) )

    return actions

class TxItem(Item):
    name = 'Transaction'
    @classmethod
    def coerce_item(cls, data):
        # Coerce binary string.
        def coerce_string(v):
            return Transaction.deserialize(v)

        # Coerce hex string.
        def coerce_hex_string(v):
            return Transaction.deserialize(x(v))

        # Coerce transaction instance.
        def coerce_tx(v):
            return Transaction.from_tx(v)

        for i in [coerce_string, coerce_hex_string, coerce_tx]:
            try:
                value = i(data)
            except Exception:
                continue
            else:
                if value:
                    return cls(value)

    def __init__(self, *args):
        super(TxItem, self).__init__(*args)
        def copy_txid():
            QApplication.clipboard().setText(b2lx(self.value.GetHash()))
        self.actions.append(('Copy Transaction ID', copy_txid))

    def raw(self):
        return b2x(self.value.serialize())
item_types.append(TxItem)

class BlockItem(Item):
    name = 'Block'
    @classmethod
    def coerce_item(cls, data):
        # Coerce binary string.
        def coerce_string(v):
            return Block.deserialize(v)

        # Coerce hex string.
        def coerce_hex_string(v):
            return Block.deserialize(x(v))

        # Coerce block instance.
        def coerce_block(v):
            return Block.from_block(v)

        for i in [coerce_string, coerce_hex_string, coerce_block]:
            try:
                value = i(data)
            except Exception:
                continue
            else:
                if value:
                    return cls(value)

    def __init__(self, *args):
        super(BlockItem, self).__init__(*args)
        def copy_hash():
            QApplication.clipboard().setText(b2lx(self.value.GetHash()))
        self.actions.append(('Copy Block Hash', copy_hash))

    def raw(self):
        return b2x(self.value.serialize())
item_types.append(BlockItem)

class BlockHeaderItem(Item):
    name = 'Block Header'
    @classmethod
    def coerce_item(cls, data):
        # Coerce binary string.
        def coerce_string(v):
            return BlockHeader.deserialize(v)

        # Coerce hex string.
        def coerce_hex_string(v):
            return BlockHeader.deserialize(x(v))

        # Coerce block header instance.
        def coerce_header(v):
            return BlockHeader.from_header(v)

        for i in [coerce_string, coerce_hex_string, coerce_header]:
            try:
                value = i(data)
            except Exception:
                continue
            else:
                if value:
                    return cls(value)

    def __init__(self, *args):
        super(BlockHeaderItem, self).__init__(*args)
        def copy_hash():
            QApplication.clipboard().setText(b2lx(self.value.GetHash()))
        self.actions.append(('Copy Block Hash', copy_hash))

    def raw(self):
        return b2x(self.value.serialize())
item_types.append(BlockHeaderItem)


def make_plugin():
    p = Plugin(ItemsPlugin, category=Category.Core, has_gui=False)
    p.instantiate_item = instantiate_item
    p.get_item_actions = get_actions
    return p

class ItemTypesObject(QObject):
    """This class exists so that a signal can be emitted when item_types changes."""
    itemTypesChanged = pyqtSignal(list, name='itemTypesChanged')

class ItemsPlugin(BasePluginUI):
    """For augmentation purposes, we use a plugin to help with item types."""
    tool_name = 'Item Types'
    description = 'Helps handle data that is of a certain type.'

    def __init__(self, *args):
        super(ItemsPlugin, self).__init__(*args)
        self.item_types_object = ItemTypesObject()
        self.itemTypesChanged = self.item_types_object.itemTypesChanged
        self.augment('item_types', callback=self.on_item_types_augmented, undo_callback=self.undo_item_types_augmented)
        self.augment('item_actions', callback=self.on_item_actions_augmented, undo_callback=self.undo_item_actions_augmented)

    def on_item_types_augmented(self, data):
        try:
            for i in data:
                if issubclass(i, Item):
                    item_types.append(i)
        except Exception:
            # data is not an iterable.
            if issubclass(data, Item):
                item_types.append(data)

        self.itemTypesChanged.emit(item_types)

    def undo_item_types_augmented(self, data):
        try:
            for i in data:
                if issubclass(i, Item):
                    item_types.remove(i)
        except Exception:
            # data is not an iterable.
            if issubclass(data, Item):
                item_types.remove(data)

        self.itemTypesChanged.emit(item_types)

    def on_item_actions_augmented(self, data):
        if isinstance(data, ItemAction):
            item_actions.append(data)
            return
        # If iterable, iterate.
        for i in data:
            if isinstance(i, ItemAction):
                item_actions.append(i)

    def undo_item_actions_augmented(self, data):
        if isinstance(data, ItemAction):
            item_actions.remove(data)
            return
        # If iterable, iterate.
        for i in data:
            if isinstance(i, ItemAction):
                item_actions.remove(i)
