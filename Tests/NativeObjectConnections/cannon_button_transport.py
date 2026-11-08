"""Finite CannonButton transport comparison; original bytes stay under work/."""
from pathlib import Path
import argparse,json,os,struct,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
os.chdir(ROOT);sys.path.insert(0,str(ROOT))
from Tests.clawparity.program import claw
OUT=ROOT/'work/native-object-connections/cannon_button_transport'
def original_bytes(p,a,n):
 s=next(s for s in p.sections if s.address<=a and a+n<=s.address+s.size)
 return (s.data+bytes(max(0,s.size-len(s.data))))[a-s.address:a-s.address+n]
def prepare():
 p=claw();OUT.mkdir(parents=True,exist_ok=True)
 spans=[(0x510020,4),(0x50ba3c,0x28),(0x513740,0x28),(0x522d48,0x18),(0x5245bc,0x48),(0x523148,8),(0x532c0c,8),(0x537210,4),(0x5430c4,4),(0x53774c,4),(0x52e1b8,0x10)]
 (OUT/'input.json').write_text(json.dumps({'image':[dict(token=a,bytes=list(original_bytes(p,a,n))) for a,n in spans]}))
 metadata=[]
 for pc,continuation,target in [(0x414cf5,0x414cfa,0x4f63ec),(0x414d10,0x414d15,0x415090),(0x414d49,0x414d4e,0x4dc870)]:
  code=original_bytes(p,pc,5);assert code[0]==0xe8 and pc+5+struct.unpack('<i',code[1:])[0]==target and continuation==pc+5
  metadata.append(dict(call=pc,continuation=continuation,target=target))
 table=struct.unpack('<10I',original_bytes(p,0x50ba3c,40))
 assert table[:9]==(0x484d90,0x4c9e30,0x414de0,0x4041b0,0x4c96b0,0x4152e0,0x4bb030,0x4c96b0,0x4c96b0),tuple(hex(x) for x in table)
 (OUT/'metadata.json').write_text(json.dumps(dict(image_sha256=p.sha256,calls=metadata,vtable=list(table)),indent=2))
def wait_for_load():
 while True:
  load=float(subprocess.check_output(["sysctl","-n","vm.loadavg"],text=True).split()[1])
  if load<16:return
  print(f"Waiting for load {load} to fall below 16",file=sys.stderr,flush=True);time.sleep(30)
def build():
 wait_for_load()
 objects=subprocess.check_output([str(ROOT/'work/test-env/bin/python'),'-m','tools.claw.native_objects','--dir','work/native-player-check','--jobs','1'],text=True).splitlines()
 sources=['Sources/ClawTokenHeap.swift','Sources/ClawNativeCanonicalHost.swift','Sources/ClawNativeMfcLocks.swift','Sources/ClawNativeMfcMemory.swift','Tests/NativeObjectConnections/cannon_button_transport.swift']
 subprocess.run(['xcrun','swiftc','-import-objc-header','Sources/Claw-Bridging-Header.h',*sources,*objects,'-lc++','-lz','-o',str(OUT/'transport')],check=True)
