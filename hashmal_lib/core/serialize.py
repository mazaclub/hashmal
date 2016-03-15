
# Field metadata tuple members.

# Signifies that this field represents an amount of coins.
FIELD_COIN = object()


class Field(object):
    """Serialization field.

    Attributes:
        - attr (str): Attribute name.
        - fmt (str): Format. Usually a 2-character string for use with struct.pack()/unpack().
        - num_bytes (int): Number of bytes the data occupies when serialized.
        - default_value: Default attribute value.
        - metadata (tuple): Data to help client code know how to treat the attribute.

    """
    def __init__(self, attr, fmt, num_bytes, default_value, metadata=None):
        self.attr = attr
        self.fmt = fmt
        self.num_bytes = num_bytes
        self.default_value = default_value
        self.metadata = metadata if metadata else ()

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self.__eq__(other)

    def is_coin_amount(self):
        """Get whether this field represents an amount of coins."""
        return FIELD_COIN in self.metadata
