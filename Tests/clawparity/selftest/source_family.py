"""Source capability schema, runner and generated dispatch foundation regressions."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

from .. import build, runner
from ..cases import Case, compiler_contract_errors
from ..kernel import CONTEXT_ALL, SOURCE_PRESERVABLE
from .source_context import program

ROOT = Path(__file__).resolve().parents[3]


def prepare():
    directory = ROOT / 'work/pilot/source_family_selftest'
    directory.mkdir(parents=True, exist_ok=True)
    relative = str(directory.relative_to(ROOT))
    (directory / 'Module.cpp').write_text(Path(__file__).with_name('source_context_module.cpp').read_text())
    (directory / 'cases.py').write_text('''from Tests.clawparity.cases import Case
from Tests.clawparity.selftest.source_context import context, callback

def cases(random_source):
    for ebp in (0, 1, 0xffffffff, 0x12345678):
        def setup(env, ebp=ebp):
            env.override(0x401200, callback)
            return context(ebp=ebp)
        yield Case(str(ebp), 0x401000, setup=setup, source_context=lambda x:x, source_return_pc=0x401080)
'''.replace('Tests.clawparity', __package__.rsplit('.selftest', 1)[0]))
    # Length is derived from the synthetic authored caller, never original bytes.
    end = 0x40101e
    spec = {'schema':1, 'id':'source_family_selftest', 'title':'Synthetic ordinary source graph', 'abi':'canonical',
        'program':'ordinary-source-synthetic', 'sources':[relative+'/Module.cpp'],
        'owned':[{'address':'0x401000', 'interval_end':hex(end), 'convention':'cdecl', 'argc':0, 'returns':'u32',
                  'source_context':{'input_mask':CONTEXT_ALL, 'output_mask':CONTEXT_ALL, 'preserve_mask':SOURCE_PRESERVABLE}}],
        'callees':{'0x401100':{'kind':'whole','convention':'compiler-context','argc':0,'returns':'context',
                             'compiler_context':{'input_mask':CONTEXT_ALL,'output_mask':CONTEXT_ALL}},
                   '0x401200':{'kind':'fixture','convention':'cdecl','argc':1,'returns':'u32','fixture':'scripted'}},
        'oracle':{'kind':'clawparity','cases':relative+'/cases.py','entry':'claw_source_context_selftest_entry'},
        'evidence':{'level':'none'},'integration':{'level':'source-only'}}
    path = directory/'family.json'; path.write_text(json.dumps(spec,indent=2)+'\n')
    return path, spec


def checks():
    from tools.claw import gen_project, manifest, skeleton
    path, spec = prepare()
    marker = object()
    found = {'schema':not manifest.validate(spec),
             'legacy_case_positional_context':Case('legacy', 0, None, 0, (), None, 'return', (), marker).compiler_context is marker}
    for flavor in ('O0','O2'):
        result = runner.run(path,flavor=flavor,trace=True)
        found['runner_'+flavor] = result['status']=='pass'
    result = runner.run(path,original_only=True,trace=True)
    found['source_cases_coverage'] = result['status']=='pass' and result['coverage']['0x401000']['fraction']==1
    text = (path.parent/'Module.cpp').read_text()
    for label, old, new in (
        ('real_pc','0x40100f, child','0x401010, child'),
        ('stack_word','run.put(s.esp, s.ebp);','run.put(s.esp, s.ebp ^ 1u);'),
        ('preserved','s.ebp = run.get(s.esp);','s.ebp = run.get(s.esp) ^ 1u;'),
        ('context_output','return value;','return value ^ 1u;')):
        variant = path.parent/(label+'.cpp');variant.write_text(text.replace(old,new))
        bad = runner.run(path,module_source=variant)
        found['reject_'+label] = bad['status']=='fail' and bool(bad.get('failures'))
    halted_spec = copy.deepcopy(spec)
    halted_cases = path.parent/'halted_cases.py'
    halted_cases.write_text((path.parent/'cases.py').read_text().replace('context, callback', 'context, halt_callback as callback')
                           .replace('source_return_pc=0x401080)', 'source_return_pc=0x401080, expect="halt")'))
    halted_spec['oracle']['cases'] = str(halted_cases.relative_to(ROOT))
    halted_path = path.parent/'halted.json'; halted_path.write_text(json.dumps(halted_spec))
    found['physical_halt_runner'] = runner.run(halted_path)['status']=='pass'
    found['physical_halt_cases'] = runner.run(halted_path, original_only=True)['status']=='pass'
    for label, replacement in {
        'memory_safety': 'run.fail(CLAW_FAULT_MEMORY);',
        'abi_safety': 'run.fail(CLAW_FAULT_ABI);',
        'budget_safety': 'run.fail(CLAW_FAULT_BUDGET);',
        'fake_halt': 'run.fail(CLAW_FAULT_HALT);',
        'physical_register': 'child.eax ^= 1;',
        'missing_physical_inputs': 'child.inputMask &= ~CLAW_CONTEXT_EDX;',
        'halt_header': 's.reserved0 = 1;',
    }.items():
        bad = path.parent/('halt_'+label+'.cpp')
        bad.write_text(text.replace('    uint32_t value = run.source_call(', '    '+replacement+'\n    uint32_t value = run.source_call('))
        result = runner.run(halted_path,module_source=bad)
        found['halt_reject_'+label] = result['status']=='fail'
        if label == 'physical_register':
            found['halt_register_snapshot_observable'] = any('physical halt state' in f.get('detail','') for f in result.get('failures',[]))
    wrong_pc = runner.run(halted_path,module_source=path.parent/'real_pc.cpp')
    found['halt_reject_wrong_real_pc'] = wrong_pc['status']=='fail'
    invalids = []
    for field,value in [('input_mask',0),('output_mask',0),('preserve_mask',1),('input_mask',True),('output_mask',0x800)]:
        invalid = copy.deepcopy(spec);invalid['owned'][0]['source_context'][field]=value;invalids.append(invalid)
    invalid = copy.deepcopy(spec);invalid['callees']['0x401100']['kind']='fixture';invalids.append(invalid)
    invalid = copy.deepcopy(spec);invalid['callees']['0x401100']['compiler_context']['input_mask']=0;invalids.append(invalid)
    invalid = copy.deepcopy(spec);invalid['owned'][0]['compiler_context']={'input_mask':2047,'output_mask':2047};invalids.append(invalid)
    for index,invalid in enumerate(invalids): found['invalid_schema_'+str(index)] = bool(compiler_contract_errors(invalid))
    with tempfile.TemporaryDirectory(dir=ROOT/'work/pilot',prefix='source-generators-') as temporary:
        temporary=Path(temporary)
        generated=copy.deepcopy(spec)
        generated['sources']=[str((temporary/'Stub.cpp').relative_to(ROOT))]
        generated['oracle']['cases']=str((temporary/'cases.py').relative_to(ROOT))
        generated_path=temporary/'family.json';generated_path.write_text(json.dumps(generated))
        skeleton.generate(generated_path)
        source=temporary/'Stub.cpp'
        found['skeleton_source_contract'] = 'CLAW_SOURCE_MODULE_ENTRY(' in source.read_text() and 'ClawSourceContract' in source.read_text()
        build.library('source-family-skeleton',[source])
        found['skeleton_compiles']=True
        admitted=copy.deepcopy(spec);admitted['sources']=['Sources/SyntheticSourceFamily.cpp'];admitted['evidence']['level']='admitted'
        with patch.object(gen_project,'checked_source',side_effect=lambda path, *, root=None:path):
            registry=gen_project.canonical_inventory([admitted],[])[2]
        found['registry_source_metadata']=registry[0]['source_context']==spec['owned'][0]['source_context']
        ordinary=dict(registry[0],address=0x401200,entry='claw_ordinary_entry');ordinary.pop('source_context')
        (temporary/'dispatch.h').write_text(gen_project.canonical_dispatch_text(registry+[ordinary]))
        c=temporary/'dispatch.c'
        c.write_text('''#include "dispatch.h"
#include <assert.h>
static unsigned calls;
uint32_t claw_source_context_selftest_entry(uint32_t f,uint32_t r,const uint32_t*a,uint32_t n,ClawHost*h,uint32_t*out){calls++;*out=1;return 1;}
uint32_t claw_ordinary_entry(uint32_t f,uint32_t r,const uint32_t*a,uint32_t n,ClawHost*h,uint32_t*out){calls++;*out=1;return 1;}
int main(void){
 ClawCall c={0};ClawHost h={0};ClawSourceContext s={0};uint32_t out=77;
 assert(claw_canonical_lookup(0x401000)->sourceCapability==1);
 assert(claw_canonical_lookup(0x401000)->sourceInputMask==2047);
 assert(claw_canonical_lookup(0x401000)->sourceOutputMask==2047);
 assert(claw_canonical_lookup(0x401000)->sourcePreserveMask==1138);
 c.function=0x401000;assert(!claw_canonical_dispatch(&c,&h,&out));assert(h.fault==5&&out==77&&!calls);
 c.function=0x401200;
 h.fault=0;c.sourceContext=&s;assert(!claw_canonical_dispatch(&c,&h,&out));
 h.fault=0;c.sourceContext=0;c.sourceReturnPC=0x401080;assert(!claw_canonical_dispatch(&c,&h,&out));
 h.fault=0;c.sourceReturnPC=0;h.sourceContext=&s;assert(!claw_canonical_dispatch(&c,&h,&out));
 h.fault=0;h.sourceContext=0;h.sourceReturnPC=0x401080;assert(!claw_canonical_dispatch(&c,&h,&out));
 assert(out==77&&!calls);h.fault=0;h.sourceReturnPC=0;
 assert(claw_canonical_dispatch(&c,&h,&out));assert(out==1&&calls==1);return 0;
}
''')
        binary=temporary/'dispatch'
        subprocess.run(build.compiler()+['-x','c','-std=c11','-I',str(ROOT/'Sources'),str(c),'-o',str(binary)],check=True,capture_output=True)
        subprocess.run([str(binary)],check=True,capture_output=True)
        found['dispatch_rejects_source_capability']=True
    return found


if __name__=='__main__':
    result=checks();failed=[k for k,v in result.items() if not v]
    print(json.dumps({'checked':len(result),'failed':failed,'passed':not failed}))
    raise SystemExit(bool(failed))
