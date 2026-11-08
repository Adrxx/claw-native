"""Destination elections from production service arms, with explicit domains.

The Swift dry-run compiles the original switch labels and argument-count
guards. Effects and memory/value guards are not executed: they are retained
as obligations in the report. A selected arm proves a service exists, not
that arbitrary guest memory is valid or that the service has executed.
Mathematical calls use the real C++ service, including its x87 validation.
"""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

GENERATOR_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def switches(text, signature, body):
    method = body(text, signature)
    # All selected methods have one address switch. Nested conversion and
    # formatting switches have a different indentation and are never arms.
    match = re.search(r'(?m)^( +)switch (q\.function|function|call\.function|e\.function) \{', method)
    if not match:
        raise ValueError('Missing production address switch: '+signature)
    indent = match[1]
    pattern = re.compile(r'(?m)^'+indent+r'(case ([^\n:]+)|default):')
    labels = list(pattern.finditer(method, match.end()))
    arms = []
    for index, label in enumerate(labels):
        if label[2] is None:
            continue
        def constant(m):
            value=re.search(r'\b'+m[1]+r':UInt32 = (0x[0-9a-f]+)',text)
            if not value:raise ValueError('Unresolved production constant: '+m[1])
            return value[1]
        resolved=re.sub(r'Self\.(\w+)',constant,label[2])
        if not re.fullmatch(r'0x[0-9a-f]+(?:\s*,\s*0x[0-9a-f]+)*', resolved):
            raise ValueError('Unreviewed production switch label: '+label[2])
        end = labels[index+1].start() if index+1 < len(labels) else len(method)
        effect = method[label.end():end]
        if not re.search(r'\breturn\s+(?!nil\b|fail\(|resources\.fail\()[\w.]+',effect):
            # An explicit nil-only arm does not provide a native destination.
            continue
        # Keep simple ABI guards. Other guards remain explicit, unproved
        # domains; never interpret their absence from this probe as acceptance.
        count = None
        first = re.search(r'\bguard\s+(.*?)\s+else\s*\{', effect, re.S)
        if first:
            for candidate in first[1].split(','):
                candidate=candidate.strip()
                plain=candidate.replace('a.count','0').replace('q.function','0').replace('function','0')
                if candidate=='a.isEmpty' or (candidate.startswith('a.count') and
                        re.fullmatch(r'[0-9xa-fA-F\s()?:=!<>|&.+-]+',plain)):
                    count=candidate.replace('q.function','f').replace('function','f')
                    break
        arms.append(dict(label=resolved, original_label=label[2],targets=[int(v,16) for v in re.findall(r'0x[0-9a-f]+',resolved)],
                         count_guard=count, production_arm=effect.strip(),
                         production_switch=match[2], signature=signature))
    return arms


def branches(text, signature, body):
    method=body(text,signature)
    result=[]
    for match in re.finditer(r'(?m)^        if q\.function == (0x[0-9a-f]+)(?:\s*\{|,)',method):
        branch=body(method,match[0])
        if not re.search(r'\breturn\s+(?!nil\b|fail\(|resources\.fail\()[\w.]+',branch):continue
        result.append(dict(label=match[1],targets=[int(match[1],16)],count_guard=None,
                           production_arm=branch,signature=signature,production_switch='q.function'))
    return result


