from bitcoin.core.script import CScriptOp

def push_script(x):
    return CScriptOp.encode_op_pushdata(x.decode('hex')).encode('hex')
