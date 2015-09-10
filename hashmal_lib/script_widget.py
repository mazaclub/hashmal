"""Classes for displaying a Script."""

import pyparsing
from pyparsing import Word, QuotedString, ZeroOrMore, OneOrMore, Combine

import bitcoin
from bitcoin.core.script import OPCODE_NAMES

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from gui_utils import monospace_font
from core.script import Script

def transform_human(text, variables=None):
    """Transform user input with given context.

    This is separated from scriptedit.transform_human_script()
    so that this can be used with a known (or empty) context.

    Args:
        text (str): User input.
        variables (dict): State of the Variables tool.

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

class ScriptEdit(QTextEdit):
    """Script editor.

    Keeps an internal Script instance that it updates
    with its text, and uses to convert formats.
    """
    def __init__(self, parent=None):
        super(ScriptEdit, self).__init__(parent)
        self.current_format = 'Human'
        self.script = Script()
        self.textChanged.connect(self.on_text_changed)
        self.setFont(monospace_font)
        # For tooltips
        self.context = []

    def on_text_changed(self):
        txt = str(self.toPlainText())
        self.set_data(txt, self.current_format)

    def copy_hex(self):
        txt = self.get_data('Hex')
        QApplication.clipboard().setText(txt)

    def contextMenuEvent(self, e):
        menu = self.createStandardContextMenu()
        menu.addAction('Copy Hex', self.copy_hex)
        menu.exec_(e.globalPos())

    def set_format(self, fmt):
        self.current_format = fmt
        self.setPlainText(self.get_data())

    def set_data(self, text, fmt):
        script = None
        if fmt == 'Hex' and len(text) % 2 == 0:
            try:
                script = Script(text.decode('hex'))
            except Exception:
                pass
        elif fmt == 'Human':
            txt, self.context = transform_human(text)
            script = Script.from_human(txt)
        self.script = script

    def get_data(self, fmt=None):
        if fmt is None:
            fmt = self.current_format
        if not self.script: return ''
        if fmt == 'Hex':
            return self.script.get_hex()
        elif fmt == 'Human':
            return self.script.get_human()

    def event(self, e):
        if e.type() == QEvent.ToolTip:
            cursor = self.cursorForPosition(e.pos())
            context = self.get_tooltip(cursor.position())
            if not context:
                QToolTip.hideText()
            else:
                QToolTip.showText(e.globalPos(), context)
            return True
        return super(ScriptEdit, self).event(e)

    def get_tooltip(self, index):
        """Returns the contextual tip for the word at index."""
        if index < 0 or len(self.toPlainText()) < index:
            return ''
        for start, end, value, match_type in self.context:
            if index >= start and index < end:
                return '{} ({})'.format(value, match_type)
