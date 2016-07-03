"""Integration with txsc."""
import ast
import ply

import txsc
from txsc.ir import formats, linear_nodes
from txsc.language import Language
from txsc.asm.asm_parser import ASMParser
from txsc.asm.asm_language import ASMSourceVisitor, ASMTargetVisitor
from txsc.txscript import lexer, script_parser, txscript_language
from txsc.script_compiler import ScriptCompiler

import opcodes
import utils

def get_int(s):
    """Get the int value of a decimal or hex string."""
    for base in [10, 16]:
        try:
            return int(s, base)
        except ValueError:
            pass

class HashmalASMParser(ASMParser):
    tokens = ('OP', 'PUSH', 'OPCODE', 'NAME', 'STR',
              'DOUBLEQUOTE',)

    t_NAME = r'\$[a-zA-Z][a-zA-Z0-9_]*'
    t_DOUBLEQUOTE = r'\"'
    t_STR = r'\"[^\"]*\"'
    t_PUSH = r'(0x)?[a-fA-F0-9]+'


    def __init__(self, variables=None):
        self.variables = variables if variables is not None else {}
        self.opcode_names = [str(i) for i in opcodes.opcodes_by_name.keys()]
        self.opcode_names_implicit = [i[3:] for i in self.opcode_names]
        super(HashmalASMParser, self).__init__()

    def t_OP(self, t):
        r'(?!0x)[a-zA-Z0-9_]+'
        if t.value in self.opcode_names:
            t.value = self.opcode_names_implicit[self.opcode_names.index(t.value)]
            t.type = 'OPCODE'
        elif t.value in self.opcode_names_implicit:
            t.type = 'OPCODE'
        else:
            int_value = get_int(t.value)
            if int_value is not None:
                t.value = hex(int_value)
                t.type = 'PUSH'
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


class HashmalASMSourceVisitor(ASMSourceVisitor):
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
        return super(HashmalASMSourceVisitor, self).process_value(value)


class HashmalASMTargetVisitor(ASMTargetVisitor):
    def __init__(self, *args, **kwargs):
        kwargs['omit_op_prefixes'] = False
        super(HashmalASMTargetVisitor, self).__init__(*args, **kwargs)

    def visit_Push(self, node):
        length, data = super(HashmalASMTargetVisitor, self).visit_Push(node)
        data = utils.format_hex_string(data, with_prefix=False).decode('hex')
        if all(ord(c) < 128 and ord(c) > 31 for c in data):
            s = ''.join(['"', data, '"'])
        else:
            s = ''.join(['0x', data.encode('hex')])
        return s


class HashmalASMLanguage(Language):
    """Hashmal-compatible ASM script language."""
    name = 'hashmal-asm'
    source_visitor = HashmalASMSourceVisitor
    target_visitor = HashmalASMTargetVisitor


# Human language.

class HashmalHumanLexer(lexer.ScriptLexer):
    tokens = lexer.ScriptLexer.tokens + ('VARIABLE',)

    t_VARIABLE = r'\$[a-zA-Z0-9]+'

class HashmalHumanParser(script_parser.ScriptParser):
    tokens = HashmalHumanLexer.tokens
    precedence = HashmalHumanLexer.precedence
    def __init__(self, variables=None, **kwargs):
        self.variables = variables if variables is not None else {}
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.lexer = ply.lex.lex(module=HashmalHumanLexer())
        self.parser = ply.yacc.yacc(module=self, debug=False)

    def p_expr_variable(self, p):
        '''expr : VARIABLE'''
        name = p[1][1:]
        value = self.variables.get(name)

        if value is None:
            result = ast.Str('"' + p[1] + '"')
        else:
            # Use ScriptParser to figure out what value is.
            parser = script_parser.ScriptParser()
            src = '%s;' % value
            module = parser.parse(src)
            result = module.body[0]

        p[0] = result


class HashmalHumanSourceVisitor(txscript_language.TxScriptSourceVisitor):
    variables = None
    def __init__(self, *args, **kwargs):
        super(HashmalHumanSourceVisitor, self).__init__(*args, **kwargs)
        self.parser = HashmalHumanParser(self.variables)

class HashmalHumanLanguage(Language):
    """Hashmal-compatible TxScript script language."""
    name = 'hashmal-txscript'
    source_visitor = HashmalHumanSourceVisitor
    supports_symbol_table = True

txsc.config.add_language(HashmalASMLanguage())
txsc.config.add_language(HashmalHumanLanguage())

compiler = ScriptCompiler()

def set_variables_dict(variables):
    """Set the variables that will be substituted during compilation."""
    HashmalASMLanguage.source_visitor.variables = variables
    HashmalHumanLanguage.source_visitor.variables = variables

def compiler_options(d=None):
    """Create compiler options."""
    options = {
        'allow_invalid_comparisons': True,
        'optimization': 1,
    }
    if d:
        options.update(d)
    return options

def compile_source(s, source_lang, target_lang):
    """Compile source_lang to target_lang.

    Use a specific function (e.g. hex_to_asm(s) for more safety.
    """
    compiler.setup_options(compiler_options({'source_lang': source_lang, 'target_lang': target_lang}))
    compiler.compile(s)
    return compiler.output()

def hex_to_asm(s):
    """Compile hex to ASM format."""
    return compile_source(s, 'btc', 'hashmal-asm')

def hex_to_txscript(s):
    """Compile hex to TxScript format."""
    return compile_source(s, 'btc', 'hashmal-txscript')

def asm_to_hex(s):
    """Compile ASM format to hex."""
    return compile_source(s, 'hashmal-asm', 'btc')

def asm_to_txscript(s):
    """Compile ASM format to TxScript."""
    return compile_source(s, 'hashmal-asm', 'hashmal-txscript')

def txscript_to_hex(s):
    """Compile TxScript to hex."""
    return compile_source(s, 'hashmal-txscript', 'btc')

def txscript_to_asm(s):
    """Compile TxScript to ASM format."""
    return compile_source(s, 'hashmal-txscript', 'hashmal-asm')
