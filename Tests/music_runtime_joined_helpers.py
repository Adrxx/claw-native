"""Frozen SpecialCommand admits original music pause/resume into recovered backend."""
import ctypes as C
import music_runtime_helpers as h
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX
APP=h.BASE+0x7000
class Globals(C.Structure):_fields_=[('words',h.U*97)]
class Context(C.Structure):_fields_=[('scene',h.Scene),('globals',C.POINTER(Globals)),('fault',h.U)]
class Call(C.Structure):_fields_=[('function',h.U),('receiver',h.U),('argumentCount',h.U),('arguments',h.U*8),('name',C.c_char_p),('localMask',h.U),('buffer',h.UP),('bufferWords',h.U)]
Dependency=C.CFUNCTYPE(h.U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
g=Globals();c=Context(h.ctx.scene,C.pointer(g),0)
h.lib.claw_special_command_entry.argtypes=[h.U,h.U,h.UP,h.U,C.POINTER(Context),Dependency,C.c_void_p,h.UP];h.lib.claw_special_command_entry.restype=h.U
@Dependency
def dependency(ctx,call,_):
 e=call.contents;args=list(e.arguments[:e.argumentCount]);assert e.function in(0x4b55a0,0x4b55b0);h.events.append((e.function,e.receiver,tuple(args),0,(),h.snapshot()));out=h.U();aa=(h.U*len(args))(*args);assert h.lib.claw_music_entry(e.function,e.receiver,aa,len(args),C.byref(h.ctx),h.dependency,None,C.byref(out))and not h.ctx.fault;return out.value

def native(f,t,args,out):
 aa=(h.U*len(args))(*args);ok=h.lib.claw_special_command_entry(f,t,aa,len(args),C.byref(c),dependency,None,C.byref(out));assert not c.fault;return ok

def original(uc,address,size,user):
 if h.selectedEntry not in(0x42d420,0x42d440)or address not in(0x4b55a0,0x4b55b0):return False
 args=h.get(uc.reg_read(UC_X86_REG_ESP)+4,1)if address==0x4b55b0 else[];h.events.append((address,uc.reg_read(UC_X86_REG_ECX),tuple(args),0,(),h.snapshot()));return True
h.extraNative=native;h.extraSource=original
