"""Finite display probes. No original game writes; calls original setting owner."""
import json, hashlib, sys
sys.path.insert(0,str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from pathlib import Path
from PIL import Image
from Tests.clawparity.program import claw
from Tests.NativeEndOfLevel.trace import EndOfLevelTrace
from unicorn.x86_const import UC_X86_REG_ESP
LOW='--low-detail' in sys.argv
OUT=Path('work/parity-display') / ('low-detail' if LOW else ''); OUT.mkdir(parents=True,exist_ok=True)
class Probe(EndOfLevelTrace):
 def setup_navigation(self,app):
  super().setup_navigation(app)
  self.menu_rows=[]
  # IFC commands from CLAW.IFC, executed by the original Display handler.
  # Full original GDI menu painting is outside this probe; app keys are real.
  menu=self.word(app+0x2c)
  route=[('detail-default',None),('detail-off',0x34be),('detail-on',0x34be),('front-off',0x34bf),('front-on',0x34bf),('movies-on',0x34c1),('movies-off',0x34c1)]
  for label,command in route:
   if command is not None:self.run(0x45cb90,menu,(command,),phase=label)
   self.menu_rows.append(dict(mark=label,settings={hex(o):self.word(app+o) for o in (0x68,0x120,0x124,0x128)}))
   if LOW and label=='detail-on':self.run(0x45cb90,menu,(0x34be,),phase='low-detail')
 def end_of_level(self,app):
  self.rows=[]; self.clock_step=0
  self.frame(app,'baseline')
  state=self.word(app+0x2c);parent=self.word(state+0xc)
  node=self.word(self.word(parent+8)+0x14);tagged=hidden=0;seen=set()
  while node and node not in seen:
   seen.add(node);entity=self.word(node+8)
   if entity and self.word(entity+0x164)&0x2000:
    tagged+=1;hidden+=bool(self.word(entity+8)&0x10000)
   node=self.word(node)
  self.detail_entities=dict(tagged=tagged,hidden=hidden)
  self.front_rows=[]
  world=self.word(self.word(app+0x30)+0x24)
  for front in [0,1]:
   self.run(0x42ce20,app,(front,),phase='front-layer')
   self.frame(app,'front-layer-frame')
   flags=[self.word(self.word(self.word(world+0x38)+4*i)+8) for i in range(self.word(world+0x3c))]
   self.front_rows.append(dict(front=front,flags=flags))
   primary=next(s for s in self.com_objects.values() if s.get('caps')==0x218)
   Image.frombytes('L',(640,480),bytes(self.machine.mem_read(primary['pixels'],640*480))).save(OUT/f'original-front-{front}.png')
  for n in [10,9,8,7,6,5,4,3,2,1,0,11,10]:
   before=len(self.presentations)
   self.run(0x429ed0,app,(n,1,1),phase='layout')
   clears=len(self.presentations)-before
   self.frame(app,'layout-frame')
   primary=next(s for s in self.com_objects.values() if s.get('caps')==0x218)
   pixels=bytes(self.machine.mem_read(primary['pixels'],primary['pitch']*primary['height']))
   im=Image.frombytes('L',(640,480),pixels);im.save(OUT/f'original-layout-{n}.png')
   row=dict(requested=n,accepted=self.word(app+0x68),rect=[self.word(0x5370c8+i*4) for i in range(4)],clear_presentations=clears,pixels_sha256=hashlib.sha256(pixels).hexdigest())
   self.rows.append(row); print(json.dumps(row),flush=True)
  self.level_two_loaded=True
p=Probe(3_000_000_000,None)
p.execute()
r=dict(status='pass' if p.stop is None and len(getattr(p,'rows',[]))==13 else 'fail',original_sha256=claw().sha256,rows=getattr(p,'rows',[]),menu_rows=getattr(p,'menu_rows',[]),front_rows=getattr(p,'front_rows',[]),detail_entities=getattr(p,'detail_entities',{}),low_detail=LOW,stop=p.stop)
(OUT/'original.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
