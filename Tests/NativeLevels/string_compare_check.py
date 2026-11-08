"""Independent original-derived checks for the bounded CRT string adapter.

Original CRT instructions run only on the reference side of this check. The
comparison includes all CPU registers, flags, x87 state, live caller stack,
input storage and program globals. Retired callee stack is outside this cdecl
contract. This is platform boundary evidence, not family admission or app parity.
"""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import random
import struct

from unicorn import Uc, UcError, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
    UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP,
    UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EFLAGS, UC_X86_REG_FPCW,
    UC_X86_REG_FPSW, UC_X86_REG_FPTAG, UC_X86_REG_FP0)
from Tests.clawparity.program import claw
from Tests.NativeMenuBase.trace import MenuTrace, Blocked
from Tests.NativeLevels.string_compare_fixture import StringCompareFixture
from Tests.NativeLevels.storage import read_trace, fingerprint

ROOT = Path(__file__).resolve().parents[2]
ENTRY, COMPARE, BOUND = 0x4a3dc0, 0x4a3cf0, 4096
STACK_BASE, ARENA, STOP = 0x02000000, 0x61000000, 0x70000080
REGISTERS = dict(eax=UC_X86_REG_EAX, ebx=UC_X86_REG_EBX,
    ecx=UC_X86_REG_ECX, edx=UC_X86_REG_EDX, esi=UC_X86_REG_ESI,
    edi=UC_X86_REG_EDI, ebp=UC_X86_REG_EBP, esp=UC_X86_REG_ESP,
    eip=UC_X86_REG_EIP, eflags=UC_X86_REG_EFLAGS,
    fpcw=UC_X86_REG_FPCW, fpsw=UC_X86_REG_FPSW, fptag=UC_X86_REG_FPTAG,
    **{f'fp{i}': UC_X86_REG_FP0+i for i in range(8)})


class Probe(StringCompareFixture, MenuTrace):
    pass


def create(program):
    probe = object.__new__(Probe)
    probe.program = program
    probe.machine = Uc(UC_ARCH_X86, UC_MODE_32)
    probe.machine.mem_map(program.base, (program.size+4095)&~4095)
    for section in program.sections:
        probe.machine.mem_write(section.address, section.data)
    for base, size in ((STACK_BASE, 0x10000), (ARENA, 0x10000), (STOP&~4095, 4096)):
        probe.machine.mem_map(base, size)
    probe.platform, probe.platform_names = Counter(), {}
    probe.physical_events = []
    probe.deny_platform = None
    probe.phase = 'string-compare-control'
    probe.imports = {}
    return probe


def setup(probe, entry, left, right, variant=0, alias=False, *,
          entry_stack=None, continuation=STOP):
    machine = probe.machine
    probe.platform.clear()
    probe.platform_names.clear()
    probe.physical_events.clear()
    probe.deny_platform = None
    probe.put(0x540e00, 0)
    probe.put(0x540e88, 0)
    sp = STACK_BASE+0x8000+(variant%8)*4 if entry_stack is None else entry_stack
    if not STACK_BASE+256 <= sp <= STACK_BASE+0x10000-256:
        raise ValueError('Observed caller stack is outside the bounded control arena')
    machine.mem_write(sp-256, b'\xa5'*512)
    machine.mem_write(ARENA, b'\x96'*0x10000)
    lp, rp = ARENA+17, ARENA+0x3003
    machine.mem_write(lp, left+b'\0')
    machine.mem_write(rp, right+b'\0')
    if alias:
        rp = lp
    for index, reg in enumerate((UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
            UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP)):
        machine.reg_write(reg, (0x1234ab98+index*0x11111111+variant*0x10001)&0xffffffff)
    machine.reg_write(UC_X86_REG_ESP, sp)
    machine.reg_write(UC_X86_REG_EIP, entry)
    machine.reg_write(UC_X86_REG_EFLAGS, (0x202, 0x293, 0x246, 0xad7)[variant%4])
    machine.reg_write(UC_X86_REG_FPCW, 0x027f)
    machine.reg_write(UC_X86_REG_FPSW, 0x0100)
    for index in range(8):
        machine.reg_write(UC_X86_REG_FP0+index, (0x8000000000000000+index*0x10000000000000, 0x3fff+index))
    machine.reg_write(UC_X86_REG_FPTAG, 0xfff0)
    probe.put(sp, continuation)
    probe.put(sp+4, lp)
    probe.put(sp+8, rp)
    return sp


