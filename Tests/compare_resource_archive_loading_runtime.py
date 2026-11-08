#!/usr/bin/env python3
import resource_archive_loading_helpers as H
from resource_archive_loading_helpers import *
reset();compare(0x4b7210,CONTROL,[],'controllerConstructor');H.allowed={(0,168)};compare(0x4b72e0,CONTROL,[NAME,1,0],'wholeOpenHeaderActualDirectoryReadFailure');compare(0x4b74d0,CONTROL,[0],'wholeClose');compare(0x4b7250,CONTROL,[],'destructor',False)
print('PASS initial',H.calls,H.snapshots,flush=True)
import struct,hashlib,json,gzip,random
folders=[];files=[]
def word(i):return struct.unpack_from('<I',rez,i)[0]
def walk(at,size,path=()):
 folders.append((path,at,size));end=at+size
 while at<end:
  kind,offset,length=word(at),word(at+4),word(at+8);namepos=at+(16 if kind==1 else 28);nul=rez.index(0,namepos,end);name=rez[namepos:nul]
  if kind==1:walk(offset,length,path+(name,));at=nul+1
  else:
   metaend=rez.index(0,nul+1,end);count=word(at+24);files.append((path,name,at,metaend+1+count*4-at));at=metaend+1+count*4
walk(word(131),word(135));assert len(folders)==1384 and len(files)==13077
profiles=[]
for i,(path,offset,size)in enumerate(folders):
 if len(path)==1 or path[:2]in((b'STATES',b'ROLLER'),(b'STATES',b'CREDITS')) or(path and path[0].startswith(b'LEVEL') and path[-1]in(b'PALETTES',b'WORLDS')):
  reset(i);compare(0x4b7210,CONTROL,[],'retailController');put(CONTROL+12,[FILEHANDLE]);compare(0x4b6600,FOLDER,[CONTROL,0,NAME,offset,size,0],'retailFolder',common=True);compare(0x4b6ed0,FOLDER,[offset,size],('wholeRetailDirectory',path));compare(0x4b66d0,FOLDER,[],'retailDirectoryCleanup',False,common=True);profiles.append(dict(path='_'.join(p.decode('ascii')for p in path),offset=offset,bytes=size))
print('PASS retail shallow',H.calls,H.snapshots,len(profiles),flush=True)
#Actual nested source graphs, separate from the whole archive recursion.
for i,(path,offset,size)in enumerate(folders):
 if path[:2]in((b'STATES',b'ROLLER'),(b'STATES',b'CREDITS')) and len(path)==2 or(path and path[0].startswith(b'LEVEL') and path[-1]in(b'PALETTES',b'WORLDS')):
  reset(i);H.capture=len(H.captures)<8;compare(0x4b7210,CONTROL,[],'nestedController');put(CONTROL+12,[FILEHANDLE]);compare(0x4b6600,FOLDER,[CONTROL,0,NAME,offset,size,0],'nestedRoot',common=True);compare(0x4b6b60,FOLDER,[offset,size],('wholeNestedRetail',path));compare(0x4b66d0,FOLDER,[],'nestedCleanup',False,common=True);H.capture=False
print('PASS nested',H.calls,H.snapshots,flush=True)
#Whole opener over exact168-byte retail header and real root/level/STATES
#directories. Deeper FILE reads deliberately fail; source ignores load result.
allowed={(0,168),(word(131),word(135))}|{(o,n)for p,o,n in folders if len(p)==1}
reset();H.allowed=allowed;H.capture=True;compare(0x4b7210,CONTROL,[],'joinedOpenCtor');assert compare(0x4b72e0,CONTROL,[NAME,1,0],'joinedActualRootOpenLimitedFileTransport')==1;compare(0x4b74d0,CONTROL,[0],'joinedClose');H.closeResults=[0xffffffff];compare(0x4b7250,CONTROL,[],'joinedDestructorStaleHandle',False);H.capture=False
print('PASS whole opener',H.calls,H.snapshots,flush=True)
#Finite open/close/flush decisions and virtual retry ordering.
for readonly in(0,1,2):
 for create in(0,1,2):
  reset();compare(0x4b7210,CONTROL,[],'openModeCtor');compare(0x4b7bd0,CONTROL,[NAME,readonly,create],('fopenMode',readonly,create));compare(0x4b7c80,CONTROL,[],'flush');compare(0x4b7c40,CONTROL,[],'close')
