"""Original owner-record calls; explicit unit records, no window-success fixtures."""
import json,struct,sys
from pathlib import Path
from Tests.clawparity.program import claw
from Tests.clawparity.kernel import Machine,STACK_TOP
p=claw();rows=[]
for count in (0,1,0x7fffffff,0xffffffff):
 m=Machine(p,0x64000000,0x1000);record=0x64000013;initial=bytes((i*7+19)&255 for i in range(0x284));m.write(0x64000000,initial);m.write(0x541340,struct.pack('<I',count))
 steps=[]
 for f in (0x423300,0x4b8990,0x423300):
  result=m.call(f,ecx=record,stack_pointer=STACK_TOP-0x100)
  assert result.completed and result.eax==record
  steps.append(dict(function=f,eax=result.eax,record=m.read(0x64000000,0x284).hex(),counter=m.words(0x541340,1)[0]))
 rows.append(dict(sha256=p.sha256,count=count,token=record,initial=initial.hex(),steps=steps))
out=Path(sys.argv[1]).resolve();assert Path('work').resolve() in out.parents;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rows,indent=2)+'\n');print('PASS4 fresh original outer-owner unit profiles12sourcecalls')
