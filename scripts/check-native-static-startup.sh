#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
exec work/test-env/bin/python - "$@" <<'PY'
import fcntl,gzip,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
from tools.claw import gen_project
from Tests.clawparity.program import claw
root=Path.cwd(); requested=list(sys.argv[1:]);selectors=[x for x in requested if x in ('--v2','--v3','--v4','--v5','--v6','--v7','--v8','--v9')]
assert len(selectors)<=1,'select one reference version'
version=int(selectors[0][-1]) if selectors else 1
if selectors:requested.remove(selectors[0])
frozen=root/('work/native-static-startup-check/frozen-v'+str(version))
sha=lambda b:hashlib.sha256(b).hexdigest()
program=claw(); provenance_bytes=(frozen/'provenance.json').read_bytes()
if version in (3,4,5,6,7,8,9):assert sha(provenance_bytes)=={3:'c7bc36d3161026825f768d349e55616962b632158b6626fdb61c20ebf8332a15',4:'5735038a9cffa1ec467d7b379722f2b1bef85c972b8369300606d70d9fd4e86d',5:'70f08260c2103dfe0791fc6ba30cdf743ae6969129cefdc709da8b9a81bde396',6:'e78490dd06e1b85dc0ec5fdb9da674472a0da4de2183d70b465baa250385cdc9',7:'fd1ec4f31628a1304f451a1a76a4cc726caaa06c59589e5ff452a77daeb6386a',8:'61d4840bbfe6805f2be0c790fac951d7a364f13920951810e64e3db0a067a603',9:'f159f3091855fb84a194a4f77cd9508b0f38c7b6611ebefdca66989aed1e44b3'}[version],'frozen provenance drift'
provenance=json.loads(provenance_bytes)
assert provenance['programSha256']==program.sha256
archive_inputs={}
if version==7:
 archive_root=Path('work/coordination/source-fixture-original-producer-inputs')
 archive_manifest=archive_root/'manifest.json'
 archive_inputs[str(archive_manifest)]='b26bc65cb0264da04d3d45533d2ab2b89356f530b92e88ebda582d8303a216da'
 archived_producers={
  'Tests/clawparity/kernel.py':'85c31b38083e0377800acb41b16f90286e668c3ae1656d7d7d88330a8c70686b',
  'Tests/clawparity/env.py':'c824ec411b823afc2f7a77365d1db8233878b7c543b0aef1422f9e3a71d1b087'}
 for name,expected in archived_producers.items():
  assert provenance['producerHashes'].get(name)==expected,'unexpected archived original producer identity'
  archive_inputs[str(archive_root/name)]=expected
 for name,expected in archive_inputs.items():
  path=Path(name)
  assert not path.is_absolute() and '..' not in path.parts
  assert not any(Path(*path.parts[:i+1]).is_symlink() for i in range(len(path.parts))), 'archived original producer symlink'
  assert path.is_file() and path.resolve()==path.absolute() and sha(path.read_bytes())==expected,'archived original producer drift: '+name
 manifest=json.loads(archive_manifest.read_text())
 expected_rows=[dict(source_path=name,archive_path=str(archive_root/name),sha256=expected,bytes=(archive_root/name).stat().st_size) for name,expected in archived_producers.items()]
 assert type(manifest.get('schema_version')) is int and manifest['schema_version']==1 and manifest.get('archived_inputs')==expected_rows,'archived original manifest mapping'
 current=manifest.get('current_inputs');assert isinstance(current,list) and len(current)==2 and {r['path'] for r in current}==set(archived_producers),'current native input mapping'
 for row in current:
  assert set(row)=={'path','sha256','bytes'} and sha(Path(row['path']).read_bytes())==row['sha256'] and Path(row['path']).stat().st_size==row['bytes'],'current native input drift'
if version==8:
 from tools.claw.milestone import static_list_archived_producers
 archive_inputs=static_list_archived_producers(provenance,root)
if version==9:
 from tools.claw.milestone import static_final_archived_producers,validate_static_final_inputs
 archive_inputs=static_final_archived_producers(provenance,root)
for path,digest in provenance.get('producerHashes',{}).items():
 if version>=8:continue
 if version==7 and path in archived_producers:continue
 assert sha(Path(path).read_bytes())==digest,'original producer drift: '+path

