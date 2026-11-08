"""Independent native-owner join reference; unchanged x86 policy and sprintf.

Only physical beep/log/dialog and CRT allocation/locking are substituted. The
RET-only display sink executes. All derived text and observations stay in work/.
This is a focused native join, not family admission or visible UI acceptance.
"""
import json
import re
import struct
import sys
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_REG_EBX
from unicorn.x86_const import UC_X86_REG_ESP
from Tests.clawparity.program import claw
from Tests.clawparity.kernel import Machine, STACK_BASE, STACK_SIZE

ROOTS = ((False, 0x4b4ed0, 0x4b520b), (True, 0x4bd260, 0x4bda95))
FILENAME = 0x3000000


def instructions(program, start, end):
    section = next(s for s in program.sections if s.address <= start < s.address + len(s.data))
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    return list(decoder.disasm(section.data[start-section.address:end-section.address], start))


def selection_inputs(code):
    """Read comparison constants and bounded indexed dispatch from original bytes."""
    values = {0, 1, 0xffffffff, 0x12345678, 0x80000000, 0x7fffffff}
    for index, ins in enumerate(code):
        if ins.mnemonic == 'cmp':
            for op in ins.operands:
                if op.type == X86_OP_IMM and op.imm & 0xffffffff >= 0x80000000:
                    values.add(op.imm & 0xffffffff)
        if ins.mnemonic == 'lea' and len(ins.operands) == 2:
            op = ins.operands[1]
            if op.type == X86_OP_MEM and op.mem.base == X86_REG_EBX and op.mem.disp:
                following = code[index+1]
                if following.mnemonic == 'cmp' and following.operands[-1].type == X86_OP_IMM:
                    bound = following.operands[-1].imm
                    if 0 <= bound <= 64:
                        base = -op.mem.disp & 0xffffffff
                        values.update((base+n) & 0xffffffff for n in range(-1, bound+2))
    return sorted(values)


class Reference:
    def __init__(self, program):
        self.machine = Machine(program, FILENAME, 0x40000)
        self.stub_function = {v:k for k,v in self.machine.import_stub.items()}
        self.machine.on_external = self.external
        for address in (0x4a48e0, 0x4a7bc0, 0x4a7c40):
            self.machine.intercept(address)
        self.machine.observe(0x4a3920, self.format_entry)
        self.machine.observe(0x4bc110, self.display_sink)
        self.code = {}
        for display, start, end in ROOTS:
            code = instructions(program, start, end)
            self.code[display] = code
            for ins in code:
                if ins.mnemonic == 'call' and ins.op_str == '0x4a3920':
                    self.machine.observe(ins.address+ins.size, self.format_return)
        self.pristine = self.machine.read(program.data_start, program.base+program.size-program.data_start)
        self.data_start = program.data_start

    def string(self, token):
        data = bytearray()
        for offset in range(4096):
            value = self.machine.read(token+offset, 1)
            if value == b'\0':
                return data.decode('cp1252')
            data.extend(value)
        raise AssertionError('unterminated reference string')

    def event(self, kind, args, text='', caption=''):
        self.events.append(dict(kind=kind, arguments=list(args), text=text, caption=caption))
        occurrence = sum(e['kind'] == kind for e in self.events)
        for mutation in self.row['mutations']:
            if mutation['kind'] == kind and mutation['occurrence'] == occurrence:
                self.machine.write(self.flags, struct.pack('<4I', *mutation['flags']))

    def format_entry(self, machine, address):
        sp = machine.register(UC_X86_REG_ESP)
        destination, fmt = machine.words(sp+4, 2)
        conversions = re.findall(r'%(?:%|s|i|d)', self.string(fmt))
        count = 2 + sum(c != '%%' for c in conversions)
        self.pending_format = (destination, machine.words(sp+4, count))

    def format_return(self, machine, address):
        destination, args = self.pending_format
        self.event('format', args, self.string(destination))

    def display_sink(self, machine, address):
        self.event('display-sink', machine.words(machine.register(UC_X86_REG_ESP)+4, 1))

    def external(self, machine, address):
        function = self.stub_function.get(address, address)
        sp = machine.register(UC_X86_REG_ESP)
        if function in (0x4a7bc0, 0x4a7c40):
            machine.return_from_external(0, 0)
        elif function == 0x4a48e0:
            size = machine.words(sp+4, 1)[0]
            token = self.heap
            self.heap += (size+15) & ~15
            assert self.heap < FILENAME+0x40000
            machine.return_from_external(token, 0)
        elif function == 0x546ca4:
            self.event('beep', machine.words(sp+4, 1))
            machine.return_from_external(1, 4)
        elif function == 0x546a08:
            args = machine.words(sp+4, 1)
            self.event('log', args, self.string(args[0]))
            machine.return_from_external(0, 4)
        elif function == 0x546d48:
            args = machine.words(sp+4, 4)
            self.event('dialog', args, self.string(args[1]), self.string(args[2]))
            machine.return_from_external(1, 16)
        else:
            raise AssertionError(f'unexpected original physical dependency {function:#x}')

    def run(self, row):
        self.row = row
        self.events = []
        self.flags = 0x54139c if row['display'] else 0x54130c
        self.heap = FILENAME+0x1000
        self.machine.write(self.data_start, self.pristine)
        self.machine.write(STACK_BASE, bytes(STACK_SIZE))
        self.machine.write(FILENAME, b'C:\\join\\caf\xe9.cpp\0')
        self.machine.write(self.flags, struct.pack('<4I', *row['flags']))
        self.machine.reset_x87()
        result = self.machine.call(0x4bd260 if row['display'] else 0x4b4ed0,
                                   arguments=(row['filename'], row['line'], row['result']))
        assert result.completed, row['name']
        return dict(row, events=self.events, finalFlags=list(self.machine.words(self.flags, 4)))


