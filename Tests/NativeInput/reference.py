"""Fresh original-only sparse input outputs and an exact mouse-call trace."""
from pathlib import Path
import json,sys
from Tests.clawparity.program import claw
from Tests.clawparity.env import Env

def probe(function,size,mouse=False):
    env=Env(claw()); token=env.object(size,'input',fill=0xa5);events=[]
    if mouse:
        for offset,value in ((0x1cc,4),(0x1d0,0),(0x20c,0),(0x230,10),(0x234,0),(0x238,6),(0x23c,6),(0x240,320),(0x244,240)):
            env.put(token+offset,value)
        def service(owner,call):
            events.append({'function':call.function,'arguments':list(call.arguments),'stackPointer':call.stack_pointer})
            if call.function==0x546cd0:owner.put(call.arguments[0],300,400);return 1
            if call.function==0x546d9c:return 1
            return 0
        env.fixture(0x546cd0,'stdcall',1,service,arguments=('out:8',))
        env.fixture(0x546ce4,'stdcall',1,service)
        env.fixture(0x546d9c,'stdcall',2,service)
    before=env.read(token,size).hex();env._freeze()
    side=env.run_original(function,token,(),check_objects=True)
    assert side.completed and not side.errors
    return {'function':function,'before':before,'after':env.machine.read(token,size).hex(),'events':events,'rawEAX':side.eax}
rows=[probe(0x4b3410,584),probe(0x430d30,144),probe(0x430d80,144),probe(0x4b3490,584,True)]
Path(sys.argv[1]).write_text(json.dumps(rows,indent=2)+'\n')
