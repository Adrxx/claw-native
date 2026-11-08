#!/usr/bin/env python3
import resource_table_construction_helpers as H
from resource_table_construction_helpers import *
reset();compare(0x4b6600,FOLDER,[CONTROL,0,NAME,0,0,0],'folderConstructor');compare(0x4b7170,FOLDER,[0x504944],'getOrCreateType');compare(0x4b69a0,FOLDER,[META],'createChild');compare(0x4b6a60,FOLDER,[27,META,0x504944],'createResource');compare(0x4b66d0,FOLDER,[],'wholeTreeDestroy',False)
print('PASS initial',H.calls,H.snapshots,flush=True)
import random,json,hashlib,struct,gzip
r=random.Random(0x4b6600)
#Complete map/bucket constructor, preserved unused bucket words/header layout.
for count in(0,1,2,5,9,19,31,127):
 for seed in range(4):
  reset(seed);compare(0x4d53a0,MAP,[count],('map',count,seed));table=get(MAP+4);assert get(table-4)==count
  for i in range(count):assert get(table+16*i+8)==0 and get(table+16*i+12)==0
  compare(0x4d5420,MAP,[],'mapDestroy',False);assert get(MAP+4)==table
for seed in range(16):
 reset(seed);compare(0x4d5410,NODE,[],'bucket');compare(0x4b64b0,OBJECT,[r.getrandbits(32)],'typeConstructor');compare(0x4b6530,OBJECT,[],'emptyTypeDestructor',False)
#Retained source namespace construction, duplicates and collision order.
for seed in range(24):
 reset(seed);H.capture=seed<2;compare(0x4b6600,FOLDER,[CONTROL,0,NAME,seed,seed+9,seed+17],'treeCtor')
 for i,s in enumerate((b'alpha',b'bravo',b'cider',b'Delta',b'ALPHA',b'',b'longername')):
  write(META,s+b'\0');value=compare(0x4b69a0,FOLDER,[META],('folderAdmission',seed,s));assert bool(value)==(i!=4)
 for tag in(0,0x504944,0x414e49,0xffffffff,0x504944):compare(0x4b7170,FOLDER,[tag],('typeReuse',seed,tag))
 for i,s in enumerate((b'FRAME001',b'FRAME002',b'FRAME003',b'frame001',b'OTHER',b'',b'X')):
  write(META,s+b'\0');value=compare(0x4b6a60,FOLDER,[i if i!=4 else 0,META,0x504944],('resourceAdmission',seed,i,s));assert bool(value)==(i not in(3,4))
 compare(0x4b66d0,FOLDER,[],'recursiveDestroy',False);H.capture=False
print('PASS retained',H.calls,H.snapshots,flush=True)
#Allocation failures preserve source partial maps/name pointers and return.
for f,t,args,n in[(0x4b6600,FOLDER,[CONTROL,0,NAME,1,2,3],3),(0x4b64b0,OBJECT,[0x504358],2),(0x4d53a0,MAP,[19],1)]:
 for failed in range(n):reset();H.failedOrdinal=failed;compare(f,t,args,('constructorFailedAllocation',hex(f),failed))
for f,args in[(0x4b69a0,[META]),(0x4b7170,[0x504944]),(0x4b6a60,[17,META,0x504944])]:
 reset();compare(0x4b6600,FOLDER,[CONTROL,0,NAME,0,0,0],'failureRoot');
 if f==0x4b6a60:compare(0x4b7170,FOLDER,[0x504944],'existingTypeForResourceAllocationFailure')
 H.failedOrdinal=H.ordinal;compare(f,FOLDER,args,('failedObjectAlloc',hex(f)))
#Source allocator and timestamp callbacks can mutate aliases before re-reads.
for mutation in(1,2,3):
 reset();compare(0x4b6600,FOLDER,[CONTROL,0,NAME,0,0,0],'aliasRoot');H.mutate=mutation;H.mutationTarget=META if mutation==1 else FOLDER+24;compare(0x4b69a0,FOLDER,[META],('creatorAlias',mutation));H.mutate=0;compare(0x4b66d0,FOLDER,[],'aliasCleanup',False)
#Generic insertion really calls the embedded node's original virtual hash.
for index in(0,1,4):
 reset();compare(0x4d53a0,MAP,[5],'virtualHashMap');put(NODE,[VT,0,0,0,0,0]);H.mutate=index;compare(0x4d5450,MAP,[NODE],('customHash',index),False);compare(0x4d5490,MAP,[NODE],'customRemove',False)
print('PASS failures/aliases',H.calls,H.snapshots,flush=True)
#Untouched embedded words and name allocation prefixes across admitted lengths.
for length in(0,1,2,3,4,7,19,63,64,127):
 reset(length);write(NAME,b'A'*length+b'\0');compare(0x4b6600,FOLDER,[CONTROL,0,NAME,0xf0000001,0xdeadbeef,0xffffffff],('folderRawFields',length));compare(0x4b66d0,FOLDER,[],'folderRawCleanup',False)
for timestamp in(0,1,0x80000000,0xffffffff):
 reset();H.timeValue=timestamp;compare(0x4b7cc0,CONTROL,[],'sourceTimeLocal');compare(0x4b6600,FOLDER,[CONTROL,0,NAME,0,0,0],'timeRoot');compare(0x4b69a0,FOLDER,[META],'timeChild')
