import player_fade_blend_runtime_helpers as H
from player_fade_blend_runtime_helpers import *
for direction in(0,1):
 for bpp in(1,2,3,4):
  for center in[(15,11),(1,1),(29,21),(15,0),(15,22),(0,11),(30,11)]:
   gradientProfile(bpp=bpp,direction=direction,cx=center[0],cy=center[1]);maximum=get(EFFECT+0x5c)[0]
   for step in sorted({0,1,3,maximum//2,maximum-1,maximum}):compare(0x4ed800,EFFECT,[step],f'wholepositive{direction}/{bpp}/{center}/{step}')
   compare(0x4ee860,EFFECT,[],'gradient-post')
for field,value in[(0,3),(24,31),(28,23),(20,3)]:
 prepare();put(DESC+12,[0]);put(DESC+field,[value]);compare(0x4ec050,MANAGER,[1,DESC],f'factory-diagnostic{field}/{value}')
# Original palette builder and first-tie nearest-color conversion.
for gradient in(0,1,2,3,7):
 for target in(0,0xffffff,0x123456,0xff0080):
  prepare();put(COLORS,[rng.getrandbits(32)for _ in range(256)]);put(EFFECT+4,[0,0x5136e8,ARRAY,0,8,0]);compare(0x4c6bd0,EFFECT+4,[COLORS,gradient,target],f'palette{gradient}/{target}')
for i in range(40):
 prepare();put(COLORS,[rng.getrandbits(32)for _ in range(256)]);compare(0x4c7580,0,[COLORS,*[rng.getrandbits(32)for _ in range(3)]],'nearest')
# Positive gradients across signed magnitudes, odd shapes and retained steps.
for i in range(100):
 w=rng.randrange(1,70);h=rng.randrange(1,60);gradient=rng.choice([1,2,3,7,31,255,511]);direction=rng.randrange(2);bpp=rng.randrange(1,5)
 gradientProfile(w,h,bpp,direction,gradient,pad=rng.randrange(9),cx=rng.randrange(w),cy=rng.randrange(h));maximum=get(EFFECT+0x5c)[0]
 for step in sorted({0,maximum,*[rng.randrange(maximum+1)for _ in range(4)]}):compare(0x4ed800,EFFECT,[step],f'randompositive{i}/{step}')
 compare(0x4ee860,EFFECT,[],'postrandom')
# Aliasing is observable: actual repeated center writes can re-read changed
# source bytes. Verify primary/other/capture overlap and shifted source starts.
for direction in(0,1):
 for offset in(0,1,3,7):
  gradientProfile(direction=direction,gradient=7)
  H.pixelMappings={SURFACE0:PIXEL0,SURFACE1:PIXEL0+offset,CAPTURE:PIXEL0+offset}
  for step in(0,3,7,get(EFFECT+0x5c)[0]):compare(0x4ed800,EFFECT,[step],f'alias{direction}/{offset}/{step}')
  H.pixelMappings=None
# Direct helper calls include asymmetric row clipping and canonical-half skips.
for i in range(120):
 w=rng.randrange(1,60);h=rng.randrange(1,50);gwidth=rng.choice([1,3,31,255]);gradientProfile(w,h,direction=0,gradient=gwidth,cx=rng.randrange(w),cy=rng.randrange(h));radius=rng.randrange(1,90);row=rng.randrange(h)
 compare(0x4ee170,EFFECT,[row,radius*radius,radius,PALETTEPIX,PIXEL0,PIXEL1],'directband')
# A source color palette from extracted CD assets, expanded into the explicit
# four-byte palette argument view. The channel labels are not inferred.
rawPalette=(ROOT/'App/GameData/LEVEL1/PALETTES/MAIN.PAL').read_bytes();assert len(rawPalette)==768
words=[int.from_bytes(rawPalette[i:i+3]+b'\0','little')for i in range(0,768,3)]
for gradient in(3,9,17):
 prepare();put(COLORS,words);put(EFFECT+4,[0,0x5136e8,ARRAY,0,8,0]);compare(0x4c6bd0,EFFECT+4,[COLORS,gradient,0x183060],'actual-palette')
# Exact ties prefer index0; high bytes of channel arguments are masked.
for fill in(0,0x7f7f7f,0xffffff):
 prepare();put(COLORS,[fill]*256);compare(0x4c7580,0,[COLORS,0xff000020,0x1000040,0x88880060],'firsttie')
# Palette allocator failure at the object or backing byte allocation preserves
# each original reached store and leak, including originally safe0 returns.
for ordinal in(0,1):
 prepare();put(COLORS,words);put(EFFECT+4,[0,0x5136e8,ARRAY,0,8,0]);H.allocationFailureOrdinal=ordinal;compare(0x4c6bd0,EFFECT+4,[COLORS,3,0],'palette-failure')
# Raw CString construction and capacity/header/terminator stores, literal,
# zero-length and integer-resource paths. By-value release retains the cell.
for text in(0,0x53404c,0x5340a0,9):
 prepare();compare(0x4f65f2,TEMP,[text],'cstring-ctor');value=get(TEMP)[0];compare(0x4ec6b0,MANAGER,[value],'byvalue-release')
for length in(0,1,3,17,127):
 prepare();compare(0x4f6480,TEMP,[length],'cstring-allocation')
# Whole factory success/failure and composed source clocks on a positive circle.
for direction in(0,1):
 for bpp in(1,2,3,4):
  gradientProfile(bpp=bpp,direction=direction,gradient=7);H.clockStart=16777217;H.clockDelta=32
  compare(0x4ec9c0,EFFECT,[100,20,1],'positive-runner')
  compare(0x4ec600,MANAGER,[EFFECT],'empty-manager-removal')
for fn in(0x48fae0,0x48fbe0):
 for center in[(15,11),(31,11),(0xffffffff,11),(15,23)]:
  prepare();compare(fn,OWNER,[*center,100,20],'whole-wrapper-or-diagnostic')
# Pure palette lifetime follows source flags and re-reads array slots after
# object reset/free callbacks; unused tails and dangling flags remain exact.
for ownerFlag in(0,1):
 for objectFlag in(0,1):
  for fn in(0x4c78d0,0x4c76e0,0x4c7510,0x4c6270,0x4c61f0):
   prepare();put(PALOBJECT,[objectFlag,256,PALETTEPIX]);put(EFFECT+4,[ownerFlag,0x5136e8,ARRAY,1,4,0]);put(ARRAY,[PALOBJECT,0x12345678,0xabcdef00]);receiver=PALOBJECT if fn in(0x4c78d0,0x4c76e0)else EFFECT+4;arguments=[PALOBJECT]if fn==0x4c7510 else [];compare(fn,receiver,arguments,'palette-lifetime')
for count,capacity,grow,newCount in[(0,0,0,0),(0,0,0,1),(1,1,0,5),(2,6,0,3),(3,6,4,0),(4,4,7,5)]:
 prepare();put(EFFECT+8,[0x5136e8,ARRAY if capacity else 0,count,capacity,grow]);put(ARRAY,[PALOBJECT]*8);compare(0x4dee30,EFFECT+8,[newCount,0xffffffff],'palette-array')
# Genuine initializer→palette build→controller→post→derived destructor graphs.
# All per-color conversion and source circle writes execute original bodies.
for direction in(0,1):
 for bpp in(1,2,3,4):
  prepare(bpp=bpp,direction=direction);put(COLORS,words);put(PALETTE+12,[COLORS]);put(DESC+12,[PALETTE]);put(DESC+20,[3]);put(DESC+32,[0]);compare(0x4ed5e0,EFFECT,[],'real-gradient-constructor');put(EFFECT+0x24,[SURFACE0,SURFACE1,HOLDER]);compare(0x4ed670,EFFECT,[DESC],'real-gradient-initialize');H.clockStart=100;H.clockDelta=25;compare(0x4ec9c0,EFFECT,[100,0,1],'real-gradient-run');compare(0x4ed600,EFFECT,[1],'real-gradient-deletion')
# Unequal source/destination/capture pitches: clear blending indexes capture
# with the other surface pitch, exactly as the original instructions do.
for direction in(0,1):
 for bpp in(1,2,3,4):
  gradientProfile(bpp=bpp,direction=direction,gradient=7);put(SURFACE1+0x1c,[31*bpp+9]);put(CAPTURE+0x1c,[31*bpp+13])
  for step in(0,3,8,get(EFFECT+0x5c)[0]):compare(0x4ed800,EFFECT,[step],'unequal-stride')
# Negative/zero gradient retains frozen original no-blend paths, including
# signed endpoint overflow; the helper itself is a complete no-op.
for gradient in(0,0xffffffff,0xfffffffd,0x80000000):
 for direction in(0,1):
  prepare(direction=direction);put(DESC+20,[gradient]);compare(0x4ed670,EFFECT,[DESC],'signed-gradient-init');compare(0x4ee6b0,EFFECT,[],'signed-radius')
  for step in(0,3,7,get(EFFECT+0x5c)[0]):compare(0x4ed800,EFFECT,[step],'signed-gradient-step')
  compare(0x4ee170,EFFECT,[11,100,10,PALETTEPIX,PIXEL0,PIXEL1],'signed-gradient-helper')
# Native stack seed faithfully represents capture-local use without pre.
# This is raw finite-source evidence, not a real platform allocation profile.
gradientProfile(direction=1);put(EFFECT+0x40,[0]);compare(0x4ed800,EFFECT,[3],'explicit-capture-local-seed')
# Pure palette free callback mutates current array slot; source re-reads it
# after resetting the old object and before freeing the current one.
prepare();put(PALOBJECT,[1,256,PALETTEPIX]);put(EFFECT+4,[0,0x5136e8,ARRAY,1,4,0]);put(ARRAY,[PALOBJECT]);H.mutation=3;compare(0x4c7510,EFFECT+4,[PALOBJECT],'mutable-array-slot')
# Original factory diagnostic returns0 after a true source string allocation,
# release and circle teardown; next retained call may use the manager normally.
prepare();put(DESC+24,[31]);compare(0x4ec050,MANAGER,[1,DESC],'retained-invalid-circle');put(DESC+24,[15]);compare(0x4ec050,MANAGER,[1,DESC],'retained-valid-circle');compare(0x4ec600,MANAGER,[EFFECT],'retained-remove-circle')
# Palette backing allocation failure for negative shifted size, and zero shift.
for gradient,ordinal in[(0xffffffff,1),(0x80000000,-1)]:
 prepare();put(COLORS,words);put(EFFECT+4,[0,0x5136e8,ARRAY,0,8,0]);H.allocationFailureOrdinal=ordinal;compare(0x4c6bd0,EFFECT+4,[COLORS,gradient,0],'signed-palette-builder')
# Exact unsafe prefixes: source would write through a null allocator result.
prepare();H.allocationFailure=True;H.comparePrefix(0x4f6480,TEMP,[17],'cstring-null-write',1,0x4f649e)
prepare();put(COLORS,words);put(EFFECT+4,[0,0x5136e8,0,0,0,0]);H.allocationFailureOrdinal=2;H.comparePrefix(0x4c6bd0,EFFECT+4,[COLORS,3,0],'palette-array-null-write',2,0x4dee91)
prepare();put(DESC+12,[0]);put(DESC,[3]);H.allocationFailure=True;H.comparePrefix(0x4ec050,MANAGER,[1,DESC],'diagnostic-string-null-write',1,0x4f649e)
# Missing palette/owned node prefixes preserve earlier border writes and
# leave later row-table/previous-step/vtable stores unreached.
gradientProfile(direction=0);H.comparePrefix(0x4ee170,EFFECT,[11,49,7,0,PIXEL0,PIXEL1],'null-palette-helper-prefix',1,0x4ee2d5)
gradientProfile(direction=1);put(EFFECT+0x1c,[0]);H.comparePrefix(0x4ed800,EFFECT,[3],'null-palette-whole-step-prefix',1,0x4edb28)
prepare();put(EFFECT+4,[1,0x5136e8,ARRAY,1,4,0]);put(ARRAY,[0]);H.comparePrefix(0x4c61f0,EFFECT+4,[],'null-owned-node-prefix',1,0x4c78d0)
report={'calls':H.calls,'events':H.events,'prefixes':H.prefixCount,'instructions':sum(0x400000<=a<0x528000 and a not in H.COUNTS for a in m.executed),'sha256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'}
print(json.dumps(report));(WORK/'verification.json').write_text(json.dumps(report,indent=2))
