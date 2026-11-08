"""Finite GameImage -> whole SurfaceBlit -> declared physical endpoint checks."""
import ctypes as C
import surface_blit_helpers as h
U=h.U
IM,ACTOR,TARGET=h.BASE+0x8000,h.BASE+0x8400,h.BASE+0x8800
class GameArgs(C.Structure):_fields_=[('words',U*8),('count',U)]
class GameCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*8),('count',U),('destination',C.POINTER(U)),('source',C.POINTER(U))]
GameService=C.CFUNCTYPE(U,C.c_void_p,GameCall)
class GameHost(C.Structure):_fields_=[('scene',h.Host),('user',C.c_void_p),('service',GameService)]
h.lib.claw_game_image_entry.argtypes=[U,U,GameArgs,C.c_void_p,GameHost,C.POINTER(U),C.POINTER(U)]
@GameService
def service(_,e):
 try:
  assert e.function in(0x4b9ce0,0x4b9d80)
  #Publish the same sparse FX alias updated by the original drawing caller.
  h.put(0x543108,list(h.ig[1:26]));a=h.Args();a.count=e.count
  a.words[:e.count]=e.arguments[:e.count];a.destination=e.destination;a.source=e.source;out=U()
  assert h.lib.claw_surface_blit_entry(e.function,e.receiver,a,C.byref(h.context),h.dependency,None,C.byref(out))and not h.context.fault
  return out.value
 except Exception as ex:h.errors.append(ex);return 0
host=GameHost(h.host,None,service)
calls=snapshots=0
for kind in(0x10,0x11):
 for flip in(0,2,4,6):
  for x,y in((8,6),(2,3),(15,11)):
   h.fresh(kind^flip);h.capture=False;h.localMask=5 if flip else 8;h.currentFunction=0x4d2890
   h.put(IM,[0x513a70,0,0,0,8,6,4,3,0,0,kind,h.SRC,0]);h.put(ACTOR,[0]*128);h.put(ACTOR+64,[flip]);h.put(ACTOR+76,[x,y]);h.put(ACTOR+84,[0x80000000,0,0,0]);h.put(TARGET,[0]*12);h.put(TARGET+16,[16,12]);h.put(TARGET+44,[h.DST]);h.put(h.SRC+184,[int(kind==0x11)])
   h.ig[0]=0;h.ig[1:26]=[100]+[0]*24;h.put(0x5430c4,[0]);h.put(0x543108,list(h.ig[1:26]));before=h.raw();h.events.clear();h.originalEvents.clear();h.errors.clear();h.index=0
   a=GameArgs();a.words[:2]=[ACTOR,TARGET];a.count=2;fault=U();out=U()
   assert h.lib.claw_game_image_entry(0x4d2890,IM,a,C.addressof(h.ig),host,C.byref(fault),C.byref(out))and not fault.value and not h.errors,h.errors
   expected=h.raw();events=list(h.events);h.native=False;h.index=0;h.m.u.mem_write(h.BASE,before[:h.SIZE]);h.m.u.mem_write(h.IMAGE_START,before[h.SIZE:]);h.m.call(0x4d2890,IM,h.pack(ACTOR,TARGET));assert h.raw()==expected,(kind,flip,x,y,'memory');assert h.originalEvents==events,(kind,flip,x,y,'calls');h.native=True;calls+=1;snapshots+=len(events)+1
print('PASS',calls,'whole GameImage/SurfaceBlit source chains /',snapshots,'ordered full snapshots',flush=True)
