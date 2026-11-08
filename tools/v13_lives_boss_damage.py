"""Read-only original-instruction probes; neither native admission nor UI replay.
All instruction text is decoded transiently. No image bytes are changed.
"""
import hashlib, json, struct, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86_const import X86_OP_MEM, X86_OP_IMM, X86_OP_REG
from unicorn import UC_HOOK_CODE
from unicorn import x86_const as xr
from Tests.clawparity.program import claw, claw_v13
from Tests.clawparity.kernel import Machine, STACK_TOP

ROOT=Path(__file__).resolve().parents[1]
DEC=Cs(CS_ARCH_X86, CS_MODE_32); DEC.detail=True
THIS,ACTOR,LOGIC,PRIVATE,SCENE,MANAGER,PLANE,HUD=(0x3000000+i*0x1000 for i in range(8))
REGS={n:getattr(xr,'UC_X86_REG_'+n.upper()) for n in ['eax','ebx','ecx','edx','esi','edi','ebp','esp']}
PROFILES={
 'v10':dict(program=claw, reset=0x415ce0, callback=0x415df0, defaults=0x534c80, difficulty=0x53725c, actor_logic=0x6c, health=0x10c, damage=0x104, owner_actor=0xc, scale=0x5262b0, health_scale=0x5262b4, normal_scale=0x440e00, hud=0x4912a0, resource=0x4c7900),
 'v13':dict(program=claw_v13, reset=0x416dd0, callback=0x416ee0, defaults=0x532bf8, difficulty=0x535990, actor_logic=0x7c, health=0x128, damage=0x120, owner_actor=0x10, scale=0x524580, health_scale=0x524584, normal_scale=0x441e10, hud=0x494880, resource=0x4c6d60),
}
# Semantic owners, not matched-body equivalence claims. Entries are inspected
# independently in each pinned image. Values are expectations, never injected.
CONTACT=[
 ('Raux',2,0x47e2d0,0x480cb0,10,5),
 ('Katherine',4,0x453df0,0x455740,10,5),
 ('Wolvington',6,0x49fbf0,0x4a3830,30,5),
 ('Gabriel (inherited enemy contact)',8,0x44c000,0x44d900,10,10),
 ('Marrow',10,0x458d40,0x45ad80,10,10),
 ('Aquatis',12,0x404990,0x404d80,15,10),
 ('RedTail (inherited enemy contact)',13,0x44c000,0x44d900,10,10),
 ('Omar',14,0x463460,0x4659e0,30,30),
]
ATTACKS=[
 ('Wolvington magic projectile',6,0x4a0cf0,0x4a48a0,15,5,'spawn'),
 ('Gabriel cannonball, zero-only default',8,0x414be0,0x415ab0,10,10,'default'),
 ('Gabriel bomb, zero-only default',8,0x445ef0,0x447330,15,5,'default'),
 ('RedTail knife',13,0x480c40,0x483480,10,5,'spawn'),
 ('RedTail bullet',13,0x481400,0x483c70,15,15,'spawn'),
 ('RedTail pirate contact',13,0x4828e0,0x4851d0,10,10,'scaled'),
 ('RedTail spikes',13,0x484680,0x486ee0,20,20,'scaled'),
 ('Omar elemental projectile',14,0x464cc0,0x467160,15,15,'spawn'),
]

def guard():
 load=subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True)
 if float(load.split()[1])>=16: raise RuntimeError('wait for load below 16: '+load.strip())

def code(p,address,size=0x1800):
 s=next(s for s in p.sections if s.address<=address<s.address+len(s.data))
 return list(DEC.disasm(s.data[address-s.address:address-s.address+size],address))

