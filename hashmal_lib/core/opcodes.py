"""Script opcdes.

This module exists to allow opcode overriding.
"""

from bitcoin.core.script import *
from bitcoin.core import scripteval

opcode_names = dict(OPCODE_NAMES)
opcodes_by_name = dict(OPCODES_BY_NAME)
disabled_opcodes = list(DISABLED_OPCODES)

overridden_opcodes = {}

def is_overridden(op_value):
    return op_value in overridden_opcodes.keys()

def override(opcode, stack, txTo, inIdx, flags, execution_data, err_raiser):
    if not is_overridden(opcode):
        return False

    return overridden_opcodes[opcode](stack, txTo, inIdx, flags, execution_data, err_raiser)

def set_overridden_opcodes(ops):
    global opcode_names, opcodes_by_name, disabled_opcodes, overridden_opcodes
    opcode_names = dict(OPCODE_NAMES)
    opcodes_by_name = dict(OPCODES_BY_NAME)
    overridden_opcodes = {}

    if not ops:
        return

    for value, name, func in ops:
        v = CScriptOp(value)
        opcode_names[v] = name
        opcodes_by_name[name] = v
        overridden_opcodes[v] = func

# Known opcode overrides

def clams_checklocktimeverify(stack, txTo, inIdx, flags, execution_data, err_raiser):
    if len(stack) < 1:
        # We can't use scripteval.MissingOpArgumentsError here because it
        # uses python-bitcoinlib's OPCODE_NAMES dict.
        err_raiser(scripteval.EvalScriptError,
                   'missing arguments for CHECKLOCKTIMEVERIFY; need 1 item; but none on stack')

    if not execution_data:
        err_raiser(scripteval.EvalScriptError,
                    'CHECKLOCKTIMEVERIFY requires execution data items "block_height" and "block_time"')

    locktime = scripteval._CastToBigNum(stack[-1], err_raiser)
    block_height = execution_data.block_height
    block_time = execution_data.block_time
    last = ''

    if locktime == 0:
        last = 'Locktime is zero, so it passed.'
    else:
        number = block_height if locktime < 500000000 else block_time
        word = 'block height:' if locktime < 500000000 else 'block time:'
        if locktime < number:
            last = 'Locktime passed (%s < %s %s).' % (locktime, word, number)
        else:
            err_raiser(scripteval.EvalScriptError,
                        'Locktime %s is not final' % locktime)

    return stack, opcodes_by_name.get('OP_CHECKLOCKTIMEVERIFY'), last

