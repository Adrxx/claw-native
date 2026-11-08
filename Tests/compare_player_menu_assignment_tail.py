#!/usr/bin/env python3
"""Ordinary CString titles through the menu's exact-byte Assignment facade."""
import ctypes as C,subprocess,json,hashlib
import player_menu_management_helpers as h
probe=h.WORK/'libMenuAssignmentProbe.dylib'
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',str(h.ROOT/'Tests/player_menu_management_assignment_probe.cpp'),str(h.WORK/'libSaveFileRuntime.dylib'),str(h.ROOT/'work/application-level-progression-agent/libProgressionFrozenSupport.dylib'),'-o',str(probe)],check=True)
p=C.CDLL(str(probe));# Exact callback types/context below are the menu facade's public ABI, not the
# differently shaped inherited PlayerCache ABI.
p.claw_test_menu_assignment_probe.argtypes=[h.U,h.U,C.POINTER(h.MenuContext),h.MenuDependency,C.c_void_p,h.UP]
def route(f,t,args,n,ctx,dep,user,out):
 assert f==0x4f66cc and n==1
 return p.claw_test_menu_assignment_probe(t,args[0],ctx,dep,user,out)
h.lib.claw_player_menu_management_entry=route
h.EXTERNAL.pop(0x4f66cc,None) # unchanged original assignment body executes
for value in(b'USERREMOVECONFIRM',b'USERNEW',b'EDITPLAYERS',b'Ada Cove',b'Lin Coast'):
 h.prepare();h.put(h.TIME_CELL,[h.ctx.emptyStringToken]);h.putBytes(h.DATA,value+b'\0');h.compareMenu(0x4f66cc,h.TIME_CELL,[h.DATA],'ordinary-title-tail')
 assert h.text(h.get(h.TIME_CELL)[0])==value
 token=h.get(h.TIME_CELL)[0]-12;assert h.allocationSpans[token]==len(value)+13 and h.get(token)[0]==1
# The fallback byte transport belongs to the borrowed save host. Its opaque
# context is distinct from the outer Menu word host and explicitly non-null.
outerCookie=C.c_uint32(0x12345678);saveCookie=C.c_uint32(0x87654321);opaqueErrors=[]
@h.Lookup
def outerWords(context,token,count):
 if context!=C.addressof(outerCookie):opaqueErrors.append(('outer',context));return None
 return h.loadLookup(None,token,count)
@h.ByteLookup
def saveBytes(context,token,count):
 if context!=C.addressof(saveCookie):opaqueErrors.append(('save',context));return None
 return h.loadBytes(None,token,count)
h.prepare();h.mc.scene.context=C.addressof(outerCookie);h.mc.scene.lookup=outerWords;h.strings.bytes=h.ByteLookup();h.lc.save.scene.context=C.addressof(saveCookie);h.lc.save.lookupBytes=saveBytes;h.put(h.TIME_CELL,[h.ctx.emptyStringToken]);h.putBytes(h.DATA,b'USERREMOVECONFIRM\0');h.compareMenu(0x4f66cc,h.TIME_CELL,[h.DATA],'distinct-save-byte-context');assert not opaqueErrors and h.text(h.get(h.TIME_CELL)[0])==b'USERREMOVECONFIRM'
v={'pairedWholeOriginalAssignmentCalls':h.calls,'orderedSnapshots':h.eventCount,'distinctNonnullSaveContextProfiles':1,'exactSourceAllocationBytes':[30,20,24,21,22],'sourceSha256':hashlib.sha256((h.ROOT/'Sources/PlayerMenuManagementRuntime.cpp').read_bytes()).hexdigest(),'scope':'test-only internal facade probe; public menu header unchanged'}
(h.WORK/'assignment-tail-verification.json').write_text(json.dumps(v,indent=2)+'\n');print('PASS',json.dumps(v))