def write(m,a,*words):m.write(a,struct.pack('<'+'I'*len(words),*(w&0xffffffff for w in words)))
def reg(m,n,v):m.uc.reg_write(REGS[n],v)
def prepare(m,c):
 m.write(THIS,b'\0'*0x8000)
 for n in REGS:reg(m,n,STACK_TOP if n=='esp' else THIS)
 write(m,THIS+c['owner_actor'],ACTOR)
 write(m,THIS+0x2c,ACTOR)
 write(m,ACTOR+c['actor_logic'],LOGIC)
 write(m,LOGIC+0x14,PRIVATE)
 write(m,ACTOR+0xc,SCENE);write(m,SCENE+0x24,MANAGER);write(m,MANAGER+0x5c,PLANE)
 write(m,PLANE+0x30,24576,6144);write(m,PLANE+0x84,689,4723)
 m.reset_x87()

def segment(m,start,end):
 # Execute intact original bytes with the real pinned startup x87 policy.
 handle=m.uc.hook_add(UC_HOOK_CODE,lambda u,a,s,_:u.emu_stop(),begin=end,end=end)
 try:m.uc.emu_start(start,end,timeout=1_000_000,count=10000)
 finally:m.uc.hook_del(handle)
 assert m.uc.reg_read(xr.UC_X86_REG_EIP)==end,hex(m.uc.reg_read(xr.UC_X86_REG_EIP))
 return dict(start=hex(start),end_exclusive=hex(end),sha256=hashlib.sha256(m.read(start,end-start)).hexdigest())

def scalar(m,c,entry,expected,kind='scaled',field=None,initial=0):
 field=c['damage'] if field is None else field
 ins=code(m.program,entry)
 # Stop at the next root's RET when searching: only the selected owner.
 stop=next(i for i,x in enumerate(ins) if x.mnemonic.startswith('ret'))
 ins=ins[:stop+1]
 stores=[i for i,x in enumerate(ins) if x.mnemonic=='mov' and len(x.operands)==2 and x.operands[0].type==X86_OP_MEM and x.operands[0].mem.disp==field and x.operands[1].type==X86_OP_IMM]
 literal=None
 if not stores:
  stores=[i for i,x in enumerate(ins) if x.mnemonic=='mov' and x.operands[0].type==X86_OP_MEM and x.operands[0].mem.disp==field and x.operands[1].type==X86_OP_REG and x.reg_name(x.operands[1].reg)!='eax']
  assert len(stores)==1
  source=ins[stores[0]].operands[1].reg
  litix=next(i for i in range(stores[0]-1,-1,-1) if ins[i].mnemonic=='mov' and ins[i].operands[0].type==X86_OP_REG and ins[i].operands[0].reg==source and ins[i].operands[1].type==X86_OP_IMM)
  assert all(source not in x.regs_access()[1] for x in ins[litix+1:stores[0]])
  literal=ins[litix]
 assert len(stores)==1,(hex(entry),field,len(stores))
 ix=stores[0]; store=ins[ix]; base=store.reg_name(store.operands[0].mem.base)
 prepare(m,c);write(m,ACTOR+field,initial)
 literal_proof=None
 if literal:literal_proof=segment(m,literal.address,literal.address+literal.size)
 if kind=='scaled':
  last=next(j for j in range(ix+1,len(ins)) if ins[j].mnemonic=='mov' and ins[j].operands[0].type==X86_OP_MEM and ins[j].operands[0].mem.disp==field and ins[j].operands[1].type==X86_OP_REG)
  # Only original arithmetic/conversion inside this bounded scalar path.
  assert all(x.mnemonic not in ('jmp','je','jne') for x in ins[ix:last+1])
  assert any(x.mnemonic=='fmul' for x in ins[ix:last+1])
  reg(m,base,ACTOR)
  proof=segment(m,store.address,ins[last+1].address)
 elif kind=='default':
  assert ins[ix-1].mnemonic in ('jne','jnz')
  compare=ins[ix-2];assert compare.mnemonic in ('cmp','test')
  reg(m,base,ACTOR)
  start=compare.address
  if compare.mnemonic=='test':
   load=ins[ix-3];assert load.mnemonic=='mov' and load.operands[1].type==X86_OP_MEM and load.operands[1].mem.disp==field
   start=load.address
  else:
   op=compare.operands[1]
   if op.type==X86_OP_REG:reg(m,compare.reg_name(op.reg),0)
   else:assert op.type==X86_OP_IMM and op.imm==0
  proof=segment(m,start,store.address+store.size)
 else:
  reg(m,base,ACTOR);proof=segment(m,store.address,store.address+store.size)
 value=m.words(ACTOR+field,1)[0]
 assert value==expected,(hex(entry),kind,value,expected)
 return dict(owner=hex(entry),store=hex(store.address),field=hex(field),initial=initial,value=value,literal_proof=literal_proof,**proof)

