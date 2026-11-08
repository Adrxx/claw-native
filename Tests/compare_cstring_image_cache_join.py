#!/usr/bin/env python3
import struct,json
import cstring_image_cache_join_helpers as g
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
 row=next(x for x in folders if x[0]==path);g.reset(joined=True)
 g.compare(0x4b7210,g.CONTROL,[],'controller');g.put(g.CONTROL+12,0x7771)
 g.compare(0x4b6600,g.FOLDER,[g.CONTROL,0,g.DIRECTORYNAME,row[1],row[2],0],'sourceFolder',common=True)
 g.compare(0x4b6b60,g.FOLDER,[row[1],row[2]],'sourceArchiveTree')
 g.write(g.KEY,b'MENU\0' if path[1]==b'MENU' else b'BOOTY\0')
 count=g.compare(0x4cff40,g.IMAGECONTROLLER,[g.FOLDER,g.KEY,g.SEPARATOR],f'{path}/whole-assign-join')
 assert count==(20 if path[1]==b'MENU'else 52)
 assert g.compare(0x4cff40,g.IMAGECONTROLLER,[g.FOLDER,g.KEY,g.SEPARATOR],'retained-duplicate')==count
 assert g.compare(0x4d0120,g.IMAGECONTROLLER,[g.FOLDER,g.KEY,g.SEPARATOR],'retained-restore')==count
 table=g.get(g.IMAGECONTROLLER+20);roots=[]
 for bucket in range(g.get(g.IMAGECONTROLLER+24)):
  p=g.get(table+bucket*4)
  while p:roots.append(g.text(g.get(p+8)));p=g.get(p)
 for name in roots:g.write(g.KEY,name+b'\0');g.compare(0x4cf230,g.IMAGECONTROLLER,[g.KEY],f'{path}/{name}/remove',False)
 g.compare(0x4b66d0,g.FOLDER,[],'REZ-cleanup',False,common=True)
 print('PASS source CString/cache join',path,count,len(g.imageLoads),g.calls,g.snapshots,flush=True)
report=dict(wholeOriginalCalls=g.calls,orderedFullSnapshots=g.snapshots,textAddresses=len([a for a in g.m.executed if 0x401000<=a<0x50adb5]),totalAddresses=len(g.m.executed),limit='source assignment/prepare/allocation/release execute; direct map clear/key destruction and physical images/FILE remain existing explicit boundaries')
(g.WORK/'cache-join-verification.json').write_text(json.dumps(report,indent=2)+'\n')
