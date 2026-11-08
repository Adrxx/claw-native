import resource_data_helpers as h
import random,json,struct,hashlib,gzip
# Basic allocation/caching/release and source metadata lifetime.
for compose in(0,1):
 for i in range(100):
  h.reset(i,length=i%70);h.capture=bool(compose and i<3);h.ctx.allocator=h.C.pointer(h.array)if compose else h.C.POINTER(h.Array)();h.compare(0x4b61b0,h.RESOURCE,[],f'type{i}');h.compare(0x4b61c0,h.RESOURCE,[],f'acquire{compose}{i}');h.compare(0x4b61c0,h.RESOURCE,[],f'cached{compose}{i}');h.compare(0x4b6230,h.RESOURCE,[],f'release{compose}{i}');h.compare(0x4b6230,h.RESOURCE,[],f'releaseagain{compose}{i}')
h.capture=False
# Actual whole constructor preserves null-name word0, unnamed iterator fields.
for seed in range(100):
 h.reset(seed);h.put(h.RESOURCE,[random.Random(seed).getrandbits(32)for _ in range(24)]);h.put(h.RESOURCE,[0]);h.put(h.AUX,[1,2,0xffffffff]);name=h.NAME if seed%2 else 0;metadata=h.META if seed%3 else 0;aux=h.AUX if seed%4 else 0
 args=[h.OWNER,name,seed,h.TYPE,metadata,64,1234,seed+10,3,aux];h.capture=seed<10;h.compare(0x4b5ff0,h.RESOURCE,args,f'construct{seed}');h.compare(0x4b61c0,h.RESOURCE,[],f'ctorload{seed}');h.compare(0x4b6120,h.RESOURCE,[],f'destroy{seed}');h.capture=False
# Mapping wins, wraps and does not clear/release a stale allocation.
for i in range(50):
 h.reset(i);h.put(h.OWNER+12,[0xfffffff0+i]);h.put(h.OWNER+32,[0x12345678+i]);h.put(h.RESOURCE+24,[h.AUX]);h.compare(0x4b61c0,h.RESOURCE,[],f'mapped{i}');h.compare(0x4b6230,h.RESOURCE,[],f'staleRelease{i}');h.put(h.RESOURCE+24,[h.AUX]);h.compare(0x4b6120,h.RESOURCE,[],f'mappedDestroy{i}')
# Source retry/reopen retains offset/count/destination; subsequent handles fresh.
for seek,reads,retries in [([1,0],[],[1]),([1,1,0],[],[1,1]),([1],[],[0]),([],[2,3,64],[1,1]),([],[0],[0]),([1,0],[1,64],[1,1])]:
 h.reset();h.seekResults=seek[:];h.readResults=reads[:];h.retryResults=retries[:];h.capture=True;h.compare(0x4b61c0,h.RESOURCE,[],f'retry{seek}{reads}');h.compare(0x4b6230,h.RESOURCE,[],'retryrelease');h.capture=False
# Mutable raw resource/owner aliases at elected allocator/read boundaries.
for mutation in('owner','length','cache'):
 h.reset();h.mutation=mutation;h.capture=True;h.compare(0x4b61c0,h.RESOURCE,[],f'alias{mutation}');h.compare(0x4b6230,h.RESOURCE,[],f'aliasrelease{mutation}');h.capture=False
for compose in(0,1):
 h.reset();h.allocFail=True;h.ctx.allocator=h.C.pointer(h.array)if compose else h.C.POINTER(h.Array)();h.compare(0x4b61c0,h.RESOURCE,[],f'allocfail{compose}')
# Original disc payloads, allclasses/worlds and actual byte sizes/offsets.
b=(h.ROOT/'Original/claw-disc/files/DATA/CLAW.REZ').read_bytes();assert hashlib.sha256(b).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596';assets=[]
def w(o):return struct.unpack_from('<I',b,o)[0]
def walk(at,size,path=()):
 end=at+size
 while at<end:
  kind,target,length=w(at),w(at+4),w(at+8);start=at+(16 if kind else 28);nul=b.index(0,start,end);name=b[start:nul]
  if kind:walk(target,length,path+(name,));at=nul+1
  else:
   tag=w(at+20);assets.append((path,name,tag,w(at+16),target,length));at=nul+2
walk(w(131),w(135));selected={}
for row in assets:
 path,name,tag,id,offset,length=row
 if length>=h.SIZE-(h.ALLOC-h.BASE):continue
 key=(path[0]if path else b'',tag)
 if key not in selected:selected[key]=row
# Include actual BOOTY Level14PCX and all14 compressed worlds.
for row in assets:
 path,name,tag,id,offset,length=row
 if tag==0x575744 or(path[:2]==(b'STATES',b'BOOTY')and tag==0x504358):selected[(path,name,tag)]=row