def new_game(m,c,difficulty):
 prepare(m,c);write(m,c['difficulty'],difficulty)
 result=m.call(c['reset']);assert result.completed
 expected_defaults=m.read(c['defaults'],0x138)
 # No allocator needed: preallocate the ordinary player's private record.
 # Stop at the first resource service, AFTER original default-to-player copy
 # and actor health sync. No game/resource stand-ins influence these values.
 ins=code(m.program,c['callback'])
 target=next(i.address for i in ins if i.mnemonic=='call' and i.operands[0].type==X86_OP_IMM and i.operands[0].imm==c['resource'])
 handle=m.uc.hook_add(UC_HOOK_CODE,lambda u,a,s,_:u.emu_stop(),begin=target,end=target)
 try:
  result=m.call(c['callback'],arguments=(ACTOR,))
  assert not result.completed and m.uc.reg_read(xr.UC_X86_REG_EIP)==target
 finally:m.uc.hook_del(handle)
 assert m.read(PRIVATE,0x138)==expected_defaults
 values=m.words(PRIVATE,78)
 assert m.words(ACTOR+c['health'],1)[0]==values[18]
 # Execute original HUD subtraction/clamp with the resulting player pointer.
 hud=code(m.program,c['hud'])
 ix=next(i for i,x in enumerate(hud) if x.mnemonic=='mov' and len(x.operands)==2 and x.operands[0].type==X86_OP_REG and x.reg_name(x.operands[0].reg)=='eax' and x.operands[1].type==X86_OP_MEM and x.operands[1].mem.disp==0x7c and x.reg_name(x.operands[1].mem.base)=='ecx')
 reg(m,'ecx',PRIVATE);reg(m,'esi',HUD);reg(m,'edx',0)
 end=next(x.address+x.size for x in hud[ix:] if x.mnemonic=='and' and x.op_str=='eax, edx')
 hp=segment(m,hud[ix].address,end)
 displayed=m.uc.reg_read(xr.UC_X86_REG_EAX)
 expected=(3 if difficulty==0 else 9) if m.program.name=='claw-v1.0' else (7 if difficulty==0 else 9)
 assert (values[31],displayed)==(expected,expected-1)
 assert [values[i] for i in (18,28,29,30)]==([100,10,5,3] if difficulty==0 else [100,50,40,20])
 return dict(difficulty=difficulty,initializer=hex(c['reset']),callback=hex(c['callback']),stopped_before_resource=hex(target),defaults=hex(c['defaults']),record_bytes=0x138,health=values[18],pistol=values[28],magic=values[29],dynamite=values[30],lives_including_current=values[31],hud_spare_lives=displayed,extra_life_threshold=values[59],hud_proof=hp)

