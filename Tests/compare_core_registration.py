#!/usr/bin/env python3
"""Original handler registration, bitset construction, and backing release."""
import ctypes as C,json,random
import core_registration_helpers as t
for seed in range(160):
 t.prepare(seed);t.compare(0,0,('CRT handlers',seed),initialize=True)
 for receiver in(t.HANDLER,0x544b68,0x544b18):
  t.compare(0x4dc3a0,receiver,('handler ctor',seed,receiver),0x533474+seed)
 for handler in(0,0x544b18,0x544b68,t.HANDLER):t.compare(0x4db620,t.OBJ,('base ctor',seed,handler),handler)
for count in range(33):
 for repeat in range(8):
  active=t.prepare(count=count)
  for receiver in(t.HANDLER,0x544b68):
   for key in [0,*active[:2],*active[-2:],0x80000000,0xffffffff,t.BASE+0x8000]:
    t.compare(0x4dc3d0,receiver,('search',count,repeat,receiver,key),key)
    for function in(0,0x12345678):t.compare(0x4dc560,receiver,('register/update/remove',count,repeat,receiver,key,function),key,function)
for n in(0,1,31,32,33,63,64,65,97,4095):
 for fail in(False,True):
  for fn in(0x4dc7b0,0x4dc180,0x4dbe10):
   t.prepare();t.g.defaultBitCount=n;t.fail_alloc=fail
   t.compare(fn,t.OBJ,('bitset init',fn,n,fail),t.STRING if fn==0x4dbe10 else n,n if fn==0x4dbe10 else 0)
   assert t.g.words[129]==0,'bitset ctor invented registration'
for n in(0xffffffe0,0xfffffff0,0xffffffff):
 for fn in(0x4dc7b0,0x4dc180,0x4dbe10):
  t.prepare();t.g.defaultBitCount=n;t.fail_alloc=True;t.compare(fn,t.OBJ,('oversize allocator failure',fn,n),t.STRING if fn==0x4dbe10 else n,n if fn==0x4dbe10 else 0)
for n in range(40):
 t.prepare();t.g.words[14]=0;t.compare(0x4dbe10,t.OBJ,('null string error',n),0,0)
# Full register -> update -> capacity gate -> removal -> destructor histories.
for history in range(40):
 t.prepare();t.compare(0,0,('chain CRT',history),initialize=True);keys=list(range(t.BASE+0x1000,t.BASE+0x1200,16));random.Random(history).shuffle(keys)
 for key in keys:t.compare(0x4dc560,0x544b68,('chain insert',history,key),key,0x401000+key%256)
 assert t.g.words[129]==32
 for key in(keys[0],0xffffffff):t.compare(0x4dc560,0x544b68,('full blocks update/new',history,key),key,0x44556677)
 for key in keys[1:]:t.compare(0x4dc560,0x544b68,('chain remove',history,key),key,0)
 t.put(keys[0],[0x513e34,0x544b68,32,0]);t.compare(0x4db6c0,keys[0],('chain base destructor',history));assert t.g.words[129]==0
 # Original empty list insertion uses the preserved handler index.
 t.g.words[(0x544b68-t.GBASE)//4+1]=history%32
 t.compare(0x4dc560,0x544b68,('empty stale insertion index',history),t.OBJ,0x456789ab)
for wrapper in(0x4a49b0,0x4f6428):
 for small in(0,0x300abcd):
  for seed in range(80):
   t.prepare(seed);t.small_block=small;t.small_values=(seed^0xf0000000,seed^0xaabbccdd)
   t.compare(wrapper,0,('CRT free wrapper',wrapper,small,seed),t.BASE+0x4000)
   t.compare(wrapper,0,('null free wrapper',wrapper,small,seed),0)
# Join the frozen bitset destructor with real populated registration and free
# wrappers. The two exact internal service boundaries are observed, then execute.
for n in(32,33,63,64,65,97,1024):
 for small in(0,0x300abcd):
  for seed in range(12):
   t.prepare();t.compare(0x4dc180,t.OBJ,('destructor ctor',n,small,seed));t.compare(0x4dc7b0,t.OBJ,('destructor explicit backing',n,small,seed),n)
   t.compare(0x4dc560,0x544b68,('destructor register',n,small,seed),t.OBJ,0x12345678);t.small_block=small
   t.compare(0x4dbcd0,t.OBJ,('joined destructor',n,small,seed),destructor=True);assert t.g.words[129]==0
report={'completeOperations':t.calls,'orderedCompleteSnapshots':t.events,'originalAddresses':len(t.m.executed),'rawHeapBytes':t.SIZE,'globalWords':130,'selectedHandlerConstructors':5,'genericConstructorProof':'separate helper'}
(t.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

# The caller proof uses only this worker's artifact directories.
import subprocess,sys
subprocess.run([sys.executable,str(t.ROOT/'Tests/core_registration_enemy_probe.py')],check=True)
