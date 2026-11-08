#!/usr/bin/env python3
import light_pid_blitter_helpers as h
import itertools,json,struct
fixture=h.header(7,4)+bytes([2,0,1,130,3,2,3,4,135,1,5,1,6,2,7,8,131,7,9,10,11,12,13,14,15])
for render in(0,1):
 for top,bottom,left,right in((t,b,l,q)for t in range(4)for b in range(t,4)for l in range(7)for q in range(l,7)):
  for fx,fy in itertools.product((0,1),repeat=2):h.check(fixture,(left,top,right,bottom),(5,4,11,4+bottom-top),fx,fy,('directed',top,bottom,left,right),render=render)
 print('PASS directed allflip/clip matrix renderWord',render,flush=True)
#OriginalXY uninitialized local with positive/signed/overflowing supplied seed.
for seed in(1,6,7,31,0x1003000,0xffffffff):
 for top in(1,2,3):
  for render in(0,1):h.check(fixture,(0,top,6,2 if seed==0xffffffff else 3),(5,5,11,8-top),1,1,('stackseed',seed,top),seed=seed,render=render)
#Literal grammar, odd offsets and deliberately overlapping logical rows.
for index in range(300):
 w,ht=h.r.randrange(1,40),h.r.randrange(1,12);body=bytearray()
 for y in range(ht):
  x=0
  while x<w:
   n=h.r.randrange(1,min(127,w-x)+1)
   if h.r.randrange(3)==0:body.append(128+n)
   else:body.append(n);body.extend(h.r.randrange(256)for _ in range(n))
   x+=n
 data=h.header(w,ht)+body;top=h.r.randrange(ht);bottom=h.r.randrange(top,ht);left=h.r.randrange(w);right=h.r.randrange(left,w);dy=h.r.randrange(3,7);dx=h.r.randrange(-2,10)
 for fx,fy in itertools.product((0,1),repeat=2):
  for render in(0,1):h.check(data,(left,top,right,bottom),(dx,dy,h.r.randrange(-10,20),dy+bottom-top+h.r.randrange(-1,2)),fx,fy,('generated',index),render=render,pitchOverride=h.r.randrange(12,w+30))
print('PASS generated overlap/odd-offset histories and supplied stackseeds',flush=True)
#True dispatcher rejection/no-table bodies and frozen normal-mode composition.
for src in((-1,0,6,3),(0,0,7,3),(0,-1,6,3),(0,4,6,4),(0,0,-1,-1),(1,2,1,2),(0,2,6,1)):
 for fx,fy in itertools.product((0,1),repeat=2):h.check(fixture,src,(5,4,11,7),fx,fy,('dispatcher',src))
for fx,fy in itertools.product((0,1),repeat=2):
 h.check(fixture,(0,0,6,3),(5,4,11,7),fx,fy,'nulltable',tablePresent=False)
 h.check(fixture,(0,0,6,3),(5,4,11,7),fx,fy,'formatreject',fmt=2)
 h.check(fixture,(0,0,6,3),(5,4,11,7),fx,fy,'normaldelegate',mode=1)
#Both actual normally elected Flare/LFX PIDs with every actual64KiB LIGHT and
#AVERAGE CLT; source active/length words arbitrary, payload is the sole read.
assets=list((h.ROOT/'work/original-disc-assets/GAME/IMAGES/LIGHTFX').rglob('*.PID'));tables=list((h.ROOT/'work/original-disc-assets').glob('LEVEL*/PALETTES/*.CLT'));tableCount=0;draws=0
for path in sorted(tables):
 clt=path.read_bytes();n=struct.unpack_from('<I',clt)[0]
 if n!=65536:continue
 palette=clt[4:];assert len(palette)==65536;tableCount+=1
 for asset in assets:
  data=asset.read_bytes();w,ht=struct.unpack_from('<2I',data,8)
  for src in((0,0,w-1,ht-1),(0,1,w-1,ht-1),(1,0,w-1,ht-1),(0,0,w//2,ht-1),(w//3,ht//3,w*2//3,ht*2//3)):
   for fx,fy in itertools.product((0,1),repeat=2):
    for render in(0,1):h.check(data,src,(5,5,5+src[2]-src[0],5+src[3]-src[1]),fx,fy,('actual',path,asset),palette=palette,render=render);draws+=1
 print('PASS actual table',path.parent.parent.name,path.name,flush=True)
#Retained background receives genuine repeated lighting, without clearing rows.
for asset in assets:
 data=asset.read_bytes();w,ht=struct.unpack_from('<2I',data,8);palette=(h.ROOT/'work/original-disc-assets/LEVEL1/PALETTES/LIGHT.CLT').read_bytes()[4:];initial=None
 for i in range(64):
  src=(0,i%3,w-1,ht-1);initial=h.check(data,src,(5,4,5+w,4+ht-1-i%3),i&1,(i>>1)&1,('retained',asset,i),palette=palette,render=i%2,initial=initial)
report={'pairedCalls':h.calls,'orderedSnapshots':h.snapshots,'writes':h.totalWrites,'originalAddresses':len(h.m.executed-{0x4b9730,h.UNLOCK,h.m.stop}),'actualPIDs':len(assets),'actual64KiBTables':tableCount,'actualDraws':draws,'retainedDraws':128};(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
