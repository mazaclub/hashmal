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
    @staticmethod
    def decode_human_word(word):
        opcode = opcodes.opcodes_by_name.get(word)
        if opcode is not None:
            return format_hex_string(hex(opcode), with_prefix=False)
        # Make sure hex is formatted.
        elif is_hex(word):
            word = format_hex_string(word, with_prefix=False)
        # Hex-encode text.
        else:
            if word.startswith('"') and word.endswith('"'):
                word = word[1:-1]
            word = word.encode('hex')
        return push_script(word)

    @classmethod
    def from_human(cls, data):
        hex_str = compiler.human_to_hex(data)
        hex_str = format_hex_string(hex_str, with_prefix=False)
        if not hex_str:
            return cls()
        return cls(hex_str.decode('hex'))

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

    def human_iter(self):
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

    def get_human(self):
        """Get the script as a human-readable string."""
        return compiler.hex_to_human(self.get_hex())


def transform_human(text, variables=None):
    """Transform user input with given context.

    Args:
        text (str): User input.
        variables (dict): Variables for purposes of substitution.

    Returns:
        A 2-tuple of: (A human-readable script that Script can parse,
            A list of contextual information for tooltips, etc.)
    """
    if variables is None:
        variables = {} # No mutable default value.
    # these are parseActions for pyparsing.
    def var_name_to_value(s, loc, toks):
        for i, t in enumerate(toks):
            val = variables.get(t[1:])
            if val:
                toks[i] = val
        return toks
    def implicit_opcode_to_explicit(s, loc, toks):
        """Add "OP_" prefix to an opcode."""
        for i, t in enumerate(toks):
            toks[i] = '_'.join(['OP', t])
        return toks
    def hex_to_formatted_hex(s, loc, toks):
        """Add "0x" prefix and ensure even length."""
        for i, t in enumerate(toks):
            new_tok = format_hex_string(t)
            toks[i] = new_tok
        return toks
    def decimal_to_formatted_hex(s, loc, toks=None):
        """Convert decimal to hex."""
        if toks is None:
            return
        for i, t in enumerate(toks):
            token = int(t)
            if token == 0:
                token = '0x00'
            else:
                token = _bignum.bn2vch(token).encode('hex')
            new_tok = format_hex_string(token)
            toks[i] = new_tok
        return toks
    # ^ parseActions for pyparsing end here.
    str_literal = QuotedString('"')
    var_name = Combine(Word('$') + Word(pyparsing.alphas))
    var_name.setParseAction(var_name_to_value)

    # Here we populate the list of contextual tips.

    # Explicit opcode names
    op_names = [str(i) for i in opcodes.opcodes_by_name.keys()]
    op_names_explicit = ' '.join(op_names)
    def is_small_int(op):
        """True if op is one of OP_1, OP_2, ...OP_16"""
        try:
            i = int(op[3:])
            return True
        except ValueError:
            return False
    op_names_implicit = ' '.join([i[3:] for i in op_names if not is_small_int(i)])

    # Hex, implicit (e.g. 'a') and explicit (e.g. '0x0a')
    explicit_hex = Combine(Word('0x') + Word(pyparsing.hexnums) + pyparsing.WordEnd())
    decimal_number = Combine(pyparsing.WordStart() + pyparsing.Optional('-') + OneOrMore(Word(pyparsing.nums)) + pyparsing.WordEnd())
    explicit_hex.setParseAction(hex_to_formatted_hex)
    decimal_number.setParseAction(decimal_to_formatted_hex)

    # Opcodes, implicit (e.g. 'ADD') and explicit (e.g. 'OP_ADD')
    explicit_op = pyparsing.oneOf(op_names_explicit)
    implicit_op = Combine(pyparsing.WordStart() + pyparsing.oneOf(op_names_implicit))
    implicit_op.setParseAction(implicit_opcode_to_explicit)

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

    # Now we do the actual transformation.
    strings = []
    try:
        words = shlex.split(text, posix=False)
    except Exception:
        words = text.split()
    for s in words:
        # Do not transform strings if they are string literals.
        is_literal = True if pyparsing.Optional(str_literal).parseString(s) else False
        if not is_literal:
            s = var_name.transformString(s)
            s = implicit_op.transformString(s)
            s = decimal_number.transformString(s)
            s = explicit_hex.transformString(s)
        strings.append(s)
    return ' '.join(strings), context_tips

