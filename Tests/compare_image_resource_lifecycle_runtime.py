import image_resource_lifecycle_helpers as h
import random
rng=random.Random(0x4d27a0)
for seed in range(64):
 h.fresh(seed)
 for f in(0x4d26c0,0x4ce900,0x4ce8e0):
  h.fresh(seed);h.put(h.IMAGE+44,h.SURFACE if seed&1 else 0,h.COMP if seed&2 else 0)
  h.compare(f,h.IMAGE,[seed]if f==0x4ce8e0 else [],'cleanup seed',meaningful=f==0x4ce8e0)
 h.fresh(seed);h.put(h.COMP+12,h.PAYLOAD if seed&1 else 0);h.put(h.COMP+32,h.AUX if seed&2 else 0)
 h.compare(0x4bfc20,h.COMP,[],'compressed destructor',meaningful=False)
 h.fresh(seed);h.factory=h.SURFACE if seed&1 else 0;h.put(h.SURFACE+20,rng.choice([0,1,17,-19,0x7fffffff]),rng.choice([0,1,31,-7,0x80000000]));h.put(h.SURFACE+184,seed&2);h.put(0x54316c,seed&4);h.put(0x543170,rng.getrandbits(32));h.compare(0x4d2540,h.IMAGE,[rng.getrandbits(32),rng.getrandbits(32),seed&8],'blank init')
 h.fresh(seed);h.lost=seed&1;h.restore=seed&2;h.kind=rng.choice([0x504358,0x504944,0x524944,0x424d50,0x414e49]);h.resident=h.PAYLOAD if seed&4 else 0;h.put(h.RESOURCE+20,128 if seed&8 else 0);h.pixelResult=seed&16
 h.compare(0x4d27a0,h.IMAGE,[h.RESOURCE,seed&32],'restore gates')
 h.fresh(seed);h.put(h.IMAGE+44,h.SURFACE if seed&1 else 0);h.compare(0x4d2790,h.IMAGE,[rng.getrandbits(32)],'surface vertical-flip wrapper',meaningful=False)
# Callback-mutated pointers are reread at the actual source stages.
for mutation in(1,2,3):
 h.fresh(mutation);h.mutation=mutation;h.lost=1;h.restore=1
 h.compare(0x4d26c0 if mutation!=3 else 0x4d27a0,h.IMAGE,[]if mutation!=3 else[h.RESOURCE,1],'mutated child identities',meaningful=mutation==3)
# Aliased two compressed payload fields issue two frees; no guessed deduplication.
h.fresh();h.put(h.COMP+32,h.PAYLOAD);h.compare(0x4bfc20,h.COMP,[],'duplicate free identities',meaningful=False);assert h.freed==[h.PAYLOAD,h.PAYLOAD]
# Retained clear is idempotent because the IMAGE pointers are cleared. The
# bare compressed destructor intentionally preserves its pointer fields.
h.fresh();h.capture=True
for f,a in((0x4d26c0,[]),(0x4d26c0,[]),(0x4d2540,[31,20,1]),(0x4d27a0,[h.RESOURCE,1]),(0x4ce8e0,[1])):h.compare(f,h.IMAGE,a,'retained image lifetime',meaningful=f not in(0x4d26c0,))
h.capture=False
h.fresh();h.put(h.IMAGE+44,0);assert h.compare(0x4d27a0,h.IMAGE,[h.RESOURCE,1],'absent surface')==1
h.fresh();h.put(h.SURFACE+8,0);h.compare(0x4d27a0,h.IMAGE,[h.RESOURCE,1],'null DD prefix',unsafe=True)
# Whole PID reload wrapper: real frozen pixel leaves are covered in the joined
# retail graph; isolated numeric/palette cases keep those leaves explicit.
for seed in range(64):
 h.fresh(seed);data=h.BASE+0xa000+(seed&1);h.objects[data&~3]=2048+(data&3);h.live[data&~3]=2048+(data&3)
 h.write(data,random.Random(seed).randbytes(2048));width=4 if seed&2 else 8;height=3 if seed&4 else 7
 flags=(1 if seed&8 else 0)|(128 if seed&16 else 0)
 h.write(data+4,h.pack(flags,width,height));h.put(h.SURFACE+20,height,width)
 h.put(h.GRAPHICS+0x474,[8,16,24,32][seed%4]);h.put(h.GRAPHICS+0x878,seed&32);h.pixelResult=seed%3!=0;h.factory=h.SURFACE if seed%5 else 0
 h.capture=seed<16;h.compare(0x4bf680,h.SURFACE,[h.GRAPHICS,data,803,seed],'PID reload numeric');h.capture=False
for length in(0,768,769,800):
 h.fresh();data=h.BASE+0xa000;h.write(data,random.Random(1).randbytes(2048));h.objects[data&~3]=2048+(data&3);h.live[data&~3]=2048+(data&3);h.write(data+4,h.pack(128,4,3));h.put(h.SURFACE+20,3,4);h.put(h.GRAPHICS+0x474,8);h.put(h.GRAPHICS+0x878,0)
 h.compare(0x4bf680,h.SURFACE,[h.GRAPHICS,data,length,0],'embedded palette cutoff')
# Deliberate source/destination palette alias: source begins one byte before
# output, requiring source byte-store order rather than packed-word copying.
h.fresh();data=0x542390;h.write(data+4,h.pack(128,4,3));h.put(h.SURFACE+20,3,4);h.put(h.GRAPHICS+0x474,8);h.put(h.GRAPHICS+0x878,0);h.compare(0x4bf680,h.SURFACE,[h.GRAPHICS,data,799,0],'palette overlapping bytes')
print('PASS',h.calls,'whole original calls /',h.snapshots,'full snapshots /',sum(0x401000<=a<0x50adb5 for a in h.m.executed),'text /',len(h.m.executed),'total addresses',flush=True)

# Exact-sized replay stream; each callback retains source-owned writes,
# explicit service writes and live identities separately.
import gzip,struct
pack=lambda *v:struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def patches(a,b):return [(i,y)for i,(x,y)in enumerate(zip(a,b))if x!=y]
with gzip.open(h.WORK/'sanitizer-corpus.bin.gz','wb',compresslevel=1)as out:
 out.write(pack(len(h.captures)))
 for f,t,a,before,after,bi,value,meaningful,objects,initialLive,replay in h.captures:
  out.write(pack(f,t,len(a),*(a+[0]*(10-len(a))),value,meaningful,len(objects),len(replay)));out.write(before);out.write(after);out.write(bi)
  for token,n in objects.items():out.write(pack(token,n,int(token in initialLive)))
  shadow=before+bi[0x510000-h.iBase:0x553000-h.iBase]
  for f,t,a,value,beforeEffect,afterEffect,liveBefore,liveAfter in replay:
   b=patches(shadow,beforeEffect);d=patches(beforeEffect,afterEffect);life=[(p,int(p in liveAfter))for p in set(liveBefore)^set(liveAfter)]
   out.write(pack(f,t,len(a),*(list(a)+[0]*(10-len(a))),value,len(b),len(d),len(life)))
   for i,v in b+d:out.write(pack(i)+bytes([v]))
   for p,v in life:out.write(pack(p,v))
   shadow=afterEffect
print('CORPUS',len(h.captures),'exact span cases',flush=True)
