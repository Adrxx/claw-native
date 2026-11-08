import player_fade_runtime_helpers as H
from player_fade_runtime_helpers import *
for fn,args,receiver in [(0x4ecbc0,[],DESC),(0x4ecb30,[],DESC),(0x4ebf80,[],MANAGER),(0x4c61d0,[],EFFECT+4),(0x4ec8d0,[],EFFECT),(0x4ed5e0,[],EFFECT),(0x4ecb00,[SURFACE0,SURFACE1],EFFECT),(0x4ecb20,[HOLDER],EFFECT),(0x4ed670,[DESC],EFFECT),(0x4ee6b0,[],EFFECT),(0x4ee820,[],EFFECT),(0x4ee860,[],EFFECT),(0x4ec050,[1,DESC],MANAGER)]:
 prepare();compare(fn,receiver,args,hex(fn))
for direction in(0,1):
 for bpp in(1,2,3,4):
  prepare(direction=direction,bpp=bpp);compare(0x4ed670,EFFECT,[DESC],'init');compare(0x4ee6b0,EFFECT,[],'max');maximum=get(EFFECT+0x5c)[0]
  for step in range(0,maximum+1,3):compare(0x4ed800,EFFECT,[step],f'step{direction}/{bpp}/{step}')
  compare(0x4ed800,EFFECT,[maximum],'final')
for fn in(0x48fae0,0x48fbe0):
 prepare();compare(fn,OWNER,[15,11,100,20],'wholewrapper')


# Directed finite metadata/failure/ownership cases and arbitrary surface geometry.
for i in range(180):
 w=rng.randrange(1,90);h=rng.randrange(1,70);direction=rng.randrange(3);bpp=rng.randrange(1,5)
 prepare(w,h,bpp,direction,pad=rng.randrange(0,12));put(DESC+24,[rng.randrange(w),rng.randrange(h)])
 compare(0x4ed670,EFFECT,[DESC],f'randominit{i}');compare(0x4ee6b0,EFFECT,[],f'randomradius{i}')
 maximum=get(EFFECT+0x5c)[0]
 sequence=sorted({0,maximum,*[rng.randrange(maximum+1)for _ in range(5)]})
 for step in sequence:compare(0x4ed800,EFFECT,[step],f'retainedstep{i}/{step}')
# The radius method reads surface geometry again, not cached init dimensions.
for i in range(40):
 prepare();put(SURFACE0+0x14,[rng.randrange(15,500),rng.randrange(20,1000)]);compare(0x4ee6b0,EFFECT,[],f'uncachedradius{i}')
for field,value in[(4,0),(8,0),(16,0),(20,5),(24,0xffffffff),(28,23),(24,31)]:
 prepare(direction=0);put(DESC+12,[0]);put(DESC+field,[value]);compare(0x4ed670,EFFECT,[DESC],f'initfailorfallthrough{field}/{value}')
for paletteOwn in(0,1):
 for palette in(0,PALETTE):
  for deleting in(0,1,2,3):
   prepare();put(EFFECT+0x1c,[palette]);put(EFFECT+0x30,[paletteOwn]);compare(0x4ed600,EFFECT,[deleting],'delete')
for i in range(40):
 prepare();items=[EFFECT if rng.randrange(3)==0 else 0 for _ in range(rng.randrange(8))];put(ARRAY,items);put(MANAGER+0x18,[len(items)]);compare(0x4ec600,MANAGER,[rng.choice([EFFECT,0,PALETTE])],'removefirst')
# All three pointer-array growth routes in the original inlined factory.
for count,capacity,grow in[(0,0,0),(2,2,0),(3,6,0),(4,4,7)]:
 prepare();put(MANAGER+0x18,[count,capacity,grow]);put(ARRAY,[0xabc]*8)
 if not capacity:put(MANAGER+0x14,[0])
 compare(0x4ec050,MANAGER,[1,DESC],'factoryarray')
# Actual default descriptor geometry 320,240 on640x480, including full buffers.
for fn in(0x48fae0,0x48fbe0):
 for bypass in(0,1):
  for center in[(320,240),(0,0),(639,479),(1,479)]:
   prepare(640,480,pad=0);g.bypass=bypass;H.clockStart=100;H.clockDelta=80
   compare(fn,OWNER,[*center,240,20],f'actualviewport{fn}/{bypass}/{center}')
