"""Actual REZ folder→image/cache/restore/clear with frozen source bodies."""
import image_resource_lifecycle_join_helpers as g
import struct
folders=[]
w=lambda at:struct.unpack_from('<I',g.rez,at)[0]
def walk(offset,size,path=()):
 if not size:return
 at=offset;end=offset+size
 while at<end:
  kind=w(at);start=at+(16 if kind==1 else 28);nul=g.rez.index(0,start,end);name=g.rez[start:nul]
  if kind==1:
   child=path+(name,);folders.append((child,w(at+4),w(at+8)));walk(w(at+4),w(at+8),child);at=nul+1
  else:meta=g.rez.index(0,nul+1,end);at=meta+1+w(at+24)*4
walk(w(131),w(135))
for suffix in [('MENU','SPARKLE'),('MENU','CURSOR'),('BOOTY','SCORENUMBERS'),('BOOTY','SYMBOLS')]:
 path=tuple(x.encode()for x in('STATES',suffix[0],'IMAGES',suffix[1]));row=next(x for x in folders if x[0]==path)
 g.reset(joined=True);g.compare(0x4b7210,g.CONTROL,[],'source controller');g.put(g.CONTROL+12,0x7771)
 g.compare(0x4b6600,g.FOLDER,[g.CONTROL,0,g.DIRECTORYNAME,row[1],row[2],0],'source folder',common=True)
 g.compare(0x4b6b60,g.FOLDER,[row[1],row[2]],'source directory')
 g.write(g.KEY,b'_'.join(path[1:])+b'\0')
 count=g.compare(0x4cff40,g.IMAGECONTROLLER,[g.FOLDER,g.KEY,g.SEPARATOR],'source image load')
 assert count==1,(suffix,count)
 g.compare(0x4cff40,g.IMAGECONTROLLER,[g.FOLDER,g.KEY,g.SEPARATOR],'source duplicate')
 g.surfaceLost=0;g.restoreResult=0;g.compare(0x4d0120,g.IMAGECONTROLLER,[g.FOLDER,g.KEY,g.SEPARATOR],'intact restore')
 g.surfaceLost=0x887601c2;g.restoreResult=0;g.compare(0x4d0120,g.IMAGECONTROLLER,[g.FOLDER,g.KEY,g.SEPARATOR],'in-place restore')
 g.surfaceLost=0x887601c2;g.restoreResult=1;g.compare(0x4d0120,g.IMAGECONTROLLER,[g.FOLDER,g.KEY,g.SEPARATOR],'recreated restore')
 g.surfaceLost=0;g.restoreResult=0
 g.compare(0x4cf230,g.IMAGECONTROLLER,[g.KEY],'source removal',False)
 assert g.get(g.IMAGECONTROLLER+28)==0
 g.compare(0x4cff40,g.IMAGECONTROLLER,[g.FOLDER,g.KEY,g.SEPARATOR],'load after removal')
 g.lifecycle.image=g.C.addressof(g.imageGlobals)
 g.compare(0x4cfa80,g.IMAGECONTROLLER,[],'whole controller clear',False)
 g.compare(0x4cfa80,g.IMAGECONTROLLER,[],'repeat whole controller clear',False)
 assert g.get(0x54316c)==0 and g.imageGlobals.flags==0
 g.compare(0x4b66d0,g.FOLDER,[],'source REZ cleanup',False,common=True)
 print('PASS retained group',path,g.calls,g.snapshots,flush=True)
print('PASS',g.calls,'whole original joined calls /',g.snapshots,'full snapshots /',sum(0x401000<=a<0x50adb5 for a in g.m.executed),'text /',len(g.m.executed),'total addresses',flush=True)
