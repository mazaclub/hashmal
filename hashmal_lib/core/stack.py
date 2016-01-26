import hashlib
import sys
from collections import namedtuple

import bitcoin
from bitcoin.core.script import *
from bitcoin.core.scripteval import *
from bitcoin.core.scripteval import (
        _CastToBigNum, _CastToBool, _CheckSig, _CheckMultiSig,
        _ISA_UNOP, _ISA_BINOP, _CheckExec, _bord, MAX_STACK_ITEMS
)

import opcodes


def e(*args):
    """For hex-encoding things."""
    return tuple([i.encode('hex') for i in args])

# Contains info about the tx's block, etc.
# Mainly for opcodes like CHECKLOCKTIMEVERIFY.
ExecutionData = namedtuple('ExecutionData', ('block_height', 'block_time'))

StackState = namedtuple('StackState', ('stack', 'last_op', 'log'))

class ScriptExecution(object):
    def __init__(self, tx_script=None, txTo=None, inIdx=0, flags=None, execution_data=None):
        super(ScriptExecution, self).__init__()
        self.error = None
        self.steps = []
        # Whether the script exited with a nonzero value.
        self.script_passed = None
        # Whether the script has been verified.
        self.script_verified = False

    def evaluate(self, tx_script, txTo=None, inIdx=0, flags=None, execution_data=None):
        self.error = None
        self.steps = []
        if flags is None:
            flags = ()
        self.script_passed = None
        self.script_verified = False

        stack = Stack(tx_script, txTo, inIdx, flags, execution_data)
        verifying = False
        if stack.txTo:
            iterator = stack.verify_step()
            verifying = True
        else:
            iterator = stack.step()
        while 1:
            try:
                state, last_op, log = iterator.next()
                self.steps.append(StackState(list(state), last_op, log))
            except StopIteration:
                break
            except Exception as e:
                self.error = e
                break

        if self.steps and self.steps[-1].stack:
            if verifying:
                self.script_verified = True
            top_value = _CastToBool(self.steps[-1].stack[-1])
            self.script_passed = top_value
        return self.steps

class Stack(object):
    """State of a Script's execution."""
    def __init__(self, tx_script, txTo=None, inIdx=0, flags=None, execution_data=None):
        super(Stack, self).__init__()
        self.tx_script = tx_script
        self.txTo = txTo
        self.inIdx = inIdx
        if flags is None:
            flags = ()
        self.flags = flags
        self.execution_data = execution_data
        self.init_stack = []

    def verify_step(self):
        """Generator for verifying a script.

        Re-implemented VerifyScript from python-bitcoinlib for stack log.
        """
        if not self.txTo:
            raise VerifyScriptError('Verification requires a transaction')

        # Store original tx script.
        tx_script = self.tx_script

        self.init_stack = []
        # Set tx_script to scriptSig of transaction.
        self.tx_script = scriptSig = self.txTo.vin[self.inIdx].scriptSig

        iterator = self.step()
        while 1:
            try:
                yield iterator.next()
            except StopIteration:
                break

        # Store copy of current stack for P2SH verification.
        stack_copy = list(self.init_stack)
        # Set tx_script to the original script being tested.
        self.tx_script = tx_script

        iterator = self.step()
        while 1:
            try:
                yield iterator.next()
            except StopIteration:
                break

        if len(self.init_stack) == 0:
            raise VerifyScriptError("scriptPubKey left an empty stack")
        if not _CastToBool(self.init_stack[-1]):
            raise VerifyScriptError("scriptPubKey returned false")

        # Pay-To-Script-Hash verification.
        if tx_script.is_p2sh():
            if not scriptSig.is_push_only():
                raise VerifyScriptError("P2SH scriptSig not is_push_only()")
            if not len(stack_copy):
                raise VerifyScriptError("scriptSig left an empty stack")

            # Set tx script to the pubkey from scriptSig.
            self.tx_script = pubkey = CScript(stack_copy.pop())
            self.init_stack = stack_copy

            iterator = self.step()
            while 1:
                try:
                    yield iterator.next()
                except StopIteration:
                    break

            if not len(stack_copy):
                raise VerifyScriptError("P2SH inner scriptPubKey left an empty stack")

            if not _CastToBool(stack_copy[-1]):
                raise VerifyScriptError("P2SH inner scriptPubKey returned false")

    def step(self):
        """Generator for evaluating a script.

        Re-implemented _EvalScript from python-bitcoinlib for stack log.
        """
        stack = self.init_stack
        scriptIn = self.tx_script
        txTo = self.txTo
        inIdx = self.inIdx
        flags = self.flags
        execution_data = self.execution_data
        if len(scriptIn) > MAX_SCRIPT_SIZE:
            raise EvalScriptError('script too large; got %d bytes; maximum %d bytes' %
                                            (len(scriptIn), MAX_SCRIPT_SIZE),
                                  stack=stack,
                                  scriptIn=scriptIn,
                                  txTo=txTo,
                                  inIdx=inIdx,
                                  flags=flags)

        altstack = []
        vfExec = []
        pbegincodehash = 0
        nOpCount = [0]
        last = ''
        for (sop, sop_data, sop_pc) in scriptIn.raw_iter():
            last = ''
            fExec = _CheckExec(vfExec)

            def err_raiser(cls, *args):
                """Helper function for raising EvalScriptError exceptions

                cls   - subclass you want to raise

                *args - arguments

                Fills in the state of execution for you.
                """
                raise cls(*args,
                        sop=sop,
                        sop_data=sop_data,
                        sop_pc=sop_pc,
                        stack=stack, scriptIn=scriptIn, txTo=txTo, inIdx=inIdx, flags=flags,
                        altstack=altstack, vfExec=vfExec, pbegincodehash=pbegincodehash, nOpCount=nOpCount[0])


            if sop in opcodes.disabled_opcodes:
                err_raiser(EvalScriptError, 'opcode %s is disabled' % opcodes.opcode_names[sop])

            if sop > OP_16:
                nOpCount[0] += 1
                if nOpCount[0] > MAX_SCRIPT_OPCODES:
                    err_raiser(MaxOpCountError)

            def check_args(n):
                if len(stack) < n:
                    err_raiser(MissingOpArgumentsError, sop, stack, n)


            if sop <= OP_PUSHDATA4:
                if len(sop_data) > MAX_SCRIPT_ELEMENT_SIZE:
                    err_raiser(EvalScriptError,
                               'PUSHDATA of length %d; maximum allowed is %d' %
                                    (len(sop_data), MAX_SCRIPT_ELEMENT_SIZE))

                elif fExec:
                    stack.append(sop_data)
