

class Field(object):
    """Serialization field."""
    def __init__(self, attr, fmt, num_bytes, default_value):
        self.attr = attr
        self.fmt = fmt
        self.num_bytes = num_bytes
        self.default_value = default_value

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self.__eq__(other)
