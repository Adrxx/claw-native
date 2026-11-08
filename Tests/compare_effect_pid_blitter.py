#!/usr/bin/env python3
import effect_pid_blitter_helpers as h
import itertools,json,struct,hashlib
fixture=h.header(7,4)+bytes([2,0,1,130,3,2,3,4,135,1,5,1,6,2,7,8,131,7,9,10,11,12,13,14,15])
for mode in(4,8,22,50):
 for render in(0,1):
  for top,bottom,left,right in((t,b,l,q)for t in range(4)for b in range(t,4)for l in range(7)for q in range(l,7)):
   for fx,fy in itertools.product((0,1),repeat=2):h.check(fixture,(left,top,right,bottom),(5,4,11,4+bottom-top),fx,fy,('directed',mode,top,bottom,left,right),render=render,mode=mode)
  print('PASS directed allflip/clip matrix mode/renderWord',mode,render,flush=True)
#Mode50 actual512byte source rank tables across all14 source PAL profiles.
ranks=json.loads((h.WORK/'ranks.json').read_text())['records']
for entry in ranks:
 table=bytes.fromhex(entry['rank'])
 for value in(0,1,128,254,255):
  for fx,fy in itertools.product((0,1),repeat=2):h.check(fixture,(0,0,6,3),(5,5,11,8),fx,fy,('rank512',entry['level'],value),mode=50,value=value,palette=table)
#Longest literal exercises original stale scratch byte128 in mirrored mode50.
long=h.header(127,3)+b''.join(bytes([127])+bytes(range(127))for _ in range(3))
for mode in(4,8,22,50):
 for fx,fy in itertools.product((0,1),repeat=2):
  for render in(0,1):h.check(long,(0,0,126,2),(5,5,131,7),fx,fy,('longrun',mode),mode=mode,render=render,palette=bytes.fromhex(ranks[0]['rank'])if mode==50 else None)
#Exact wrapped coefficient profiles with zero rank difference, plus lowbytefill.
for mode in(22,50):
 for value in(0,1,255,256,0xffffffff,0x7fffffff,0x80000000):
  for fx,fy in itertools.product((0,1),repeat=2):h.check(fixture,(0,0,6,3),(5,5,11,8),fx,fy,('numeric',mode,value),mode=mode,value=value,palette=bytes(512)if mode==50 else None)
#Actual table capacities, including16KiB SHADE bounded reachable index profiles.
tables=list((h.ROOT/'work/original-disc-assets').glob('LEVEL*/PALETTES/*.CLT'))
for path in sorted(tables):
 table=path.read_bytes()[4:]
 for mode in(4,8):
  for fx,fy in itertools.product((0,1),repeat=2):
   for render in(0,1):
    initial=bytes(x&63 for x in h.r.randbytes(7+36*18))if len(table)==16384 else None
    h.check(fixture,(0,0,6,3),(5,5,11,8),fx,fy,('actualCLT',path,mode),mode=mode,value=52,render=render,palette=table,initial=initial)
#Generated grammar/oddstride/overlappingrows catches source old-index timing.
for index in range(180):
 w,ht=h.r.randrange(1,40),h.r.randrange(1,12);body=bytearray()
 for y in range(ht):
  x=0
  while x<w:
   n=h.r.randrange(1,min(127,w-x)+1)
   if h.r.randrange(3)==0:body.append(128+n)
   else:body.append(n);body.extend(h.r.randrange(256)for _ in range(n))
   x+=n
 data=h.header(w,ht)+body;top=h.r.randrange(ht);bottom=h.r.randrange(top,ht);left=h.r.randrange(w);right=h.r.randrange(left,w);dy=h.r.randrange(3,7);dx=h.r.randrange(-2,10)
 for mode in(4,8,22,50):
  fx,fy=h.r.randrange(2),h.r.randrange(2)
  h.check(data,(left,top,right,bottom),(dx,dy,h.r.randrange(-10,20),dy+bottom-top+h.r.randrange(-1,2)),fx,fy,('generated',index,mode),mode=mode,render=index%2,pitchOverride=h.r.randrange(12,w+30),palette=bytes.fromhex(ranks[index%14]['rank'])if mode==50 else None,value=index%256)
