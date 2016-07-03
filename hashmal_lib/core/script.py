import pyparsing
from pyparsing import Word, QuotedString, OneOrMore, Combine
import shlex

from bitcoin.core import _bignum
from bitcoin.core.script import CScript

import compiler
import opcodes
from utils import is_hex, push_script, format_hex_string

class Script(CScript):
    """Transaction script.

    Subclassed from CScript to provide methods for
    getting/setting according to certain formats.
    """
    @classmethod
    def from_asm(cls, data):
        hex_str = compiler.asm_to_hex(data)
        hex_str = format_hex_string(hex_str, with_prefix=False)
        if not hex_str:
            return cls()
        return cls.from_hex(hex_str)

    @classmethod
    def from_txscript(cls, data):
        hex_str = compiler.txscript_to_hex(data)
        hex_str = format_hex_string(hex_str, with_prefix=False)
        if not hex_str:
            return cls()
        return cls.from_hex(hex_str)

    @classmethod
    def from_hex(cls, data):
        return cls(data.decode('hex'))

    def get_hex(self):
        """Get the script as a hex-encoded string."""
        s = []
        iterator = self.raw_iter()
        while 1:
            try:
                opcode, data, byte_index = next(iterator)
                hexcode = format_hex_string(hex(opcode), with_prefix=False)
                s.append(hexcode)
                if data:
                    s.append(data.encode('hex'))
            except StopIteration:
                break
            except Exception:
                s.append('(CANNOT_PARSE)')

        return ''.join(s)

    def asm_iter(self):
        iterator = self.raw_iter()
        while 1:
            try:
                opcode, data, byte_index = next(iterator)
                op_name = opcodes.opcode_names.get(opcode)
                if op_name and not 'DATA' in op_name:
                    s = op_name
                else:
                    if all(ord(c) < 128 and ord(c) > 31 for c in data):
                        s = ''.join(['"', data, '"'])
                    else:
                        s = ''.join(['0x', data.encode('hex')])
                yield s
            except StopIteration:
                break
            except Exception:
                yield '(CANNOT_PARSE)'

    def get_asm(self):
        """Get the script as an ASM string."""
        return compiler.hex_to_asm(self.get_hex())


def get_asm_context(text):
    """Get context from ASM input.

    Returns:
        A list of contextual information for tooltips, etc.
    """
    str_literal = QuotedString('"')
    var_name = Combine(Word('$') + Word(pyparsing.alphas))

    # Explicit opcode names.
    op_names = [str(i) for i in opcodes.opcodes_by_name.keys()]
    op_names_explicit = ' '.join(op_names)
    op_names_implicit = ' '.join([i[3:] for i in op_names])

    # Hex, implicit (e.g. 'a') and explicit (e.g. '0x0a')
    explicit_hex = Combine(Word('0x') + Word(pyparsing.hexnums) + pyparsing.WordEnd())
    decimal_number = Combine(pyparsing.WordStart() + pyparsing.Optional('-') + OneOrMore(Word(pyparsing.nums)) + pyparsing.WordEnd())

    # Opcodes, implicit (e.g. 'ADD') and explicit (e.g. 'OP_ADD')
    explicit_op = pyparsing.oneOf(op_names_explicit)
    implicit_op = Combine(pyparsing.WordStart() + pyparsing.oneOf(op_names_implicit))

    contexts = pyparsing.Optional(var_name('Variable') |
                                  str_literal('String literal') |
                                  explicit_op('Opcode') |
                                  implicit_op('Opcode') |
                                  explicit_hex('Hex') |
                                  decimal_number('Decimal'))
    matches = [(i[0].asDict(), i[1], i[2]) for i in contexts.scanString(text)]
    context_tips = []
    for i in matches:
        d = i[0]
        if len(d.items()) == 0: continue
        match_type, value = d.items()[0]
        start = i[1]
        end = i[2]
        context_tips.append( (start, end, value, match_type) )

    return context_tips