for f,nativeName in[(0x4b7c40,'closeResults'),(0x4b7c80,'flushResults')]:
 for sequence,retries in[([1],[0]),([1,0],[1]),([1,1,0],[1,1])]:
  reset();put(CONTROL,[VT]);put(VT+8,[0x710000]);put(CONTROL+12,[FILEHANDLE]);getattr(H,nativeName).extend(sequence);H.retryResults=retries[:];compare(f,CONTROL,[],('retry',hex(f),sequence,retries))
for results,retries in[([0],[0]),([0,FILEHANDLE],[1]),([0,0,FILEHANDLE],[1,1])]:
 reset();put(CONTROL,[VT]);put(VT+8,[0x710000]);H.openResults=results[:];H.retryResults=retries[:];compare(0x4b7bd0,CONTROL,[NAME,1,0],('fopenRetry',results,retries))
for create,readonly in((1,0),(1,1)):
 reset();compare(0x4b7210,CONTROL,[],'newArchiveCtor');compare(0x4b72e0,CONTROL,[NAME,readonly,create],'newArchiveSourceOrder');compare(0x4b7250,CONTROL,[],'newArchiveDestructorWriterBoundary',False)
#No header signature/version or short-read validation is invented.
for headerCount in(0,1,80,167):
 reset();write(HEADER,rez[:168]);H.readResults=[headerCount];H.allowed={(0,168)};compare(0x4b7210,CONTROL,[],'partialHeaderCtor');write(HEADER,rez[:168]);compare(0x4b72e0,CONTROL,[NAME,1,0],('ignoredHeaderReadCount',headerCount));compare(0x4b7250,CONTROL,[],'partialHeaderCleanup',False)
print('PASS transport/failures',H.calls,H.snapshots,flush=True)
#Exact source edge/failure paths over literal retail directory bytes.
profile=next(p for p in folders if p[0]==(b'STATES',b'ROLLER',b'PALETTES'))
for failure in('directoryAlloc','shortRead','seekFailure'):
 reset();compare(0x4b7210,CONTROL,[],'failureController');put(CONTROL+12,[FILEHANDLE]);compare(0x4b6600,FOLDER,[CONTROL,0,NAME,profile[1],profile[2],0],'failureFolder',common=True)
 if failure=='directoryAlloc':H.failedOrdinal=H.ordinal
 if failure=='shortRead':H.readResults=[profile[2]-1]
 if failure=='seekFailure':H.seekResults=[1]
 compare(0x4b6ed0,FOLDER,[profile[1],profile[2]],('directoryFailure',failure));compare(0x4b66d0,FOLDER,[],'failureFolderCleanup',False,common=True)
for t in(0,FOLDER):reset();compare(0x4b6b60,t,[0,0],'zeroLengthRecursiveNoDereference')
#A modified test-only copy of one real record elects nonempty metadata/aux,
#without changing the implementation or claiming these as retail records.
record=next(row for row in files if row[0]==(b'STATES',b'ROLLER',b'PALETTES'))
base=bytearray(rez[record[2]:record[2]+record[3]]);assert base[-1]==0 and base[-2]==0
for count in(1,2,3):
 for metadata in(b'',b'original-oracle-test'):
  data=bytearray(base[:-1])+metadata+b'\0';struct.pack_into('<I',data,24,count);data+=pack(*[0x11223344+i for i in range(count)])
  reset();H.fileData=bytes(data);compare(0x4b7210,CONTROL,[],'auxController');put(CONTROL+12,[FILEHANDLE]);compare(0x4b6600,FOLDER,[CONTROL,0,NAME,0,len(data),0],'auxFolder',common=True);H.capture=True;compare(0x4b6ed0,FOLDER,[0,len(data)],('modifiedRecordAux',count,metadata));H.capture=False;compare(0x4b66d0,FOLDER,[],'auxCleanup',False,common=True)
