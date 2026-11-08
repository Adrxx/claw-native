#!/usr/bin/env python3
"""Whole original glitter callbacks and composed retained baby lifetimes."""
import json
import glitter_logic_helpers as t
for state in(0,5,10,29,30,1000,0xffffffff):
 for owner in(0,t.SOURCE):
  if state==10 and not owner:continue
  t.prepare(state);t.put(t.MOTHERLOGIC+0x1c,[state]);t.put(t.MOTHERLOGIC+0x170,[owner]);t.compare(0x448440,('mother state gate',state,owner),args=(t.MOTHER,))
for enabled in(0,1,0xffffffff):
 for rect in((-20,-25,20,25),(5,6,5,6),(1,2,0,1),(0,0,0xffffffff,0xffffffff),(0xfffffffe,0xfffffffd,2,3),(5,6,1,2)):
  for seed in range(8):
   t.prepare(seed);t.put(t.OWNER+0x124,[enabled]);t.put(t.SOURCE+0x118,rect);t.put(t.MOTHERLOGIC+0x1c,[10]);t.compare(0x448440,('wrapped signed rect/shared RNG',enabled,rect,seed),args=(t.MOTHER,))
for mutation in(1,2):
 t.prepare(mutation);t.put(t.MOTHERLOGIC+0x1c,[10]);t.mutation=mutation;t.compare(0x448440,('live RNG owner rereads',mutation),args=(t.MOTHER,))
for fn in(0x4485a0,0x470110):
 for mode in(0,5,29,30,1000,0xffffffff):
  for stopped,delay in((0,0),(1,0),(1,1),(0xffffffff,0xffffffff)):
   t.prepare(mode);t.put(t.MOTHERLOGIC+0x1c,[mode]);t.put(t.MOTHER+0x19c,[delay,stopped]);t.compare(fn,('explicit image/ANI service',fn,mode,stopped,delay),args=(t.MOTHER,))
 for mutation in(3,4):
  t.prepare(mutation);t.mutation=mutation;t.put(t.MOTHERLOGIC+0x1c,[0 if mutation==3 else 5]);t.compare(fn,('captured primary/live completion',fn,mutation),args=(t.MOTHER,))
for seed in range(100):
 t.prepare(seed);t.put(t.MOTHER+0x64,[0 if seed%2 else 123]);t.put(t.MOTHER+0x190,[0 if seed%3 else t.SEQUENCE]);t.compare(0x470110,('source PowerupGlitter startup/random delay',seed),args=(t.MOTHER,))
for fn,ani in((0x4485a0,'GLITTER1.ANI'),(0x470110,'CYCLE100.ANI')):
 for image in(0,1):
  for ani_found in(0,1):
   t.prepare(image);t.pc.composeAnimation=1;t.image_found=image;t.ani_found=ani_found;t.load_actual_ani(ani);t.compare(fn,('composed resource outcome',fn,image,ani_found),args=(t.MOTHER,))
for compose in(0,1):
 t.prepare(compose);t.put(t.MOTHERLOGIC+0x1c,[10]);t.pc.composeCreation=compose;t.creator_null=True;t.entry_found=False;t.compare(0x448440,('missing/null Baby creator ignored;timer still15',compose),args=(t.MOTHER,));assert t.get(t.MOTHERLOGIC+0x20)[0]==15
# An out-of-domain RNG transport output tests actual signed IDIV failure,
# distinct from the retail LCG's0..32767 result range.
t.prepare(456);t.random_override=[0x80000000];t.put(t.SOURCE+0x118,[0,0,0xfffffffe,0]);t.put(t.MOTHERLOGIC+0x1c,[10]);t.compare(0x448440,'signed IDIV overflow prefix',args=(t.MOTHER,),fault_expected=True);assert t.u.reg_read(t.UC_X86_REG_EIP)==0x4484c3
for seed in range(8):
 t.prepare(seed);t.pc.composeAnimation=1;t.load_actual_ani('CYCLE100.ANI');t.put(t.MOTHER+0x64,[0]);t.put(t.MOTHER+8,[0]);t.compare(0x470110,('retained PowerupGlitter init',seed),args=(t.MOTHER,))
 for frame in range(30):
  t.pc.animationDelta=16;t.compare(0x470110,('retained actual CYCLE100',seed,frame),args=(t.MOTHER,));assert not t.get(t.MOTHER+8)[0]&0x10000
for which in(1,2,3):t.allocation_failure(which)
for enabled in(0,1):
 for seed in range(12):
  t.prepare(seed);t.pc.composeCreation=t.pc.composeAnimation=1;t.load_actual_ani();t.put(t.OWNER+0x124,[enabled]);t.compare(0x448440,('retained mother init',enabled,seed),args=(t.MOTHER,))
  before=t.cursor;t.compare(0x448440,('retained emission/immediate Baby startup',enabled,seed),args=(t.MOTHER,));babies=[];node=t.get(t.CT+0x14)[0]
  while node:babies.append(t.get(node+8)[0]);node=t.get(node)[0]
  assert len(babies)==1+enabled and t.get(t.MOTHERLOGIC+0x20)[0]==15
  for actor in babies:
   assert t.get(t.get(actor+0x6c)[0]+0x1c)[0]==5
   for frame in range(40):
    t.pc.animationDelta=16;t.compare(0x4485a0,('retained actual baby ANI',enabled,seed,actor,frame),args=(actor,))
    if t.get(actor+8)[0]&0x10000:break
   assert t.get(actor+8)[0]&0x10000
   t.compare(0x4c9be0,('retained Baby generic deletion',enabled,seed,actor),actor,(1,))
report={'wholeOriginalCalls':t.calls,'orderedFullHeapSnapshots':t.event_count,'rawHeapBytes':t.SIZE,'originalAddresses':len(t.m.executed),'actualANIRecordDecodes':t.decodes,'retainedMotherEmissionHistories':24,'retainedBabyANIAndDestructionHistories':36,'allocationFailurePrefixes':3,'signedDivisionFailurePrefixes':1,'retainedPowerupCycleHistories':8,'scope':'Whole448440/4485a0/470110 with composedSceneCreator and ANI. Resource/allocator/audio/Windows TLS services explicit.'}
(t.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