# Source gates and music callback mutation of graph/global fields.
for fn in(0x48fae0,0x48fbe0):
 for missing in('manager','draw','primary','secondary','music','appgate'):
  prepare()
  target={'manager':OWNER+0x10,'draw':PARENT+0x1c,'primary':IMAGE0+0x2c,'secondary':IMAGE1+0x2c,'music':APP+0x50,'appgate':APP+0x14}[missing];put(target,[0]);compare(fn,OWNER,[15,11,80,0],f'gate{fn}/{missing}')
 for mutation in(1,2):
  prepare();g.bypass=1;H.mutation=mutation;compare(fn,OWNER,[15,11,80,0],f'mutation{fn}/{mutation}')
# Clock rounding/high-bit elapsed profiles; busy wait wraps its absolute deadline.
for start in(0,0x7fffffff,0x80000000,0xffffff00):
 for wait in(0,1,100,0xffffffff):
  prepare();H.clockStart=start;H.clockDelta=128;H.clockSequence=[start,(start+wait)&0xffffffff];compare(0x4ec990,EFFECT,[wait],'wait');compare(0x4b8960,0,[wait],'bypasswait');H.clockSequence=None
for start in(0,16777217,0x7fffffef,0x80000001,0xffffff00):
 for pump in(0,1):
  prepare(21,17);compare(0x4ed670,EFFECT,[DESC],'runnerinit');H.clockStart=start;H.clockDelta=64
  # Avoid wrapping inside the animation arithmetic: source uses nonwrapped
  # double timestamps, while its final FPS elapsed subtract DOES wrap.
  if start==0xffffff00:H.clockDelta=16
  compare(0x4ec9c0,EFFECT,[80,0,pump],f'runner{start}/{pump}')
# Metadata palette/capture setup is complete; pixel-gradient body stays explicit.
for direction in(0,1):
 for supplied in(0,PALETTE):
  prepare(direction=direction);put(DESC+12,[PALETTE]);put(DESC+20,[3]);put(DESC+32,[supplied]);put(PALETTE+0xc,[PIXELCAP]);compare(0x4ed670,EFFECT,[DESC],'paletteinit');compare(0x4ee820,EFFECT,[],'capturepre');compare(0x4ee860,EFFECT,[],'capturepost')
# Retained source fade-out then fade-in, with original803a timing arguments.
for i in range(16):
 prepare(80,60,pad=i%7);H.clockStart=100+i*100000;H.clockDelta=125
 compare(0x48fae0,OWNER,[40,30,1250,0],'respawnfadeout')
 # Second render target stays owned by the scene; use its seeded indexed image.
 H.clockStart+=3000
 compare(0x48fbe0,OWNER,[40,30,1000,500],'respawnfadein')
# Source default descriptor local(320,240) is valid on original viewport.
prepare(640,480,pad=0);compare(0x4ec050,MANAGER,[1,0],'null-default-descriptor')
# Negative gradient width reaches the same no-blend helper return.
for direction in(0,1):
 prepare(direction=direction);put(DESC+20,[0xffffffff]);compare(0x4ed670,EFFECT,[DESC],'negativegradientinit');compare(0x4ee6b0,EFFECT,[],'negativegradientradius')
 for step in(0,4,11,get(EFFECT+0x5c)[0]):compare(0x4ed800,EFFECT,[step],'negativegradientstep')
# Exact finite failure prefixes before factory diagnostics and palette pixels.
for direction in(0,1):
 prepare(direction=direction);put(DESC+24,[31]);H.comparePrefix(0x4ec050,MANAGER,[1,DESC],'invalid-center-factory',3,0x4ec3aa)
 prepare(direction=direction);put(EFFECT+0x2060,[3]);H.comparePrefix(0x4ed800,EFFECT,[0],'gradient-unrecovered-prefix',3,0x4ed87a if direction else 0x4edf99)
for duration in(0,1,1000):
 for start in(0,16777216,0x80000000):H.compareStalledRunner('stalled-or-zero-duration',duration,start)
prepare();put(DESC,[3]);H.comparePrefix(0x4ec050,MANAGER,[1,DESC],'wrong-circle-descriptor',3,0x4ec2ef)
prepare();H.comparePrefix(0x4ec050,MANAGER,[1,0],'invalid-default-center',3,0x4ec36b)
prepare();H.allocationFailure=True;H.comparePrefix(0x4ec050,MANAGER,[1,DESC],'null-allocation-write-prefix',1,0x4ecb08);H.allocationFailure=False
numericProfiles=H.verifyNumericProfile()
report={'calls':H.calls,'events':H.events,'prefixes':H.prefixCount,'numericProfiles':numericProfiles,'instructions':sum(0x400000<=address<0x528000 and address not in H.COUNTS for address in m.executed),'sha256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'}
print(json.dumps(report));(WORK/'verification.json').write_text(json.dumps(report,indent=2))