profile_inventory={row['name']:row for row in provenance['profiles']}
if version==9:
 from tools.claw.static_build_inputs import load_final_build
 scoped_build=load_final_build(root);selection=scoped_build['selection']
 cpp=selection['cpp'];swift=selection['swift'];registry=selection['registry'].encode();inputs=scoped_build['inputs']
else:
 addresses={0x4a5880,0x4a3610,0x4a3560,0x4a35f0,0x4a5860,0x4a5870,0x4a7b90,0x4a7bc0,0x4a7c40,0x501fbd,0x501fc7,0x501fc8,0x50226e,0x502278,0x502279,0x502c90,0x502c9a}
 addresses.update({0x4a2cf1,0x4f5e89,0x4a2f62,0x4a48c0,0x502ca4})
 if version>=3:addresses.update({0x502876,0x502880,0x502881,0x502c51,0x502c5b,0x502c5c,0x503722,0x50372c,0x50372d,0x503748,0x503752,0x503753,0x403540,0x403550,0x403ad0})
 if version>=4:
  for wrapper in [0x403540,0x4042b0,0x4064c0,0x406e90,0x4074a0,0x408520,0x409150,0x409fe0]:addresses.update({wrapper,wrapper+0x10,wrapper+0x30})
  addresses.update({0x4dc680,0x40b820,0x40b830})
 if version==5:
  interpretation=frozen/'original-row-interpretation.json'
  assert sha(interpretation.read_bytes())=='b0bb06e5a9c234ae2e4bea3d3e354f41dc5213b6c6a73bd6cfa9e0068f63cbe2','corrected original row interpretation drift'
  corrected=json.loads(interpretation.read_text())
  assert corrected['provenanceSha256']==sha(provenance_bytes) and corrected['programSha256']==program.sha256
  for row in corrected['rows']:
   if row['index']<=34:addresses.update({row['wrapper'],row['thunk'],row['registration']})
  addresses.update({0x4251e0,0x4251f0,0x50257f,0x4f65f2,0x4f6433})
 manifest={p:p.read_bytes() for p in gen_project.FAMILIES.glob('*.json')}
 rows=gen_project.canonical_inventory([json.loads(b) for b in manifest.values()],json.loads(gen_project.EXCLUDE_FILE.read_text()))[2]
 if version>=6:
  first=provenance['profiles'][0]; data=(frozen/first['path']).read_bytes();assert sha(data)==first['sha256']
  logical=gzip.decompress(data);assert sha(logical)==first['logicalSha256'];reference=json.loads(logical)
  observed={e['function'] for e in reference['entries']}
  # This selects admitted source addresses only; the immutable original states remain comparison inputs.
  addresses.update(r['address'] for r in rows if r['family'].startswith('static_') and r['address'] in observed)
  addresses.update({0x50257f,0x503510,0x4a56e0,0x502301,0x50210b,0x4f5e89,0x4f5133,0x50228f,0x503420,0x502e47,0x502e95,0x502f05,0x50335e,0x503167,0x502fb6,0x502ff8,0x4a4a20,0x502335,0x502369,0x502f84,0x502f26,0x4a48c0,0x501f01,0x501fde,0x4f6439,0x4f6433,0x4f65f2})
  # The entry59 wrapper and thunk are needed solely for its declared pre-instruction cut.
  addresses.update({0x43d330,0x43d340})
  addresses.update({0x4f50fd,0x4a5690})
 if version>=7:
  # Explicit finite additions; missing admission fails before compilation.
  addresses.update({0x440ee0,0x4dc280,0x4dc200,0x440f30,0x453cc0,0x453d00,0x45acb0,0x4f54ea,0x4db620})
  # Entry120 wrapper/thunk only; the next body remains an observer cut.
  addresses.add(0x502405)
  addresses.update(r['address'] for r in rows if r['address'] in {0x50240a,0x4db4d0})
 if version>=8:
  addresses.update({0x4f709b,0x502d30,0x502d3a})
  list_family=json.loads(Path('Tests/families/static_list_records.json').read_text())
  whole={int(address,16) for address,meta in list_family['callees'].items() if meta['kind']=='whole'}
  assert whole=={0x4a4a20,0x4f6a9a,0x50228f,0x502e95,0x502f05,0x502f26}
  addresses.update(whole)
 if version==9:
  final_family=json.loads(Path('Tests/families/static_final_records.json').read_text())
  addresses.update(int(entry['address'],16) for entry in final_family['owned'])
  whole={int(address,16)for address,meta in final_family['callees'].items()if meta['kind']=='whole'}
  assert whole=={0x4f709b,0x50228f,0x502e95,0x502f05,0x502f26}
  addresses.update(whole)
 rows=[r for r in rows if r['address'] in addresses];assert {r['address'] for r in rows}==addresses
 registry=gen_project.canonical_dispatch_text(rows).encode()
 families={r['family'] for r in rows}; selected={p:b for p,b in manifest.items() if json.loads(b).get('id') in families}
 cpp=sorted({s for b in selected.values() for s in json.loads(b)['sources']})
 swift=['Sources/ClawTokenHeap.swift','Sources/ClawNativeCanonicalHost.swift','Sources/ClawNativeCrtMemory.swift','Sources/ClawNativeCrtServices.swift','Tests/NativeStaticStartup/main.swift']
 if version>=6:swift[1:1]=['Sources/ClawNativeMfcLocks.swift','Sources/ClawNativeMfcMemory.swift']
 paths=cpp+swift+['Tests/NativeStaticStartup/Bridge.h','scripts/check-native-static-startup.sh','tools/claw/gen_project.py']
 paths += [str(p.relative_to(root)) for p in (root/'Sources').rglob('*') if p.suffix in ('.h','.hpp') and p!=gen_project.DISPATCH_HEADER]
 if version==7:paths+=['Tests/clawparity/env.py','Tests/clawparity/kernel.py',*archive_inputs]
 if version>=8:paths+=['Tests/clawparity/env.py','Tests/clawparity/kernel.py','tools/claw/milestone.py',*archive_inputs]
 inputs={str(p.relative_to(root)):b for p,b in selected.items()};inputs.update({p:Path(p).read_bytes() for p in paths})
