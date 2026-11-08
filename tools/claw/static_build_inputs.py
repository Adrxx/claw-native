"""V9 static-only dependency selection; legacy and application inventories are separate.

Selection is pure. Loading hashes exact selected files and all header members,
then recomputes selection from every manifest. Unrelated valid source/family
additions do not change this scope; global canonical validation still fails closed.
"""
import gzip
import hashlib
import json
from pathlib import Path

from . import gen_project

RECIPE_INPUTS = (
    'Makefile','scripts/check-native-static-startup.sh','tools/claw/static_build_inputs.py',
    'tools/claw/milestone.py','tools/claw/gen_project.py','tools/claw/manifest.py',
    'tools/claw/owned_ranges.py','tools/claw/index.py','tools/claw/paths.py',
    'tools/claw/__init__.py','tools/claw/__main__.py','tools/claw/legacy.py',
    'Tests/clawparity/__init__.py','Tests/clawparity/program.py','Tests/clawparity/cases.py',
    'Tests/clawparity/env.py','Tests/clawparity/kernel.py',
    'Tests/families/schema.json','tools/claw/app_exclude.json',
)
SWIFT_INPUTS = (
    'Sources/ClawTokenHeap.swift','Sources/ClawNativeMfcLocks.swift','Sources/ClawNativeMfcMemory.swift',
    'Sources/ClawNativeCanonicalHost.swift','Sources/ClawNativeCrtMemory.swift',
    'Sources/ClawNativeCrtServices.swift','Tests/NativeStaticStartup/main.swift',
)


def select_final_build(manifest, canonical_rows, reference):
    """Return selected source paths/rows/dispatch without filesystem or Git reads."""
    version=9
    addresses={0x4a5880,0x4a3610,0x4a3560,0x4a35f0,0x4a5860,0x4a5870,0x4a7b90,0x4a7bc0,0x4a7c40,0x501fbd,0x501fc7,0x501fc8,0x50226e,0x502278,0x502279,0x502c90,0x502c9a}
    addresses.update({0x4a2cf1,0x4f5e89,0x4a2f62,0x4a48c0,0x502ca4})
    if version>=3:addresses.update({0x502876,0x502880,0x502881,0x502c51,0x502c5b,0x502c5c,0x503722,0x50372c,0x50372d,0x503748,0x503752,0x503753,0x403540,0x403550,0x403ad0})
    if version>=4:
     for wrapper in [0x403540,0x4042b0,0x4064c0,0x406e90,0x4074a0,0x408520,0x409150,0x409fe0]:addresses.update({wrapper,wrapper+0x10,wrapper+0x30})
     addresses.update({0x4dc680,0x40b820,0x40b830})
    rows=canonical_rows
    if version>=6:
     observed={e['function'] for e in reference['entries']}
     # This selects admitted source addresses only; the immutable original states remain comparison inputs.
     addresses.update(r['address'] for r in rows if r['family'].startswith('static_') and r['address'] in observed)
     addresses.update({0x50257f,0x503510,0x4a56e0,0x502301,0x50210b,0x4f5e89,0x4f5133,0x50228f,0x503420,0x502e47,0x502e95,0x502f05,0x50335e,0x503167,0x502fb6,0x502ff8,0x4a4a20,0x502335,0x502369,0x502f84,0x502f26,0x4a48c0,0x501f01,0x501fde,0x4f6439,0x4f6433,0x4f65f2})
     addresses.update({0x43d330,0x43d340})
     addresses.update({0x4f50fd,0x4a5690})
    if version>=7:
     # Explicit finite additions; missing admission fails before compilation.
     addresses.update({0x440ee0,0x4dc280,0x4dc200,0x440f30,0x453cc0,0x453d00,0x45acb0,0x4f54ea,0x4db620})
     addresses.add(0x502405)
     addresses.update({0x50240a,0x4db4d0})
    if version>=8:
     addresses.update({0x4f709b,0x502d30,0x502d3a})
     list_family=json.loads(manifest['Tests/families/static_list_records.json'])
     whole={int(address,16) for address,meta in list_family['callees'].items() if meta['kind']=='whole'}
     assert whole=={0x4a4a20,0x4f6a9a,0x50228f,0x502e95,0x502f05,0x502f26}
     addresses.update(whole)
    if version==9:
     final_family=json.loads(manifest['Tests/families/static_final_records.json'])
     addresses.update(int(entry['address'],16) for entry in final_family['owned'])
     whole={int(address,16)for address,meta in final_family['callees'].items()if meta['kind']=='whole'}
     assert whole=={0x4f709b,0x50228f,0x502e95,0x502f05,0x502f26}
     addresses.update(whole)
    rows=[r for r in rows if r['address'] in addresses];assert {r['address'] for r in rows}==addresses
    registry=gen_project.canonical_dispatch_text(rows).encode()
    families={r['family'] for r in rows}; selected={p:b for p,b in manifest.items() if json.loads(b).get('id') in families}
    cpp=sorted({s for b in selected.values() for s in json.loads(b)['sources']})
    return dict(cpp=cpp,swift=list(SWIFT_INPUTS),manifests=sorted(selected),rows=rows,
                registry=registry.decode())


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _read(root,name):
    path=Path(name)
    if (path.is_absolute() or '..' in path.parts or path.as_posix()!=name
            or any((root/Path(*path.parts[:i+1])).is_symlink()for i in range(len(path.parts)))
            or not (root/path).is_file()):
        raise ValueError('static final dependency path: '+name)
    return (root/path).read_bytes()


