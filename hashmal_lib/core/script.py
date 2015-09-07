import bitcoin
from bitcoin.base58 import CBase58Data
from bitcoin.core.script import CScript, OPCODE_NAMES, OPCODES_BY_NAME
from utils import push_script

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

            found = False
            accepted_forms = [word]
            try:
                a = int(word)
            except ValueError:
                accepted_forms.append( ''.join(['OP_', word]) )

            # e.g. "OP_DUP" and "DUP" are both valid
            for i in accepted_forms:
                opcode = OPCODES_BY_NAME.get(i)
                if opcode:
                    found = True
                    hex_str.append(hex(opcode)[2:])
            if found:
                continue

            # data to be pushed
            pushdata = word

            try:
                i = int(pushdata, 16)
                if pushdata.startswith('0x'):
                    pushdata = pushdata[2:]
                if len(pushdata) % 2 != 0:
                    pushdata = ''.join(['0', pushdata])
            except Exception:
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
                    s.append(''.join(['0x', data.encode('hex')]))
            except StopIteration:
                break
            except Exception:
                s.append('(CANNOT_PARSE)')
        return ' '.join(s)