#Allocation failure of missing type is NOT a safe resource creator return.
reset();compare(0x4b6600,FOLDER,[CONTROL,0,NAME,0,0,0],'unsafeTypeRoot');H.failedOrdinal=H.ordinal;H.comparePrefix(0x4b6a60,FOLDER,[17,META,0x504944],'nullTypeUncheckedIDMap',0x4d54f4)
reset();H.comparePrefix(0x4d5450,MAP,[0],'nullInsertNode',0x4d5458)
reset();put(MAP,[5,ALLOC]);H.comparePrefix(0x4d5490,MAP,[0],'nullRemoveNode',0x4d54a3)
print('PASS directed',H.calls,H.snapshots,H.prefixes,flush=True)
#Compose real source allocator wrappers against their unchanged original CRT
#transport, keeping the same object graph and seed fields.
for seed in range(8):
 reset(seed);ctx.allocator=C.pointer(array);compare(0x4b6600,FOLDER,[CONTROL,0,NAME,0,0,0],'composedAllocatorRoot');compare(0x4b69a0,FOLDER,[META],'composedAllocatorChild');compare(0x4b6a60,FOLDER,[17,META,0x414e49],'composedAllocatorResource');compare(0x4b66d0,FOLDER,[],'composedAllocatorCleanup',False)
print('PASS composed allocator',H.calls,H.snapshots,H.prefixes,flush=True)
#Retail REZ metadata is a read-only input adapter, not an archive-loader port.
b=(ROOT/'Original/claw-disc/files/DATA/CLAW.REZ').read_bytes();assert hashlib.sha256(b).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596'
def word(o):return struct.unpack_from('<I',b,o)[0]
rows=[]
def walk(at,size,path=()):
 end=at+size
 while at<end:
  kind,target,length=word(at),word(at+4),word(at+8);start=at+(16 if kind else 28);nul=b.index(0,start,end);name=b[start:nul]
  if kind:walk(target,length,path+(name,));at=nul+1
  else:rows.append((path,name,word(at+20),word(at+16)));at=nul+2
walk(word(131),word(135))
selected={}
for path,name,tag,id in rows:
 if path and(path[0]in(b'CLAW',b'GAME')or path[0].startswith(b'LEVEL')or path[:2]in((b'STATES',b'CREDITS'),(b'STATES',b'ROLLER'))):selected.setdefault((path[0],tag),(path,name,tag,id))
actual=[]
for seed,(path,name,tag,id)in enumerate(selected.values()):
 reset(seed);compare(0x4b6600,FOLDER,[CONTROL,0,NAME,0,0,0],'retailRoot');parent=FOLDER
 for part in path:
  write(META,part+b'\0');parent=compare(0x4b69a0,parent,[META],('retailFolder',path,part));assert parent
 write(META,name+b'\0');res=compare(0x4b6a60,parent,[id,META,tag],('retailResource',path,name,tag,id));assert res
 ty=get(res+8);assert compare(0x4b8070,ty+28,[id],'retailIDLookup')==res
 compare(0x4b66d0,FOLDER,[],'retailTreeCleanup',False);actual.append(dict(path='_'.join(p.decode('ascii')for p in path),name=name.decode('ascii'),tag=tag,id=id))
print('PASS retail',H.calls,H.snapshots,H.prefixes,len(actual),flush=True)
#Final paired corpus: original-verified finite constructors/creators/cleanup.
with gzip.open(WORK/'sanitizer-corpus.bin.gz','wb')as f:
 f.write(pack(len(H.captures)))
 for function,t,args,before,after,img,result,objects,events,initialLive in H.captures:
  meaningful=function!=0x4b66d0;f.write(pack(function,t,len(args),*(args+[0]*10)[:10],result,int(meaningful),len(objects),len(events)));f.write(before);f.write(after);f.write(img)
  for token,size in objects.items():f.write(pack(token,(size+3)&~3,int(token<ALLOC or token in initialLive)))
  shadow=before+img[0x510000-iBase:0x553000-iBase]
  for function,t,args,result,bef,aft,mask,localsBefore,localsAfter in events:
   patchesBefore=[(i,v)for i,(old,v)in enumerate(zip(shadow,bef))if old!=v];patchesService=[(i,v)for i,(old,v)in enumerate(zip(bef,aft))if old!=v]
   f.write(pack(function,t,len(args),*(args+[0]*10)[:10],result,mask,len(localsBefore),len(patchesBefore),len(patchesService)))
   for lhs,rhs in zip(localsBefore,localsAfter):f.write(pack(len(lhs)));f.write(lhs);f.write(rhs)
   for patches in(patchesBefore,patchesService):
    for off,val in patches:f.write(struct.pack('<IB',off,val))
   shadow=aft
report=dict(originalSHA256=hashlib.sha256((ROOT/'Original/claw10/CLAW.EXE').read_bytes()).hexdigest(),wholeOriginalCalls=H.calls,orderedFullSnapshots=H.snapshots,unsafePrefixes=H.prefixes,instrumentedTextAddresses=len([a for a in m.executed if 0x401000<=a<0x50adb5]),totalInstrumentedAddresses=len(m.executed),heapBytes=SIZE,globalBytes=0x43000,retailProfiles=actual,sanitizerCorpusCases=len(H.captures),boundaries='unchanged source folder/type/table construction; physical time/allocator, nonnormal locale, broader archive boot explicit')
(WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS final',H.calls,H.snapshots,H.prefixes,'text',report['instrumentedTextAddresses'],'retail',len(actual),'sanitizer',len(H.captures),flush=True)
