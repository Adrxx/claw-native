"""Actual frozen palette construction and scheduler admission; no setup invented."""
import ctypes as C,json,gzip,struct
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ESP,UC_X86_REG_EIP
import palette_fade_helpers as h
U=h.U;WORK=h.ROOT/'work/palette-fade-setup-agent';WORK.mkdir(parents=True,exist_ok=True)
MANAGER=h.BASE+0x8000;RGB_INPUT=h.BASE+0x5800
OwnerDep=C.CFUNCTYPE(U,C.POINTER(h.Palette),C.POINTER(h.Call),C.c_void_p)
h.lib.claw_palette_resource_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(h.Palette),OwnerDep,C.c_void_p,C.POINTER(U)]
base_effect=h.effect;allocIndex=0;failAt=0;createHR=0;nativeEvents=[];originalEvents=[];errors=[];calls=snapshots=0;capture=False;records=[];corpus=[]
original_callback=h.dependency
#Construction transports use the source allocator and one real CreatePalette ABI.
def effect(f,t,a):
 global allocIndex
 if f==0x4f63ec:
  allocIndex+=1
  if allocIndex==failAt:return 0
 if f==0x700014:
  if not createHR:h.put(a[3],[h.PAL])
  return createHR
 return base_effect(f,t,a)
h.effect=lambda f,t,a:effect(f,t,a)
def event(f,t,a,mask,buffers):return(f,t,tuple(a),mask,tuple(buffers),h.hashlib.sha256(h.raw()).digest(),tuple(h.created),tuple(h.freed))
@OwnerDep
def owner_dependency(_,p,user):
 q=p.contents;a=list(q.arguments[:q.count]);buffers=[C.string_at(q.buffers[i],q.sizes[i])for i in range(q.bufferCount)];before=h.raw();nativeEvents.append(event(q.function,q.receiver,a,q.mask,buffers))
 try:
  value=effect(q.function,q.receiver,a)
  if capture:records.append((q.function,q.receiver,a,q.mask,value,buffers,[C.string_at(q.buffers[i],q.sizes[i])for i in range(q.bufferCount)],h.hashlib.sha256(before).digest(),[(i,y)for i,(x,y)in enumerate(zip(before,h.raw()))if x!=y]))
  return value
 except Exception as ex:errors.append(ex);h.palette.fault=1;return 0
#Existing helper records source allocator/diagnostic calls. Add only its missing
#physical CreatePalette endpoint, normalizing its actual automatic entry array.
def create_hook(u,f,size,user):
 if f!=0x700014:return
 sp=u.reg_read(UC_X86_REG_ESP);a=h.m.read_words(sp+4,5);buffers=[bytes(u.mem_read(a[2],1024))];a[2]=0;originalEvents.append(event(f,0,a,4,buffers));value=effect(f,0,a);u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_EIP,h.m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+24)
h.m.u.hook_add(UC_HOOK_CODE,create_hook,begin=0x700014,end=0x700014)
#Capture the other original endpoint events in the identical rich shape.
def observer(u,f,size,user):
 if f not in h.COUNTS:return
 n,pop=h.COUNTS[f];sp=u.reg_read(UC_X86_REG_ESP)
 #The existing handler has already returned before this observer is called,
 #so record from its just-added authoritative original event.
 ef,et,a,buffers,digest,created,freed=h.originalEvents[-1]
 originalEvents.append((ef,et,a,0,buffers,digest,created,freed))
h.m.u.hook_add(UC_HOOK_CODE,observer)
def compare_owner(f,t,a,void=False):
 global calls,snapshots,allocIndex
 h.native=True;nativeEvents.clear();originalEvents.clear();h.originalEvents.clear();records.clear();errors.clear();h.palette.fault=0;before=h.raw();start=(h.cursor,list(h.created),list(h.freed),allocIndex);out=U();args=(U*len(a))(*a)
 assert h.lib.claw_palette_resource_entry(f,t,args,len(a),C.byref(h.palette),owner_dependency,None,C.byref(out))and not h.palette.fault and not errors,errors
 expected=h.raw();ev=list(nativeEvents);end=(h.cursor,list(h.created),list(h.freed),allocIndex);h.native=False;h.cursor=start[0];h.created[:]=start[1];h.freed[:]=start[2];allocIndex=start[3];h.m.u.mem_write(h.BASE,before[:h.SIZE]);h.m.u.mem_write(h.IMAGE_START,before[h.SIZE:]);value=h.m.call(f,t,h.pack(*a));assert h.raw()==expected,(hex(f),'memory');assert originalEvents==ev,(hex(f),'events',[(x[:5],y[:5])for x,y in zip(ev,originalEvents)],len(ev),len(originalEvents));assert end==(h.cursor,list(h.created),list(h.freed),allocIndex),(hex(f),'ownership')
 if not void:assert out.value==value,(hex(f),'return')
 h.native=True;calls+=1;snapshots+=len(ev)+1
 if capture:corpus.append((0,f,t,a,out.value,not void,before,expected,start[1],list(records)))
 return out.value