def full_state0(m,c,difficulty):
 """Complete state zero, with the same bounded resource/ground services as
 the v1.0 initialization oracle. Original inventory/idle/facing/physics code
 executes; the independent prefix probe above needs no stand-ins at all.
 """
 old=m.program.name=='claw-v1.0'
 prepare(m,c);write(m,c['difficulty'],difficulty)
 assert m.call(c['reset']).completed
 game,config,table,inputs=THIS+0x8000,THIS+0x9000,THIS+0xa000,THIS+0xb000
 write(m,0x5371fc if old else 0x535910,game)
 write(m,0x537204 if old else 0x535918,inputs)
 write(m,game+0x2c,config);write(m,config,table)
 mode=m.first_free_stub;write(m,table+0x10,mode)
 # Each tuple names a narrowly observed external boundary and its actual ABI.
 fixtures=(
  [(0x4c7900,2,0,'images'),(0x4c7fa0,1,0,'hit-callback'),
   (0x4cd800,2,0,'ground-placement'),(0x4c79e0,2,0,'animation'),
   (0x4bc110,0,0,'engine-refresh'),(0x41f990,0,0,'frame-resources'),
   (0x41fc30,0,0,'frame-update'),(0x4cd740,2,1,'ground-query')]
  if old else
  [(0x4c6d60,2,0,'images'),(0x4c7730,1,0,'hit-callback'),
   (0x4ce420,2,0,'ground-placement'),(0x4c6e40,2,0,'animation'),
   (0x4e0aa0,0,0,'engine-refresh'),(0x420c70,0,0,'frame-resources'),
   (0x420f10,0,0,'frame-update'),(0x4ce360,2,1,'ground-query')])
 specs={a:(argc,value,name) for a,argc,value,name in fixtures}
 specs[mode]=(0,0,'single-player-mode')
 calls=[]
 def external(machine,address):
  assert address in specs,hex(address)
  argc,value,name=specs[address];calls.append(name)
  machine.return_from_external(value,argc*4)
 m.on_external=external
 for a in specs:
  if a!=mode:m.intercept(a)
 try:
  result=m.call(c['callback'],arguments=(ACTOR,))
  assert result.completed and result.eax==1
 finally:m.release_intercepts();m.on_external=None
 values=m.words(PRIVATE,78)
 expected=(3 if old else 7) if difficulty==0 else 9
 assert values[31]==expected
 assert [values[i] for i in (18,28,29,30)]==([100,10,5,3] if difficulty==0 else [100,50,40,20])
 return dict(completed=True,health=values[18],pistol=values[28],magic=values[29],dynamite=values[30],lives_including_current=values[31],fixture_calls=calls)

def profile_defaults(m,c,easy):
 old=m.program.name=='claw-v1.0'
 profile,name,app=THIS,THIS+0xc000,THIS+0xd000
 m.write(THIS,b'\0'*0x10000);m.write(name,b'Player\0')
 init=0x49a5a0 if old else 0x49dfa0
 result=m.call(init,ecx=profile,arguments=(name,0,0,4 if easy else 0))
 assert result.completed and result.eax==1
 payload=m.read(profile+4,0x2644)
 # Select this freshly constructed profile using the original selector;
 # no input device is installed, so no keyboard import is needed.
 write(m,0x537204 if old else 0x535918,0)
 select=0x42bf90 if old else 0x42db50
 assert m.call(select,ecx=app,arguments=(profile,)).completed
 assert m.words(c['difficulty'],1)[0]==easy
 return dict(constructor=hex(init),selector=hex(select),easy=easy,flags=m.words(profile+4,1)[0],selected_level=m.words(profile+8,1)[0],serialized_bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())

def shipped_defaults():
 import zlib
 manifest=json.loads((ROOT/'work/v13/rez-manifests.json').read_text())
 # Both archive identities are pinned independently of that manifest.
 expected={'v10':'b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596','v13':'2f9fed9b5bc7d027d2c724e458baf2493a37f3f563135b99fd79d3c509bd4788'}
 maps={};raws={}
 for v in ('v10','v13'):
  source=ROOT/manifest[v]['path']
  with source.open('rb') as stream:
   assert hashlib.file_digest(stream,'sha256').hexdigest()==expected[v]
   for path,record in manifest[v]['files'].items():
    if not path.endswith('.WWD'):continue
    stream.seek(record['offset']);raw=stream.read(record['size'])
    assert hashlib.sha256(raw).hexdigest()==record['sha256']
    if v=='v10':raws[path]=raw
    else:assert raws[path]==raw
    if v=='v13':continue
    data=raw[:1524]+zlib.decompress(raw[1524:])
    u32=lambda off:struct.unpack_from('<I',data,off)[0]
    objects=[]
    for plane in range(u32(732)):
     p=u32(736)+plane*160;cursor=u32(p+140)
     for _ in range(u32(p+128)):
      lengths=struct.unpack_from('<4I',data,cursor+4);pos=cursor+284;text=[]
      for length in lengths:text.append(data[pos:pos+length].decode('ascii'));pos+=length
      if text[1].startswith(('Aquatis','Gabriel','Raux','Marrow','Wolvington','Omar','RedTail','Katherine')):
       objects.append(dict(id=u32(cursor),logic=text[1],expanded_offset=hex(cursor),damage=u32(cursor+160),health=u32(cursor+168)))
      cursor=pos
    if objects:maps[path]=dict(sha256=record['sha256'],objects=objects)
 assert len(raws)==14
 files=[]
 for source in sorted((ROOT/'Original').rglob('*')):
  if source.is_file() and source.suffix.lower() in ('.ini','.reg','.cfg'):
   raw=source.read_bytes()
   # Distribution configs contain no lives/health/damage/difficulty override.
   relevant=[line for line in raw.decode('latin1').splitlines() if any(key in line.lower() for key in ['lives','health','damage','difficulty','easy mode'])]
   assert not relevant,(source,relevant)
   files.append(dict(path=str(source.relative_to(ROOT)),sha256=hashlib.sha256(raw).hexdigest(),relevant_settings=relevant))
 return dict(archives=expected,identical_worlds=14,boss_map_records=maps,config_files=files)

