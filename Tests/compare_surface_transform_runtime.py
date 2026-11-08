"""Source4b99d0 full heap/ordered lock/allocator comparisons."""
import surface_transform_helpers as h
import struct,json
for width in(0,1,2,3,4,7,16,31):
 for height in(-1,0,1,2,3,4,7):
  for extra in(0,1,5):
   h.fresh(width,height,width+extra,width*31+height);h.compare('numeric rows',capture=width in(2,3)and height in(2,3))
for status in(0x80004005,0x887601c2):
 for restore in(0,1):
  h.fresh(7,5,11);h.lockResult=status;h.restore=restore;h.compare('lock failure',True)
h.fresh(7,5,11);h.allocation=False;h.compare('allocation failure unlock',True)
h.fresh(7,5,11);h.unlockResult=0x80004005;h.compare('ignored unlock failure',True)
h.fresh(7,5,11);h.mutate=True;h.compare('post allocation geometry reread',True)
for pitch in(0,1,3):
 h.fresh(7,5,pitch);h.compare('overlapping row stride',True)
h.fresh(7,5,11);h.alias=h.SURFACE+64;h.compare('scratch aliases surface unrelated fields',True)
for offset in(0,1,8):
 h.fresh(7,5,11);h.alias=h.PIXELS+offset;h.compare('scratch aliases pixels',True)
# Depth does not change the width-byte loop: untouched row tail is compared.
for depth in(8,16,24,32):
 h.fresh(5,7,5*(depth//8)+3);h.put(h.SURFACE+164,depth);h.compare('all pixel depths',True)
profiles={}
for p in sorted((h.ROOT/'App/GameData').rglob('*.PID')):
 b=p.read_bytes();w,y=struct.unpack_from('<II',b,8)
 if 0<w<=640 and 1<y<=480:profiles.setdefault((w,y),str(p.relative_to(h.ROOT)))
for (w,y),p in profiles.items():
 h.fresh(w,y,(w+3)&~3,len(p));before=h.read(h.PIXELS,h.live[h.PIXELS]);h.compare('retail derived '+p)
 # Retained involution asserted only for disjoint ordinary pitch/temporary.
 h.compare('retained restore '+p);assert h.read(h.PIXELS,h.live[h.PIXELS])==before
h.fresh(3,5,7);h.compose=False;h.compare('explicit whole lock boundary',True)
print('PASS',h.calls,'whole original calls /',h.snapshots,'full snapshots /',len(profiles),'retail-derived dimensions /',sum(0x401000<=a<0x50adb5 for a in h.m.executed),'text /',len(h.m.executed),'total',flush=True)
print('CAPTURE',len(h.captures),flush=True)

# Exact allocation replay corpus retains every callback's full native writes.
import gzip
pack=h.pack
def patches(a,b):return [(i,y)for i,(x,y)in enumerate(zip(a,b))if x!=y]
with gzip.open(h.WORK/'corpus.bin.gz','wb',compresslevel=1)as out:
 out.write(pack(len(h.captures)))
 for before,after,initialLive,objects,freed,events,policy,trace in h.captures:
  out.write(pack(policy[4],len(objects),len(trace)));out.write(before);out.write(after);out.write(bytes(h.pe))
  for token,n in objects.items():out.write(pack(token,n,int(token in initialLive)))
  shadow=before
  for f,t,a,value,beforeEffect,afterEffect,liveBefore,liveAfter in trace:
   b=patches(shadow,beforeEffect);d=patches(beforeEffect,afterEffect);life=[(p,int(p in liveAfter))for p in set(liveBefore)^set(liveAfter)]
   out.write(pack(f,t,len(a),*(list(a)+[0]*(8-len(a))),value,len(b),len(d),len(life)))
   for i,v in b+d:out.write(pack(i)+bytes([v]))
   for p,v in life:out.write(pack(p,v))
   shadow=afterEffect