def compare():
 wait_for_load()
 from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
 from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EBP,UC_X86_REG_EFLAGS
 p=claw();native=json.loads((OUT/'native.json').read_text());u=Uc(UC_ARCH_X86,UC_MODE_32);mapped=set()
 def map_range(a,n):
  for page in range(a&~4095,(a+n+4095)&~4095,4096):
   if page not in mapped:u.mem_map(page,4096);mapped.add(page)
 for s in p.sections:map_range(s.address,s.size);u.mem_write(s.address,s.data)
 map_range(0,4096);map_range(0x01ff0000,0x20000);map_range(0x62000000,0x10000)
 for span in native['initial']:map_range(span['token'],len(span['bytes']));u.mem_write(span['token'],bytes(span['bytes']))
 def get(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def put(a,v):u.mem_write(a,struct.pack('<I',v))
 actor,logic=0x10002000,0x10003000
 next_alloc=0x62000000;allocations={};calls=[];allocation_failure=False;failure_cut=False
 abi={0x4f63ec:(1,False),0x4a48e0:(1,False),0x415090:(1,True),0x4c7fa0:(1,True),0x4c8060:(1,True),0x4c8160:(2,True),0x4c81b0:(0,True),0x4f6286:(2,True),0x4c7970:(1,True),0x4c8220:(1,True),0x4dba00:(1,True),0x4c96b0:(0,True),0x4dc870:(1,False),0x4f6974:(1,True),0x4c9e30:(1,True),0x414de0:(1,True),0x415210:(0,True),0x415250:(0,True),0x4152e0:(0,True),0x4041b0:(1,True),0x4c82a0:(1,True),0x484d90:(1,True),0x4f6428:(1,False)}
 resources={(0x10006010,0x522d54):0x10009100,(0x10006010,0x522d48):0x10009200,(0x10006110,0x5245f0):0x10007000,(0x10006210,0x5245d8):0x10008000,(0x10006310,0x5245bc):0x10009000}
 allowed=set(abi)-{0x415210,0x4152e0}
 # 415210 is inlined by the admitted constructor; contact root has no nested call event.
 def ret(result,pop=0):
  sp=u.reg_read(UC_X86_REG_ESP);u.reg_write(UC_X86_REG_EAX,result);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,get(sp))
 def hook(uc,a,size,data):
  nonlocal next_alloc,failure_cut
  if a==0x0200f000:uc.emu_stop();return
  sp=uc.reg_read(UC_X86_REG_ESP);receiver=uc.reg_read(UC_X86_REG_ECX)
  if a in abi and a in allowed:
   count,method=abi[a];calls.append(dict(function=a,receiver=receiver if method else 0,args=[get(sp+4+i*4) for i in range(count)]))
  if allocation_failure and a==0x5022b5:
   failure_cut=True;uc.emu_stop();return
  if a==0x4a48e0:
   if allocation_failure:ret(0);return
   count=get(sp+4);token=next_alloc;next_alloc=(token+count+15)&~15;assert count in (0x54,0x174),hex(count)
   u.mem_write(token,b'\xcc'*count);allocations[token]=count;ret(token)
  elif a==0x4f6286:
   key=(receiver,get(sp+4));assert key in resources,key;put(get(sp+8),resources[key]);ret(1,8)
  elif a==0x4f6428:
   token=get(sp+4);assert token in allocations,hex(token);del allocations[token];ret(0)
 u.hook_add(UC_HOOK_CODE,hook)
 results=[]
 for step in native['steps']:
  calls=[];name=step['name']
  if name=='contact':entry=0x4152e0;receiver=get(logic+0x18);args=[]
  elif name=='retire':entry=0x484d90;receiver=get(logic+0x18);args=[1]
  else:entry=0x414cc0;receiver=0;args=[actor];put(logic+0x1c,step['command'])
  sp=0x02008000;u.mem_write(sp,struct.pack('<'+'I'*(len(args)+1),0x0200f000,*args))
  put(0,0xffffffff);u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_EBP,sp+0x80);u.reg_write(UC_X86_REG_ECX,receiver);u.reg_write(UC_X86_REG_EFLAGS,2)
  try:u.emu_start(entry,0x0200f000,count=200000)
  except Exception as e:raise AssertionError(f'{name} original fault PC={u.reg_read(UC_X86_REG_EIP):x}: {e}') from e
  assert u.reg_read(UC_X86_REG_EIP)==0x0200f000,(name,'budget')
  if name=='retire':put(logic+0x18,0)
  differences=[]
  for span in step['spans']:
   a=span['token'];expected=bytes(span['bytes']);actual=bytes(u.mem_read(a,len(expected)))
   if actual!=expected:differences.append((hex(a),[(hex(a+i),x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y][:12]))
  assert not differences,(name,'bytes',differences[:8])
  def normalize(c):
   def norm(v):return 'stack-output' if 0x01ff0000<=v<0x02010000 else v
   return dict(function=c['function'],receiver=c['receiver'],args=[norm(v) for v in c['args']])
  actual=[normalize(c) for c in calls];expected=[normalize(c) for c in step['calls']]
  assert actual==expected,(name,'ordered calls',actual,expected)
  results.append(dict(name=name,spans=len(step['spans']),calls=len(calls),live_allocations=dict(allocations)))
 # Exhaustion executes the real operator-new retry/handler lookup. Both hosts
 # stop at the missing thread-policy owner; neither reports a returning callback.
 allocation_failure=True;calls=[]
 for span in native['initial']:u.mem_write(span['token'],bytes(span['bytes']))
 sp=0x02008000;u.mem_write(sp,struct.pack('<II',0x0200f000,actor));put(0,0xffffffff)
 u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,0);u.reg_write(UC_X86_REG_EBP,sp+0x80);u.reg_write(UC_X86_REG_EFLAGS,2)
 u.emu_start(0x414cc0,0x0200f000,count=10000)
 assert failure_cut and get(logic+0x1c)==1000 and get(logic+0x18)==0,'original allocation failure cut'
 result=dict(status='pass',callback='0x414cc0',native_owner='ClawNativeCanonicalHost / ClawNativeMfcMemory',profiles=len(results),comparisons=results,controls=native['controls'],original_allocation_failure_cut='0x5022b5',metadata=json.loads((OUT/'metadata.json').read_text()),unresolved_dependencies=[])
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--prepare-only',action='store_true');parser.add_argument('--compare-only',action='store_true');parser.add_argument('--no-build',action='store_true');args=parser.parse_args()
 if not args.compare_only:prepare()
 if args.prepare_only:return
 if not args.compare_only:
  if not args.no_build:build()
  subprocess.run([str(OUT/'transport'),str(OUT)],check=True)
 compare()
if __name__=='__main__':main()
