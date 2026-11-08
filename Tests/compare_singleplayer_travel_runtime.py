#!/usr/bin/env python3
"""Independent original execution and raw retail command inventory; no duplicate runtime."""
import singleplayer_travel_helpers as h
from pathlib import Path
import json,hashlib,struct,zlib
# Re-run unchanged test assertions while redirecting only its output directory.
source=Path(__file__).with_name('compare_special_command_runtime.py').read_text().replace('import special_command_helpers as h','import singleplayer_travel_helpers as h')
exec(compile(source,str(Path(__file__).with_name('compare_special_command_runtime.py')),'exec'),globals())
prior=json.loads((h.WORK/'verification.json').read_text())
assert h.m.read_words(0x50c264+0x40,1)==[0x46c900]
assert h.m.read_words(0x50c264+0x54,1)==[0x46c630]
assert h.m.read_words(0x50c0c4+4,1)==[0x40ac20]
assert h.m.read_words(0x50b43c+4,1)==[0x40b6a0]
assert h.m.read_words(0x50b43c+0x24,1)==[0x40b720]
assert h.m.read_words(0x50b494+4,1)==[0x40d470]
def observe_mode10(uc,address,size,user):
 if address==0x4ce8b0:h.event(address,h.u.reg_read(h.UC_X86_REG_ECX),())
h.u.hook_add(h.UC_HOOK_CODE,observe_mode10)
inventory=[]
for level in range(1,15):
 path=h.ROOT/f'work/original-disc-assets/LEVEL{level}/WORLDS/WORLD.WWD'
 original=path.read_bytes();b=original;flags,planeCount,offset=struct.unpack_from('<I',b,8)[0],*struct.unpack_from('<II',b,732)
 if flags&2:b=b[:offset]+zlib.decompress(b[offset:])
 for plane in range(planeCount):
  ph=struct.unpack_from('<40I',b,offset+160*plane);pos=ph[35]
  for index in range(ph[32]):
   w=struct.unpack_from('<71I',b,pos);end=pos+284+sum(w[1:5]);cursor=pos+284;text=[]
   for size in w[1:5]:text.append(b[cursor:cursor+size].split(b'\0')[0].decode('ascii'));cursor+=size
   # Inventory logic AND image-set evidence; no guessed numeric pickup type.
   if text[1]=='EndLevelGem' or 'MAPPIECE' in text[2] or 'WARP' in text[2]:
    inventory.append(dict(level=level,plane=plane,index=index,id=w[0],logic=text[1],imageSet=text[2],target=[w[55],w[56]],rawSHA256=hashlib.sha256(b[pos:end]).hexdigest(),worldSHA256=hashlib.sha256(original).hexdigest()))
   pos=end
assert len([r for r in inventory if r['level']==1 and r['imageSet']=='GAME_WARP'])==8
# Ignored late queued map requests: source readiness rejects the new state10.
# VT mode slots are original image identities; all scene/UI services remain adapters.
for record in [r for r in inventory if r['logic']=='EndLevelGem' or 'MAPPIECE' in r['imageSet']]:
 h.setup(record['id']);h.RETURNS[0x4ce8b0]=10;h.put(h.O+0x14,[record['level']]);h.compare(0x426e30,('retail map request executes source owner',record['level'],record['id']),(0,0x800e,0),h.MANAGER)
 assert h.g.playerToken==0 and h.words(h.MANAGER+0xe4)[0]==1
 state=h.words(h.MANAGER+0x2c)[0];assert h.words(state)[0]==0x50c0c4
 assert h.m.read_words(0x50c0c4+0x10,1)==[0x4ce8b0]
 #4c9e40 is the original return10 leaf, not a host mode override.
 for command in (0x800e,0x805c):
  before=h.snap();h.compare(0x426e30,('retained late command ignored in source state10',record['level'],record['id'],command),(0,command,0),h.MANAGER);assert h.snap()==before
report=dict(prior,wholeOriginalCalls=h.calls,orderedFullSnapshots=h.event_count,originalAddresses=len(h.m.executed),retailInventory=inventory,retailMapProfiles=len([r for r in inventory if r['logic']=='EndLevelGem' or 'MAPPIECE' in r['imageSet']]),additionalEvidence='literal original VT mode10 rejects repeated800e/805c after retained source transition; complete heap/globals/events; child UI/spatial/fade remain explicit services')
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print({k:v for k,v in report.items()if k not in ('retainedHistories','retailInventory')},flush=True)