#Repeated source directory calls prepend another set; no editor duplicate gate.
reset();compare(0x4b7210,CONTROL,[],'repeatController');put(CONTROL+12,[FILEHANDLE]);compare(0x4b6600,FOLDER,[CONTROL,0,NAME,profile[1],profile[2],0],'repeatFolder',common=True)
for i in range(3):compare(0x4b6ed0,FOLDER,[profile[1],profile[2]],('repeatActualDirectory',i))
compare(0x4b66d0,FOLDER,[],'repeatCleanup',False,common=True)
#Original unchecked failure instructions, with all earlier state retained.
reset();compare(0x4b7210,CONTROL,[],'unsafePathCtor');H.failedOrdinal=H.ordinal;H.comparePrefix(0x4b72e0,CONTROL,[NAME,1,0],'nullPathAllocationCopy',0x4b733e)
reset();compare(0x4b7210,CONTROL,[],'unsafeFolderController');put(CONTROL+12,[FILEHANDLE]);compare(0x4b6600,FOLDER,[CONTROL,0,NAME,0,0,0],'unsafeFolder',common=True);source=next(p for p in folders if p[0]==(b'CLAW',));H.failedOrdinal=H.ordinal+1;H.comparePrefix(0x4b6ed0,FOLDER,[source[1],source[2]],'nullChildAllocationInsertion',0x4d5458)
print('PASS final source',H.calls,H.snapshots,H.prefixes,flush=True)
report=dict(originalSHA256='350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263',REZSHA256=hashlib.sha256(rez).hexdigest(),wholeOriginalCalls=H.calls,orderedFullSnapshots=H.snapshots,unsafePrefixes=H.prefixes,instrumentedTextAddresses=len([a for a in m.executed if 0x401000<=a<0x50adb5]),totalInstrumentedAddresses=len(m.executed),heapBytes=SIZE,globalBytes=0x43000,retailDirectoryProfiles=profiles,retailRecordInventory=dict(folders=len(folders),files=len(files),metadataAuxZero=True),sanitizerCases=len(H.captures),limits='full retail directory sources; bounded nested/whole opener with declared deep-file failure; FILE/time/allocator transport explicit; writer/compactor not recovered')
(WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
#Exact allocation/liveness corpus. Header scratch is a normalized source local;
#its full before/after buffer is separately compared at FILE transport.
with gzip.open(WORK/'sanitizer-corpus.bin.gz','wb')as f:
 f.write(pack(len(H.captures)))
 for function,t,args,before,after,img,result,meaningful,objects,events,initialLive in H.captures:
  f.write(pack(function,t,len(args),*(args+[0]*10)[:10],result,int(meaningful),len(objects),len(events)));f.write(before);f.write(after);f.write(img)
  for token,size in objects.items():f.write(pack(token,(size+3)&~3,int(token<ALLOC or token in initialLive)))
  shadow=bytearray(before+img[0x510000-iBase:0x553000-iBase]);shadow[HEADER-BASE:HEADER-BASE+168]=bytes(168)
  for function,t,args,result,bef,aft,mask,localsBefore,localsAfter in events:
   beforePatches=[(i,v)for i,(old,v)in enumerate(zip(shadow,bef))if old!=v];servicePatches=[(i,v)for i,(old,v)in enumerate(zip(bef,aft))if old!=v]
   f.write(pack(function,t,len(args),*(args+[0]*10)[:10],result,mask,len(localsBefore),len(beforePatches),len(servicePatches)))
   for lhs,rhs in zip(localsBefore,localsAfter):f.write(pack(len(lhs)));f.write(lhs);f.write(rhs)
   for patches in(beforePatches,servicePatches):
    for off,val in patches:f.write(struct.pack('<IB',off,val))
   shadow=aft
print('PASS corpus',len(H.captures),flush=True)