def inventory(root, body, digest):
    resources = (root/'Sources/ClawNativeMenuResources.swift').read_text()
    interface = (root/'Sources/ClawNativeMenuInterface.swift').read_text()
    # Check the installed dependency and every selected delegation, rather
    # than treating an unrelated method containing an address as a route.
    if 'self.service(q)' not in body(interface,'        resources.dependency ='):
        raise ValueError('Native dependency is no longer installed')
    service = body(interface,'    private func service(_ q:ClawCall)')
    resource_service = body(resources,'    func service(_ q:ClawCall,request:')
    if 'dependency?(q)' not in resource_service:
        raise ValueError('Resource dependency fallback changed')
    methods = [
        ('resources','Sources/ClawNativeMenuResources.swift','    func service(_ q:ClawCall,request:', None),
        ('interface','Sources/ClawNativeMenuInterface.swift','    private func service(_ q:ClawCall)',None),
        ('movie','Sources/ClawNativeMenuInterface.swift','    private func movieLibrary(', 'movieLibrary(q.function,r,a)'),
        ('archive','Sources/ClawNativeMenuInterface.swift','    func service(_ function:UInt32,_ r:UInt32,_ a:[UInt32])->UInt32?', 'archiveServices.service(q.function,r,a)'),
        ('save-files','Sources/ClawNativeMenuInterface.swift','    func service(_ function:UInt32,_ r:UInt32,_ a:[UInt32],heap:', 'files.service(q.function,r,a,heap:heap)'),
        ('settings','Sources/ClawNativeMenuInterface.swift','    func service(_ function:UInt32,_ a:[UInt32],heap:', 'settings?.service(q.function,a,heap:heap)'),
        ('music','Sources/ClawNativeMenuMusic.swift','    func service(_ function:UInt32,_ receiver:UInt32,_ a:', 'music?.service(q.function,r,a)'),
        ('diagnostics','Sources/ClawNativeDiagnostics.swift','    fileprivate func call(_ call:', 'diagnosticService(q,frame:frame)'),
        ('raw-rect','Sources/ClawNativeDisplay.swift','    func rawActorService(', 'rawActorService(ClawNativeMenuRawDisplayHost(resources),q)'),
    ]
    routes = []
    inputs = {}
    for name,path,signature,delegation in methods:
        if delegation and delegation not in service:
            raise ValueError('Missing native delegation: '+delegation)
        text = (root/path).read_text()
        inputs[path] = digest(root/path)
        arms = switches(text,signature,body)
        if name=='save-files':
            declared=re.search(r'static let functions:Set<UInt32> = \[([^\]]+)\]',text)
            if not declared:raise ValueError('Missing CFile service election')
            allowed={int(v,16) for v in re.findall(r'0x[0-9a-f]+',declared[1])}
            if any(t not in allowed for arm in arms for t in arm['targets']):
                raise ValueError('CFile switch arm is absent from its entrance election')
        if name=='raw-rect':
            # This is the only rawActor entry delegated by the interface.
            arms=[dict(a,label='0x546d58',targets=[0x546d58]) for a in arms if 0x546d58 in a['targets']]
        for arm in arms:
            arm.update(route=name,path=path,source_sha256=inputs[path],production_method=body(text,signature))
            routes.append(arm)
    # The interface also elects a few imports/MFC providers before its
    # switch. Only exact top-level address branches with real return effects
    # are selected. Their complete conditions remain visible in the witness.
    for arm in branches(interface,'    private func service(_ q:ClawCall)',body):
        arm.update(route='interface-branch',path='Sources/ClawNativeMenuInterface.swift',
                   source_sha256=inputs['Sources/ClawNativeMenuInterface.swift'])
        routes.append(arm)
    display_path='Sources/ClawNativeDisplay.swift'
    display=(root/display_path).read_text();inputs[display_path]=digest(root/display_path)
    if 'display.menuPhysicalService(q)' not in service:raise ValueError('Display service disconnected')
    physical=body(display,'    func menuPhysicalService(')
    if 'menuTextService(q)' not in physical:raise ValueError('Display text service disconnected')
    for arm in branches(display,'    func menuPhysicalService(',body):
        arm.update(route='display-physical',path=display_path,source_sha256=inputs[display_path]);routes.append(arm)
    text=body(display,'    private func menuTextService(')
    election=re.search(r'guard (\[[^\n]+\]\.contains\(q.function\)) else',text)
    if not election:raise ValueError('Text destination election changed')
    def constants(match):
        name=match[1]
        value=re.search(r'\b'+name+r':UInt32 = (0x[0-9a-f]+)',display)
        if not value:raise ValueError('Unresolved display constant: '+name)
        return value[1]
    expression=re.sub(r'Self\.(\w+)',constants,election[1])
    targets=[int(v,16) for v in re.findall(r'0x[0-9a-f]+',expression)]
    routes.append(dict(route='display-text',path=display_path,source_sha256=inputs[display_path],
        label=','.join(hex(v) for v in targets),targets=targets,count_guard=None,
        production_arm=text,signature='    private func menuTextService(',production_switch=election[1]))
    path='Sources/ClawNativePaletteResources.swift'
    palette=(root/path).read_text();inputs[path]=digest(root/path)
    if 'palette.menuPhysicalService(q)' not in service:raise ValueError('Palette service disconnected')
    physical=body(palette,'    func menuPhysicalService(')
    election=re.search(r'if (\[[^\n]+\]\.contains\(q.function\))',physical)
    if not election or 'return graphicsService(call)' not in physical:
        raise ValueError('Palette graphics delegation changed')
    for arm in switches(palette,'    func graphicsService(',body):
        # The two original DirectDrawCreate import spellings are literal
        # elections in both the parent and the graphics service switch.
        if not all(hex(t) in election[1] for t in arm['targets']):continue
        arm.update(route='palette-graphics',path=path,source_sha256=inputs[path],
                   parent_election=election[1],parent_preconditions=physical)
        routes.append(arm)
    return routes,inputs


