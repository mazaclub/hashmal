from bitcoin.core.script import CScriptOp

def push_script(x):
    """Return hex-encoded PUSH operation.

    Args:
        x(str): Hex-encoded string to push.
    """
    return CScriptOp.encode_op_pushdata(x.decode('hex')).encode('hex')
