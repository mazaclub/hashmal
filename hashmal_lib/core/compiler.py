"""Integration with txsc."""
import txsc
from txsc.ir import formats, linear_nodes
from txsc.language import Language
from txsc.asm.asm_parser import ASMParser
from txsc.asm.asm_language import ASMSourceVisitor, ASMTargetVisitor
from txsc.script_compiler import ScriptCompiler

import opcodes
import utils

class HashmalASMParser(ASMParser):
    tokens = ('OP', 'PUSH', 'OPCODE', 'NAME', 'STR',
              'DOUBLEQUOTE',)

    t_NAME = r'\$[a-zA-Z][a-zA-Z0-9_]*'
    t_DOUBLEQUOTE = r'\"'
    t_STR = r'\"[^\"]*\"'


    def __init__(self, variables=None):
        self.variables = variables if variables is not None else {}
        super(HashmalASMParser, self).__init__()

    def t_OP(self, t):
        r'[a-zA-Z0-9_]+'
        op_names = [str(i) for i in opcodes.opcodes_by_name.keys()]
        op_names_implicit = [i[3:] for i in op_names]
        if t.value in op_names:
            t.value = op_names_implicit[op_names.index(t.value)]

        if t.value.startswith('0x'):
            t.type = 'PUSH'
        elif t.value in op_names_implicit:
            t.type = 'OPCODE'
        return t

    def t_error(self, t):
        raise Exception("Illegal character '%s'" % t.value)


    def p_error(self, p):
        raise SyntaxError('Syntax error: %s' % p)

    def p_script(self, p):
        '''script : word
                  | script word
        '''
        if isinstance(p[1], list):
            p[0] = p[1]
            p[0].append(p[2])
        else:
            p[0] = [p[1]]

    def p_word_push(self, p):
        '''word : PUSH'''
        p[0] = p[1]

    def p_word_opcode(self, p):
        '''word : OPCODE'''
        p[0] = p[1]

    def p_variable(self, p):
        '''word : NAME'''
        name = p[1][1:]
        val = self.variables.get(name)

        # TODO
        if val is None:
            val = '"' + p[1] + '"'

        p[0] = val

    def p_string_literal(self, p):
        '''word : STR'''
        p[0] = p[1]


class HashmalSourceVisitor(ASMSourceVisitor):
    variables = None
    def transform(self, source):
        if not source:
            return self.instructions
        parser = HashmalASMParser(self.variables)
        if isinstance(source, list):
            source = '\n'.join(source)
        parsed = parser.parse_source(source)

        if parsed is None:
            print('\nFailed to parse.\n')
        assert isinstance(parsed, list)
        map(self.process_value, parsed)
        return self.instructions

    def process_value(self, value):
        if isinstance(value, str) and value.startswith('"') and value.endswith('"'):
            push = value[1:-1][::-1]
            self.add_instruction(linear_nodes.Push(data=push))
            return
        elif isinstance(value, str) and value.startswith('0x'):
            push = formats.hex_to_bytearray(value)[::-1]
            if 0 <= int(value, 16) <= 16:
                push = linear_nodes.small_int_opcode(int(value, 16))()
                self.add_instruction(push)
            else:
                self.add_instruction(linear_nodes.Push(data=push))
            return
        return super(HashmalSourceVisitor, self).process_value(value)


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
    name = 'hashmal-asm'
    source_visitor = HashmalSourceVisitor
    target_visitor = HashmalTargetVisitor

    @classmethod
    def set_variables_dict(cls, variables):
        cls.source_visitor.variables = variables

txsc.config.add_language(HashmalLanguage())

compiler = ScriptCompiler()

def compiler_options(d=None):
    """Create compiler options."""
    options = {
        'allow_invalid_comparisons': True,
        'optimization': 1,
    }
    if d:
        options.update(d)
    return options

def hex_to_asm(s):
    """Compile hex to ASM format."""
    compiler.setup_options(compiler_options({'source_lang': 'btc', 'target_lang': 'hashmal-asm'}))
    compiler.compile(s)
    return compiler.output()

def asm_to_hex(s):
    """Compile ASM format to hex."""
    compiler.setup_options(compiler_options({'source_lang': 'hashmal-asm', 'target_lang': 'btc'}))
    compiler.compile(s)
    return compiler.output()
