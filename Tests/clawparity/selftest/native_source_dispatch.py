"""Synthetic generator contract checks; no game sources or derived instructions."""
import json
import subprocess
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch


def checks():
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    try:
        from tools.claw import gen_project
    finally:
        sys.path.pop(0)
    manifests=[]
    for index, (convention, contract) in enumerate((
        ('compiler-context', {'compiler_context':dict(input_mask=2047,output_mask=2047)}),
        ('cdecl', {'source_context':dict(input_mask=2047,output_mask=1523,preserve_mask=1138)}),
        ('cdecl', {'source_context':dict(input_mask=2047,output_mask=1523,preserve_mask=1138,optional=True)}),
        ('cdecl', {}))):
        name='synthetic_'+str(index)
        manifests.append(dict(id=name,abi='canonical',sources=['Sources/Synthetic'+str(index)+'.cpp'],
            owned=[dict(address=hex(0x401000+index*0x100),convention=convention,argc=0,
                        returns='context' if index==0 else 'u32',**contract)],
            evidence=dict(level='admitted'),oracle=dict(kind='clawparity',entry='claw_'+name+'_entry')))
    with patch.object(gen_project,'checked_source',side_effect=lambda path, *, root=None:path):
        rows=gen_project.canonical_inventory(manifests,[])[2]
    assert rows[0]['compiler_context']==dict(input_mask=2047,output_mask=2047)
    assert rows[2]['source_context']['optional'] is True
    with tempfile.TemporaryDirectory(dir=gen_project.ROOT/'work',prefix='native-source-dispatch-') as tmp:
        tmp=Path(tmp)
        (tmp/'dispatch.h').write_text(gen_project.canonical_dispatch_text(rows))
        declarations='\n'.join('uint32_t claw_synthetic_'+str(i)+'_entry(uint32_t f,uint32_t r,const uint32_t*a,uint32_t n,ClawHost*h,uint32_t*out){calls++;*out=123;return 1;}' for i in range(4))
        (tmp/'main.c').write_text('''#include "dispatch.h"
#include <assert.h>
static unsigned calls;
'''+declarations+'''
int main(void) {
 ClawCall c={0};ClawHost h={0};ClawCompilerContext k={0};ClawSourceContext s={0};
 uint32_t out=77;uint64_t budget=100;
 assert(claw_canonical_lookup(0x401000)->compilerCapability==1);
 assert(claw_canonical_lookup(0x401000)->compilerInputMask==2047);
 assert(claw_canonical_lookup(0x401000)->compilerOutputMask==2047);
 assert(claw_canonical_lookup(0x401100)->sourceCapability==1);
 assert(claw_canonical_lookup(0x401200)->sourceCapability==2);
 c.function=0x401000;assert(!claw_canonical_dispatch(&c,&h,&out)&&!calls&&out==77);
 h.fault=0;c.function=0x401100;assert(!claw_canonical_dispatch(&c,&h,&out)&&!calls);
 h.fault=0;c.function=0x401200;assert(claw_canonical_dispatch(&c,&h,&out)&&calls==1);
 calls=0;out=77;c.function=0x401000;h.remainingOperations=&budget;
 h.entryStackPointer=c.stackPointer=k.esp=CLAW_STACK_TOP;k.inputMask=k.outputMask=2047;
 h.compilerContext=c.compilerContext=&k;
 assert(claw_canonical_dispatch_context(&c,&h,CLAW_CANONICAL_COMPILER_GRAPH,&out)&&calls==1&&out==123);
 calls=0;out=77;k.inputMask=2046;
 assert(!claw_canonical_dispatch_context(&c,&h,2,&out)&&!calls&&out==77);
 h.fault=0;k.inputMask=2047;h.sourceContext=&s;
 assert(!claw_canonical_dispatch_context(&c,&h,2,&out)&&!calls);
 h.fault=0;h.sourceContext=0;c.sourceContext=&s;
 assert(!claw_canonical_dispatch_context(&c,&h,2,&out)&&!calls);
 h.fault=0;c.sourceContext=0;h.compilerContext=0;
 assert(!claw_canonical_dispatch_context(&c,&h,2,&out)&&!calls);
 h.fault=0;h.compilerContext=&k;
 assert(!claw_canonical_dispatch_context(&c,&h,99,&out)&&!calls);
 h.fault=0;c.function=0x401300;
 assert(!claw_canonical_dispatch_context(&c,&h,2,&out)&&!calls);
 h.fault=0;c.function=0x401000;c.receiver2=1;
 assert(!claw_canonical_dispatch_context(&c,&h,2,&out)&&!calls);
 h.fault=0;c.receiver2=0;c.x87ArgumentCount=1;
 assert(!claw_canonical_dispatch_context(&c,&h,2,&out)&&!calls);
 h.fault=0;c.x87ArgumentCount=0;h.remainingOperations=0;
 assert(!claw_canonical_dispatch_context(&c,&h,2,&out)&&!calls);
 h.fault=0;h.remainingOperations=&budget;c.compilerContext=0;h.compilerContext=0;
 c.function=0x401100;h.sourceContext=c.sourceContext=&s;
 h.sourceReturnPC=c.sourceReturnPC=0x401080;s.esp=CLAW_STACK_TOP;
 s.inputMask=2047;s.outputMask=1523;s.preserveMask=1138;
 assert(claw_canonical_dispatch_context(&c,&h,1,&out)&&calls==1);
 calls=0;out=77;c.function=0x401200;
 assert(claw_canonical_dispatch_context(&c,&h,1,&out)&&calls==1);
 calls=0;out=77;
 assert(!claw_canonical_dispatch(&c,&h,&out)&&!calls);
 h.fault=0;s.preserveMask=0;
 assert(!claw_canonical_dispatch_context(&c,&h,1,&out)&&!calls);
 h.fault=0;s.preserveMask=1138;c.function=0x401300;
 assert(!claw_canonical_dispatch_context(&c,&h,1,&out)&&!calls);
 h.fault=0;c.function=0x401100;h.sourceReturnPC=0;
 assert(!claw_canonical_dispatch_context(&c,&h,1,&out)&&!calls);
 h.faultAddress=0x123456;assert(!claw_canonical_dispatch_context(&c,&h,1,&out)&&h.faultAddress==0x123456&&!calls);
 return 0;
}
''')
        for language,standard in (('c','c11'),('c++','c++17')):
            binary=tmp/('test-'+language)
            subprocess.run(['xcrun','clang++' if language=='c++' else 'clang','-x',language,'-std='+standard,
                '-I',str(gen_project.ROOT/'Sources'),str(tmp/'main.c'),'-o',str(binary)],check=True)
            subprocess.run([str(binary)],check=True)
    return dict(metadata=True,c_dispatch=True,cpp_dispatch=True)

if __name__=='__main__':
    result=checks()
    print(json.dumps(dict(checked=len(result),passed=all(result.values()))))
