#!/usr/bin/env python3
"""Whole original96-byte420970 seek; raw constructor metadata are fixtures."""
import json,ctypes as C
import actor_animation_helpers as g
for n in range(900):
    count=n%9
    g.setup(max(1,count))
    g.put(g.SEQ+16,[count if n%13 else 0xffffffff])
    table=[g.RECORDS+i*0x40 if (n+i)%4 else 0 for i in range(max(1,count))]
    g.put(g.PTRS,table)
    index=[0,1,count-1,count,count+1,0xffffffff,0x80000000,0x7fffffff][n%8]
    g.compare(0x420970,g.ANI,('whole seek',n),index&0xffffffff)
    g.put(g.ANI+28,[n%3,n%5,n])
    g.compare(0x420970,g.ANI,('retained seek',n),[0,count-1,0xffffffff][n%3]&0xffffffff)
report={'wholeCalls':g.calls,'rawHeapBytes':g.SIZE,'globalBytes':8,'orderedEvents':g.event_count,'originalAddresses':len(g.m.executed)}
(g.ROOT/'work/root-animation-seek-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS whole original420970 seek/fallback/delay-stop-code/reset and retained histories',json.dumps(report))
