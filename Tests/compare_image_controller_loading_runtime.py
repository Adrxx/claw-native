#!/usr/bin/env python3
import image_controller_loading_helpers as g
for seed in range(64):
 g.reset(seed);g.capture=seed==0
 if seed%2:g.put(g.MAP+24,1+seed%11)
 if seed%3:g.put(g.MAP+8,1+seed%19)
 for key in (b'KEY',b'key',b'',b'K\x80\xff',b'collision',b'KEY'):
  g.write(g.KEY,key+b'\0');g.put(g.OUT,0xabcdef01)
  g.compare(0x4f5d5c,g.MAP,[g.KEY,g.OUT],f'{seed}/{key}/hash-miss')
  g.compare(0x4f6286,g.MAP,[g.KEY,g.OUT],f'{seed}/{key}/lookup')
  slot=g.compare(0x4f62a8,g.MAP,[g.KEY],f'{seed}/{key}/insert')
  g.put(slot,0xfed00000+seed)
  g.compare(0x4f6286,g.MAP,[g.KEY,g.OUT],f'{seed}/{key}/retained')
 for key in (b'KEY',b'key',b'',b'K\x80\xff',b'collision',b'KEY'):
  g.write(g.KEY,key+b'\0');g.compare(0x4f5db6,g.MAP,[g.KEY],f'{seed}/{key}/remove')
 assert g.get(g.MAP+12)==0 and g.get(g.MAP+4)==0 and g.get(g.MAP+20)==0
g.capture=False
print('PASS dictionaries',g.calls,g.snapshots,flush=True)
for seed in range(16):
 g.reset(seed);g.mutation=1;g.mutationTarget=g.MAP+24
 g.compare(0x4f62a8,g.MAP,[g.KEY],f'allocator-mutation/{seed}')
for buckets in(1,3,17,64):
 for allocate in(0,1,2):
  g.reset();g.compare(0x4f615b,g.MAP,[buckets,allocate],f'table-init/{buckets}/{allocate}',False)
  g.compare(0x4f615b,g.MAP,[17,0],f'table-release/{buckets}/{allocate}',False)
print('PASS mutation/table',g.calls,g.snapshots,flush=True)
# Actual source directory records, then actual frozen bucket traversal/image load.
import struct
folders=[]
def w(i):return struct.unpack_from('<I',g.rez,i)[0]
def walk(at,n,path=()):
 folders.append((path,at,n));end=at+n
 while at<end:
  kind=w(at);start=at+(16 if kind==1 else 28);nul=g.rez.index(0,start,end);name=g.rez[start:nul]
  if kind==1:walk(w(at+4),w(at+8),path+(name,));at=nul+1
  else:meta=g.rez.index(0,nul+1,end);at=meta+1+w(at+24)*4
walk(w(131),w(135))
for path in[(b'STATES',b'MENU',b'IMAGES'),(b'STATES',b'BOOTY',b'IMAGES')]:
 row=next((x for x in folders if x[0]==path),None)
 if row is None:print('NO PROFILE',path,flush=True);continue
 g.reset(joined=True);g.compare(0x4b7210,g.CONTROL,[],f'{path}/controller');g.put(g.CONTROL+12,0x7771)
 g.compare(0x4b6600,g.FOLDER,[g.CONTROL,0,g.DIRECTORYNAME,row[1],row[2],0],f'{path}/folder',common=True)
 g.compare(0x4b6b60,g.FOLDER,[row[1],row[2]],f'{path}/source-REZ-graph')
 g.write(g.KEY,b'MENU\0' if path[1]==b'MENU' else b'BOOTY\0')
 count=g.compare(0x4cff40,g.IMAGECONTROLLER,[g.FOLDER,g.KEY,g.SEPARATOR],f'{path}/source-registry')
 print('PASS joined',path,count,len(g.imageLoads),g.calls,g.snapshots,flush=True)

 # Retained source cache duplicate load, restoration and named removal.
 initial=g.get(g.IMAGECONTROLLER+28);beforeLoads=len(g.imageLoads)
 assert g.compare(0x4cff40,g.IMAGECONTROLLER,[g.FOLDER,g.KEY,g.SEPARATOR],f'{path}/duplicate')==count
 assert len(g.imageLoads)==beforeLoads and g.get(g.IMAGECONTROLLER+28)==initial
 assert g.compare(0x4d0120,g.IMAGECONTROLLER,[g.FOLDER,g.KEY,g.SEPARATOR],f'{path}/restore')==count
 table=g.get(g.IMAGECONTROLLER+20);roots=[]
 for bucket in range(g.get(g.IMAGECONTROLLER+24)):
  p=g.get(table+bucket*4) if table else 0
  while p:
   roots.append((g.text(g.get(p+8)),g.get(p+12)));p=g.get(p)
 for name,root in roots:
  g.write(g.KEY,name+b'\0');g.compare(0x4f6286,g.IMAGECONTROLLER+16,[g.KEY,g.OUT],f'{path}/{name}/true-lookup')
  assert g.get(g.OUT)==root
  g.compare(0x4cf230,g.IMAGECONTROLLER,[g.KEY],f'{path}/{name}/remove',False)
 assert g.get(g.IMAGECONTROLLER+28)==0 and g.get(g.IMAGECONTROLLER+20)==0
 g.compare(0x4b66d0,g.FOLDER,[],f'{path}/REZ-cleanup',False,common=True)
 print('PASS retained',path,g.calls,g.snapshots,flush=True)
