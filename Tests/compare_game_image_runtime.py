#!/usr/bin/env python3
"""Original raw image runtime full graph oracle."""
import json
import game_image_helpers as g
for i in range(1000):
 g.reset();g.policy=i%4;g.put(g.ACTOR+8,[0x40000 if i%3==0 else 0]);g.put(g.ACTOR+0x40,[i%16|(0x10000000 if i%5 else 0),g.rng.randrange(40),50]);g.put(g.IMAGE+0x30,[g.BASE+0x7900 if i%2 else 0]);g.put(g.ACTOR+0x4c,[g.rng.randrange(-200,900)&0xffffffff,g.rng.randrange(-200,700)&0xffffffff]);g.compare(0x4d2890,g.IMAGE,[g.ACTOR,g.TARGET],f'draw/{i}')
for i in range(40):
 data=g.struct.pack('<8I',10,i%8,8,2,0xfffffff9,9,0,0)+bytes([0xc8,0,0xc8,7]);g.loadingFixture(data);g.g.surfaceLoadFlags=i%2;g.current['keyFail']=0x80004005 if i%5==0 else 0
 g.compare(0x4d2410,g.IMAGE,[g.RAW,4,len(data),i%2],f'load/{i}')
for i in range(12):
 data=g.struct.pack('<8I',10,1,8,2,0,0,0,0)+bytes([0xc8,0,0xc8,7]);g.loadingFixture(data);g.current['createFail']=True;g.compare(0x4d2410,g.IMAGE,[g.RAW,4,len(data),1],f'create-failure/{i}')

actual=retained=0
paths=sorted((g.ROOT/'App/GameData/IMAGES').rglob('*.PID'))+sorted((g.ROOT/'App/GameData/LEVEL1').rglob('*.PID'))
for path in paths:
 data=path.read_bytes();g.loadingFixture(data);flags,_,_=g.struct.unpack_from('<3I',data,4)
 g.compare(0x4d2410,g.IMAGE,[g.RAW,4,len(data),1],f'actual-load/{path}');actual+=1
 for flip in (0,2,4,6):
  g.put(g.ACTOR+0x40,[flip]);g.compare(0x4d2890,g.IMAGE,[g.ACTOR,g.TARGET],f'actual-draw/{path}/{flip}');actual+=1
for path in paths[::41]:
 data=path.read_bytes();g.loadingFixture(data);g.compare(0x4d2410,g.IMAGE,[g.RAW,4,len(data),1],f'history-load/{path}')
 for step in range(12):
  g.g.animationDelta=step%5+1;g.put(g.ACTOR+0x40,[step%4*2|8|0x10000000,step%11,7]);g.put(g.ACTOR+0x4c,[step*70,240]);g.compare(0x4d2890,g.IMAGE,[g.ACTOR,g.TARGET],f'history-draw/{path}/{step}');retained+=1
pixel=0
selected=[p for p in paths if ('/RAT/' in str(p) or '/IMAGES/FRAME' in str(p))and g.struct.unpack_from('<I',p.read_bytes(),4)[0]&0x60==0x20]
for path in selected[::7]:
 data=path.read_bytes();g.loadingFixture(data);g.compare(0x4d2410,g.IMAGE,[g.RAW,4,len(data),1],f'pixel-load/{path}');g.pixelTarget()
 for step in range(12):
  g.put(g.ACTOR+8,[0x40000 if step%2 else 0]);g.put(g.ACTOR+0x40,[step%4*2]);g.put(g.ACTOR+0x4c,[[4,320,640][step%3], [4,240,480][step%3]]);g.compare(0x4d2890,g.IMAGE,[g.ACTOR,g.TARGET],f'joined-pixel/{path}/{step}');pixel+=1
# File-backed image factory and raw surface factory success/failure metadata.
for i in range(20):
 data=g.struct.pack('<8I',10,1,8,2,0,0,0,0)+bytes([0xc8,0,0xc8,7]);g.loadingFixture(data);g.current['keyEnabled']=i%2
 g.put(g.MANAGER+0xc,[g.PARENT]);g.put(g.MANAGER+0x10,[0x51079c,g.TABLE,0,16,16]);g.put(g.TABLE,[0]*16);g.put(g.MANAGER+0x64,[0x7fffffff,0xffffffff])
 g.compare(0x4ce3d0,g.MANAGER,[g.RAW,i%16,1],f'image-factory/{i}')
for i in range(12):
 data=g.struct.pack('<8I',10,1,8,2,0,0,0,0)+bytes([0xc8,0,0xc8,7]);g.loadingFixture(data)
 g.put(g.MANAGER+0xc,[g.PARENT]);g.put(g.MANAGER+0x10,[0x51079c,g.TABLE,0,16,16]);g.put(g.TABLE,[0]*16);g.put(g.MANAGER+0x64,[0x7fffffff,0xffffffff])
 if i%2:g.current['fileFail']=True
 else:g.compare(0x4ce3d0,g.MANAGER,[g.RAW,i%16,1],f'factory-before-duplicate/{i}')
 g.compare(0x4ce3d0,g.MANAGER,[g.RAW,i%16,1],f'factory-duplicate-or-fail/{i}')
for key in (0,1,255,0xffffffff):
 data=g.struct.pack('<8I',10,129,8,2,0,0,0,0)+bytes([0xc8,0,0xc8,7])+bytes(range(256))*3;g.loadingFixture(data);g.g.surfaceColorKey=key
 g.compare(0x4d2410,g.IMAGE,[g.RAW,4,len(data),1],f'embedded-palette/key/{key}')
for function,values in ((0x4d2410,[g.RAW,0,32,1]),(0x4d2410,[g.RAW,5,32,1]),(0x4bf9c0,[g.MANAGER,g.RAW,3,32,0,0]),(0x4bf9c0,[g.MANAGER,g.RAW,4,0,0,0])):
 data=g.struct.pack('<8I',10,1,8,2,0,0,0,0)+bytes([0xc8,0,0xc8,7]);g.loadingFixture(data);g.compare(function,g.IMAGE,values,f'reject/{function}/{values}')
report={'calls':g.calls,'orderedFullHeapEvents':g.eventCount,'originalAddresses':len([a for a in g.m.executed if a<0x1000000]),'rawHeapBytes':g.SIZE,'actualAssetCount':len(paths),'actualAssetLoaderAndDrawCalls':actual,'retainedDrawCalls':retained,'joinedActualCompressedPixelDrawCalls':pixel}
(g.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