asan=os.environ.get('CLAW_NATIVE_ASAN','1')=='1';opt=os.environ.get('CLAW_NATIVE_OPTIMIZE','0')=='1'
get=lambda args:subprocess.check_output(args,text=True).strip()
sdk=get(['xcrun','--show-sdk-path']);clang=get(['xcrun','--find','clang++']);swiftc=get(['xcrun','--find','swiftc'])
cflags=['-std=c++17','-ffp-contract=off','-isysroot',sdk];sflags=['-sdk',sdk]
if version>=6:sflags+=['-D','STATIC_APPLICATION']
if asan:cflags+=['-fsanitize=address,undefined','-fno-omit-frame-pointer'];sflags+=['-sanitize=address']
if opt:cflags+=['-O2'];sflags+=['-O']
certificate={'inputs':{p:sha(b) for p,b in inputs.items()},'registry':sha(registry),'cflags':cflags,'sflags':sflags,'clang':get([clang,'--version']),'swift':get([swiftc,'--version']),'original':program.sha256,'reference_provenance':sha((frozen/'provenance.json').read_bytes())}
if version==9:certificate['selected_build']=scoped_build['membership']
cache=root/'work/native-static-startup-cache';cache.mkdir(exist_ok=True);key=sha(json.dumps(certificate,sort_keys=True).encode());destination=cache/key
with (cache/(key+'.lock')).open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 if not destination.exists():
  temp=Path(tempfile.mkdtemp(prefix=key+'.',dir=cache));snap=temp/'snapshot'
  for name,b in inputs.items():p=snap/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
  (temp/'ClawCanonicalDispatch.h').write_bytes(registry)
  (temp/'Bridge.h').write_bytes(inputs['Tests/NativeStaticStartup/Bridge.h'])
  env=dict(os.environ)
  for name in ('CPATH','C_INCLUDE_PATH','CPLUS_INCLUDE_PATH','OBJC_INCLUDE_PATH','LIBRARY_PATH','SDKROOT'):env.pop(name,None)
  include=str(snap/'Sources');objects=[]
  for name in cpp:
   obj=temp/(Path(name).stem+'.o');subprocess.run([clang,*cflags,'-I',include,'-c',str(snap/name),'-o',str(obj)],check=True,env=env);objects.append(str(obj))
  subprocess.run([swiftc,*sflags,'-import-objc-header',str(temp/'Bridge.h'),'-I',include,*[str(snap/name) for name in swift],*objects,'-lc++','-o',str(temp/'check')],check=True,env=env)
  (temp/'certificate.json').write_text(json.dumps(certificate,indent=2))
  (temp/'binary.sha256').write_text(sha((temp/'check').read_bytes()));temp.rename(destination)
