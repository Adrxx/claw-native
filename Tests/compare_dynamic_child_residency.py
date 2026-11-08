#!/usr/bin/env python3
"""Whole original scheduler versus frozen native composition; owned fixtures."""
import dynamic_child_residency_helpers as h
import hashlib,json,random
histories=[]
def check(label,expect=None):
 h.compareOuter(0x46ac30,label)
 state={'active':h.activeActors(),'childFlags':h.words(h.CHILD+8,1)[0],'member':h.words(h.CHILD+0x88,7),'parentChild':h.words(h.PARENT_PRIVATE+0x150,1)[0],'free':[e[1]for e,_ in h.events if e[0]=='free']}
 histories.append({'label':label,**state})
 # Logical frees are observed separately from emulator allocation storage. Source
 # rereads cleared actor bytes after deleting it; retain storage for that read.
 assert all(state['free'].count(t)<=1 for t in (h.PARENT,h.PARENT_PRIVATE,h.PARENT_LOGIC,h.CHILD,h.CHILD_PRIVATE,h.CHILD_LOGIC))
 if expect=='dormant':assert h.CHILD not in state['active'] and state['member'][3] and state['childFlags']&0x10000 and h.CHILD not in state['free']
 if expect=='active':assert h.CHILD in state['active'] and not state['member'][3] and state['childFlags']&0x10000
 if expect=='deleted':assert h.CHILD not in state['active'] and h.CHILD in state['free'] and h.CHILD_PRIVATE in state['free'] and h.CHILD_LOGIC in state['free'] and not state['childFlags']
 return state
h.prepareChild();s=check('parent cleanup marks visited child then final residency culls','dormant')
assert h.PARENT in s['free'] and h.PARENT_PRIVATE in s['free'] and s['parentChild']==h.CHILD
for i in range(12):h.advance();check(f'dormant marked child retained stationary frame{i}','dormant')
h.setCenter(820);h.advance();s=check('camera approaches stored child member reactivation then delete','deleted');assert not s['member'][3]
# A dormant member's last stored coordinates, rather than current actor pose,
# control reactivation. Live parent movement is represented by a named external
# pose mutation; it is not claimed as recovered flight/collision here.
h.prepareChild();check('before dormant live pose mutation','dormant');stored=h.words(h.CHILD+0x98,2)
h.put(h.CHILD+76,[6000,5000]);h.advance();s=check('dormant pose changes without moving source cell','dormant');assert s['member'][4:6]==stored
h.setCenter(820);h.advance();check('stored coordinates elect moved marked child then delete','deleted')
# Actual emitter uses child z=parent z-1; parent cleanup is deferred until
# after all actors have been visited, so both z orders defer child deletion.
h.prepareChild(childFirst=False);check('higher-z child also marked after full traversal','dormant')
for flags,x,expect in ((0x40000,1581,'active'),(0x40000,1582,'dormant'),(0x40002,1601,'active'),(0x40020,1601,'deleted'),(0x840000,1601,'active'),(0x1040000,1601,'dormant'),(0x140000,1601,'dormant'),(0xc0020,1601,'deleted')):
 h.prepareChild(childX=x,childFlags=flags);s=check(f'exact flag/layer boundary{flags:x}/{x}',expect)
 if expect=='active':h.advance();check(f'next active pass deletes{flags:x}','deleted')
 elif expect=='dormant':
  h.setCenter(x);h.advance();check(f'layer reactivation deletes{flags:x}','deleted')
# Binary32 truncation controls the rectangle center. No player-distance shortcut.
for f,expect in ((780.999,'dormant'),(781.001,'active')):
 h.prepareChild(childX=1581);h.put(h.PLANE+16,[h.fb(f)]);check(f'plane float center{f}',expect)
# Ordinary single pass and source18ms subdivision preserve different deletion
# timing. No invented repeated fixed-step scheduler is substituted.
for delta in (0,1,17,18,19,20,36,37,54,55,98,99,100,101,0xffffffff):
 h.prepareChild();h.advance(delta);s=check(f'whole outer source delta{delta}')
 if delta>18 and delta<100 and delta<=36:assert h.CHILD in s['free']
 else:assert s['member'][3] and s['childFlags']&0x10000
# Re-entering the same center does not rerun activation. A freshly dormant
# member inside the cached rectangle is intentionally retained until change.
h.prepareChild(childX=1581);check('active source boundary child','active')
h.nativeEntry(0x4d4d10,h.words(h.PLANE+0xb0,1)[0],(0,4730))
h.advance();check('same cached center cannot elect newly dormant flagged member','dormant')
h.setCenter(782);h.advance();check('changed cached center elects flagged member','deleted')
# Shared grid teardown frees dormant actors, then releases cell/layer storage.
# 4d50e0 itself leaves membership/counts; do not reactivate those freed members.
h.prepareChild();check('before dormant grid teardown','dormant');grid=h.words(h.PLANE+0xb0,1)[0];layers=h.words(grid+4,3)
h.compare(0x4d50e0,grid,'whole dormant actor destruction',returns=False)
frees=[e[1]for e,_ in h.events if e[0]=='free'];assert h.CHILD in frees and h.CHILD_PRIVATE in frees and h.CHILD_LOGIC in frees
h.compare(0x4d4b00,grid,'whole layer/cell ownership teardown',returns=False);assert h.words(grid+4,3)==[0,0,0]
# Retained deterministic center histories cover out/in/cached cells across all
# source layers, including primary countdown and skipped callback paths.
rng=random.Random(0x411cd0)
for i in range(40):
 flags=0x40000|rng.choice((0,0x800000,0x1000000));center=rng.randrange(400,1800);x=center+rng.choice((1300,1600,2000));h.prepareChild(center=center,childX=x,childFlags=flags)
 h.put(h.CHILD_LOGIC+0x20,[rng.choice((0,100,0xffffffff)),rng.choice((0,1,7))]);check(f'seeded history{i} initial','dormant')
 for j in range(3):h.setCenter(center-rng.randrange(0,100));h.advance(rng.choice((0,16,18,100)));check(f'seeded history{i} dormant{j}','dormant')
 h.setCenter(x);h.advance();check(f'seeded history{i} elected terminal','deleted')
result={'originalSHA256':hashlib.sha256(h.opts.exe.read_bytes()).hexdigest(),'wholeCalls':h.calls,'orderedFullSnapshots':h.event_count,'snapshotBytes':len(h.snapshot()),'originalAddresses':len(h.m.executed),'histories':len(histories),'completePrivateWords':[86,19],'actorsActualWords':109,'hostCompatibilityActorWords':128,'transportBoundaries':['clock/timeGetTime','keyboard GetAsyncKeyState','bounds update4025c0','renderer4cb9b0','presentation vtable34','overlay46c2c0','device4b98b0','no eligible contact pairs','parked Flare primary1000 (ANI not elected)']}
(h.WORK/'histories.json').write_text(json.dumps(histories,indent=2));(h.WORK/'verification.json').write_text(json.dumps(result,indent=2));print('PASS',json.dumps(result))
