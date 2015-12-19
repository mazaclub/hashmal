import pyparsing
from pyparsing import Word, QuotedString, OneOrMore, Combine
import bitcoin
from bitcoin.base58 import CBase58Data
from bitcoin.core.script import CScript, OPCODE_NAMES, OPCODES_BY_NAME

from utils import is_hex, push_script

class Script(CScript):
    """Transaction script.

    Subclassed from CScript to provide methods for
    getting/setting according to certain formats.
    """
    @classmethod
    def from_human(cls, data):
        hex_str = []
        d = data.split()
        while 1:
            if len(d) == 0:
                break
            word = d[0]
            d = d[1:]

            if word.startswith('PUSHDATA'):
                continue

            opcode = OPCODES_BY_NAME.get(word)
            if opcode:
                hex_str.append(hex(opcode)[2:])
                continue

            # data to be pushed
            pushdata = word

            if is_hex(pushdata):
                if pushdata.startswith('0x'):
                    pushdata = pushdata[2:]
                if len(pushdata) % 2 != 0:
                    pushdata = ''.join(['0', pushdata])
            else:
                pushdata = word.encode('hex')
            hex_str.append(push_script(pushdata))

        hex_str = ''.join(hex_str)
        return cls(hex_str.decode('hex'))

    def get_hex(self):
        """Get the script as a hex-encoded string."""
        s = []
        iterator = self.raw_iter()
        while 1:
            try:
                opcode, data, byte_index = next(iterator)
                hexcode = hex(opcode)[2:]
                if len(hexcode) % 2 != 0:
                    hexcode = ''.join(['0', hexcode])
                s.append(hexcode)
                if data:
                    s.append(data.encode('hex'))
            except StopIteration:
                break
            except Exception:
                s.append('(CANNOT_PARSE)')

        return ''.join(s)

    def get_human(self):
        """Get the script as a human-readable string."""
        s = []
        iterator = self.raw_iter()
        while 1:
            try:
                opcode, data, byte_index = next(iterator)
                op_name = OPCODE_NAMES.get(opcode)
                if op_name:
                    s.append(op_name)
                elif opcode < OPCODES_BY_NAME['OP_PUSHDATA1']:
                    if all(ord(c) < 128 and ord(c) > 31 for c in data):
                        s.append(data)
                    else:
                        s.append(''.join(['0x', data.encode('hex')]))
            except StopIteration:
                break
            except Exception:
                s.append('(CANNOT_PARSE)')
        return ' '.join(s)


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
    def str_literal_to_hex(s, loc, toks):
        for i, t in enumerate(toks):
            toks[i] = ''.join(['0x', t.encode('hex')])
        return toks
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
            new_tok = t
            # Add '0x' prefix
            if not t.startswith('0x'):
                if t.startswith('x'):
                    new_tok = ''.join(['0', t])
                else:
                    new_tok = ''.join(['0x', t])
            # Even-length string
            if len(new_tok) % 2 != 0:
                new_tok = ''.join([new_tok[0:2], '0', new_tok[2:]])
            toks[i] = new_tok
        return toks
    # ^ parseActions for pyparsing end here.
    str_literal = QuotedString('"')
    str_literal.setParseAction(str_literal_to_hex)
    var_name = Combine(Word('$') + Word(pyparsing.alphas))
    var_name.setParseAction(var_name_to_value)

    # Here we populate the list of contextual tips.

    # Explicit opcode names
    op_names = [str(i) for i in OPCODE_NAMES.keys()]
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
    implicit_hex = Combine(pyparsing.WordStart() + OneOrMore(Word(pyparsing.hexnums)) + pyparsing.WordEnd())
    explicit_hex.setParseAction(hex_to_formatted_hex)
    implicit_hex.setParseAction(hex_to_formatted_hex)

    # Opcodes, implicit (e.g. 'ADD') and explicit (e.g. 'OP_ADD')
    explicit_op = pyparsing.oneOf(op_names_explicit)
    implicit_op = Combine(pyparsing.WordStart() + pyparsing.oneOf(op_names_implicit))
    implicit_op.setParseAction(implicit_opcode_to_explicit)

    contexts = pyparsing.Optional(var_name('Variable') |
                                  str_literal('String literal') |
                                  explicit_op('Opcode') |
                                  implicit_op('Opcode') |
                                  explicit_hex('Hex') |
                                  implicit_hex('Hex'))
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

    s = text
    s = var_name.transformString(s)
    s = str_literal.transformString(s)
    s = implicit_op.transformString(s)
    s = implicit_hex.transformString(s)
    s = explicit_hex.transformString(s)
    return s, context_tips