assert json.loads((destination/'certificate.json').read_text())==certificate,'cache certificate differs'
assert sha((destination/'check').read_bytes())==(destination/'binary.sha256').read_text(),'cache executable differs'
assert (destination/'ClawCanonicalDispatch.h').read_bytes()==registry,'cache registry differs'
for path,data in inputs.items():assert (destination/'snapshot'/path).read_bytes()==data,'cache input differs: '+path
assert all(Path(p).read_bytes()==b for p,b in inputs.items()),'inputs changed during compile'
if version==9:
 current=load_final_build(root);assert current['membership']==scoped_build['membership'] and current['inputs']==inputs,'selected build changed during compile'
profiles=requested or list(profile_inventory)
reports=[]
for name in profiles:
 row=profile_inventory[name];source=frozen/row['path']; compressed=source.read_bytes();assert sha(compressed)==row['sha256'],'frozen shard drift'
 logical=gzip.decompress(compressed);assert sha(logical)==row['logicalSha256'],'logical shard drift'
 if version==9:
  original=json.loads(logical);validate_static_final_inputs(dict(declared_platform_inputs=original.get('platformProfileInputs'),physical_policy_sha256=original.get('physicalPolicySha256')),original)
 plain=destination/(name+'.json');plain.write_bytes(logical)
 done=subprocess.run([str(destination/'check'),str(plain)],capture_output=True,text=True)
 if done.returncode:sys.stderr.write(done.stdout+done.stderr);raise SystemExit(done.returncode)
 report=json.loads(done.stdout.splitlines()[-1]);report['reference_sha256']=sha(source.read_bytes())
 artifact=plain.with_suffix('.native.json');retained=destination/('golden-'+name+'.native.json');retained.write_bytes(artifact.read_bytes())
 report['native_artifact']=str(retained);report['native_artifact_sha256']=sha(retained.read_bytes());reports.append(report)
controls=[]
if not requested:
 for action in ['entry-reentry','return-reentry','entry-owner','return-owner']+(['entry-table','return-table'] if version>=3 else []):
  plain=destination/({1:'two-wrappers-seed0',2:'three-wrappers-seed0',3:'seven-wrappers-seed0',4:'fifteen-wrappers-seed0',5:'thirtyfour-wrappers-seed0',6:'joint58-clean',7:'extended119-clean',8:'list133-clean',9:'final144-clean'}[version]+'.json');env=dict(os.environ,CLAW_NATIVE_STATIC_AUTHORITY=action)
  done=subprocess.run([str(destination/'check'),str(plain)],capture_output=True,text=True,env=env)
  if done.returncode:sys.stderr.write(done.stdout+done.stderr);raise SystemExit(done.returncode)
  report=json.loads(done.stdout.splitlines()[-1]);artifact=plain.with_suffix('.native.json')
  retained=destination/('authority-'+action+'.native.json');retained.write_bytes(artifact.read_bytes())
  report['native_artifact']=str(retained);report['native_artifact_sha256']=sha(retained.read_bytes());controls.append(report)
assert all(Path(p).read_bytes()==b for p,b in inputs.items()),'inputs changed during replay'
if version==9:
 current=load_final_build(root);assert current['membership']==scoped_build['membership'] and current['inputs']==inputs,'selected build changed during replay'
result={'status':'pass','command':'native-static-startup','sanitized':asan,'optimized':opt,'profiles':reports,'authority_controls':controls,'checks':sum(r['checks'] for r in reports+controls),'certificate':str(destination/'certificate.json'),'native_table_walker':True,'gameplay':False,'reference_version':version}
output=Path(os.environ.get('CLAW_NATIVE_STATIC_CHECK_DIR',str(root/'work/coordination')))/({1:'static-tail-native-',2:'static-lock-native-',3:'static-seven-native-',4:'static-fifteen-native-',5:'static-thirtyfour-native-',6:'static-application-native-',7:'static-extended-native-',8:'static-list-native-',9:'static-final-native-'}[version]+('sanitized' if asan else 'optimized')+'-report.json');output.parent.mkdir(parents=True,exist_ok=True);result['report_path']=str(output.resolve());output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
PY
