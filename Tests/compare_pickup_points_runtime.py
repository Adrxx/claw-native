#!/usr/bin/env python3
"""Whole original points spawn/selection/controller and retained actual ANI."""
import json
import pickup_points_helpers as t
values=[100,500,1500,2500,5000,7500,10000,15000,25000,0,99,101,501,1501,2499,5001,7499,10001,14999,24999,0xffffffff,0x80000000]
for compose in(0,1):
 for value in values:
  for bounds in((0,9),(3,7),(0,0),(9,0)):
   t.prepare(value);t.pc.composeCreation=compose;t.put(t.SOURCE+0xfc,[value]);t.put(t.POINTS+0x64,bounds);t.compare(0x4737c0,('spawn/map',compose,value,bounds),args=(t.SOURCE,))
for value in values:
 t.prepare(value);t.image_found=False;t.put(t.SOURCE+0xfc,[value]);t.compare(0x4737c0,('missing image',value),args=(t.SOURCE,))
t.prepare(1);t.pc.composeCreation=1;t.entry_found=False;t.compare(0x4737c0,'missing PointsIcon metadata returns normally',args=(t.SOURCE,))
t.prepare(1);t.creator_null=True;t.compare(0x4737c0,'creator null is normal',args=(t.SOURCE,))
t.prepare(2);t.mutation=1;t.compare(0x4737c0,'image transport changes item score and root range',args=(t.SOURCE,))
for state in(0,5,29,30,1000,0xffffffff):
 for stopped,delay in((0,0),(1,0),(1,1),(0xffffffff,0xffffffff)):
  t.prepare(state);t.put(t.POINTLOGIC+0x1c,[state]);t.put(t.POINTACTOR+0x19c,[delay,stopped]);t.compare(0x473a70,('explicit animation service',state,stopped,delay),args=(t.POINTACTOR,))
for mutation in(2,3):
 t.prepare(mutation);t.mutation=mutation;t.put(t.POINTLOGIC+0x1c,[0 if mutation==2 else 5]);t.compare(0x473a70,('capture logic / live actor after callback',mutation),args=(t.POINTACTOR,))
for found in(0,1):
 for index in(-0x80000000,-1,0,1,7,9,10,0x7fffffff):
  t.prepare(index);t.image_found=found;t.compare(0x4c7900,('indexed setter',found,index),t.POINTACTOR,(0x52a6c0,index))
for bounds in((0,9),(3,7),(-3,-1),(9,0)):
 for index in(-4,-3,-1,0,1,7,9,10):
  t.prepare(index);t.put(t.POINTS+0x64,bounds)
  # For negative legal frames, provide the original absolute table address.
  t.compare(0x40f680,('signed getter',bounds,index),t.POINTS,(index,))
for n in(1,2,3):t.allocation_failure(n)
for found in(0,1):
 t.prepare(found);t.pc.composeAnimation=1;t.ani_found=found;t.load_actual_ani();t.compare(0x473a70,('actual ANI startup lookup success/failure',found),args=(t.POINTACTOR,))
for value in values[:10]:
 for delta in(16,75,300,0xffffffff):
  t.prepare(value);t.pc.composeCreation=t.pc.composeAnimation=1;t.load_actual_ani();t.put(t.SOURCE+0xfc,[value]);t.compare(0x4737c0,('retained spawn',value,delta),args=(t.SOURCE,))
  actor=t.get(t.CT+0x14)[0];actor=t.get(actor+8)[0] # CList head node→actor.
  t.compare(0x473a70,('retained startup',value,delta),args=(actor,));t.pc.animationDelta=delta
  steps=0
  while not t.get(actor+8)[0]&0x10000 and steps<45:
   t.compare(0x473a70,('actual ANI lifetime',value,delta,steps),args=(actor,));steps+=1
  assert t.get(actor+8)[0]&0x10000,('actual lifetime',value,delta,steps)
  t.compare(0x4c9be0,('retained generic destruction',value,delta),actor,(1,));assert t.get(actor+0x6c)[0]==0
# Synthetic audio resource attached to actual ANI records: proves transport
# ordering and external audio-global mutation without inventing native sound.
t.prepare(777);t.pc.composeAnimation=1;t.load_actual_ani();t.put(t.RECORDS+44,[t.BASE+0x7a000]);t.compare(0x473a70,'ANI audio startup',args=(t.POINTACTOR,));t.pc.animationDelta=16
t.compare(0x473a70,'actual first ANI record with injected audio leaf',args=(t.POINTACTOR,))
assert len(t.native_events)==1 and t.native_events[0][0][0]in(0x4c88e0,0x4208e0)
report={'completeOriginalCalls':t.calls,'orderedFullHeapSnapshots':t.event_count,'originalAddresses':len(t.m.executed),'heapBytes':t.SIZE,'actualANIRecordDecodes':t.decodes,'retainedActualANIHistories':40,'genericDestructionHistories':40,'actualAllocationFailurePrefixes':3,'scope':'Whole4737c0/473a70/40f680 plus actual image setters, composed original scene creator and ActorAnimation. Resource lookup/allocation/audio boundaries explicit.'}
(t.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
