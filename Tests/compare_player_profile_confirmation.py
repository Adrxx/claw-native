#!/usr/bin/env python3
"""Ordinary state13 popup, cancel, record delete, source save and fallback."""
import itertools,json,hashlib
import player_profile_confirmation_helpers as h
for data in(5,6):
 h.prepare();h.compareConfirmation(0x429275,h.OWNER,[data],'inline-state13-constructor',construct=True);assert h.get(h.OWNER+344)[0]==data and h.get(h.OWNER)[0]==0x50bf94
for kind in range(8):
 h.prepare();h.cc.composeStrings=1;h.compareConfirmation(0x4399d0,h.OWNER,[kind],'whole-popup-kind')
 assert h.get(h.OWNER+352)[0]
for result in(0,1):
 h.prepare();h.cc.composeStrings=1;h.popupResult=result;assert h.compareConfirmation(0x4399d0,h.OWNER,[6],'source-popup-return')==result
for mode in(3,4,5,11,13):
 h.prepare();h.cc.composeStrings=1;h.previousMode=mode;h.compareConfirmation(0x438c40,h.OWNER,[h.APP,1,5],'whole-state13-init');assert h.get(0x5375bc)[0]==h.OWNER and h.get(h.CURSOR+76)[0]==36 and h.get(h.CURSOR+80)[0]==50
for base,popup,capture in((0,1,h.BITMAP),(1,0,h.BITMAP),(1,1,0)):
 h.prepare();h.cc.composeStrings=1;h.baseResult=base;h.popupResult=popup;h.captureResult=capture;assert h.compareConfirmation(0x438c40,h.OWNER,[h.APP,1,5],'normal-init-service-failure')==0 and h.get(0x5375bc)[0]==0
for mode in(3,5,11,13):
 h.prepare();h.previousMode=mode;h.compareConfirmation(0x43a760,h.OWNER,[],'previous-source-refresh',False)
for fn,nested in itertools.product((0x4247c0,0x4247e0),(0,1)):
 h.prepare();h.put(h.OWNER,[0x50d304]);h.put(0x5375c4,[nested]);h.compareConfirmation(fn,h.OWNER,[],'ok-cancel-source-publication',False);assert h.get(0x52545c)[0]==(1 if fn==0x4247c0 else 2)
 if nested:assert h.get(0x5375c0)[0]==1 and not h.posted
 else:assert h.posted==[(0x1122,0x111,0x8036,0)]
for target,selected in((h.RECORDS,h.RECORDS),(h.RECORDS+0x3000,h.RECORDS),(h.RECORDS+0x3000,h.RECORDS+0x3000)):
 h.prepare();h.cc.composeStrings=1;h.put(h.OWNER,[0x50d304]);h.put(0x53ebe0,[target]);h.put(h.APP+100,[selected]);h.compareConfirmation(0x485160,h.OWNER,[],'ordinary-confirmed-removal',False)
 if target==h.RECORDS:assert h.get(h.M+12)[0]==3 and not h.posted
 else:assert h.get(h.M+12)[0]==2 and target in h.freed and h.get(h.APP+100)[0]==h.RECORDS and h.posted[-1][2]==0x8036
# Actual source-created profiles, encrypted writer and source reader precede
# retained cancel and confirmation. The selected deletion uses the real token.
h.prepare(0);h.globalSeed=bytes(h.image[h.GS-h.IS:h.GS-h.IS+h.GN]);h.files={}
for name in(b'Player',b'Ada',b'Lin'):
 h.putBytes(h.DATA,name+b'\0');h.compare(0x49bdb0,h.M,[h.DATA,0,0,4 if name==b'Ada'else 0],'source-created-profile')
h.compare(0x49bbc0,h.M,label='source-created-save');blob=h.files[b'CLAW.USR'];h.prepare(0);h.files={b'C:\\CLAW\\CLAW.USR':blob};h.globalSeed=bytes(h.image[h.GS-h.IS:h.GS-h.IS+h.GN]);h.compare(0x49b840,h.M,[0x525618],'source-retained-save-reader')
records=[];node=h.get(h.M+4)[0]
while node:records.append(h.get(node+8)[0]);node=h.get(node)[0]
target=next(r for r in records if h.text(r+20)==b'Ada');default=next(r for r in records if h.text(r+20)==b'Player');h.put(h.APP+100,[target]);h.put(0x53ebe0,[target]);h.cc.composeStrings=1;h.compareConfirmation(0x4399d0,h.OWNER,[6],'retained-remove-popup');child=h.get(h.OWNER+352)[0];h.compareConfirmation(0x4247e0,child,[],'retained-cancel',False);assert h.get(h.M+12)[0]==3 and target not in h.freed
h.compareConfirmation(0x4399d0,h.OWNER,[6],'retained-remove-reopen');child=h.get(h.OWNER+352)[0];h.compareConfirmation(0x485160,child,[],'retained-confirm',False);assert h.get(h.M+12)[0]==2 and h.get(h.APP+100)[0]==default and target in h.freed
# Ordinary existing two-profile manager with no Player proves the exact save
# ordering: remaining Lin is written before fallback Player is created.
h.prepare(0);h.globalSeed=bytes(h.image[h.GS-h.IS:h.GS-h.IS+h.GN]);h.files={}
for name in(b'Ada',b'Lin'):
 h.putBytes(h.DATA,name+b'\0');h.compare(0x49bdb0,h.M,[h.DATA,0,0,0],'source-no-default-profile')
target=h.get(h.get(h.M+4)[0]+8)[0];h.put(h.APP+100,[target]);h.put(0x53ebe0,[target]);h.put(h.OWNER,[0x50d304]);h.cc.composeStrings=1;h.compareConfirmation(0x485160,h.OWNER,[],'source-default-after-writer',False);assert h.get(h.M+12)[0]==2 and h.get(h.M+44)[0]==1 and h.text(h.get(h.APP+100)[0]+20)==b'Player';assert len(h.files[b'CLAW.USR'])==9828
v={'pairedCallsAndInlineSpans':h.calls,'orderedSnapshots':h.eventCount,'mappedTextAddresses':len([v for v in h.m.executed if 0x401000<=v<=0x50adb5]),'totalInstrumentedAddresses':len(h.m.executed),'wholeEntries':9,'constructorInterval':['429275','4292c6'],'sourceHashes':{p:hashlib.sha256((h.ROOT/p).read_bytes()).hexdigest()for p in('Sources/PlayerProfileConfirmationRuntime.h','Sources/PlayerProfileConfirmationRuntime.cpp')},'limits':['428c40 controller remains addressed','CWnd4236c0/423840 and source graphics/resource methods are declared fixture boundaries','physical UI/file/graphics not native acceptance','whole425730 outside scope']}
(h.WORK/'verification.json').write_text(json.dumps(v,indent=2)+'\n');print('PASS',json.dumps(v))
