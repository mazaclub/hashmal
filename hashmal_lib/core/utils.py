from bitcoin.core.script import CScriptOp
import hexs

def format_hex_string(x, with_prefix=True):
    """Ensure hex-encoded value has an even length."""
    if not is_hex(x):
        return
    new_val = hexs.format_hex(x)
    if with_prefix:
        new_val = '0x' + new_val
    return new_val

def is_hex(x):
    return hexs.is_hex(x)

def push_script(x):
    """Return hex-encoded PUSH operation.

    Args:
        x(str): Hex-encoded string to push.
    """
    return CScriptOp.encode_op_pushdata(x.decode('hex')).encode('hex')
