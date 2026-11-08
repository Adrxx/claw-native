"""Bounded paper-fader platform comparison; no startup replay or admission claim.

Run with work/test-env/bin/python -m Tests.NativeLevelTwo.check_fader_power.
The original CRT is executed only by this local comparison, never by the fixture.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import *
from Tests.clawparity.program import claw
from Tests.NativeLevelTwo.trace import LevelTwoTrace
from Tests.NativeLevels.storage import read_trace, stored_path
from Tests.NativeMenuBase.trace import Blocked, ROOT, MenuTrace

POWER = 0x4f1b30
CALLERS = (0x4ee6cf, 0x4ee6eb, 0x4ee718, 0x4ee738)
STACK = 0x2008000
STOP = 0x3000000
OBJECT = 0x4000000
RECT = OBJECT + 0x100


def machine(program):
    u = Uc(UC_ARCH_X86, UC_MODE_32)
    u.mem_map(program.base, (program.size + 4095) & ~4095)
    for section in program.sections:
        u.mem_write(section.address, section.data)
    for address, size in ((0x2000000, 0x10000), (STOP, 4096), (OBJECT, 4096)):
        u.mem_map(address, size)
    return u


def trace_for(u):
    trace = LevelTwoTrace.__new__(LevelTwoTrace)
    trace.machine = u
    trace.startup_paper = True
    trace.display_mode = (640, 480, 8)
    trace.math_events = []
    trace.last_transfer = None
    return trace


def x87(u):
    status, tags = u.reg_read(UC_X86_REG_FPSW), u.reg_read(UC_X86_REG_FPTAG)
    top = (status >> 11) & 7
    # Empty/dead register payloads are not architectural inputs or returns.
    live = [(i, list(u.reg_read(UC_X86_REG_FP0 + i))) for i in range(8)
            if ((tags >> (2*i)) & 3) != 3]
    return dict(control=u.reg_read(UC_X86_REG_FPCW), status=status,
                tags=tags, top=top, live=live)


def fp_setup(u, top, base, exponent=2., tails=(7.25, -13.5)):
    u.reg_write(UC_X86_REG_FPCW, 0x27f)
    u.reg_write(UC_X86_REG_FPSW, ((top + 2 + len(tails)) & 7) << 11)
    u.reg_write(UC_X86_REG_FPTAG, 0xffff)
    trace = trace_for(u)
    for value in reversed((exponent, base, *tails)):
        trace.x87_result(0, value)
    assert x87(u)['top'] == top


def power_case(program, *, base, top, caller, captured=None, flags=0):
    results = []
    for fixture in (False, True):
        u = machine(program)
        trace = trace_for(u)
        sp = STACK
        if captured is None:
            fp_setup(u, top, base)
            u.reg_write(UC_X86_REG_FPSW, (top << 11) | flags)
            u.reg_write(UC_X86_REG_ESP, sp)
        else:
            sp = int(captured['stack'], 16)
            u.reg_write(UC_X86_REG_ESP, sp)
            for name, value in captured['registers'].items():
                u.reg_write(globals()['UC_X86_REG_' + name.upper()], int(value, 16))
            for register, name in ((UC_X86_REG_FPCW, 'fpcw'), (UC_X86_REG_FPSW, 'fpsw'),
                                   (UC_X86_REG_FPTAG, 'fptag')):
                u.reg_write(register, captured[name])
            for i, value in enumerate(captured['fp_registers']):
                u.reg_write(UC_X86_REG_FP0 + i, tuple(value))
        u.mem_write(sp, struct.pack('<I', caller))
        u.reg_write(UC_X86_REG_EIP, POWER)
        before = x87(u)
        if fixture:
            trace.math_fixture(POWER)
        else:
            u.emu_start(POWER, caller, count=20000)
        assert u.reg_read(UC_X86_REG_EIP) == caller
        assert u.reg_read(UC_X86_REG_ESP) == sp + 4
        results.append(x87(u))
    if results[0] != results[1]:
        raise AssertionError(dict(kind='power', base=base, top=top, caller=hex(caller),
                                  before=before, original=results[0], fixture=results[1]))
    return dict(base=base, top=top, flags=flags, caller=hex(caller), captured=captured is not None,
                result=results[0])


def consumer_case(program, x, y, top):
    results, operands = [], []
    for fixture in (False, True):
        u = machine(program)
        trace = trace_for(u)
        u.reg_write(UC_X86_REG_ESP, STACK)
        u.mem_write(STACK, struct.pack('<I', STOP))
        u.reg_write(UC_X86_REG_ECX, OBJECT)
        trace.put(OBJECT + 0x38, RECT)
        trace.put(OBJECT + 0x4c, x & 0xffffffff)
        trace.put(OBJECT + 0x50, y & 0xffffffff)
        trace.put(RECT + 0x14, 480)
        trace.put(RECT + 0x18, 640)
        u.reg_write(UC_X86_REG_FPCW, 0x27f)
        u.reg_write(UC_X86_REG_FPSW, ((top + 1) & 7) << 11)
        u.reg_write(UC_X86_REG_FPTAG, 0xffff)
        trace.x87_result(0, 7.25)
        seen = []
        def hook(machine, address, size, data):
            if address == POWER:
                seen.append(dict(caller=hex(trace.word(machine.reg_read(UC_X86_REG_ESP))),
                                 operands=[trace.x87_value(0), trace.x87_value(1)]))
                if fixture:
                    trace.math_fixture(address)
            elif fixture and address == 0x4a30e0:
                trace.math_fixture(address)
        u.hook_add(UC_HOOK_CODE, hook)
        u.emu_start(0x4ee6b0, STOP, count=100000)
        assert u.reg_read(UC_X86_REG_EIP) == STOP
        assert u.reg_read(UC_X86_REG_ESP) == STACK + 4
        results.append(dict(radius=trace.word(OBJECT + 0x5c), x87=x87(u)))
        operands.append(seen)
    if results[0] != results[1] or operands[0] != operands[1]:
        raise AssertionError(dict(kind='consumer', x=x, y=y, top=top,
                                  original=results[0], fixture=results[1], operands=operands))
    assert len(operands[0]) == 4
    assert {call['caller'] for call in operands[0]} == {hex(c) for c in CALLERS}
    return dict(x=x, y=y, top=top, result=results[0], powers=operands[0])


def negative_controls(program):
    controls = [dict(name='unknown-caller', caller=0x4ee6d0),
                dict(name='non-paper', paper=False), dict(name='wrong-exponent', exponent=3.),
                dict(name='fractional-base', base=350.5), dict(name='horizontal-overflow', base=641.),
                dict(name='vertical-overflow', caller=CALLERS[1], base=481.),
                dict(name='unsupported-control', control=0x37f),
                dict(name='unchanged-menu-default', menu=True)]
    passed = []
    for control in controls:
        u = machine(program)
        trace = trace_for(u)
        trace.startup_paper = control.get('paper', True)
        fp_setup(u, 6, control.get('base', 350.), control.get('exponent', 2.))
        u.reg_write(UC_X86_REG_FPCW, control.get('control', 0x27f))
        u.reg_write(UC_X86_REG_ESP, STACK)
        u.mem_write(STACK, struct.pack('<I', control.get('caller', CALLERS[0])))
        before = x87(u), bytes(u.mem_read(STACK, 16)), u.reg_read(UC_X86_REG_ESP)
        try:
            (MenuTrace.math_fixture(trace, POWER) if control.get('menu') else trace.math_fixture(POWER))
        except Blocked:
            assert before == (x87(u), bytes(u.mem_read(STACK, 16)), u.reg_read(UC_X86_REG_ESP))
            assert not trace.math_events
            passed.append(control['name'])
        else:
            raise AssertionError('Unsupported profile accepted: ' + control['name'])
    return passed


def unchanged_audio_profiles(program):
    checked = []
    for exponent, base in ((10., 2.), (10., 100.), (0., 2.), (-10., 2.)):
        results = []
        for inherited in (False, True):
            u = machine(program)
            trace = trace_for(u)
            fp_setup(u, 6, base, exponent)
            u.reg_write(UC_X86_REG_ESP, STACK)
            u.mem_write(STACK, struct.pack('<I', STOP))
            (MenuTrace.math_fixture(trace, POWER) if inherited else trace.math_fixture(POWER))
            results.append(dict(x87=x87(u), events=trace.math_events,
                                pc=u.reg_read(UC_X86_REG_EIP), sp=u.reg_read(UC_X86_REG_ESP)))
        assert results[0] == results[1], (exponent, base, results)
        checked.append(dict(exponent=exponent, base=base))
    return checked


def captured_reference(path):
    """Stream observations and retain the existing stored-byte provenance hash."""
    path = stored_path(path)
    with path.open('rb') as stream:
        checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
    return read_trace(path), checksum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--captured', type=Path, default=ROOT/'work/paper-roll/rebased/level-two-play/trace.json.gz')
    parser.add_argument('--output', type=Path, default=ROOT/'work/paper-roll/rebased/level-two-play/fader-power-check.json')
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((ROOT/'work').resolve()):
        parser.error('Derived comparison evidence must stay under ignored work/')
    program = claw()
    captured, captured_sha256 = captured_reference(args.captured)
    context = captured['stopped_context']
    assert context['last_transfer'] == dict(site='0x4ee6ca', target='0x4f1b30', kind='direct_call')
    power = [power_case(program, base=350., top=6, caller=CALLERS[0], captured=context)]
    # Adjacent captured inputs, zeros, signs, exact powers and domain edges.
    for caller, bound in zip(CALLERS, (640, 480, 480, 640)):
        for base in sorted({-bound, -350, -1, 0, 1, 2, 349, 350, 351, bound - 1, bound}):
            for top in range(8):
                power.append(power_case(program, base=float(base), top=top, caller=caller))
    for base in (-350., 0., 350.):
        for top in range(8):
            for flags in (0x100, 0x200, 0x400, 0x4000, 0x3f, 0x4720):
                power.append(power_case(program, base=base, top=top, caller=CALLERS[0], flags=flags))
    domain_sweep = [power_case(program, base=float(base), top=6, caller=CALLERS[0])
                    for base in range(1, 641)]
    consumer = []
    for x, y in ((350, 0), (349, 0), (351, 0), (350, 1), (350, 479),
                 (0, 0), (640, 480), (320, 240), (1, 1), (639, 479)):
        for top in (0, 3, 7):
            consumer.append(consumer_case(program, x, y, top))
    negative = negative_controls(program)
    audio = unchanged_audio_profiles(program)
    report = dict(status='pass', scope='Bounded original CRT power and original paper-fader consumer comparison; no full play replacement or admission claim',
                  original_sha256=program.sha256,
                  captured_trace_sha256=captured_sha256,
                  captured_played_ms=captured.get('level_two_played_ms'),
                  comparison_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  fixture_sha256=hashlib.sha256((ROOT/'Tests/NativeLevelTwo/trace.py').read_bytes()).hexdigest(),
                  power_cases=power, integer_domain_sweep=domain_sweep, consumer_cases=consumer, negative_controls=negative, unchanged_audio_profiles=audio)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status='pass', power_cases=len(power), integer_domain_sweep=len(domain_sweep), consumer_cases=len(consumer),
                          negative_controls=len(negative), unchanged_audio_profiles=len(audio), original_sha256=program.sha256, output=str(args.output))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
