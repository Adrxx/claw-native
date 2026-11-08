"""Allocation and callback-order controls for the later-level grid adapter; no emulation."""
from Tests.NativeLevels.storage import EventLog
import argparse
import hashlib
import json
from Tests.NativeLevels import ROOT, add_level, output_dir
from Tests.NativeLevels.trace import LevelTrace, Blocked


class Memory:
    def reg_read(self, register):
        return 0x1000

    def context_save(self):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_level(parser)
    args = parser.parse_args()
    trace = object.__new__(LevelTrace)
    trace.phase = 'command-8075'
    trace.machine = Memory()
    trace.allocations = {0x2000: 4+8*73728}
    trace.physical_events, trace.array_callbacks = EventLog(), []
    trace.cpu_state = lambda: []
    trace.platform_call = lambda *args: None
    observed = []
    trace.start_array_element = lambda frame: observed.append(frame.copy())
    words = {0:0,0x1004:0x2004,0x1008:8,0x100c:73728,0x1010:0x4f4a90,0x1014:0x4c96b0}
    trace.word = lambda address: words[address]
    trace.fixture(0x4a4590)
    assert observed[-1]['base']==0x2004 and observed[-1]['stride']==8 and observed[-1]['count']==73728
    assert observed[-1]['constructor']==0x4f4a90 and observed[-1]['pop']==20
    construction = observed[-1]['event']
    assert construction['phase'] == 'command-8075'
    controls = 1
    for address,value in ((0x1004,0x2008),(0x1008,4),(0x100c,0x100001),(0x1010,0x4f4a94),(0x1014,0)):
        old = words[address]
        words[address] = value
        try:
            trace.fixture(0x4a4590)
        except Blocked:
            pass
        else:
            raise AssertionError(f'Invalid grid operand {address:#x} accepted')
        words[address] = old
        controls += 1
    words[0x1010] = 0x4c96b0
    trace.phase = 'command-800e'
    trace.fixture(0x4a4450)
    assert observed[-1]['base']==0x2004+8*73727 and observed[-1]['stride']==-8
    assert observed[-1]['constructor']==0x4c96b0 and observed[-1]['pop']==16
    destruction = observed[-1]['event']
    assert destruction['phase'] == 'command-800e'
    assert construction['phase'] == 'command-8075', 'Later phases must not rewrite earlier events'
    assert [event['phase'] for event in trace.physical_events] == ['command-8075', 'command-800e']
    controls += 1
    physical = LevelTrace(1000, None, level=args.level)
    expected_limit = (0x50000000 if args.level >= 6 else
                      0x6f000000 if args.level >= 4 else 0x69000000)
    assert physical.heap_limit == expected_limit
    if args.level >= 6:
        assert physical.heap_next == 0x30000000
    physical.heap_next = expected_limit - 32
    pointer = physical.allocate(16)
    assert bytes(physical.machine.mem_read(pointer, 16)) == b'\xa5'*16
    assert physical.allocations[pointer] == 16
    heap_controls = 1
    for size in (16, 0x800001):
        before = physical.heap_next
        try:
            physical.allocate(size)
        except Blocked:
            assert physical.heap_next == before
        else:
            raise AssertionError('Invalid or out-of-bounds allocation accepted')
        heap_controls += 1
    result = dict(status='pass', controls=controls,
                  grid_phases=[construction['phase'], destruction['phase']],
                  heap_controls=heap_controls, heap_limit=hex(expected_limit),
                  tracer_sha256=hashlib.sha256((ROOT/'Tests/NativeLevels/trace.py').read_bytes()).hexdigest())
    out = output_dir(args.level)
    out.mkdir(parents=True,exist_ok=True)
    (out/'service-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    main()
