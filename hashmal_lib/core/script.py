import shlex

from bitcoin.core import _bignum
from bitcoin.core.script import CScript
import ply

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


# These are human-friendly representations of lexer token types.
asm_match_types = {
    'PUSH': 'Data push',
    'NAME': 'Variable',
    'STR': 'String literal',
}

def get_asm_context(text):
    """Get context from ASM input.

    Returns:
        A list of contextual information for tooltips, etc.
    """
    context_tips = []
    lexer = ply.lex.lex(module=compiler.HashmalASMSourceVisitor.instantiate_parser())
    lexer.input(text)

    token = lexer.token()
    while token:
        value = token.value
        # A ParsedToken is used to preserve the original value.
        if isinstance(value, compiler.ParsedToken):
            value = value.input_value
        match_type = asm_match_types.get(token.type, token.type.capitalize())

        start = token.lexpos
        end = start + len(value)

        tip = (start, end, value, match_type)

        context_tips.append(tip)
        token = lexer.token()

    return context_tips

# These are human-friendly representations of HashmalHumanLexer lexer token types.
txscript_match_types = {
    'HEXSTR': 'Hex string',
    'TYPENAME': 'Type name',
    'STR': 'String literal',
    'ASSUME': 'Keyword - Assumption',
    'FUNC': 'Keyword - Function definition',
    'LET': 'Keyword - Name definition',
    'MUTABLE': 'Keyword - Mutable name',
    'RETURN': 'Keyword - Return',
    'PUSH': 'Keyword - Data push',
    'VERIFY': 'Keyword - Verify',

    'IF': 'Conditional',
    'ELSE': 'Conditional',

    'AND': 'Boolean operator',
    'OR': 'Boolean operator',
    'NOT': 'Boolean operator',
}

def get_txscript_context(text):
    """Get context from TxScript input.

    Returns:
        A list of contextual information for tooltips, etc.
    """
    context_tips = []
    lexer = ply.lex.lex(module=compiler.HashmalHumanLexer())
    lexer.input(text)

    token = lexer.token()
    while token:
        value = token.value
        # A ParsedToken is used to preserve the original value.
        if isinstance(value, compiler.ParsedToken):
            value = value.input_value
        match_type = txscript_match_types.get(token.type, token.type.capitalize())

        start = token.lexpos
        end = start + len(str(value))

        tip = (start, end, value, match_type)

        context_tips.append(tip)
        token = lexer.token()

    return context_tips
