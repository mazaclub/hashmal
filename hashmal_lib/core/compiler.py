"""Integration with txsc."""
import txsc
from txsc.language import Language
from txsc.asm.asm_language import ASMSourceVisitor, ASMTargetVisitor
from txsc.script_compiler import ScriptCompiler

import utils

class HashmalTargetVisitor(ASMTargetVisitor):
    def __init__(self, *args, **kwargs):
        kwargs['omit_op_prefixes'] = False
        super(HashmalTargetVisitor, self).__init__(*args, **kwargs)

    def visit_Push(self, node):
        length, data = super(HashmalTargetVisitor, self).visit_Push(node)
        data = utils.format_hex_string(data, with_prefix=False).decode('hex')
        if all(ord(c) < 128 and ord(c) > 31 for c in data):
            s = ''.join(['"', data, '"'])
        else:
            s = ''.join(['0x', data.encode('hex')])
        return s


class HashmalLanguage(Language):
    name = 'hashmal'
    target_visitor = HashmalTargetVisitor

txsc.config.add_language(HashmalLanguage())

compiler = ScriptCompiler()

def hex_to_human(s):
    """Compile hex to human-readable format."""
    compiler.setup_options({'source_lang': 'btc', 'target_lang': 'hashmal'})
    compiler.compile(s)
    return compiler.output()