def load_final_build(root):
    """Load pinned original inputs and exact v9 build/recipe dependency bytes.

    Toolchain identity is supplied by existing milestone/compiler certificate
    code. External SDK/system libraries are version identified, not byte archived.
    """
    from . import milestone as m
    root=Path(root)
    provenance_bytes=_read(root,m.STATIC_FINAL_REFERENCE)
    if _sha(provenance_bytes)!=m.STATIC_FINAL_REFERENCE_SHA256:
        raise ValueError('static final provenance fingerprint')
    provenance=json.loads(provenance_bytes)
    reference_hashes=m.static_final_archived_producers(provenance,root)
    reference_hashes[m.STATIC_FINAL_REFERENCE]=m.STATIC_FINAL_REFERENCE_SHA256
    original='Original/claw10/CLAW.EXE';reference_hashes[original]=m.ORIGINAL_SHA256
    clean=None
    for row in provenance['profiles']:
        if row['path']!=row['name']+'.json.gz':raise ValueError('static final shard path')
        name=str(Path(m.STATIC_FINAL_REFERENCE).parent/row['path']);data=_read(root,name)
        if _sha(data)!=row['sha256'] or len(data)!=row['bytes']:raise ValueError('static final shard fingerprint')
        reference_hashes[name]=row['sha256']
        if row['name']=='final144-clean':
            logical=gzip.decompress(data)
            if _sha(logical)!=row['logicalSha256']:raise ValueError('static final logical fingerprint')
            clean=json.loads(logical)
    if clean is None:raise ValueError('static final missing clean reference')
    manifest={str(path.relative_to(root)):_read(root,str(path.relative_to(root)))for path in sorted((root/'Tests/families').glob('*.json'))}
    rows=gen_project.canonical_inventory([json.loads(data)for data in manifest.values()],json.loads(_read(root,'tools/claw/app_exclude.json')),root=root)[2]
    selection=select_final_build(manifest,rows,clean)
    headers=sorted(str(path.relative_to(root))for path in (root/'Sources').rglob('*')
        if path.suffix in ('.h','.hpp') and path!=root/'Sources/ClawCanonicalDispatch.h')
    paths=set(selection['cpp']+selection['swift']+selection['manifests']+headers+list(RECIPE_INPUTS)+['Tests/NativeStaticStartup/Bridge.h'])
    # Namespace-package initializers are absent today; if introduced they execute
    # during these imports and must become fingerprinted dependencies.
    paths.update(name for name in ('tools/__init__.py','Tests/__init__.py')if (root/name).exists())
    paths.update(reference_hashes)
    inputs={name:_read(root,name)for name in sorted(paths)}
    if any(_sha(inputs[name])!=expected for name,expected in reference_hashes.items()):
        raise ValueError('static final retained reference fingerprint')
    membership={key:selection[key]for key in ('cpp','swift','manifests','rows')}
    membership.update(headers=headers,recipes=sorted(paths-set(reference_hashes)-set(selection['cpp'])-set(selection['swift'])-set(selection['manifests'])-set(headers)),
                      references=sorted(reference_hashes),registry_sha256=_sha(selection['registry'].encode()))
    return dict(selection=selection,inputs=inputs,membership=membership)


def final_input_inventory(root):
    build=load_final_build(root)
    result={name:_sha(data)for name,data in build['inputs'].items()}
    result['@static-final/selected-build-membership']=_sha(json.dumps(build['membership'],sort_keys=True,separators=(',',':')).encode())
    return result