# Hash-output aliases the key; the source store precedes strcmp.
for seed in range(12):
 g.reset(seed);g.compare(0x4f62a8,g.MAP,[g.KEY],f'alias/{seed}/insert')
 g.compare(0x4f5d5c,g.MAP,[g.KEY,g.KEY],f'alias/{seed}/hash-output-key')
g.reset();slot=g.compare(0x4f62a8,g.MAP,[g.KEY],'present-null-slot');assert g.get(slot)==0
g.put(g.OUT,0xabcdef01);assert g.compare(0x4f6286,g.MAP,[g.KEY,g.OUT],'present-null-value')==1 and g.get(g.OUT)==0
g.put(g.OUT,0xabcdef01);assert g.compare(0x4f6286,g.MAP,[g.ALT,g.OUT],'miss-output-preservation')==0 and g.get(g.OUT)==0xabcdef01
# Native unsupported-entry guard is an API check, not an original-function proof.
g.ctx.fault=0;out=g.U(0x12345678)
assert g.lib.claw_image_controller_loading_entry(0x12345678,g.MAP,None,0,g.C.byref(g.ctx),g.dep,None,g.C.byref(out))==0
assert out.value==0x12345678 and not g.ctx.fault
print('PASS final',g.calls,g.snapshots,flush=True)

g.reset();g.put(g.MAP+8,0);g.prefix(0x4f5d5c,g.MAP,[g.KEY,g.OUT],0x4f5d7c,'zero-bucket-divide')
g.reset();g.failedOrdinal=0;g.prefix(0x4f615b,g.MAP,[17,1],0x4a4a20,'null-bucket-memset')
g.reset();g.failedOrdinal=1;g.prefix(0x4f62a8,g.MAP,[g.KEY],0x4f6253,'null-association-plex')
print('PASS prefixes',g.prefixCount,g.snapshots,flush=True)
import hashlib,json,gzip
report=dict(wholeOriginalCalls=g.calls,orderedFullSnapshots=g.snapshots,unsafePrefixes=g.prefixCount,instrumentedTextAddresses=len([a for a in g.m.executed if 0x401000<=a<0x50adb5]),totalInstrumentedAddresses=len(g.m.executed),sanitizerCases=len(g.captures),heapBytes=g.SIZE,globalBytes=0x43000,retailProfiles={"STATES_MENU/IMAGES":{"roots":20,"loadCalls":295},"STATES_BOOTY/IMAGES":{"roots":52,"loadCalls":452}},limits="CString and physical image/FILE endpoints explicit; REZ records/table/bucket traversal and controller/cache bodies execute; source image pixels and full IFC/Story frame not proved here")
(g.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
with gzip.open(g.WORK/'sanitizer-corpus.bin.gz','wb')as target:
 target.write(g.pack(len(g.captures)))
 for f,t,a,before,after,img,result,meaningful,objects,initialLive,events in g.captures:
  target.write(g.pack(f,t,len(a),*(a+[0]*10)[:10],result,int(meaningful),len(objects),len(events)));target.write(before);target.write(after);target.write(img)
  for token,size in objects.items():target.write(g.pack(token,(size+3)&~3,int(token<g.ALLOC or token in initialLive)))
  shadow=before+img[0x510000-g.iBase:0x553000-g.iBase]
  for f,t,a,result,bef,aft,activeBefore,activeAfter in events:
   patchesBefore=[(i,v)for i,(x,v)in enumerate(zip(shadow,bef))if x!=v];patchesAfter=[(i,v)for i,(x,v)in enumerate(zip(bef,aft))if x!=v]
   changes=[(p,int(p in activeAfter))for p in set(activeBefore)|set(activeAfter)if(p in activeBefore)!=(p in activeAfter)]
   target.write(g.pack(f,t,len(a),*(list(a)+[0]*10)[:10],result,len(patchesBefore),len(patchesAfter),len(changes)))
   for patches in(patchesBefore,patchesAfter):
    for at,v in patches:target.write(struct.pack('<IB',at,v))
   for p,state in changes:target.write(g.pack(p,state))
   shadow=aft
print('PASS corpus',len(g.captures),flush=True)
