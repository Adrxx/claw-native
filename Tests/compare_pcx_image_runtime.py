#!/usr/bin/env python3
import pcx_image_helpers as H
from pcx_image_helpers import *
from unicorn import UC_HOOK_MEM_WRITE
#Whole loader paths, direct versus temporary decode and RGB palette conversion.
for planes in(1,3):
 for target in(8,24):
  for i in range(10):
   width=1+i;height=1+i%4;prepare(width,height,planes,target,i%5);data=pcx(width,height,planes,i);write(DATA,data);assert compare(0x4bebc0,SURFACE,[MANAGER,DATA,len(data)],('generatedWholePCX',planes,target,i))==1
print('PASS initialPCX',H.calls,H.eventCount,len(m.executed),flush=True)
#Every byte literal, zero-length run and all six-bit run lengths. Rows with
#overlong runs preserve writes into padding and neighboring storage.
for planes in(1,3):
 for count in range(64):
  prepare(4,2,planes,padding=200);raw=bytes((0xc0,19,0xc0|count,77))+bytes(range(32))*planes*2;write(DATA,raw)
  compare(0x4babe0 if planes==1 else 0x4bad30,SURFACE,[DATA],('rawRunSurface',planes,count))
  prepare(4,2,planes);write(DATA,raw);compare(0x4bef50 if planes==1 else 0x4bf070,SURFACE,[PIXELS,DATA,4,2],('rawRunLinear',planes,count))
for planes in(1,3):
 prepare(256,1,planes,padding=7);encoded=b''.join(bytes((0xc1,x))if x>=192 else bytes((x,))for x in range(256));write(DATA,encoded*planes)
 compare(0x4babe0 if planes==1 else 0x4bad30,SURFACE,[DATA],('allLiteralBytes',planes))
#Null paths, signed dimensions, unrelated ignored metadata, repeated locks,
#source graphics failure/recovery and target-depth dispatcher election.
for f,n in((0x4bebc0,3),(0x4babe0,1),(0x4bad30,1),(0x4bef50,4),(0x4bf070,4),(0x4ba2d0,3),(0x4ba580,3)):
 prepare();compare(f,SURFACE,[0]*n,'nullOriginalArguments')
for planes in(0,1,2,3,4,255):
 for coords in((-4,-7,1,-3),(0,0,-1,-1),(-32768,-32768,-32768,-32768),(2,0,0,1)):
  width=coords[2]-coords[0]+1;height=coords[3]-coords[1]+1;prepare(width,height,planes,8);b=bytearray(1024);struct.pack_into('<4h',b,4,*coords);b[65]=planes;write(DATA,b)
  compare(0x4bebc0,SURFACE,[MANAGER,DATA,len(b)],('signedCoordinates',planes,coords))
for target in(0,1,8,16,24,32):
 for source in(0,1,8,16,24,32):
  prepare(2,2,1,target);write(DATA,bytes(range(128)));compare(0x4b9e90,SURFACE,[DATA,source,MANAGER+0x478,1],('conversionDispatch',target,source))
for planes in(1,3):
 for profile in('lockFailure','lostRestoreFailure','lostRetryFailure','lostRecovery','unlockIgnored','headerMismatch','allocationFailure','missingManagerPalette'):
  prepare(4,3,planes,(24 if planes==1 else 8)if profile=='allocationFailure'else 8 if profile=='missingManagerPalette'else planes*8,padding=7);b=pcx(4,3,planes,42);write(DATA,b)
  if profile=='lockFailure':H.status['lock']=0x80004005
  if profile.startswith('lost'):H.status['lock']=0x887601c2
  if profile=='lostRestoreFailure':H.restore=0
  if profile=='lostRetryFailure':H.status['retry']=0x887601c2
  if profile=='unlockIgnored':H.status['unlock']=0x80004005
  if profile=='headerMismatch':put(SURFACE+24,[99])
  if profile=='allocationFailure':H.allocFailure=1
  if profile=='missingManagerPalette':put(MANAGER+0x878,[0])
  compare(0x4bebc0,SURFACE,[MANAGER,DATA,len(b)],('sourceFailure',planes,profile))
#Physical lock can alter live descriptors. Indexed widths/heights are cached
#before locking; planar widths/heights are reread afterward by the source.
for planes in(1,3):
 prepare(8,2,planes);b=pcx(8,2,planes,23);write(DATA,b)
 def mutation(native,count):put(SURFACE+20,[1,4,17],native)
 H.lockMutation=mutation;compare(0x4bebc0,SURFACE,[MANAGER,DATA,len(b)],('lockDescriptorMutation',planes))
#Source palette tie election and forward/backward row direction in full
#conversion entries, including palette/destination and source/destination alias.
for f,target in((0x4ba2d0,24),(0x4ba580,8)):
 for direction in(0,1,2,0xffffffff):
  for alias in('none','source','palette'):
   prepare(5,3,1,target,padding=3);write(DATA,random.Random(direction).randbytes(1024));palette=MANAGER+0x478;src=DATA
   if alias=='source':src=PIXELS;write(src,bytes(range(128)))
   if alias=='palette':palette=PIXELS;write(palette,random.Random(12).randbytes(1024))
   compare(f,SURFACE,[src,palette,direction],('conversionAlias',hex(f),direction,alias))