print('PASS allactualCLT/rank512/numeric/longrun/generatedoverlap profiles',flush=True)
#Caller ANI record selection is a format fixture; frozenAnimationEngine owns
#the source record/control/timing bodies. imageCommand3 usesparameter at+8.
imageIDs=[];ani=[]
for name in('STAND','WALK','POWERUPSWIPE'):
 path=h.ROOT/f'work/original-disc-assets/CLAW/ANIS/{name}.ANI';data=path.read_bytes();count,pathLength=struct.unpack_from('<2I',data,12);offset=32+pathLength;selected=[]
 for _ in range(count):
  flags,image,control,movement,parameter=struct.unpack_from('<H4h',data,offset);offset+=20
  if flags&2:offset=data.index(0,offset)+1
  if image==3:selected.append(parameter)
 assert offset==len(data);imageIDs.extend(selected);ani.append({'path':str(path.relative_to(h.ROOT)),'records':count,'imageIDs':selected,'sha256':hashlib.sha256(data).hexdigest()})
average=(h.ROOT/'work/original-disc-assets/LEVEL1/PALETTES/AVERAGE.CLT').read_bytes()[4:];rank=bytes.fromhex(next(e for e in ranks if e['level']=='LEVEL1')['rank']);actual=retained=0
for imageID in sorted(set(imageIDs)):
 path=h.ROOT/f'work/original-disc-assets/CLAW/IMAGES/FRAME{imageID:03}.PID';data=path.read_bytes();w,ht=struct.unpack_from('<2I',data,8)
 for src in((0,0,w-1,ht-1),(1,1,w-1,ht-1),(0,0,w//2,ht-1)):
  for mode in(4,8,22,50):
   for fx,fy in itertools.product((0,1),repeat=2):
    for render in(0,1):h.check(data,src,(5,5,w+5,5+src[3]-src[1]),fx,fy,('actualplayer',imageID,mode),mode=mode,value=52,render=render,palette=rank if mode==50 else average);actual+=1
 print('PASS actualplayer image',imageID,flush=True)
#Same physicalsize framebuffer spans changing ANI image dimensions/IDs.
for mode in(4,8,22,50):
 initial=scratch=None
 for i,imageID in enumerate(imageIDs*2):
  path=h.ROOT/f'work/original-disc-assets/CLAW/IMAGES/FRAME{imageID:03}.PID';data=path.read_bytes();w,ht=struct.unpack_from('<2I',data,8)
  #samePID retained2draw histories preserve exactframebuffer and scratchalias.
  initial=scratch=None
  for j in range(2):
   initial=h.check(data,(0,0,w-1,ht-1),(5,5,w+5,ht+4),i&1,(i>>1)&1,('retainedANI',mode,i,j),mode=mode,value=(52,53,54,55,101,52)[i%6],render=i%2,palette=rank if mode==50 else average,initial=initial,scratchInitial=scratch);scratch=h.lastEvidence[9];retained+=1
#No-table acceptedno-op evenfill, formatrejection and frozen1/2 composition.
for mode in(1,2,4,8,22,50):
 for fx,fy in itertools.product((0,1),repeat=2):h.check(fixture,(0,0,6,3),(5,4,11,7),fx,fy,('noTable',mode),mode=mode,tablePresent=False)
for fx,fy in itertools.product((0,1),repeat=2):h.check(fixture,(0,0,6,3),(5,4,11,7),fx,fy,'zeroPayloadFill',mode=22,value=256,payloadToken=0)
report={'pairedCalls':h.calls,'orderedSnapshots':h.snapshots,'writes':h.totalWrites,'originalAddresses':len(h.m.executed-{0x4b9730,h.UNLOCK,h.m.stop}),'actualCLTs':len(tables),'sourceRankProfiles':len(ranks),'actualPlayerPIDs':len(set(imageIDs)),'actualPlayerDraws':actual,'retainedDraws':retained,'ANIformatFixtures':ani};(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items()if k!='ANIformatFixtures'})