def build(root, body, digest, heavy_lock, wait_load):
    routes,inputs=inventory(root,body,digest)
    cpp_path=root/'Sources/ClawNativeMenuInterface.cpp'
    inputs[str(cpp_path.relative_to(root))]=digest(cpp_path)
    inputs['scripts/call_closure_providers.py']=GENERATOR_SHA256
    inputs['Sources/ClawRuntime.h']=digest(root/'Sources/ClawRuntime.h')
    for path in ('Sources/ClawNativeMenuResources.h','Sources/ClawNativeMenuResources.cpp','Sources/ClawNativeMenuInterface.h'):
        inputs[path]=digest(root/path)
    key=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()[:24]
    folder=root/'work/build/call-closure-providers'/key
    folder.mkdir(parents=True,exist_ok=True)
    binary=folder/'probe'
    if binary.exists():return binary,routes,inputs
    cpp=cpp_path.read_text()
    start=cpp.index('namespace {\n// Exact native x87 primitives')
    end=cpp.index('\nextern "C" {',start)
    search=body((root/'Sources/ClawNativeMenuResources.cpp').read_text(),'uint32_t claw_native_menu_byte_search(')
    substring=body((root/'Sources/ClawNativeMenuResources.cpp').read_text(),'uint32_t claw_native_menu_substring(')
    (folder/'math.cpp').write_text('#include "ClawNativeMenuInterface.h"\n#include "ClawNativeMenuResources.h"\n#include <cmath>\n#include <cstring>\n#include <cfloat>\n#include <limits>\n#include <algorithm>\n#include <string>\n'+cpp[start:end]+'\n'+search+'\n'+substring)
    swift='import Foundation\n'
    for name in dict.fromkeys(a['route'] for a in routes):
        swift+=f'func route_{name.replace("-","_")}(_ f:UInt32,_ a:[UInt32])->String? {{\n switch f {{\n'
        for index,arm in enumerate(routes):
            if arm['route']!=name:continue
            swift+=' case '+arm['label']+':\n'
            if arm['count_guard']:swift+='  guard '+arm['count_guard']+' else {return nil}\n'
            swift+=f'  return "{index}"\n'
        swift+=' default:return nil\n }\n}\n'
    # Execute the newly added non-I/O arms against bounded ledgers. The arm
    # bodies themselves are copied verbatim; no second implementation of
    # free, read-stream flush or CObList teardown lives in the test.
    swift+='''
final class ProviderFixture {
    var files:[UInt32:Bool] = [0x61000000:true]
    var released:[UInt32] = []
    var lists:[UInt32:Set<UInt32>] = [0x62000000:[0x61000000,0x61000010]]
    var words:[UInt32:UInt32] = [0x6200000c:2]
    var resources:ProviderFixture {self}
    func release(_ p:UInt32) {if p != 0 {released.append(p)}}
    func w(_ p:UInt32)->UInt32 {words[p] ?? 0}
    func put(_ p:UInt32,_ v:UInt32) {words[p]=v}
    func effect(_ f:UInt32,_ argc:UInt32,_ token:UInt32)->UInt32? {
        var q=ClawCall();q.function=f
        let a=argc <= 32 ? Array(repeating:token,count:Int(argc)):[]
        let r:UInt32=0x62000000
        switch q.function {
'''
    for arm in routes:
        if ((arm['route']=='resources' and set(arm['targets']) & {0x4a49b0,0x4a7920}) or
                (arm['route']=='interface' and 0x4f5192 in arm['targets'])):
            swift+='case '+arm['label']+':\n'+arm['production_arm']+'\n'
    swift+='''default:return nil
        }
        return nil
    }
}
'''
    seek=next(a for a in routes if a['route']=='save-files' and 0x4f75f5 in a['targets'])
    swift+='''
func nativeFileSeek(_ a:[UInt32],_ handle:FileHandle)->UInt32? {
    func open()->FileHandle? {handle}
    do {
'''+seek['production_arm']+'''
    } catch {return nil}
}
'''
    swift+='''
let input = FileHandle.standardInput.readDataToEndOfFile()
let rows = try JSONSerialization.jsonObject(with:input) as! [[String:Any]]
let answers:[[String:Any]] = rows.map {row in
    func n(_ k:String)->UInt32 {(row[k] as? NSNumber)?.uint32Value ?? 0}
    let f=n("target"),argc=n("argc")
    guard argc <= 32 else {return ["route":"refused"]}
    let a=Array(repeating:UInt32(0),count:Int(argc))
    if n("file_seek") != 0 {
        let url=FileManager.default.temporaryDirectory.appendingPathComponent("claw-provider-seek-"+UUID().uuidString)
        try! Data(repeating:0,count:16).write(to:url)
        defer {try? FileManager.default.removeItem(at:url)}
        let handle=try! FileHandle(forUpdating:url)
        defer {try? handle.close()}
        try! handle.seek(toOffset:UInt64(n("initial")))
        let value=nativeFileSeek((row["arguments"] as? [UInt32]) ?? [],handle)
        return ["accepted":value != nil,"value":value ?? UInt32.max,"position":try! handle.offset()]
    }
    if n("effect") != 0 {
        let fixture=ProviderFixture()
        let value=fixture.effect(f,argc,n("token"))
        return ["accepted":value != nil,"released":fixture.released.sorted(),
                "list_retained":fixture.lists[0x62000000] != nil,
                "vtable":fixture.w(0x62000000),"count":fixture.w(0x6200000c)]
    }
    if n("math") != 0 {
        var q=ClawCall(),s=ClawX87State(),out:UInt32=0
        q.function=f;q.argumentCount=argc
        s.size=UInt32(MemoryLayout<ClawX87State>.size);s.version=1;s.control=0x023f
        s.count=n("x87_count");s.popCount=n("x87_pop");s.pushCount=n("x87_push")
        // All-zero finite operands are domain fixtures. acos(0), pow(0,0),
        // ceil/floor(0) and integer conversion(0) are within production bounds.
        q.x87ArgumentCount=n("scalar") != 0 ? 1:UInt32(CLAW_X87_EXACT)
        let accepted=withUnsafeMutablePointer(to:&s) {q.x87State=$0;return claw_native_menu_math_service(&q,&out)}
        return ["route":accepted == 1 ? "math":"refused","returned":s.returned]
    }
'''
    for name in dict.fromkeys(a['route'] for a in routes):
        swift+=f'    if let r=route_{name.replace("-","_")}(f,a) {{return ["route":r]}}\n'
    swift+='''    return ["route":"refused"]
}
FileHandle.standardOutput.write(try JSONSerialization.data(withJSONObject:answers,options:[.sortedKeys]))
'''
    (folder/'main.swift').write_text(swift)
    with heavy_lock():
        if binary.exists():return binary,routes,inputs
        wait_load()
        subprocess.run(['xcrun','clang++','-std=c++17','-O1','-I'+str(root/'Sources'),'-c',str(folder/'math.cpp'),'-o',str(folder/'math.o')],check=True)
        subprocess.run(['xcrun','clang++','-dynamiclib',str(folder/'math.o'),'-o',str(folder/'providers.dylib')],check=True)
        subprocess.run(['xcrun','swiftc','-O','-I'+str(root/'Sources'),'-import-objc-header',str(root/'Sources/ClawNativeMenuInterface.h'),str(folder/'main.swift'),str(folder/'math.o'),'-Xlinker','-lc++','-o',str(binary)],check=True)
    return binary,routes,inputs


