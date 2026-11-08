#!/usr/bin/env python3
"""Complete ordinary original profile dialogs and elected application8090."""
import itertools,json,hashlib
import player_menu_management_helpers as h
for selected,flags in itertools.product((0,h.RECORDS,h.RECORDS+0x3000),(0,4)):
 h.prepare();h.put(h.APP+100,[selected]);h.put((selected or h.RECORDS)+4,[flags]);h.compareMenu(0x49b160,0,[h.DIALOG,0x110,0,0],'info-init')
 if selected:
  assert h.labels[0x408]==h.text(selected+20) and len(h.controlLists[h.CONTROL])==15 and len(h.controlLists[h.CONTROL2])==15
 else:assert h.endings==[0]
for f in(0x49b160,0x49b630):
 for command in(1,2,0x10001,0x20001,0):
  h.prepare();h.controlLists[h.CONTROL]=[b'Ada',b'Lin'];h.controlIndices[h.CONTROL]=0
  h.compareMenu(f,0,[h.DIALOG,0x111,command,0],'ok-cancel-full-command')
  if command==2:assert h.endings==[0] and h.get(h.APP+100)[0]==h.RECORDS
for f,control in((0x49b3a0,h.CONTROL),(0x49b470,h.CONTROL2)):
 for level in range(15):
  h.prepare();h.controlIndices[control]=level;h.compareMenu(f,0,[h.DIALOG,control],'ordinary-level-statistics',False)
for control in(h.CONTROL,h.CONTROL2):
 h.prepare();h.controlIndices[control]=3;h.compareMenu(0x49b160,0,[h.DIALOG,0x111,0x10000,control],'list-notification')
for t in(0,123,59999,60000,3599999,3600000,3723000,36000000,360000000):
 h.prepare();h.compareMenu(0x49c860,0,[h.TIME_CELL,t],'ordinary-time-cstring')
 assert h.get(h.get(h.TIME_CELL)[0]-12)[0]==1
for data,result in itertools.product((0,4,5,6),(0,1)):
 h.prepare();h.transitionResult=result;h.compareMenu(0x426e30,h.APP,[0,0x8090,data],'actual-8090')
 reports=[e for e in h.events if e[0]==0x429e10];assert bool(reports)==(result==0)
for count,selected in itertools.product((1,3),(0,h.RECORDS,h.RECORDS+0x3000)):
 if count==1 and selected==h.RECORDS+0x3000:continue
 h.prepare(count);h.put(h.APP+100,[selected]);h.compareMenu(0x49b630,0,[h.DIALOG,0x110,0,0],'remove-default-and-population')
 assert b'Player'not in h.controlLists[h.CONTROL]
for name in(b'Ada',b'Lin'):
 h.prepare();h.controlLists[h.CONTROL]=[name];h.controlIndices[h.CONTROL]=0;old=h.get(h.APP+100)[0];h.compareMenu(0x49afd0,0,[h.CONTROL],'find-retained-profile');assert h.get(h.APP+100)[0]==old
 h.compareMenu(0x49b630,0,[h.DIALOG,0x111,1,0],'remove-select-record');assert h.text(h.get(0x53ebe0)[0]+20)==name and h.get(h.APP+100)[0]==old and h.endings==[1]
# Ordinary retained informational history reads the dialog's snapshot, even
# when a later selection is published through the frozen setter.
h.prepare();h.put(h.APP+100,[h.RECORDS+0x3000]);h.compareMenu(0x49b160,0,[h.DIALOG,0x110,0,0],'retained-info-enter');h.put(h.APP+100,[h.RECORDS+0x6000]);h.controlIndices[h.CONTROL]=2;h.compareMenu(0x49b160,0,[h.DIALOG,0x111,0x10000,h.CONTROL],'retained-info-score');assert h.get(0x53ebe0)[0]==h.RECORDS+0x3000
h.compareMenu(0x49b160,0,[h.DIALOG,0x111,2,0],'retained-info-cancel')
# Actual frozen record initialization/list insertion and source encrypted save
# fixture precede the profile dialog histories. These bytes stay in memory.
h.prepare(0);h.globalSeed=bytes(h.image[h.GS-h.IS:h.GS-h.IS+h.GN]);h.files={}
for name in(b'Player',b'Ada',b'Lin'):
 h.putBytes(h.DATA,name+b'\0');h.compare(0x49bdb0,h.M,[h.DATA,0,0,4 if name==b'Ada'else 0],'source-created-fictional-profile')
h.compare(0x49bbc0,h.M,label='source-encrypted-fictional-save');assert len(h.files[b'CLAW.USR'])==29420
blob=h.files[b'CLAW.USR'];h.prepare(0);h.files={b'C:\\CLAW\\CLAW.USR':blob};h.globalSeed=bytes(h.image[h.GS-h.IS:h.GS-h.IS+h.GN]);h.compare(0x49b840,h.M,[0x525618],'source-retained-save-reader')
h.put(h.APP+100,[h.get(h.get(h.M+4)[0]+8)[0]]);h.compareMenu(0x49b630,0,[h.DIALOG,0x110,0,0],'source-record-remove-enter');h.controlIndices[h.CONTROL]=0;h.compareMenu(0x49b630,0,[h.DIALOG,0x111,2,0],'source-record-remove-cancel');h.compareMenu(0x49b630,0,[h.DIALOG,0x111,1,0],'source-record-remove-ok');assert h.text(h.get(0x53ebe0)[0]+20)==b'Ada' and h.get(h.M+12)[0]==3
h.put(h.APP+100,[h.get(0x53ebe0)[0]]);h.compareMenu(0x49b160,0,[h.DIALOG,0x110,0,0],'source-record-info');h.compareMenu(0x49b160,0,[h.DIALOG,0x111,1,0],'source-record-info-ok')
v={'originalSha256':hashlib.sha256((h.ROOT/'Original/claw10/CLAW.EXE').read_bytes()).hexdigest(),'pairedCalls':h.calls,'orderedSnapshots':h.eventCount,'mappedTextAddresses':len([v for v in h.m.executed if 0x401000<=v<=0x50adb5]),'totalInstrumentedAddresses':len(h.m.executed),'newWholeEntries':7,'electedCommand':['426e30','8090'],'sourceCreatedProfiles':3,'sourceEncryptedFixtureBytes':29420,'sourceRetainedSaveReaderCalls':1,'sourceHashes':{p:hashlib.sha256((h.ROOT/p).read_bytes()).hexdigest()for p in('Sources/PlayerMenuManagementRuntime.h','Sources/PlayerMenuManagementRuntime.cpp')},'limits':['physical dialog/format/file endpoints are fixtures','state13 graphical popup/428c40 transition remain dependencies','whole425730 is outside scope']}
(h.WORK/'verification.json').write_text(json.dumps(v,indent=2)+'\n');print('PASS',json.dumps(v))
