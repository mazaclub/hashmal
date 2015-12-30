"""Script opcdes.

This module exists to allow opcode overriding.
"""

from bitcoin.core.script import *

opcode_names = dict(OPCODE_NAMES)
opcodes_by_name = dict(OPCODES_BY_NAME)
disabled_opcodes = list(DISABLED_OPCODES)

overridden_opcodes = {}

def is_overridden(op_value):
    return op_value in overridden_opcodes.keys()

def override(opcode, stack, txTo, inIdx, flags, err_raiser):
    if not is_overridden(opcode):
        return False

    return overridden_opcodes[opcode](stack, txTo, inIdx, flags, err_raiser)

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