def audit(root, rows, owners, body, digest, heavy_lock, wait_load):
    from Tests.clawparity.program import claw
    imports=claw().imports
    binary,routes,inputs=build(root,body,digest,heavy_lock,wait_load)
    cohort=[r for r in rows if r['outcome']=='provider-unresolved']
    queries=[];indexes=[]
    for row in cohort:
        shape=row.get('caller_shape',{})
        selected=[]
        for variant in shape.get('variants',[shape]):
            math=bool(variant.get('x87') or variant.get('x87_scalar'))
            selected.append(len(queries))
            queries.append(dict(target=row['target'],argc=variant.get('argc',0),math=int(math),
                                scalar=variant.get('x87_scalar',0),x87_count=max(2,variant.get('x87_pop',0)),
                                x87_pop=variant.get('x87_pop',0),x87_push=variant.get('x87_push',0)))
        indexes.append(selected)
    def run(qs):
        return json.loads(subprocess.run([str(binary)],input=json.dumps(qs),text=True,capture_output=True,
                          env={**os.environ,'CLAW_GAME_VERSION':'1.0'},check=True).stdout)
    answers=run(queries)
    unowned_targets=sorted({r['target'] for r in cohort if ('claw-v1.0',r['caller']) not in owners})
    unowned_queries=[dict(target=t,argc=n) for t in unowned_targets for n in range(33)]
    # These fixtures search the production math service, rather than a second
    # Python list of CRT math addresses. They locate a destination only; an
    # unowned caller still has no emitted shape proof.
    unowned_queries += [dict(target=t,argc=n,math=1,x87_count=2,x87_pop=pop,x87_push=push,scalar=scalar)
        for t in unowned_targets for n in (0,2) for pop in range(3) for push in range(2) for scalar in (0,1)]
    unowned_answers=run(unowned_queries)
    unowned_routes={}
    for q,a in zip(unowned_queries,unowned_answers):
        if a['route']!='refused':unowned_routes.setdefault(q['target'],a)
    groups={}
    for row,selected in zip(cohort,indexes):
        probes=[dict(query=queries[i],answer=answers[i]) for i in selected]
        # Every emitted variant must have a destination. In particular, a
        # variadic call is not an invented zero-argument call.
        probe=next((p for p in probes if p['answer']['route']=='refused'),probes[0])
        query,answer=probe['query'],probe['answer']
        admitted=('claw-v1.0',row['caller']) in owners
        row['provider_caller']='admitted' if admitted else 'unowned'
        # No caller shape exists for an unowned caller. Probe all reasonable
        # counts to locate a destination, without claiming its ABI is proved.
        if not admitted:
            answer=unowned_routes.get(row['target'],answer)
        route=answer['route']
        evidence=dict(query=query,answer=answer,probes=probes,caller_admitted=admitted,
                      contract='Destination election only; memory, values, optional owners and effects are not proved.')
        if route=='math':
            evidence['route']='production-math'
        elif route!='refused':
            arm=routes[int(route)]
            evidence.update(route=arm['route'],path=arm['path'],source_sha256=arm['source_sha256'],
                            signature=arm['signature'],count_guard=arm['count_guard'],
                            production_arm=arm['production_arm'])
        else:evidence['route']='missing'
        row['provider_destination']=evidence
        if route!='refused':row['outcome']='served-provider-route' if admitted else 'provider-caller-unowned'
        group=groups.setdefault(row['target'],dict(target=row['target'],import_name=imports.get(row['target']),admitted_edges=0,unowned_edges=0,routes=Counter(),missing_admitted_sites=[]))
        group['admitted_edges' if admitted else 'unowned_edges']+=1
        group['routes'][evidence['route']]+=1
        if admitted and route=='refused':
            group['missing_admitted_sites'].append(dict(caller=row['caller'],site=row['site'],query=query))
    # A completely unrelated target and excessive count must remain refused.
    controls=run([dict(target=0xdeadbeef,argc=0),dict(target=0x4f6286,argc=33),
                  dict(target=0x4f6286,argc=1),dict(target=0x4a30e0,argc=0,math=1,x87_count=9)])
    if any(a['route']!='refused' for a in controls):raise ValueError('Provider destination probe accepts unknown/malformed call')
    missing=[g for g in groups.values() if g['missing_admitted_sites']]
    missing_edges=sum(len(g['missing_admitted_sites']) for g in missing)
    domains={}
    for arm in routes:
        domains.setdefault(arm['route'],dict(path=arm['path'],signature=arm['signature'],
            source_sha256=arm['source_sha256'],
            preconditions_and_effects=arm.get('production_method',arm['production_arm']),
            parent_preconditions=arm.get('parent_preconditions')))
    return dict(selected_edges=len(cohort),destinations=len(groups),
                admitted_edges=sum(g['admitted_edges'] for g in groups.values()),
                unowned_edges=sum(g['unowned_edges'] for g in groups.values()),
                missing_admitted_edges=missing_edges,
                served_admitted_edges=sum(g['admitted_edges'] for g in groups.values())-missing_edges,
                missing_admitted_destinations=missing,groups=list(groups.values()),
                completion_obligation_met=not missing,inputs=inputs,negative_controls=controls,service_domains=domains,
                contract='Compiled production switch elections and simple argument-count guards; actual production math service on finite zero fixtures. Remaining memory/value/lifetime/owner preconditions are explicit per arm.')
