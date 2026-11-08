"""Whole source scene logic population/factory/direct initialization oracle."""
import startup_logic_registration_helpers as h
for seed in range(128):
 h.reset(seed);h.compare(0x4c8160,h.LOGIC,[0 if seed%7==0 else 0x415df0,seed*0x10001],'direct pure logic projection')
for seed in range(96):
 h.reset(seed);h.compare(0x4d6340,h.REGISTRY,[0 if seed%11==0 else 0x415df0,h.KEY,seed], 'factory initialized raw seeds')
 h.compare(0x4d6340,h.REGISTRY,[0x41ce80,h.KEY,seed+1],'duplicate metadata replacement')
h.reset();h.mutateFactory=True;h.compare(0x4d6340,h.REGISTRY,[0x415df0,h.KEY,3],'allocation mutates source metadata ID')
for seed in range(4):
 h.reset(seed);h.switchRegistry=bool(seed&1);h.compare(0x401000,0,[h.SCENE],'whole interleaved population',False)
 assert h.sideOrdinal==84 and h.get(h.REGISTRY+28)+h.get(h.REGISTRY2+28)==212
 h.compare(0x401000,0,[h.SCENE],'retained repeated source population',False)
 assert h.sideOrdinal==168
print('PASS',h.calls,'whole original calls /',h.snapshots,'full snapshots /',sum(0x401000<=a<0x50adb5 for a in h.m.executed),'text /',len(h.m.executed),'total addresses',flush=True)
