"""Original-platform font/DC controls; no game substitutes or parity claims.

Run: work/test-env/bin/python -m Tests.NativeLevelOne.gdi_check
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct

from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EIP, UC_X86_REG_ESP
from Tests.NativeMenuBase.trace import Blocked, STACK, STOP, check_text_transport
from .trace import LevelOneTrace


def check():
    trace = LevelOneTrace()
    def call(address, *args, com=False):
        for i, value in enumerate((STOP, *args)):
            trace.put(STACK + i * 4, value)
        trace.machine.reg_write(UC_X86_REG_ESP, STACK)
        trace.machine.reg_write(UC_X86_REG_EIP, address)
        (trace.com_fixture if com else trace.fixture)(address)
        assert trace.machine.reg_read(UC_X86_REG_ESP) == STACK + 4 * (1 + len(args))
        assert trace.machine.reg_read(UC_X86_REG_EIP) == STOP
        return trace.machine.reg_read(UC_X86_REG_EAX)
    def target(name):
        return next(a for a, (_, n) in trace.imports.items() if n.split('!')[-1] == name)
    def api(name, *args):
        return call(target(name), *args)
    def com(obj, slot, *args):
        return call(trace.word(trace.word(obj) + slot), obj, *args, com=True)
    def rejects(action):
        try:
            action()
        except Blocked:
            return
        raise AssertionError('Unsupported GDI operation accepted')
    font_args = (12, 8, 0, 0, 100, 0, 0, 0, 1, 0, 0, 0, 0, trace.cstring(b'ARIAL'))
    before = dict(trace.allocations)
    rejects(lambda: api('CreateFontA', 20, *font_args[1:]))
    trace.deny_platform = target('CreateFontA')
    rejects(lambda: api('CreateFontA', *font_args))
    trace.deny_platform = None
    assert trace.allocations == before and not trace.fonts
    font = api('CreateFontA', *font_args)
    other = api('CreateFontA', *font_args)
    assert font != other and trace.fonts[font]['requested_face'] == 'ARIAL'
    palette_bytes = bytearray(1024)
    palette_bytes[28:31] = b'\xff\xff\xff'
    palette = trace.com_object('IDirectDrawPalette', entries=palette_bytes.hex())
    surface, second = trace.surface(128, 32, 0x840), trace.surface(128, 32, 0x840)
    output, rect = trace.allocate(4), trace.allocate(16)
    for s in (surface, second):
        com(s, 124, palette)
    com(surface, 68, output)
    dc = trace.word(output)
    com(second, 68, output)
    dc2 = trace.word(output)
    trace.deny_platform = target('SelectObject')
    rejects(lambda: api('SelectObject', dc, font))
    trace.deny_platform = None
    assert 'font' not in trace.dcs[dc]
    rejects(lambda: api('SelectObject', dc, surface))
    rejects(lambda: api('SelectObject', dc, 0))
    assert api('SelectObject', dc, font) == trace.STOCK_FONT
    assert api('SelectObject', dc, font) == font
    assert api('SelectObject', dc, other) == font
    assert api('SelectObject', dc, font) == other
    assert api('SelectObject', dc2, font) == trace.STOCK_FONT
    assert api('DeleteObject', font) == 0 and font in trace.allocations
    assert api('SetBkMode', dc, 1) == 2
    assert api('SetTextColor', dc, 0xffffff) == 0
    trace.machine.mem_write(rect, struct.pack('<4i', 0, 0, 128, 32))
    assert api('DrawTextA', dc, trace.cstring(b'GOD MODE ON'), 0xffffffff, rect, 0x20) == 16
    event = trace.physical_events[-1]
    assert event['selected_font'] == hex(font) and event['changed_pixels'] > 0
    assert event['logical_font']['requested_face'] == 'ARIAL'
    # All three layouts must retain the same glyphs. Center lies halfway
    # between the independent left/right renderings, within integer rounding.
    pixels = trace.com_objects[surface]['pixels']
    positions = []
    for flags in (0x20, 1, 0x22):
        trace.machine.mem_write(pixels, bytes(128 * 32))
        assert api('DrawTextA', dc, trace.cstring(b'MPKFA'), 5, rect, flags) == 16
        ink = {i for i, b in enumerate(trace.machine.mem_read(pixels, 128 * 32)) if b}
        positions.append(ink)
    left, center, right = (min(p) % 128 for p in positions)
    assert left < center < right and abs(2 * center - left - right) <= 1
    assert {i + center - left for i in positions[0]} == positions[1]
    assert {i + right - left for i in positions[0]} == positions[2]
    before = bytes(trace.machine.mem_read(pixels, 128 * 32))
    rejects(lambda: api('DrawTextA', dc, trace.cstring(b'line\nline'), 0xffffffff, rect, 1))
    rejects(lambda: api('DrawTextA', dc, trace.cstring(b'MPKFA'), 5, rect, 0x11))
    assert bytes(trace.machine.mem_read(pixels, 128 * 32)) == before
    assert api('SelectObject', dc, trace.STOCK_FONT) == font
    assert api('DeleteObject', font) == 0  # Still selected in the second DC.
    com(second, 104, dc2)  # Releasing the DC releases its selection lease.
    trace.deny_platform = target('DeleteObject')
    rejects(lambda: api('DeleteObject', font))
    trace.deny_platform = None
    assert font in trace.fonts and font in trace.allocations
    assert api('DeleteObject', font) == 1 and font not in trace.allocations
    assert api('DeleteObject', font) == 0
    rejects(lambda: api('SelectObject', dc, font))
    trace.com_objects[surface]['lost'] = True
    rejects(lambda: api('SelectObject', dc, other))
    trace.com_objects[surface]['lost'] = False
    com(surface, 104, dc)
    rejects(lambda: api('SelectObject', dc, other))
    rejects(lambda: api('DrawTextA', dc, 0, 0, rect, 0x20))
    assert api('DeleteObject', other) == 1
    rejects(lambda: api('DeleteObject', trace.STOCK_FONT))
    assert not trace.fonts and not trace.dcs
    return dict(status='pass', stdcall=True, selection_restore=True, multiple_dcs=True,
        selected_delete_fails=True, release_drops_selection=True, deleted_font_rejected=True,
        unknown_object_and_stale_dc_rejected=True, withheld_services_no_effect=True,
        logical_font_and_physical_glyph_evidence=True, centered_ascii_glyphs=True,
        unsupported_multiline_and_wordwrap_rejected=True, text_transport=check_text_transport())


def check_boss_trace(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt') as stream:
        report = json.load(stream)
    assert report['status'] == 'pass' and report['stop'] is None
    assert report['tracer_sha256'] == hashlib.sha256(Path(__file__).with_name('trace.py').read_bytes()).hexdigest()
    assert report['menu_tracer_sha256'] == hashlib.sha256(
        Path(__file__).parents[1].joinpath('NativeMenuBase/trace.py').read_bytes()).hexdigest()
    assert ''.join(k['letter'] for k in report['boss_cheat_keys'] if k.get('assistance')) == 'MPKFA'
    events = report['physical_events']
    selected = [(i, e) for i, e in enumerate(events) if e['service'] == 'SelectObject'
                and e.get('caller', {}).get('site') == '0x4227c6']
    assert selected, 'Original message renderer did not pass SelectObject at 0x4227c6'
    for i, selection in selected:
        drawing = events[i + 1]
        restoration = events[i + 2]
        assert drawing['service'] == 'DrawTextA' and drawing['selected_font'] == selection['font']
        assert drawing['flags'] == 1
        assert drawing['glyph_pixels'] > 0 and drawing['changed_pixels'] > 0
        assert restoration['service'] == 'SelectObject' and restoration['font'] == selection['previous']
        assert restoration['previous'] == selection['font']
    assert any(f['boss'].get('health', 0) > 0 for f in report['boss_frames'])
    assert report['boss_frames'][-1]['elapsed_ms'] >= 18000
    assert report['live_text_dcs'] == 0
    return dict(status='pass', original_site='0x4227c6', message_draws=len(selected),
                boss_frames=len(report['boss_frames']), elapsed_ms=report['boss_frames'][-1]['elapsed_ms'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--boss-trace', type=Path)
    args = parser.parse_args()
    result = check()
    if args.boss_trace:
        result['boss_trace'] = check_boss_trace(args.boss_trace)
    print(json.dumps(result))
