#!/usr/bin/env python3
"""Whole selected-player methods and explicit original startup instruction span."""
import ctypes as C,itertools,json,hashlib
import player_cache_application_helpers as h
for selected,inputToken,flags in itertools.product((0,h.RECORDS),(0,h.INPUT),(0,1,4,0x104,0xffffffff)):
 h.prepare();h.put(0x537204,[inputToken]);h.put(h.RECORDS+4,[flags]);h.compareApp(0x42bf90,h.APP,[selected],'selection')
 assert h.get(h.APP+100)[0]==selected and h.get(0x53725c)[0]==int(bool(selected and flags&4))
for offset in(-16,-4,0,4,16,0x2608):
 h.prepare();h.compareApp(0x430ac0,h.RECORDS+0x2604+offset,[h.RECORDS],'overlapping-binding-copy')
for value in(0,0xffffd9fc):
 h.prepare();assert h.compareApp(0x430ac0,h.INPUT,[value],'binding-null-source')==0
# Binding destination alias changes app+64;42bf90 must reread it afterwards.
h.prepare();h.put(0x537204,[h.APP+0x1c]);h.put(h.RECORDS+0x25d4,[h.RECORDS+0x3000]);h.put(h.RECORDS+0x3004,[4]);h.compareApp(0x42bf90,h.APP,[h.RECORDS],'fresh-selected-alias');assert h.get(h.APP+100)[0]==h.RECORDS+0x3000 and h.get(0x53725c)[0]==1
for scene,template,proc,result,cursors in itertools.product((0,h.SCENE),(0,0x525f30),(0,0x49b730),(0,1,0xffffffff),((0,0,0xffffffff),(0xffffffff,0xffffffff,0,0,0xffffffff))):
 h.prepare();h.put(h.APP+48,[scene]);h.dialogResult=result;h.cursorValues=list(cursors)
 h.compareApp(0x42bb00,h.APP,[template,proc],'modal-gates')
for fn in(0x42bbb0,0x42bbd0,0x42bbe0,0x42bbf0):
 for count,selected,result in itertools.product((0,1,2,0xffffffff),(0,h.RECORDS),(0,1,0xffffffff)):
  h.prepare();h.put(h.APP+100,[selected]);h.put(h.M+12,[count]);h.dialogResult=result;h.compareApp(fn,h.APP,[],'menu-elections')
for count,exclude,selected,failAdd in itertools.product((0,1,3),(0,1),(0,h.RECORDS),(0,1)):
 h.prepare(count);h.listAddFailure=bool(failAdd)
 for i in range(count):h.putBytes(h.RECORDS+i*0x3000+20,(b'Player'if i==0 else f'User{i}'.encode())+b'\0')
 h.compareApp(0x49c090,h.M,[h.CONTROL,selected,exclude],'list-population')
for app,manager,control in itertools.product((0,h.APP),(0,h.M),(0,h.CONTROL)):
 h.prepare(1);h.put(0x5371fc,[app]);h.put(h.APP+96,[manager]);h.controlResult=control;h.putBytes(h.RECORDS+20,b'Player\0')
 h.compareApp(0x49b730,0,[h.DIALOG,0x110,0,0],'dialog-init-gates')
for message,wparam,lparam in itertools.product((0,0x110,0x111,0x112),(0,1,2,0x20000,0x20001,0x10001,0xffff0000),(0,h.CONTROL)):
 h.prepare(2);h.putBytes(h.RECORDS+20,b'Player\0');h.putBytes(h.RECORDS+0x3000+20,b'Ada\0');h.listNames=[b'Player',b'Ada'];h.listIndex=1
 h.compareApp(0x49b730,0,[h.DIALOG,message,wparam,lparam],'dialog-command')
for control,index,textFail,selectedName in itertools.product((0,h.CONTROL),(0xffffffff,0,1),(0,1),(b'Ada',b'Missing')):
 h.prepare(2);h.putBytes(h.RECORDS+20,b'Player\0');h.putBytes(h.RECORDS+0x3000+20,b'Ada\0');h.listNames=[b'Player',selectedName];h.listIndex=index;h.listTextFailure=bool(textFail)
 h.compareApp(0x49b0c0,0,[control],'list-election')
for dialog,selected in itertools.product((0,h.DIALOG),(0,h.RECORDS)):
 h.prepare(1);h.put(h.APP+100,[selected]);h.putBytes(h.RECORDS+20,b'Player\0');h.compareApp(0x49b050,0,[dialog],'default-dialog-caption')

spanCalls=0
for prior,legacy,locations,email in itertools.product((b'',b'Player',b'Unknown'),(b'',b'Player',b'Ada',b'N'*31,b'N'*32),(b'',b'Location'),(b'',b'Email')):
 h.prepare();h.files={};h.putBytes(h.PRIORNAME,prior+b'\0');h.registry={0x52560c:legacy,0x5255fc:locations,0x5255f0:email}
 assert h.compareApp(0x426546,h.APP,[h.PRIORNAME],'source-cache-startup',span=True)==1;spanCalls+=1
 assert h.get(h.APP+96)[0]!=h.M and h.get(h.APP+100)[0]
 assert h.removed==([]if prior==b'Player'else[0x52560c,0x5255fc,0x5255f0])
