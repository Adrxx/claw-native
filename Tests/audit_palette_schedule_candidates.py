"""Bounded field/caller audit, using the saved private Ghidra function manifest.
This is not a proof that no indirect/computed write can exist.
"""
from pathlib import Path
import hashlib,json,re,struct
from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_AC_WRITE
from capstone.x86 import X86_OP_MEM,X86_REG_ESP
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/palette-fade-setup-agent'
b=(ROOT/'Original/claw10/CLAW.EXE').read_bytes();assert hashlib.sha256(b).hexdigest()=='350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'
pe=struct.unpack_from('<I',b,60)[0];n=struct.unpack_from('<H',b,pe+6)[0];opt=struct.unpack_from('<H',b,pe+20)[0];sections=[]
for i in range(n):
 o=pe+24+opt+40*i;size,va,rawsize,offset=struct.unpack_from('<4I',b,o+8);sections.append((0x400000+va,rawsize,offset))
def raw(start,end):
 for va,n,o in sections:
  if va<=start and end<va+n:return b[o+start-va:o+end-va+1]
 return b''
manifest=(WORK/'callers-and-functions.txt').read_text();functions=[]
for line in manifest.split('FUNCTIONS\n')[1].splitlines():
 m=re.match(r'^([0-9a-f]{8}) ([0-9a-f]{8}) (.+)$',line)
 if m:functions.append((int(m[1],16),int(m[2],16),m[3]))
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True;field34=[];candidates=[];paletteWrites=[]
for start,end,name in functions:
 bybase={};allstores=[]
 for ins in md.disasm(raw(start,end),start):
  for operand in ins.operands:
   if operand.type!=X86_OP_MEM or not(operand.access&CS_AC_WRITE)or operand.mem.base==X86_REG_ESP:continue
   row={'address':hex(ins.address),'function':hex(start),'name':name,'instruction':ins.mnemonic+' '+ins.op_str,'base':ins.reg_name(operand.mem.base),'offset':operand.mem.disp,'indexed':bool(operand.mem.index),'bytes':operand.size};allstores.append(row);bybase.setdefault(operand.mem.base,set()).add(operand.mem.disp)
   if operand.mem.disp==52 and operand.size==4:field34.append(row)
   if 0x4bb000<=ins.address<0x4bc000 and operand.mem.disp in(20,24,28,32,36,40,44,48,52):paletteWrites.append(row)
 for base,offsets in bybase.items():
  if 52 in offsets and len(offsets&{20,24,28,32,36,52})>=4:candidates.append({'function':hex(start),'name':name,'base':md.reg_name(base),'offsets':sorted(offsets),'stores':[r for r in allstores if r['base']==md.reg_name(base)and r['offset']in(20,24,28,32,36,52)]})
candidateStarts={int(c['function'],16)for c in candidates};clock=[]
for line in(ROOT/'work/v10-disassembly.txt').read_text().splitlines():
 if 'call'not in line or '[0x546df0]'not in line:continue
 addr=int(line.split(':')[0],16);owner=next((a for a,b,_ in functions if a<=addr<=b),None);clock.append({'instruction':line.strip(),'owner':hex(owner)if owner else None,'candidate':owner in candidateStarts})
report={'scope':'Ghidra-discovered function spans only; bounded field/caller evidence, not proof no possible computed write exists','function_count':len(functions),'field34_writes':field34,'scheduler_field_cluster_candidates':candidates,'palette_region_field_writes':paletteWrites,'timeGetTime_direct_calls':clock,'setup_cluster_timeGetTime_overlap':[c for c in clock if c['candidate']]};(WORK/'field-write-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('AUDIT',len(functions),'discovered functions;',len(field34),'non-ESP field34 writes;',len(candidates),'broad candidates;',len(clock),'direct clock calls;',len(report['setup_cluster_timeGetTime_overlap']),'candidate clock overlaps')