for i,row in enumerate(selected.values()):
 path,name,tag,id,offset,length=row;h.reset(i,length);h.payload=b[offset:offset+length];h.write(h.NAME,name+b'\0');h.put(h.TYPE,[tag]);args=[h.OWNER,h.NAME,id,h.TYPE,0,length,offset,0,0,0];h.capture=i<10;h.compare(0x4b5ff0,h.RESOURCE,args,f'realCtor{path}{name}');data=h.compare(0x4b61c0,h.RESOURCE,[],f'realLoad{path}{name}');assert h.read(data,length)==h.payload if length else data==0;h.compare(0x4b61c0,h.RESOURCE,[],f'realCache{path}{name}');h.compare(0x4b6230,h.RESOURCE,[],f'realRelease{path}{name}');h.compare(0x4b6120,h.RESOURCE,[],f'realDestroy{path}{name}');h.capture=False
print('PASS',h.calls,'calls',h.snapshots,'snapshots','realprofiles',len(selected),flush=True)
# Constructor normal allocation failures still return the original receiver.
for i in range(6):
 h.reset(i);h.allocFail=True;h.compare(0x4b5ff0,h.RESOURCE,[h.OWNER,h.NAME,1,h.TYPE,h.META,64,1234,0,3,h.AUX],f'ctorallocfail{i}');h.compare(0x4b6120,h.RESOURCE,[],f'ctorallocfailcleanup{i}')
for value in(1,0x87654321,0xffffffff):
 h.reset(value);h.put(h.RESOURCE,[value]);h.compare(0x4b5ff0,h.RESOURCE,[h.OWNER,0,1,h.TYPE,0,0,0,0,0,0],f'nullnamepreserves{value}');assert h.get(h.RESOURCE)==value
# Caller-facing direct read adapter and count0 path (no stream dereference).
for n in(0,1,2,3,17,64):
 h.reset();h.compare(0x4b7ab0,h.STREAM,[0,n,h.AUX],f'directread{n}')
h.reset();h.compare(0x4b7ab0,0,[0,0,0],'zeroreadnullstream')
# Source unchecked-null failure prefixes preserve all earlier side effects.
unsafe=[]
for f,t,args,mutation in [(0x4b61c0,0,[],''),(0x4b61b0,0,[],''),(0x4b6230,0,[],''),(0x4b61c0,h.RESOURCE,[],'nullOwner')]:
 h.reset();h.mutation=mutation;before=bytes(h.heap);bi=bytes(h.image);h.ctx.fault=0;h.events.clear();h.oevents.clear();a=(h.U*len(args))(*args);out=h.U();ok=h.lib.claw_resource_data_entry(f,t,a,len(args),h.C.byref(h.ctx),h.dep,None,h.C.byref(out));assert not ok and h.ctx.fault==1;expected=h.raw();ev=h.events[:];h.native=False;h.cursor=h.ALLOC;h.m.u.mem_write(h.BASE,before);h.m.u.mem_write(h.iBase,bi)
 try:h.m.call(f,t,h.pack(*args));raise AssertionError('originalfault expected')
 except h.UcError:pass
 assert h.raw()==expected and h.oevents==ev;unsafe.append((hex(f),hex(h.m.u.reg_read(h.UC_X86_REG_EIP))))
# Paired exact-span corpus including scalar service mutation patches.
with gzip.open(h.WORK/'sanitizer-corpus.bin.gz','wb')as f:
 f.write(struct.pack('<I',len(h.replays)))
 for func,t,args,before,after,image,ret,objects,events,allocator in h.replays:
  f.write(struct.pack('<16I',func,t,len(args),*(args+[0]*10)[:10],ret,len(objects),len(events)));f.write(struct.pack('<I',allocator));f.write(before);f.write(after);f.write(image)
  for token,size in objects.items():f.write(struct.pack('<2I',token,(size+3)&~3))
  for func,t,args,ret,before,after in events:
   patches=[(i,y)for i,(x,y)in enumerate(zip(before,after))if x!=y];f.write(struct.pack('<15I',func,t,len(args),*(args+[0]*10)[:10],ret,len(patches)))
   for off,val in patches:f.write(struct.pack('<IB',off,val))
report={'wholeCalls':h.calls,'completeSnapshots':h.snapshots,'unsafePrefixes':unsafe,'realProfiles':len(selected),'retailWWDHistories':len([r for r in selected.values()if r[2]==0x575744]),'distinctRetailWWDProfiles':len(set(r[4]for r in selected.values()if r[2]==0x575744)),'exactSizeReplays':len(h.replays),'instrumentedAddresses':len(h.m.executed),'originalTextInstrumented':len([v for v in h.m.executed if 0x401000<=v<0x50adb6])}
(h.WORK/'report.json').write_text(json.dumps(report,indent=2));(h.WORK/'real-profiles.json').write_text(json.dumps([{'path':'/'.join(p.decode()for p in row[0]),'name':row[1].decode(),'type':hex(row[2]),'id':row[3],'offset':row[4],'bytes':row[5]}for row in selected.values()],indent=2));print('FINAL',report,flush=True)