def main():
 guard(); report={'scope':'Original-instruction observations, not family admission or full UI replay','profiles':{},'contact':[],'attacks':[]}
 machines={}
 for v,c in PROFILES.items():
  m=Machine(c['program'](),THIS,0x10000);machines[v]=m
  report['profiles'][v]={'program_sha256':m.program.sha256,'new_game':[new_game(Machine(m.program,THIS,0x10000),c,d) for d in (0,1)],'complete_state0':[full_state0(Machine(m.program,THIS,0x10000),c,d) for d in (0,1)],'profile_defaults':[profile_defaults(Machine(m.program,THIS,0x10000),c,d) for d in (0,1)]}
  assert m.call(c['normal_scale']).completed
  assert struct.unpack('<2f',m.read(c['scale'],8))==(1.,1.)
 for name,level,old,new,left,right in CONTACT:
  row=dict(name=name,level=level)
  for v,entry,want in [('v10',old,left),('v13',new,right)]:
   m=machines[v];c=PROFILES[v]
   row[v]=scalar(m,c,entry,want)
   health_entry=({8:(0x443ab0,0x444f40),13:(0x47ff90,0x482860)}[level][v=='v13'] if 'inherited' in name else entry)
   row[v]['health']=scalar(m,c,health_entry,100,field=c['health'])
  report['contact'].append(row)
 for name,level,old,new,left,right,kind in ATTACKS:
  row=dict(name=name,level=level)
  for v,entry,want in [('v10',old,left),('v13',new,right)]:
   row[v]=scalar(machines[v],PROFILES[v],entry,want,kind)
   if kind=='default':row[v]['nonzero_preserved']=scalar(machines[v],PROFILES[v],entry,7,kind,initial=7)
  report['attacks'].append(row)
 assert report['profiles']['v10']['profile_defaults'][0]['sha256']==report['profiles']['v13']['profile_defaults'][0]['sha256']
 assert report['profiles']['v10']['profile_defaults'][1]['sha256']==report['profiles']['v13']['profile_defaults'][1]['sha256']
 report['shipped_defaults']=shipped_defaults()
 for v,c in PROFILES.items():
  addresses=[0x527130,0x527134,0x527138] if v=='v10' else [0x5253cc,0x5253d0,0x5253d4]
  report['profiles'][v]['registry_factor_defaults']=[dict(address=hex(a),value=machines[v].words(a,1)[0]) for a in addresses]
  assert [r['value'] for r in report['profiles'][v]['registry_factor_defaults']]==[500,500,200]
 report['probe_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 report['status']='pass'
 out=ROOT/'work/v13/lives-boss-damage-oracle.json';out.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'status':'pass','output':str(out),'contact_rows':len(CONTACT),'attack_rows':len(ATTACKS),'new_game_profiles':4,'complete_initializations':4,'identical_worlds':14}))
if __name__=='__main__':main()