def snapshot(probe, sp):
    machine = probe.machine
    def digest(address, size):
        return hashlib.sha256(machine.mem_read(address, size)).hexdigest()
    return dict(cpu={name: machine.reg_read(reg) for name, reg in REGISTERS.items()},
        live_stack=digest(sp, 256), inputs=digest(ARENA, 0x10000),
        program=digest(probe.program.base, (probe.program.size+4095)&~4095))


def pairs():
    values = [
        ('empty', b'', b''), ('equal', b'ConveyorBelt', b'ConveyorBelt'),
        ('mixed-case', b'LeVeL_ConveyRight', b'LEVEL_CONVEYRIGHT'),
        ('less-nonunit', b'a', b'z'), ('greater-nonunit', b'z', b'a'),
        ('left-empty', b'', b'Z'), ('right-empty', b'Z', b''),
        ('prefix-left', b'Level', b'LEVEL_'), ('prefix-right', b'LEVEL_', b'Level'),
        ('fold-then-differ', b'AAx', b'aAy'), ('fold-reverse', b'aAy', b'AAx'),
        ('after-nul', b'ab\0ignored', b'AB\0DIFFERENT'),
        ('maximum', b'a'*(BOUND-1), b'A'*(BOUND-1)),
        ('maximum-last-different', b'a'*(BOUND-2)+b'Z', b'A'*(BOUND-2)+b'B'),
    ]
    # Explicit boundary coverage does not depend on the random seed.
    for value in (1, 9, 31, 32, 64, 65, 66, 90, 91, 96, 97, 98, 122, 123, 126, 127):
        for other in (64, 65, 90, 91, 96, 97, 122, 123):
            values.append((f'byte-{value}-{other}', bytes([value]), bytes([other])))
    random_source = random.Random(0x4a3dc0)
    for index in range(40):
        base = bytes(random_source.randrange(1, 128) for _ in range(random_source.randrange(0, 96)))
        other = base.swapcase() if index%2 else base[:len(base)//2]+b'Z'
        values.append((f'deterministic-{index}', base, other))
    return values


def original_only(machine, address, size, user):
    if not (0x4a3cf0 <= address < 0x4a3d43 or 0x4a3dbb <= address < 0x4a3de6):
        raise AssertionError(f'Original left elected C-locale single-byte path: {address:#x}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', action='append', type=Path, default=[],
        help='Retained adapter replay whose observed string operands are also compared')
    args = parser.parse_args()
    program = claw()
    original, native = create(program), create(program)
    original.machine.hook_add(UC_HOOK_CODE, original_only)
    positives, negatives, failures = [], [], []
    observed = {COMPARE: [], ENTRY: []}
    trace_inputs, seen, operand_pairs = [], set(), set()
    def integer(value):
        return int(value, 0) if isinstance(value, str) else value
    for path in args.trace:
        trace = read_trace(path)
        events = trace['string_compare_boundary']['comparisons']
        trace_inputs.append(dict(path=str(path), sha256=fingerprint(path), comparisons=len(events)))
        for event in events:
            entry = integer(event['entry'])
            if entry not in observed:
                raise ValueError(f'Unelected string comparison entry in retained evidence: {entry:#x}')
            left, right = event['left'].encode('ascii'), event['right'].encode('ascii')
            sp, continuation = integer(event['entry_stack']), integer(event['continuation'])
            if not program.base <= continuation < program.base+program.size:
                raise ValueError('Observed continuation is outside the original program')
            operand_pairs.add((entry, left, right))
            key = entry, left, right, sp, continuation
            if key not in seen:
                seen.add(key)
                observed[entry].append((f'observed-{len(seen)}', left, right,
                    sp, continuation, integer(event['result'])&0xffffffff))
    if 2*len(pairs())+len(seen)+35 > 600:
        raise ValueError('Observed comparison contexts exceed the bounded 600-control budget')
    for entry in (COMPARE, ENTRY):
        profiles = [(name, left, right, None, STOP, None) for name, left, right in pairs()]
        for index, (name, left, right, entry_stack, continuation, retained_result) in enumerate(profiles+observed[entry]):
            alias = name == 'equal'
            sp = setup(original, entry, left, right, index, alias,
                entry_stack=entry_stack, continuation=continuation)
            setup(native, entry, left, right, index, alias,
                entry_stack=entry_stack, continuation=continuation)
            before = snapshot(original, sp)
            try:
                original.machine.emu_start(entry, continuation, count=200000)
                native.fixture(entry)
                expected, actual = snapshot(original, sp), snapshot(native, sp)
                assert expected == actual, {key:dict(expected=expected[key], actual=actual[key])
                    for key in expected if expected[key] != actual[key]}
                assert expected['cpu']['esp'] == sp+4 and expected['cpu']['eip'] == continuation
                assert all(expected[key] == before[key] for key in ('live_stack', 'inputs', 'program'))
                result = expected['cpu']['eax']
                assert result in (0, 1, 0xffffffff)
                if retained_result is not None:
                    assert result == retained_result, 'Recorded platform return differs from original'
                positives.append(dict(entry=hex(entry), name=name, result=result,
                    sign=-1 if result == 0xffffffff else result,
                    entry_stack=hex(sp), continuation=hex(continuation)))
            except (AssertionError, Blocked, UcError) as error:
                failures.append(dict(entry=hex(entry), name=name, reason=str(error)))
    for entry in (COMPARE, ENTRY):
        for name in ('left-nonascii', 'right-nonascii', 'left-unterminated',
                'right-unterminated', 'left-null', 'right-null', 'left-unmapped',
                'right-unmapped', 'left-terminator-too-late', 'right-terminator-too-late',
                'left-trailing-0x80', 'right-trailing-0xff', 'unmapped-frame',
                'truncated-frame', 'locale', 'multibyte', 'withheld'):
            sp = setup(native, entry, b'LEVEL_CONVEYRIGHT', b'level_conveyright')
            lp, rp = native.word(sp+4), native.word(sp+8)
            if name == 'unmapped-frame':
                native.machine.reg_write(UC_X86_REG_ESP, 0x11110000)
            elif name == 'truncated-frame':
                native.machine.reg_write(UC_X86_REG_ESP, STACK_BASE+0xfff8)
                native.put(STACK_BASE+0xfff8, STOP)
                native.put(STACK_BASE+0xfffc, lp)
            elif 'trailing' in name:
                native.machine.mem_write(lp, b'a\0')
                native.machine.mem_write(rp, b'z\0')
                native.machine.mem_write(lp if name.startswith('left') else rp,
                    b'a\x80\0' if name.startswith('left') else b'z\xff\0')
            elif name.endswith('terminator-too-late'):
                native.machine.mem_write(lp if name.startswith('left') else rp, b'a'*BOUND+b'\0')
            elif name.endswith('nonascii'):
                native.machine.mem_write(lp if name.startswith('left') else rp, b'\xc0\0')
            elif name.endswith('unterminated'):
                native.machine.mem_write(lp if name.startswith('left') else rp, b'a'*BOUND)
            elif name.endswith('null') or name.endswith('unmapped'):
                native.put(sp+(4 if name.startswith('left') else 8), 0 if name.endswith('null') else 0x11110000)
            elif name == 'locale':
                native.put(0x540e88, 1)
            elif name == 'multibyte':
                native.put(0x540e00, 932)
            elif name == 'withheld':
                native.deny_platform = entry
            before = snapshot(native, sp)
            try:
                native.fixture(entry)
            except Blocked as error:
                if snapshot(native, sp) == before:
                    negatives.append(dict(entry=hex(entry), name=name, reason=str(error)))
                else:
                    failures.append(dict(entry=hex(entry), name=name, reason='Refusal changed guest CPU or memory'))
            except Exception as error:
                failures.append(dict(entry=hex(entry), name=name, reason=f'Unstructured refusal: {error!r}'))
            else:
                failures.append(dict(entry=hex(entry), name=name, reason='Unsupported input accepted'))
    sp = setup(native, 0x4f0000, b'a', b'a')
    before = snapshot(native, sp)
    try:
        native.fixture(0x4f0000)
    except Blocked as error:
        if snapshot(native, sp) == before:
            negatives.append(dict(entry='0x4f0000', name='unknown-entry', reason=str(error)))
        else:
            failures.append(dict(name='unknown-entry', reason='Refusal changed guest state'))
    else:
        failures.append(dict(name='unknown-entry', reason='Unknown entry accepted'))
    report = dict(schema=1, status='pass' if not failures else 'fail',
        executable_sha256=program.sha256,
        adapter_sha256=hashlib.sha256((ROOT/'Tests/NativeLevels/string_compare_fixture.py').read_bytes()).hexdigest(),
        checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        retained_traces=trace_inputs, observed_operand_pairs=len(operand_pairs),
        observed_caller_contexts=len(seen),
        positive_count=len(positives), negative_count=len(negatives), positives=positives,
        negatives=negatives, failures=failures,
        scope='Bounded ASCII C-locale platform boundary; live caller stack and complete CPU, input and program preservation; no route or app claim')
    out = ROOT/'work/native-level-string-compare/result.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({key: report[key] for key in ('status', 'positive_count', 'negative_count', 'failures')}))
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
