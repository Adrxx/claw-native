"""Explicit optional source capability preserves independently compared ABIs."""
import copy
import ctypes as C
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from .. import build, runner
from ..cases import compiler_contract_errors
from ..env import Env, NativeHost, NativeSourceContext, U32
from ..kernel import ContextFault
from .source_context import context, program

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent


def checks(flavor='O2'):
    found = {}
    directory = ROOT / 'work/pilot/optional_source_selftest'
    directory.mkdir(parents=True, exist_ok=True)
    relative = str(directory.relative_to(ROOT))
    source = directory/'Module.cpp'
    source.write_text((HERE/'optional_source_module.cpp').read_text())
    cases = directory/'cases.py'
    cases.write_text('''from clawparity.cases import Case
from clawparity.selftest.source_context import context

def cases(random_source):
    for value in (0,1,0xffffffff,0x12345678):
        yield Case('ordinary'+str(value),0x401320,arguments=(value,0xabcdef01))
        for f in (0x401320,0x401330):
            yield Case('source'+str(f)+str(value),f,setup=lambda env,f=f,value=value:context(function=f,ebp=value),
                arguments=(value,0xabcdef01),source_context=lambda x:x,source_return_pc=0x401080)
'''.replace('clawparity', __package__.rsplit('.selftest', 1)[0]))
    spec = dict(schema=1,id='optional_source_selftest',title='Synthetic optional source capability',
        abi='canonical',program='ordinary-source-synthetic',sources=[relative+'/Module.cpp'],
        owned=[dict(address=hex(f),interval_end=hex(f+n),convention=convention,argc=2,returns='u32',
                    source_context=dict(input_mask=0x7ff,output_mask=0x7ff,preserve_mask=0x472,
                                        **({'optional':True} if f==0x401320 else {})))
               for f,n,convention in ((0x401320,5,'cdecl'),(0x401330,7,'stdcall'))],
        callees={},oracle=dict(kind='clawparity',cases=relative+'/cases.py',entry='claw_optional_source_entry'),
        evidence=dict(level='none'),integration=dict(level='source-only'))
    path=directory/'family.json';path.write_text(json.dumps(spec))
    found['schema_optional_bool'] = not compiler_contract_errors(spec)
    bad=copy.deepcopy(spec);bad['owned'][0]['source_context']['optional']=1
    found['schema_reject_integer'] = bool(compiler_contract_errors(bad))
    bad=copy.deepcopy(spec);bad['owned'][0]['convention']='fastcall'
    found['schema_reject_optional_fastcall'] = bool(compiler_contract_errors(bad))
    sys.path.insert(0, str(ROOT))
    try:
        from tools.claw import gen_project, skeleton, manifest
    finally:
        sys.path.pop(0)
    found['complete_manifest_schema'] = not manifest.validate(spec)
    admitted=copy.deepcopy(spec);admitted['evidence']['level']='admitted'
    with patch.object(gen_project,'checked_source',side_effect=lambda p, *, root=None:p):
        registry=gen_project.canonical_inventory([admitted],[])[2]
    found['registry_preserves_optional'] = registry[0]['source_context']['optional'] is True
    with tempfile.TemporaryDirectory(dir=directory,prefix='skeleton-') as scratch:
        scratch=Path(scratch);draft=copy.deepcopy(spec)
        draft['sources']=[str((scratch/'Stub.cpp').relative_to(ROOT))]
        draft['oracle']['cases']=str((scratch/'cases.py').relative_to(ROOT))
        draft_path=scratch/'family.json';draft_path.write_text(json.dumps(draft))
        skeleton.generate(draft_path)
        generated=(scratch/'Stub.cpp').read_text()
        found['skeleton_explicit_dual_mode'] = 'CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(' in generated
        found['skeleton_required_entry_strict'] = 'case 0x401330: return false;' in generated
        build.library('optional-source-skeleton-'+flavor,[scratch/'Stub.cpp'],flavor)
        found['skeleton_compiles'] = True
    result=runner.run(path,flavor=flavor,trace=True)
    found['both_modes_and_required_entry'] = result['status']=='pass' and result['cases']==12
    found['full_synthetic_coverage'] = all(x['fraction']==1 for x in result.get('coverage',{}).values()) and bool(result.get('coverage'))
    original=runner.run(path,original_only=True)
    found['blind_original_modes'] = original['status']=='pass' and original['cases']==12
    library=C.CDLL(str(build.library('optional-source-'+flavor,[source],flavor)))
    entry=library.claw_optional_source_entry
    entry.argtypes=[U32,U32,C.POINTER(U32),U32,C.POINTER(NativeHost),C.POINTER(U32)];entry.restype=U32
    for function, source_state, pc, label in (
        (0x401330,None,0,'required_absent'),
        (0x401320,None,0x401080,'pc_without_context'),
        (0x401320,context(function=0x401320),0,'context_without_pc')):
        env=Env(program());env._begin_case(None);env._freeze()
        try:
            outcome=env.run_native(entry,function,0,(11,22),source_context=source_state,source_return_pc=pc)
            found['reject_'+label]=not outcome.completed and outcome.fault == 5
        except ContextFault:
            found['reject_'+label]=True
    # Missing source must not silently discard live operands in the runner.
    cases.write_text("from clawparity.cases import Case\ndef cases(random_source):\n    yield Case('missing',0x401320,arguments=(1,2),source_return_pc=0x401080)\n".replace('clawparity', __package__.rsplit('.selftest', 1)[0]))
    result=runner.run(path,flavor=flavor)
    found['runner_reject_incomplete'] = result['status']=='fail' and result['failures'][0]['kind']=='harness'
    return found


def sanitized_checks():
    command,environ=build.sanitized_python()
    if command is None:
        return dict(passed=False,error='sanitizer unavailable')
    result=subprocess.run(command+['-m',__name__,'--sanitized-child'],env=environ,capture_output=True,text=True)
    try:
        report=json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError,IndexError):
        report=dict(passed=False)
    return dict(**report,returncode=result.returncode,stderr=result.stderr[-2000:],
                sanitizer_ok=result.returncode==0 and report.get('passed',False))


if __name__=='__main__':
    found=checks('sanitize' if '--sanitized-child' in sys.argv else 'O2')
    failed=[name for name,passed in found.items() if not passed]
    print(json.dumps(dict(checked=len(found),failed=failed,passed=not failed)))
    raise SystemExit(bool(failed))
