from bitcoin.core.script import CScriptOp

def format_hex_string(x, with_prefix=True):
    """Ensure hex-encoded value has an even length."""
    if not is_hex(x):
        return
    # Add '0x' prefix
    new_val = x
    if not x.startswith('0x'):
        if x.startswith('x'):
            new_val = ''.join(['0', x])
        else:
            new_val = ''.join(['0x', x])
    # Even-length string
    if len(new_val) % 2 != 0:
        new_val = ''.join([new_val[0:2], '0', new_val[2:]])
    return new_val if with_prefix else new_val[2:]

def is_hex(x):
    try:
        i = int(x, 16)
        return True
    except ValueError:
        pass
    return False

def push_script(x):
    """Return hex-encoded PUSH operation.

    Args:
        x(str): Hex-encoded string to push.
    """
    return CScriptOp.encode_op_pushdata(x.decode('hex')).encode('hex')
