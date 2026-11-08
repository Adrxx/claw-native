#!/usr/bin/env python3
"""Whole notification/no-op audio helper plus finite string/packet graphs."""
import player_death_services_helpers as h
for value in(0,1,2,3,5,0xffffffff):
 for n in range(64):
  h.mode=value;h.prepare();h.mutation=n%3
  h.compare(0x41ebd0,[],('normal-mode-no-notice',value,n))
for n in range(256):
 h.prepare();h.compare(0x4b7aa0,[h.rng.getrandbits(32)],('RET4-active-voices',n),receiver=h.MANAGER)
for mutation in(0,1,2):
 h.mutation=mutation;h.mode=4
 for randomValue in[*range(26),26,32767,0x7fffffff,0x80000000,0xffffffff]:
  for refs in(0,1,5,0xffffffff):
   h.randomValue=randomValue;h.prepare(refs=refs);h.resolvedClient=h.rng.choice([0,h.CLIENT]);h.allocateResult=h.rng.choice([0,h.ALLOCATION])
   h.compare(0x41ebd0,[],('all-phrases-status-copy',mutation,randomValue,refs))
h.mutation=0
for refs in(0,1,5,0x7fffffff,0x80000000,0xffffffff):
 for n in range(32):
  h.prepare(refs=refs);h.compare(0x41ee40,[h.SCRATCH],('name-CString-copy',refs,n),receiver=h.CLIENT)
for n in range(256):
 h.prepare();h.mutation=n%3;h.resolvedClient=h.rng.choice([0,h.CLIENT,h.CLIENT2]);h.allocateResult=h.rng.choice([0,h.ALLOCATION]);h.compare(0x47a220,[],('client-gate-allocation',n),receiver=h.OWNER)
texts=[b'',b'a',b'\r',b'abc\r\n',b'abc\r\n\t',b'abc\xff\x80',b'x'*127,b'x'*128,b'x'*129,b'x'*192,b'abc \r\n',bytes([255])*129]
for text in texts:
 for prepend in(0,1):
  for display in(0,1):
   for n in range(6):
    h.prepare(name=b'Claw',refs=h.rng.choice([1,0xffffffff]));h.mutation=n%3;h.resolvedClient=h.rng.choice([0,h.CLIENT]);h.put_bytes(h.MESSAGE,text+b'\0');h.compare(0x479f10,[h.MESSAGE,h.rng.getrandbits(32),prepend,display],('send-trim-controls',text[:10],len(text),prepend,display,n),receiver=h.OWNER)
h.prepare();h.compare(0x479f10,[0,1,0,1],('null-send',),receiver=h.OWNER)
for probe in(0x40af90,0x4750d0):
 h.COUNTS[probe]=0
 for n in range(32):
  h.prepare();h.mutation=0;h.randomValue=n%26;h.resolvedClient=h.CLIENT
  h.put(h.VT+0x10,[probe]);h.compare(0x41ebd0,[],('actual-state-probe',hex(probe),n))
for n in range(32):
 h.prepare();h.mode=4;h.mutation=0;h.randomValue=n%26;h.resolvedClient=h.CLIENT;h.allocateResult=h.ALLOCATION
 for frame in range(8):
  h.compare(0x41ebd0,[],('retained-death-notices',n,frame))
  h.compare(0x4b7aa0,[0],('retained-no-stop',n,frame),receiver=h.MANAGER)
import player_death_services_callers as joined
for mode in(3,4):
 h.mode=mode;h.mutation=0;h.resolvedClient=h.CLIENT;h.allocateResult=h.ALLOCATION
 for n in range(48):
  h.randomValue=n%26
  joined.compare(0x417b00,n%2,('fall-death-source-chain',mode,n))
  joined.compare(0x417c50,0,('spike-death-source-chain',mode,n))
print(f'PASS {joined.joinedCalls} true original fall/spike death chains, frozen powerup reset and actual mode3/4 probes; active voices preserved',flush=True)
adapted=(set(h.COUNTS)-{0x40af90,0x4750d0})|{h.INCREMENT,h.DECREMENT,h.m.stop}
addresses={a for a in h.m.executed-adapted if 0x400000<=a<0x550000}
assert {0x41ebd0,0x4b7aa0,0x41ee40,0x4f6449,0x479f10,0x47a220,0x4f6584}<=addresses
print(f'PASS {h.calls} whole original death-service calls /{h.events} ordered full snapshots /{len(addresses)} original instruction addresses; complete256KiB heaps+112KiB globals+adapted CString local, active voice preservation, all26phrase branches.',flush=True)
(h.WORK/'coverage.json').write_text(h.json.dumps({'calls':h.calls,'events':h.events,'originalInstructionAddresses':[hex(a)for a in sorted(addresses)]},indent=2)+'\n')