#                    continue
                    yield (stack, sop, '%s was pushed to the stack.' % e(sop_data))
                    continue

            elif fExec or (OP_IF <= sop <= OP_ENDIF):

                if opcodes.is_overridden(sop):
                    yield opcodes.override(sop, stack, txTo, inIdx, flags, execution_data, err_raiser)
                    continue

                elif sop == OP_1NEGATE or ((sop >= OP_1) and (sop <= OP_16)):
                    v = sop - (OP_1 - 1)
                    stack.append(bitcoin.core._bignum.bn2vch(v))
                    last = '%s was pushed to the stack.' % e(stack[-1])

                elif sop in _ISA_BINOP:
                    last = _BinOp(sop, stack, err_raiser)

                elif sop in _ISA_UNOP:
                    last = _UnaryOp(sop, stack, err_raiser)

                elif sop == OP_2DROP:
                    check_args(2)
                    last1 = stack.pop()
                    last2 = stack.pop()
                    last = '%s and %s were dropped.' % e(last1, last2)

                elif sop == OP_2DUP:
                    check_args(2)
                    v1 = stack[-2]
                    v2 = stack[-1]
                    stack.append(v1)
                    stack.append(v2)
                    last = '%s and %s were copied onto the top.' % e(v1, v2)

                elif sop == OP_2OVER:
                    check_args(4)
                    v1 = stack[-4]
                    v2 = stack[-3]
                    stack.append(v1)
                    stack.append(v2)
                    last = '%s and %s were copied onto the top.' % e(v1, v2)

                elif sop == OP_2ROT:
                    check_args(6)
                    v1 = stack[-6]
                    v2 = stack[-5]
                    del stack[-6]
                    del stack[-5]
                    stack.append(v1)
                    stack.append(v2)
                    last = '%s and %s were moved to the top.' % e(v1, v2)

                elif sop == OP_2SWAP:
                    check_args(4)
                    tmp = stack[-4]
                    stack[-4] = stack[-2]
                    stack[-2] = tmp

                    tmp = stack[-3]
                    stack[-3] = stack[-1]
                    stack[-1] = tmp
                    last = '%s and %s were swapped with %s and %s' % e(*stack[-4:])

                elif sop == OP_3DUP:
                    check_args(3)
                    v1 = stack[-3]
                    v2 = stack[-2]
                    v3 = stack[-1]
                    stack.append(v1)
                    stack.append(v2)
                    stack.append(v3)
                    last = '%s, %s and %s were copied onto the top.' % e(v1, v2, v3)

                # TODO stack log
                elif sop == OP_CHECKMULTISIG or sop == OP_CHECKMULTISIGVERIFY:
                    tmpScript = CScript(scriptIn[pbegincodehash:])
                    _CheckMultiSig(sop, tmpScript, stack, txTo, inIdx, err_raiser, nOpCount)

                elif sop == OP_CHECKSIG or sop == OP_CHECKSIGVERIFY:
                    check_args(2)
                    vchPubKey = stack[-1]
                    vchSig = stack[-2]
                    tmpScript = CScript(scriptIn[pbegincodehash:])

                    # Drop the signature, since there's no way for a signature to sign itself
                    #
                    # Of course, this can only come up in very contrived cases now that
                    # scriptSig and scriptPubKey are processed separately.
                    tmpScript = FindAndDelete(tmpScript, CScript([vchSig]))

                    ok = _CheckSig(vchSig, vchPubKey, tmpScript, txTo, inIdx,
                                   err_raiser)
                    if not ok and sop == OP_CHECKSIGVERIFY:
                        err_raiser(VerifyOpFailedError, sop)

                    else:
                        stack.pop()
                        stack.pop()

                        if ok:
                            if sop != OP_CHECKSIGVERIFY:
                                stack.append(b"\x01")
                        else:
                            stack.append(b"\x00")
                        # TODO implement
                        if txTo is None:
                            err_raiser(EvalScriptError, 'CHECKSIG opcodes require a spending transaction.')
                        else:
                            last1 = 'After %s %s,' % ('CHECKSIG' if sop == OP_CHECKSIG else 'CHECKSIGVERIFY', 'passed' if ok else 'failed')
                            last2 = '%s was pushed to the stack.' % e(stack[-1])
                            last = ' '.join([last1, last2])

                elif sop == OP_CODESEPARATOR:
                    last = '(code separator)'
                    pbegincodehash = sop_pc

                elif sop == OP_DEPTH:
                    bn = len(stack)
                    stack.append(bitcoin.core._bignum.bn2vch(bn))
                    last = '%s (number of stack items) was pushed to the stack.' % e(stack[-1])

                elif sop == OP_DROP:
                    check_args(1)
                    last1 = stack.pop()
                    last = '%s was dropped.' % e(last1)

                elif sop == OP_DUP:
                    check_args(1)
                    v = stack[-1]
                    stack.append(v)
                    last = '%s was copied onto the top.' % e(v)

                elif sop == OP_ELSE:
                    if len(vfExec) == 0:
                        err_raiser(EvalScriptError, 'ELSE found without prior IF')
                    vfExec[-1] = not vfExec[-1]
                    last = 'Skipped ELSE statement.'
                    if vfExec[-1]:
                        last = 'Entered ELSE statement.'

                elif sop == OP_ENDIF:
                    last = 'End of IF statement.'
                    if len(vfExec) == 0:
                        err_raiser(EvalScriptError, 'ENDIF found without prior IF')
                    vfExec.pop()

                elif sop == OP_EQUAL:
                    check_args(2)
                    v1 = stack.pop()
                    v2 = stack.pop()

                    if v1 == v2:
                        stack.append(b"\x01")
                    else:
                        stack.append(b"\x00")
                    last = '%s EQUALSIGN %s, so %s was pushed to the stack.' % e(v1, v2, stack[-1])
                    last = last.replace('EQUALSIGN', '==' if v1 == v2 else '!=')

                elif sop == OP_EQUALVERIFY:
                    check_args(2)
                    v1 = stack[-1]
                    v2 = stack[-2]

                    if v1 == v2:
                        last1 = stack.pop()
                        last2 = stack.pop()
                        last = 'EQUALVERIFY passed so %s and %s were dropped.' % e(last1, last2)
                    else:
                        err_raiser(VerifyOpFailedError, sop)

                elif sop == OP_FROMALTSTACK:
                    if len(altstack) < 1:
                        err_raiser(MissingOpArgumentsError, sop, altstack, 1)
                    v = altstack.pop()
                    stack.append(v)
                    last = '%s was pushed from the altstack to the stack.' % e(v)

                elif sop == OP_HASH160:
                    check_args(1)
                    last1 = stack.pop()
                    stack.append(bitcoin.core.serialize.Hash160(last1))
                    last = '%s (HASH160 of %s) was pushed to the stack.' % e(stack[-1], last1)

                elif sop == OP_HASH256:
                    check_args(1)
                    last1 = stack.pop()
                    stack.append(bitcoin.core.serialize.Hash(last1))
                    last = '%s (HASH256 of %s) was pushed to the stack.' % e(stack[-1], last1)

                elif sop == OP_IF or sop == OP_NOTIF:
                    val = False

                    if fExec:
                        check_args(1)
                        vch = stack.pop()
                        val = _CastToBool(vch)
                        if sop == OP_NOTIF:
                            val = not val

                    if val:
                        last = 'Entered IF statement.'
                    else:
                        last = 'Skipped IF statement.'
                    vfExec.append(val)


                elif sop == OP_IFDUP:
                    check_args(1)
                    vch = stack[-1]
                    if _CastToBool(vch):
                        stack.append(vch)
                        last = 'The top stack item %s was duplicated.' % e(stack[-1])
                    else:
                        last = 'The top stack item %s was not duplicated.' % e(stack[-1])

                elif sop == OP_NIP:
                    check_args(2)
                    last1 = stack[-2]
                    del stack[-2]
                    last = '%s was removed.' % e(last1)

                elif sop == OP_NOP or (sop >= OP_NOP1 and sop <= OP_NOP10):
                    last = '(NOP)'

                elif sop == OP_OVER:
                    check_args(2)
                    vch = stack[-2]
                    stack.append(vch)
                    last = '%s was copied onto the top.' % e(vch)

                elif sop == OP_PICK or sop == OP_ROLL:
                    check_args(2)
                    n = _CastToBigNum(stack.pop(), err_raiser)
                    if n < 0 or n >= len(stack):
                        err_raiser(EvalScriptError, "Argument for %s out of bounds" % opcodes.opcode_names[sop])
                    vch = stack[-n-1]
                    rolled = False # for "last"
                    if sop == OP_ROLL:
                        rolled = True
                        del stack[-n-1]
                    stack.append(vch)
                    if rolled:
                        last = '%s was moved to the top.' % e(vch)
                    else:
                        last = '%s was copied onto the top.' % e(vch)

                elif sop == OP_RETURN:
                    err_raiser(EvalScriptError, "OP_RETURN called")

                elif sop == OP_RIPEMD160:
                    check_args(1)

                    h = hashlib.new('ripemd160')
                    tmp = stack.pop()
                    h.update(tmp)
                    stack.append(h.digest())
                    last = '%s (RIPEMD160 of %s) was pushed to the stack.' % e(stack[-1], tmp)

                elif sop == OP_ROT:
                    check_args(3)
                    tmp = stack[-3]
                    stack[-3] = stack[-2]
                    stack[-2] = tmp

                    tmp = stack[-2]
                    stack[-2] = stack[-1]
                    stack[-1] = tmp
                    last = '%s, %s and %s were rotated to the left.' % e(stack[-1], stack[-3], stack[-2])

                elif sop == OP_SIZE:
                    check_args(1)
                    bn = len(stack[-1])
                    stack.append(bitcoin.core._bignum.bn2vch(bn))
                    last = '%s (string length of %s) was pushed to the stack.' % e(stack[-1], stack[-2])

                elif sop == OP_SHA1:
                    check_args(1)
                    last1 = stack.pop()
                    stack.append(hashlib.sha1(last1).digest())
                    last = '%s (SHA1 of %s) was pushed to the stack.' % e(stack[-1], last1)

                elif sop == OP_SHA256:
                    check_args(1)
                    last1 = stack.pop()
                    stack.append(hashlib.sha256(last1).digest())
                    last = '%s (SHA256 of %s) was pushed to the stack.' % e(stack[-1], last1)

                elif sop == OP_SWAP:
                    check_args(2)
                    tmp = stack[-2]
                    stack[-2] = stack[-1]
                    stack[-1] = tmp
                    last = '%s and %s were swapped.' % e(stack[-1], stack[-2])

                elif sop == OP_TOALTSTACK:
                    check_args(1)
                    v = stack.pop()
                    altstack.append(v)
                    last = '%s was pushed to the altstack.' % e(v)

                elif sop == OP_TUCK:
                    check_args(2)
                    vch = stack[-1]
                    stack.insert(len(stack) - 2, vch)
                    last = '%s was copied into the second-to-top position.' % e(vch)

                elif sop == OP_VERIFY:
                    check_args(1)
                    v = _CastToBool(stack[-1])
                    if v:
                        last1 = stack.pop()
                        last = '%s was dropped after VERIFY passed.' % e(last1)
                    else:
                        raise err_raiser(VerifyOpFailedError, sop)

                elif sop == OP_WITHIN:
                    check_args(3)
                    bn3 = _CastToBigNum(stack[-1], err_raiser)
                    bn2 = _CastToBigNum(stack[-2], err_raiser)
                    bn1 = _CastToBigNum(stack[-3], err_raiser)
                    stack.pop()
                    stack.pop()
                    stack.pop()
                    v = (bn2 <= bn1) and (bn1 < bn3)
                    if v:
                        stack.append(b"\x01")
                    else:
                        stack.append(b"\x00")
                    last = '%s (the result of %s <= %s < %s) was pushed to the stack.' % e(stack[-1], bn2, bn1, bn3)

                else:
                    err_raiser(EvalScriptError, 'unsupported opcode 0x%x' % sop)

            yield (stack, sop, last)

            # size limits
            if len(stack) + len(altstack) > MAX_STACK_ITEMS:
                err_raiser(EvalScriptError, 'max stack items limit reached')

        # Unterminated IF/NOTIF/ELSE block
        if len(vfExec):
            raise EvalScriptError('Unterminated IF/ELSE block',
                                  stack=stack,
                                  scriptIn=scriptIn,
                                  txTo=txTo,
                                  inIdx=inIdx,
                                  flags=flags)