print('PASS directedPCX',H.calls,H.eventCount,len(m.executed),flush=True)
#All469 retail files are exact original whole loader calls. Detailed instruction
#instrumentation is retained for selected fixtures; physical events and full
#buffers are compared for every file without Python per-instruction tracing.
retail=[];golden=WORK/'golden';golden.mkdir(exist_ok=True)
manifest=[]
for i,path in enumerate(sorted((ROOT/'work/original-disc-assets').rglob('*.PCX'))):
 b=path.read_bytes();x,y,X,Y=struct.unpack_from('<4h',b,4);width=X-x+1;height=Y-y+1;planes=b[65]
 prepare(width,height,planes,padding=i%4);write(DATA,b);visible=(width*planes+i%4)*height;spills=[]
 def spillWrite(u,access,address,size,value,user):spills.append((address-PIXELS,size))
 spillHook=m.u.hook_add(UC_HOOK_MEM_WRITE,spillWrite,begin=PIXELS+visible,end=PIXELS+visible+191)
 assert compare(0x4bebc0,SURFACE,[MANAGER,DATA,len(b)],('retailPCX',str(path.relative_to(ROOT))),False)==1
 m.u.hook_del(spillHook)
 output=read(PIXELS,visible+192);(golden/f'{i}.bin').write_bytes(output);manifest.append(f'{width} {height} {planes} {i%4} {path} {golden/f"{i}.bin"}')
 retail.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(b).hexdigest(),'width':width,'height':height,'planes':planes,'surfaceSHA256':hashlib.sha256(output).hexdigest(),'visibleBytes':visible,'accessibleTailBytes':192,'maximumWrittenEnd':max([visible]+[offset+size for offset,size in spills])})
 if i%40==0:print('retailPCX',i+1,'of469',flush=True)
(WORK/'retail-manifest.txt').write_text('\n'.join(manifest)+'\n')
(WORK/'retail.json').write_text(json.dumps(retail,indent=2)+'\n')
print('PASS allRetailPCX',H.calls,H.eventCount,len(m.executed),flush=True)
#PCX metadata not read by the original decoder is deliberately contradictory.
for planes in(1,3):
 for bytesPerLine in(0,1,7,65535):
  prepare(5,2,planes);b=bytearray(pcx(5,2,planes,72));b[0:4]=b'\x00\xff\x00\x01';struct.pack_into('<H',b,66,bytesPerLine);write(DATA,b)
  compare(0x4bebc0,SURFACE,[MANAGER,DATA,len(b)],('ignoredPCXMetadata',planes,bytesPerLine))
#Raw-source/destination aliasing tests the precise streaming writes, rather
#than comparing a predecoded/cached source with its final pixels only.
for method,planes in((0x4babe0,1),(0x4bad30,3),(0x4bef50,1),(0x4bf070,3)):
 for delta in(0,1,2,7,16):
  prepare(4,2,planes,padding=8);encoded=bytes((0xc3,7,8,0xc0,13,0xc4,31))*16;write(PIXELS,encoded)
  if method in(0x4babe0,0x4bad30):args=[PIXELS+delta]
  else:args=[PIXELS,PIXELS+delta,4,2]
  compare(method,SURFACE,args,('streamingAlias',hex(method),delta))

#Retained decoded image histories across live changed descriptors and depths.
for i in range(16):
 prepare(5,3,1,8,padding=i%3);b=pcx(5,3,1,i);write(DATA,b)
 for step,target in enumerate((8,24,8,24)):
  put(MANAGER+0x474,[target]);put(SURFACE+164,[target]);put(SURFACE+28,[5*(1 if target==8 else 3)+i%3])
  compare(0x4bebc0,SURFACE,[MANAGER,DATA,len(b)],('retainedDepthHistory',i,step))
#Byte-precise EOF and forbidden destination spill stop at source instruction
#before an unsafe access. Prefix heap/events are compared, not successful EAX.
from unicorn.x86_const import UC_X86_REG_EDX
unsafe=0
for kind in('sourceEOF','destinationEnd'):
 prepare(4,1,1,8);write(DATA,b'\x07\x08');sync();events[0].clear();events[1].clear();hit=[]
 def unsafeStop(u,address,size,user):
  if kind=='sourceEOF'and address==0x4bac71 and u.reg_read(UC_X86_REG_EAX)==DATA+2:hit.append(address);u.emu_stop()
  if kind=='destinationEnd'and address==0x4bacf1 and u.reg_read(UC_X86_REG_EDX)==PIXELS+1:hit.append(address);u.emu_stop()
 handle=m.u.hook_add(UC_HOOK_CODE,unsafeStop,begin=0x4babe0,end=0x4bad21)
 try:
  try:m.call(0x4babe0,SURFACE,struct.pack('<I',DATA),max_instructions=10000)
  except AssertionError:assert hit
 finally:m.u.hook_del(handle)
 @Bytes
 def boundedBytes(v,t,n):
  if kind=='sourceEOF'and DATA<=t<DATA+0x10000 and t+n>DATA+2:return 0
  if kind=='destinationEnd'and PIXELS<=t<PIXELS+0x10000 and t+n>PIXELS+1:return 0
  return byteLookup(v,t,n)
 context.bytes=boundedBytes;out=U();args=(U*1)(DATA)
 assert not lib.claw_pcx_image_entry(0x4babe0,SURFACE,args,1,C.byref(context),dependency,None,C.byref(out))and context.fault==1
 assert len(hit)==1 and snapshot(True)==snapshot(False)and events[0]==events[1],(kind,hit)
 context.bytes=byteLookup;unsafe+=1
report={'originalSHA256':hashlib.sha256((ROOT/'Original/claw10/CLAW.EXE').read_bytes()).hexdigest(),'wholeCalls':H.calls,'orderedSnapshots':H.eventCount,'unsafePrefixes':unsafe,'instrumentedTextAddresses':sum(0x401000<=a<0x50adb5 for a in m.executed),'retailFiles':len(retail),'onePlaneFiles':sum(x['planes']==1 for x in retail),'threePlaneFiles':sum(x['planes']==3 for x in retail),'heapBytes':SIZE,'globalBytes':GLOBAL_SIZE}
(WORK/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS PCX',json.dumps(report,sort_keys=True),flush=True)