for cwd,windir,drive in itertools.product((b'',b'C:\\CLAW'),(b'',b'C:\\WINDOWS'),(3,5)):
 h.prepare();h.files={};h.currentDirectory=cwd;h.windowsDirectory=windir;h.driveType=drive
 result=h.compareApp(0x426546,h.APP,[h.PRIORNAME],'directory-startup-failure',span=True);spanCalls+=1
 assert bool(result)==bool((cwd and drive!=5)or windir)
 if not result:assert h.get(h.APP+100)[0]==h.RECORDS # untouched selection on startup failure
for history in range(3):
 h.prepare();h.files={};h.putBytes(h.PRIORNAME,b'Player\0');h.compareApp(0x426546,h.APP,[h.PRIORNAME],'retained-create',span=True);spanCalls+=1
 manager=h.get(h.APP+96)[0];originalPlayer=h.get(h.APP+100)[0]
 # Existing recovered record initializer/list insertion, then source dialog
 # input publishes that actual new token and applies its actual binding arrays.
 h.native=True;h.putBytes(h.DATA,b'Ada\0');h.lc.save=h.ctx;h.globalSeed=bytes(h.image[h.GS-h.IS:h.GS-h.IS+h.GN]);h.compare(0x49bdb0,manager,[h.DATA,0,0,4],('retained-original-record-insertion',history))
 node=h.get(manager+8)[0];newPlayer=h.get(node+8)[0];assert newPlayer!=originalPlayer
 h.compareApp(0x49b730,0,[h.DIALOG,0x110,0,0],'retained-dialog-enter');h.listIndex=1
 h.compareApp(0x49b730,0,[h.DIALOG,0x111,0x20000,h.CONTROL],'retained-double-click');assert h.get(h.APP+100)[0]==newPlayer and h.get(0x53725c)[0]==1
# Actual source-created/encrypted two-record save, then actual reader admission
# and selected prior-name publication. File dictionary keys are the caller's
# formatted full path, not a filename substitution inside source startup.
h.prepare();h.globalSeed=bytes(h.image[h.GS-h.IS:h.GS-h.IS+h.GN]);h.files={}
for name in(b'Player',b'Ada'):
 h.putBytes(h.DATA,name+b'\0');h.compare(0x49bdb0,h.M,[h.DATA,0,0,4 if name==b'Ada'else 0],'saved-fixture-source-record')
h.compare(0x49bbc0,h.M,label='saved-fixture-source-writer');blob=h.files[b'CLAW.USR']
for name in(b'Player',b'Ada'):
 h.prepare();h.files={b'C:\\CLAW\\CLAW.USR':blob};h.putBytes(h.PRIORNAME,name+b'\0');h.compareApp(0x426546,h.APP,[h.PRIORNAME],'saved-reader-selection',span=True);spanCalls+=1
 assert h.text(h.get(h.APP+100)[0]+20)==name and h.get(0x53725c)[0]==int(name==b'Ada')
 assert not h.removed
# ABI and full-word WM_COMMAND: no implicit low-word normalization.
for f,n in((0x42bf90,0),(0x49b730,3),(0x49c090,2)):
 h.prepare();out=h.U();args=(h.U*4)();assert not h.lib.claw_player_cache_application_entry(f,h.APP,args,n,C.byref(h.ac),h.appDependency,None,C.byref(out));assert h.ac.fault==3
h.unsafeAllocation(0);h.unsafeAllocation(1)
mapped=[v for v in h.m.executed if 0x401000<=v<=0x50adb5]
v={'originalSha256':hashlib.sha256((h.ROOT/'Original/claw10/CLAW.EXE').read_bytes()).hexdigest(),'pairedCallsAndSpans':h.calls,'sourceStartupSpans':spanCalls,'pairedFrozenRecordInsertionCalls':5,'pairedFrozenWriterCalls':1,'sourceEncryptedSavedSelectionProfiles':2,'orderedFullSnapshots':h.eventCount,'mappedTextAddresses':len(mapped),'totalInstrumentedAddresses':len(h.m.executed),'matchedAllocationUnsafePrefixes':2,'wholeEntries':11,'startupInterval':['426546','4266e0'],'sourceHashes':{name:hashlib.sha256((h.ROOT/name).read_bytes()).hexdigest()for name in('Sources/PlayerCacheApplicationRuntime.h','Sources/PlayerCacheApplicationRuntime.cpp')},'limits':['whole425730 remains outside scope','physical registry/window/DC/modal endpoints are deterministic fixtures','UserInfo49b160/RemoveUser49b630 callbacks remain addressed']}
(h.WORK/'verification.json').write_text(json.dumps(v,indent=2)+'\n');print('PASS',json.dumps(v))