def profiles(reference):
    for display, _, _ in ROOTS:
        prefix = 'display' if display else 'audio'
        def row(name, flags=(1,1,1,1), filename=FILENAME, line=42, result=0xffffffff, mutations=()):
            return dict(name=f'{prefix}-{name}', display=display, flags=list(flags), filename=filename,
                        line=line, result=result, mutations=list(mutations))
        for bits in range(16):
            yield row(f'flags-{bits}', flags=[(bits >> i) & 1 for i in range(4)])
        yield row('nonboolean-flags', flags=[0x80000000,2,0xffffffff,17])
        for value in selection_inputs(reference.code[display]):
            yield row(f'selection-{value:08x}', result=value)
        for filename in (0,FILENAME):
            for line in (0,1,0x7fffffff,0x80000000,0xffffffff):
                yield row(f'filename-{filename:x}-line-{line:x}', filename=filename, line=line)
        def mutation(kind, flags, occurrence=1):
            return dict(kind=kind, occurrence=occurrence, flags=list(flags))
        yield row('beep-enables-policy', flags=(0,0,1,0), mutations=[mutation('beep',(1,1,0,0))])
        yield row('beep-disables-policy', mutations=[mutation('beep',(0,0,0,0))])
        yield row('first-format-disables-output', mutations=[mutation('format',(0,1,0,0))])
        yield row('first-format-enables-output', flags=(0,1,0,0), mutations=[mutation('format',(1,1,0,0))])
        yield row('output-format-disables-dialog', mutations=[mutation('format',(1,0,0,0),2)])
        sink = 'display-sink' if display else 'log'
        yield row('sink-disables-dialog', mutations=[mutation(sink,(1,0,0,0))])
        yield row('sink-enables-dialog', flags=(1,0,0,0), mutations=[mutation(sink,(0,1,0,0))])
        yield row('dialog-mutates-flags', mutations=[mutation('dialog',(0,0,0,0))])


def main():
    program = claw()
    reference = Reference(program)
    rows = [reference.run(row) for row in profiles(reference)]
    Path(sys.argv[1]).write_text(json.dumps(dict(originalSHA256=program.sha256, rows=rows), indent=2)+'\n')
    print(json.dumps(dict(originalReference='pass', profiles=len(rows), wholeOriginalSprintf=True)))

if __name__ == '__main__':
    main()