# Re-implemented here from python-bitcoinlib for stack log.
def _UnaryOp(opcode, stack, err_raiser):
    if len(stack) < 1:
        err_raiser(MissingOpArgumentsError, opcode, stack, 1)
    bn = _CastToBigNum(stack[-1], err_raiser)
    last2 = stack.pop()
    last1 = ''

    if opcode == OP_1ADD:
        bn += 1
        last1 = '+= 1'

    elif opcode == OP_1SUB:
        bn -= 1
        last1 = '-= 1'

    elif opcode == OP_NEGATE:
        bn = -bn
        last1 = '*= -1'

    elif opcode == OP_ABS:
        if bn < 0:
            bn = -bn
        last1 = '= |%d|' % bn

    elif opcode == OP_NOT:
        bn = long(bn == 0)
        last1 = 'NOT %d' % bn

    elif opcode == OP_0NOTEQUAL:
        bn = long(bn != 0)
        last1 = '= %d != 0' % bn

    else:
        raise AssertionError("Unknown unary opcode encountered; this should not happen")

    stack.append(bitcoin.core._bignum.bn2vch(bn))
    last = '%s %s' % (last2, last1)
    return last


# Re-implemented here from python-bitcoinlib for stack log.
def _BinOp(opcode, stack, err_raiser):
    if len(stack) < 2:
        err_raiser(MissingOpArgumentsError, opcode, stack, 2)

    bn2 = _CastToBigNum(stack[-1], err_raiser)
    bn1 = _CastToBigNum(stack[-2], err_raiser)

    # We don't pop the stack yet so that OP_NUMEQUALVERIFY can raise
    # VerifyOpFailedError with a correct stack.
    last1 = ''

    if opcode == OP_ADD:
        bn = bn1 + bn2
        last1 = '+'

    elif opcode == OP_SUB:
        bn = bn1 - bn2
        last1 = '-'

    elif opcode == OP_BOOLAND:
        bn = long(bn1 != 0 and bn2 != 0)
        last1 = 'AND'

    elif opcode == OP_BOOLOR:
        bn = long(bn1 != 0 or bn2 != 0)
        last1 = 'OR'

    elif opcode == OP_NUMEQUAL:
        bn = long(bn1 == bn2)
        last1 = '=='

    elif opcode == OP_NUMEQUALVERIFY:
        bn = long(bn1 == bn2)
        if not bn:
            err_raiser(VerifyOpFailedError, opcode)
        else:
            # No exception, so time to pop the stack
            stack.pop()
            stack.pop()
            return

    elif opcode == OP_NUMNOTEQUAL:
        bn = long(bn1 != bn2)
        last1 = '!='

    elif opcode == OP_LESSTHAN:
        bn = long(bn1 < bn2)
        last1 = '<'

    elif opcode == OP_GREATERTHAN:
        bn = long(bn1 > bn2)
        last1 = '>'

    elif opcode == OP_LESSTHANOREQUAL:
        bn = long(bn1 <= bn2)
        last1 = '<='

    elif opcode == OP_GREATERTHANOREQUAL:
        bn = long(bn1 >= bn2)
        last1 = '>='

    elif opcode == OP_MIN:
        last1 = 'MIN'
        if bn1 < bn2:
            bn = bn1
        else:
            bn = bn2

    elif opcode == OP_MAX:
        last1 = 'MAX'
        if bn1 > bn2:
            bn = bn1
        else:
            bn = bn2

    else:
        raise AssertionError("Unknown binop opcode encountered; this should not happen")

    last = '%s (%s %s %s) was pushed to the stack.' % (bn, bn1, last1, bn2)
    stack.pop()
    stack.pop()
    stack.append(bitcoin.core._bignum.bn2vch(bn))
    return last