for seed in range(8):
 for error in(0,1,0x80004005):
  for failBackup in(False,True):
   h.fresh(seed);h.capture=False;capture=seed==0;allocIndex=0;failAt=3 if failBackup else 0;createHR=error;h.put(MANAGER,[h.DD]);h.put(MANAGER+0x3d4,[0x51000c,0,0,0,0,0,10]);h.put(h.DVT+20,[0x700014]);seedWords=h.get(h.ALLOC+28,4)
   backend=compare_owner(0x4bcac0,MANAGER,[RGB_INPUT,0x44])
   if not error:
    assert backend==h.ALLOC and h.get(backend+20)==[0]and h.get(backend+24)==[0]and h.get(backend+52)==[0]and h.get(backend+28,4)==seedWords
    #Use the actual source-created backend; inactive update needs no clock.
    before=h.raw();out=U();noArgs=(U*0)();h.context.fault=0;h.events.clear();assert h.lib.claw_palette_fade_entry(0x4bbb70,backend,noArgs,0,C.byref(h.context),h.dependency,None,C.byref(out))and out.value==0 and not h.context.fault and not h.events;h.native=False;h.m.u.mem_write(h.BASE,before[:h.SIZE]);h.m.u.mem_write(h.IMAGE_START,before[h.SIZE:]);assert h.m.call(0x4bbb70,backend)==0 and h.raw()==before;h.native=True;calls+=1;snapshots+=1
    if capture:corpus.append((1,0x4bbb70,backend,[],0,True,before,before,list(h.created),[]))
    if failBackup:
     assert h.get(backend+16)==[0];failAt=0;compare_owner(0x4bb870,backend,[],void=True);assert h.get(backend+16)[0]and h.get(backend+52)==[0]and h.get(backend+20)==[0]and h.get(backend+24)==[0]
    compare_owner(0x4bca10,MANAGER,[backend],void=True)
   else:assert not backend
print('PASS',calls,'whole original construction/admission/getter/cleanup calls /',snapshots,'ordered full snapshots')
p=lambda *v:struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
with gzip.open(WORK/'admission-sanitizer-replay.bin.gz','wb')as out:
 spans=h.OBJECTS+[(MANAGER,2180),(RGB_INPUT,768)];out.write(b'PADS'+p(h.SIZE,h.IMAGE_START,h.IMAGE_SIZE,len(corpus),len(spans)))
 for t,n in spans:out.write(p(t,n))
 for family,f,t,a,value,meaningful,before,expected,created,events in corpus:
  out.write(p(family,f,t,len(a),value,meaningful,len(created),len(events))+p(*a)+before)
  for t,n in created:out.write(p(t,n))
  for ef,et,a,mask,ev,buffers,outputs,digest,changes in events:
   out.write(p(ef,et,len(a),mask,ev,len(buffers),len(changes))+p(*a)+digest)
   for b,v in zip(buffers,outputs):out.write(p(len(b))+b+v)
   for i,v in changes:out.write(p(i,v))
  out.write(expected)
report={'whole_original_calls':calls,'ordered_full_snapshots':snapshots,'construction':'4bcac0 ->4bb240/4bb100/list registration; failure cleanup4bb2a0','ordinary_allocation_return':'missing backup allocation3 followed by existing4bb870 retry','scheduler_admission':'actual created backend+14/+18/+34 zero;4bbb70 returns0 with no clock','new_scheduler_setup_entry':'not established; no runtime API fabricated','source_profile_sha256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263','sanitizer_calls':len(corpus),'sanitizer_callbacks':sum(len(x[-1])for x in corpus)};(WORK/'admission-report.json').write_text(json.dumps(report,indent=2)+'\n');print('CORPUS',report['sanitizer_calls'],report['sanitizer_callbacks'])
