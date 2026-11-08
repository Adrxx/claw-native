"""Check the additional retained-world arena without executing guest code."""
import hashlib
import json
from Tests.NativeLevels import ROOT, output_dir
from Tests.NativeLevels.later_trace import LaterTrace
from Tests.NativeLevels.trace import Blocked


def main():
    trace = LaterTrace(level=13,destination=13,evidence_dir=output_dir(13),
        instruction_limit=1000,deny_platform=None,route=[],play_ms=0)
    # play_target elects this bound after restoration; inspect both mapped ends.
    trace.heap_limit = 0x61000000
    trace.heap_next = 0x50000000
    address = trace.allocate(32)
    assert address == 0x50000000
    assert bytes(trace.machine.mem_read(address,32)) == b'\xa5'*32
    assert trace.allocations[address] == 32
    trace.heap_next = 0x61000000-32
    address = trace.allocate(16)
    assert bytes(trace.machine.mem_read(address,16)) == b'\xa5'*16
    before = trace.heap_next
    try:
        trace.allocate(16)
    except Blocked:
        assert trace.heap_next == before
    else:
        raise AssertionError('Arena exhaustion was hidden')
    row = dict(status='pass',controls=3,heap_limit=hex(trace.heap_limit),
        runner_sha256=hashlib.sha256((ROOT/'Tests/NativeLevels/later_trace.py').read_bytes()).hexdigest(),
        scope='Physical observer arena only; no game decision or native parity')
    for level in (13,14):
        (output_dir(level)/'later-service-check.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps(row))


if __name__ == '__main__':
    main()
