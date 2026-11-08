"""Compile bounded retail production routes with nonexecuting native endpoints.

No address election is reproduced here. Swift branch/entrance code is copied
from the app; only destination effects (queue, decompressor, bitmap writer) are
replaced. These witnesses establish routing, not values or memory safety.
"""
import hashlib
import json
import marshal
import os
from pathlib import Path
import subprocess


def multiplayer_exclusions(root, rows, body, digest):
    """Owner decision 2026-11-03: disabled multiplayer is outside single-player.

    Elect exact original sites, never a target-wide exemption. Keep the
    original and emitted-source witnesses on every excluded row.
    """
    sites = {
        (0x477790, 0x4777b5, 0x4e0cc0),
        (0x477a10, 0x477a50, 0x4e0c80),
        (0x477a10, 0x477a8b, 0x479000),
        (0x477a10, 0x477aa0, 0x47a4b0),
        (0x477a10, 0x477acf, 0x47c4b0),
    }
    path = 'Sources/ClawNativeMenuInterface.swift'
    source = (root/path).read_text()
    disable = body(source, '    private func disableUnavailableMenuItems()')
    enter = body(source, '    func enter(previous:UInt32 = 0)')
    # Bind the actual disabled IDs and IFC disable operation, plus entry,
    # queued-input and post-frame enforcement. Fail closed on policy drift.
    required = ('var unavailable:[UInt32] = [11004,11005,12001,12002,12003,12201]',
                'resources.invoke(0x4dceb0,interface+0x154,[id,0])')
    if (any(s not in disable for s in required) or
            'disableUnavailableMenuItems()' not in enter or
            'while let event = try input.queue.next(window: input.window) {\n                disableUnavailableMenuItems()' not in source or
            'if !applicationServicesInstalled {try installApplicationServices()}\n        disableUnavailableMenuItems()' not in source):
        raise ValueError('Single-player disabled-menu policy changed; review multiplayer allow-list')
    proof = dict(reason='multiplayer, unreachable in single-player',
        decision='Owner 2026-11-03: exclude multiplayer bodies; their menu entries are disabled.',
        disabled_menu_ids=[11004,11005,12001,12002,12003,12201],
        source_inputs={path:digest(root/path)},
        disable_body_sha256=hashlib.sha256(disable.encode()).hexdigest(),
        entry_body_sha256=hashlib.sha256(enter.encode()).hexdigest(),
        contract='Single-player app composition only; these bodies are not admitted or served by this exclusion.')
    excluded=[]
    for row in rows:
        if row['outcome'] != 'owner-unresolved':continue
        if (row['caller'],row['site'],row['target']) not in sites:continue
        if not row.get('original_site') or not row.get('shape_evidence'):
            raise ValueError('Multiplayer exclusion requires original-site and emitted-source witnesses')
        row['outcome']='unreachable-single-player'
        row['single_player_exclusion']=proof
        excluded.append(row['original_site'])
    return dict(proof, excluded_edges=excluded)


def build(root, transport_binary, body, digest, heavy_lock, wait_load):
    paths = [root/p for p in ('Sources/ClawNativeMenuResources.swift',
        'Sources/ClawNativeMenuInterface.swift', 'Sources/ClawNativeScene.swift',
        'Sources/StateFiveRuntime.h')]
    # A second session can edit this file while an imported copy waits for the
    # build lock. Include the loaded generator, so that copy cannot populate
    # the current generator's cache key with its older Swift source.
    key = hashlib.sha256(marshal.dumps(build.__code__)+
        (''.join(digest(p) for p in paths)+digest(Path(__file__))+
         str(transport_binary)).encode()).hexdigest()[:24]
    folder = root/'work/build/call-closure-native'/key
    folder.mkdir(parents=True, exist_ok=True)
    binary = folder/'probe'
    if binary.exists():return binary
    resources, interface, scene = [p.read_text() for p in paths[:3]]
    # Stop at the platform switch: none of that switch serves game-range
    # targets. Preserve the entire ordering through the game-range fallback.
    service = body(resources, '    func service(_ q:ClawCall,request:')
    service = service[:service.index('        do {\n            switch q.function')]
    service = service.replace('func service(', 'func nativeService(', 1)+'        return 0\n    }\n'
    invoke = body(resources, '    @discardableResult func invoke(')
    dispatch = body(invoke, 'if let result = gameService?')
    installed_service = body(interface, '        resources.gameService =')
    game_service = body(installed_service, '            if self.base.sharedMenuResources === self.resources,')
    installed_dependency = body(interface, '        resources.dependency =')
    if 'self.service(q)' not in installed_dependency:raise ValueError('Native dependency installation changed')
    world = body(installed_service, '            if f == 0x4cdd30')
    if 'claw_world_file_entry(' not in world:raise ValueError('World teardown destination changed')
    world = world[:world.index('                var context =')]+'''                self.route = "native-world-teardown";self.outcome = "served-native-route";return 0
            }
'''
    mask = body(interface, '    private func customMaskService(')
    mask_target = body(mask, '        if function == 0x4cde90')
    if 'claw_world_file_entry(' not in mask_target:raise ValueError('Mask teardown destination changed')
    mask_target = mask_target[:mask_target.index('{')+1]+'''route = "native-mask-teardown";outcome = "served-native-route";return 0}'''
    mask = mask[:mask.index('        let host =')]+mask_target+'\n        return nil\n    }\n'
    shared = body(scene, '    func sharedInitializerService(')
    initializer = body(scene, '    func initializerService(_ q: ClawStateFiveCall)')
    initializer = initializer[:initializer.index('        if q.function == 0x4ca440')]
    initializer += '        return reject(q.function)\n    }\n'
    drain = body(scene, '    private func drainWindowInput(')
    if 'windowInput.queue.drain(' not in drain:raise ValueError('Input destination changed')
    drain = drain[:drain.index('        do {')]+'''        _ = windowInput
        resources.route = "native-window-input"
        resources.outcome = "served-native-route"
        return 0
    }
'''
    decompress = body(resources, '    private func uncompress(')
    if 'claw_level_uncompress(' not in decompress:raise ValueError('Decompression destination changed')
    decompress = decompress[:decompress.index('        let available =')]+'''        _ = block
        route = "native-zlib";outcome = "served-native-route";return 0
    }
'''
    # The dependency's exact target branch, with its bitmap-writing effect
    # replaced. The outer resource service still has to elect this dependency.
    bmp = body(body(interface, '    private func service(_ q:ClawCall)'), 'if q.function == 0x4b9e10')
    if 'ClawNativeScreenDump.bitmap(' not in bmp:raise ValueError('Bitmap destination changed')
    bmp = bmp[:bmp.index('{')+1]+'''self.route = "native-bmp";self.outcome = "served-native-route";return 0}'''
    source = (transport_binary.parent/'main.swift').read_text().split('let input = FileHandle.standardInput')[0]
    source = source.replace('    var clobber:UInt32 = 0', '''    var nativeRouting = false
    var closed = false, missingService:UInt32 = 0
    static let traceDepth = 0
    var mathServiceCounts:[UInt32:Int] = [:]
    var recent = NativeLog()
    let heap = NativeHeap()
    var commandEvent:[String:Any] = [:]
    var currentFrame:UInt32 {0x2000000}
    var resources:Probe {self}
    var receiverTable:UInt32 = 0x513a10
    lazy var base = NativeInputBase(self)
    var gameService:((UInt32,UInt32,[UInt32])->UInt32?)?
    var dependency:((ClawCall)->UInt32?)?
    var clobber:UInt32 = 0''')
    needle = '        var o = ClawLevelOwner(), convention:UInt32 = 0, argc:UInt32 = 0'
    assert source.count(needle)==1
    source = source.replace(needle, '''        if nativeRouting {return nativeInvoke(f,r,a)}
'''+needle)
    source += '''
struct NativeLog {
    enum Event {case service(UInt32,UInt32,[UInt32])}
    func append(_ e:Event) {}
    func append(text:String) {}
}
final class NativeHeap {
    var spans:[UInt32:(UnsafeMutablePointer<UInt8>,Int)] = [:]
    deinit {for (pointer,_) in spans.values {pointer.deallocate()}}
    func install(_ token:UInt32,_ bytes:[UInt8]) {
        guard token != 0,!bytes.isEmpty else {return}
        let pointer = UnsafeMutablePointer<UInt8>.allocate(capacity:bytes.count)
        for (i,byte) in bytes.enumerated() {pointer[i] = byte}
        if let (old,_) = spans[token] {old.deallocate()}
        spans[token] = (pointer,bytes.count)
    }
    func lookupBytes(_ token:UInt32,count:UInt32)->UnsafeMutablePointer<UInt8>? {
        for (base,span) in spans where token >= base && UInt64(token-base)+UInt64(count) <= UInt64(span.1) {
            return span.0.advanced(by:Int(token-base))
        }
        return nil
    }
}
enum ClawCustomLua {static let callback:UInt32 = 0x71040000}
func claw_native_menu_math_service(_ q:UnsafeMutablePointer<ClawCall>,_ out:UnsafeMutablePointer<UInt32>)->UInt32 {0}
final class NativeAudio {
    var managerIdentity:UInt32 = 0, lifecycleFault:UInt32 = 0
    func stopAll() {}
}
final class NativeErrors {
    var faultAddress:UInt32 = 0
    func service(_ q:ClawCall)->UInt32? {nil}
}
final class NativeInputBase {
    unowned let resources:Probe
    init(_ resources:Probe) {self.resources = resources;sourceHost.initialize(to:ClawHost())}
    deinit {sourceHost.deinitialize(count:1);sourceHost.deallocate()}
    var sharedMenuResources:Probe? {resources}
    static let ready:UInt32 = 0x46ac00
    var fault:UInt32 {resources.fault}
    var boundary:UInt32 {resources.fault}
    var calls:[UInt32] = [], missingOwner:UInt32 = 0
    var applicationErrors:NativeErrors?, audio:NativeAudio?
    var soundManager:UInt32 = 0, soundLoadCount:UInt32 = 0, soundStack:UInt32 = 0x2000000
    let sourceHost = UnsafeMutablePointer<ClawHost>.allocate(capacity:1)
    var windowReceiver:UInt32 = 0x61000000
    var windowInput:Bool? = true
    func reject(_ f:UInt32)->UInt32 {resources.fail(f)}
    func soundService(_ f:UInt32,_ r:UInt32,_ a:[UInt32],stack:UInt32)->UInt32 {reject(f)}
'''+shared+'\n'+initializer+'\n'+drain+'''
}
extension Probe {
    func record(_ event:[String:Any]) {
        if event["service"] as? String == "Windows process unavailable" {
            commandEvent = event;route = "native-windows-process-unavailable";outcome = "served-native-route"
        }
    }
    func w(_ token:UInt32)->UInt32 {receiverTable}
    func mapCustomSounds() {}
    func owningAllocation(_ token:UInt32)->(token:UInt32,bytes:UInt32)? {
        token == 0x61003000 ? (token,64):nil
    }
'''+mask+'\n'+decompress+'\n'+service+'''
    func nativeInvoke(_ function:UInt32,_ receiver:UInt32,_ arguments:[UInt32])->UInt32 {
'''+dispatch+'''
        // Unowned canonical/resource bodies remain obligations. Do not execute
        // or synthesize ownership at the dry-run boundary.
        outcome = "owner-unresolved";return 0
    }
    func nativeDependency(_ q:ClawCall)->UInt32? {
'''+bmp+'''
        return nil
    }
    func nativeRun(_ row:[String:Any])->[String:Any] {
        func number(_ k:String)->UInt32 {(row[k] as? NSNumber)?.uint32Value ?? 0}
        nativeRouting = true
        gameService = {[unowned self] f,r,a in
'''+body(installed_service, '            if let value = self.customMaskService(f,r,a)')+'\n'+world+game_service+'''
            return nil
        }
'''+installed_dependency.replace('self.service(q)','self.nativeDependency(q)')+'''
        if number("disable_game_service") != 0 {gameService = nil}
        if number("disable_dependency") != 0 {dependency = nil}
        closed = number("closed") != 0
        var q = ClawCall()
        q.function = number("target");q.receiver = number("receiver");q.argumentCount = number("argc")
        q.stackPointer = 0x2000000
        if q.function == 0x4dfec0,number("no_rect") == 0 {
            heap.install(q.receiver,Array(repeating:0xa5,count:number("short_rect") == 0 ? 16:15))
        }
        let a = (row["arguments"] as? [UInt32]) ?? Array(repeating:0,count:Int(min(q.argumentCount,32)))
        if q.function == 0x42beb0 {
            let strings = row["strings"] as? [String:[UInt8]]
            if let strings {
                for (token,bytes) in strings {if let token = UInt32(token) {heap.install(token,bytes)}}
            } else {
                if a.count > 0 {heap.install(a[0],Array("helper.exe".utf8)+[0])}
                if a.count > 1 {heap.install(a[1],[67,58,92,67,108,97,119,0])}
            }
        }
        withUnsafeMutableBytes(of:&q.arguments) {dst in a.withUnsafeBytes {src in dst.prefix(src.count).copyBytes(from:src)}}
        functions = [number("caller")]
        words = [0x61002000:64]
        if number("bad_window") != 0 {base.windowReceiver = 0x61000004}
        if number("no_window") != 0 {base.windowInput = nil}
        if number("bad_mask_table") != 0 {receiverTable = 0}
        let result = nativeService(q)
        if route == "native-rect-constructor",fault == 0 {outcome = "served-native-route"}
        let rect = q.function == 0x4dfec0 ? heap.lookupBytes(q.receiver,count:16).map {Array(UnsafeBufferPointer(start:$0,count:16))}:nil
        return ["outcome":outcome,"route":route,"fault":fault,"result":result,"command_event":commandEvent,"rect_bytes":rect ?? []]
    }
}
let input = FileHandle.standardInput.readDataToEndOfFile()
let rows = try JSONSerialization.jsonObject(with:input) as! [[String:Any]]
let answers = rows.map { Probe().nativeRun($0) }
FileHandle.standardOutput.write(try JSONSerialization.data(withJSONObject:answers,options:[.sortedKeys]))
'''
    (folder/'main.swift').write_text(source)
    (folder/'probe.h').write_text((transport_binary.parent/'probe.h').read_text()+'\n#include "StateFiveRuntime.h"\n')
    with heavy_lock():
        if binary.exists():return binary
        wait_load()
        subprocess.run(['xcrun','swiftc','-O','-I'+str(root/'Sources'),'-import-objc-header',str(folder/'probe.h'),
            str(folder/'main.swift'),str(transport_binary.parent/'owners.o'),
            str(transport_binary.parent/'ClawNativeLevelTransport.o'),'-Xlinker','-lc++','-o',str(binary)],check=True)
    return binary


def run(binary, queries):
    return json.loads(subprocess.run([str(binary)],input=json.dumps(queries),text=True,capture_output=True,
        env={**os.environ,'CLAW_GAME_VERSION':'1.0'},check=True).stdout)


def audit(root, rows, transport_binary, body, digest, heavy_lock, wait_load):
    cohort = [r for r in rows if r['outcome']=='owner-unresolved']
    binary = build(root, transport_binary, body, digest, heavy_lock, wait_load)
    rect_queries=[dict(target=0x4dfec0,argc=4,receiver=0x61004000,arguments=a)
        for a in ([1,2,3,4],[0xffffffff,0x80000000,0x12345678,0xabcdef01],[0,0,0,0])]
    rect_answers=run(binary,rect_queries)
    for query,answer in zip(rect_queries,rect_answers):
        expected=list(b''.join(v.to_bytes(4,'little') for v in query['arguments']))
        if (answer['outcome']!='served-native-route' or answer['result']!=query['receiver']
                or answer['rect_bytes']!=expected):raise ValueError('Native rectangle construction regressed')
    for change in ({'argc':3,'arguments':[1,2,3]},{'receiver':0},{'no_rect':1},{'short_rect':1},{'closed':1}):
        if run(binary,[dict(rect_queries[0],**change)])[0]['outcome']!='refused':
            raise ValueError('Malformed native rectangle construction accepted')
    queries = []
    for edge in cohort:
        shape = edge.get('caller_shape', {})
        def source_paths(value):
            if isinstance(value,dict):
                return ({value['path']} if 'path' in value else set()).union(
                    *(source_paths(v) for v in value.values()))
            if isinstance(value,list):return set().union(*(source_paths(v) for v in value))
            return set()
        evidence=edge.get('shape_evidence',{})
        evidence['source_inputs']={p:digest(root/p) for p in source_paths(evidence)}
        if 'original_site' in edge:
            evidence['manifest_sha256']=digest(root/'Tests/families'/f"{edge['original_site']['family']}.json")
        evidence['runtime_sha256']=digest(root/'Sources/ClawRuntime.hpp')
        if (not shape or shape.get('variants') or
                any(shape.get(k) for k in ('local','inlined','impossible','source','compiler','tail','x87','x87_scalar')) or
                'argc' not in shape or 'receiver' not in shape):
            # A local/inlined body has no emitted host-call operands. Keep the
            # original edge open here; do not invent a probe from its callee ABI.
            continue
        # Literal arguments are retained. Other values are explicit fixtures,
        # not a claim about runtime allocation or receiver provenance.
        from call_closure_shapes import integer
        expressions = shape.get('argument_expressions', [])
        args = [integer(e) if integer(e) is not None else 0x61000000+0x1000*(i+1)
                for i,e in enumerate(expressions)]
        query = dict(caller=edge['caller'],target=edge['target'],argc=shape['argc'],
                     receiver=shape['receiver'],arguments=args)
        queries.append((edge,query))
    answers = run(binary,[q for _,q in queries])
    served=[]
    for (edge,query),answer in zip(queries,answers):
        edge['native_route_probe'] = dict(request=query,answer=answer,
            contract='Compiled retail production route with nonexecuting native effects. Dynamic receiver, allocation, byte/value domains and return effects are not proved.')
        if answer['outcome']=='served-native-route' and answer['fault']==0:
            edge['outcome']='served-native-route'
            served.append((edge,query,answer))
    # Causal controls: removing the installed callback must remove its route;
    # closure and malformed input/decompression shapes must refuse. The exact
    # destination identifiers come from successful production executions above.
    controls=[]
    for edge,query,answer in served:
        controls.append((dict(query,closed=1),'refused'))
        if answer['route']=='native-window-input':
            controls += [(dict(query,disable_game_service=1),'owner-unresolved'),
                (dict(query,argc=1,arguments=[0x100]),'refused'),
                (dict(query,bad_window=1),'refused'),(dict(query,no_window=1),'refused')]
        elif answer['route']=='native-bmp':
            controls.append((dict(query,disable_dependency=1),'refused'))
        elif answer['route']=='native-windows-process-unavailable':
            controls += [(dict(query,argc=1,arguments=query['arguments'][:1]),'refused'),
                         (dict(query,strings={}),'refused')]
        elif answer['route']=='native-rect-constructor':
            controls += [(dict(query,argc=0,arguments=[]),'refused'),
                         (dict(query,receiver=0),'refused'),(dict(query,no_rect=1),'refused')]
        elif answer['route']=='native-zlib':
            controls += [(dict(query,argc=3,arguments=query['arguments'][:3]),'refused'),
                         (dict(query,receiver=0x61000000),'refused')]
        elif answer['route'] in ('native-world-teardown','native-mask-teardown'):
            controls += [(dict(query,disable_game_service=1),'owner-unresolved'),
                         (dict(query,argc=1,arguments=[0]),'refused')]
            if answer['route']=='native-mask-teardown':
                controls.append((dict(query,bad_mask_table=1),'owner-unresolved'))
    controls.append((dict(target=0x4fffff,argc=0,receiver=0),'transport-only'))
    control_answers=run(binary,[q for q,_ in controls])
    for (query,expected),answer in zip(controls,control_answers):
        if answer['outcome']!=expected:
            raise ValueError(f'Native route negative control failed: {query}: {answer}; expected {expected}')
    queue=json.loads((root/'tools/queue.json').read_text())['tasks']
    recovery={}
    for task in queue:
        if task['state'] not in ('open','taken','blocked'):continue
        for batch in task.get('call_closure_recovery_batches',[]):
            if not 5<=len(batch['targets'])<=15:
                raise ValueError('Call closure recovery batches must have 5 to 15 targets')
            for target in batch['targets']:recovery[int(target,16)]=task['id']
    multiplayer = multiplayer_exclusions(root,cohort,body,digest)
    remaining=[r for r in cohort if r['outcome']=='owner-unresolved']
    for edge in remaining:
        if edge['target'] in recovery:edge['recovery_task']=recovery[edge['target']]
    # A typed legacy call is not a canonical ClawHost call, but the app can
    # adapt it back into one. That boundary precludes a blanket vacuity claim.
    interface=(root/'Sources/ClawNativeMenuInterface.swift').read_text()
    adapter=body(interface,'            if f == 0x4cdd30')
    # Start after the initializer-list default ({} is not the function body).
    legacy=body((root/'Sources/WorldFileRuntime.cpp').read_text(),'uint32_t *temporary = nullptr)')
    if 'owner.resources.invoke(e.function,e.receiver,args)' not in adapter or 'return r.dependency(r.c, &c, r.user)' not in legacy:
        raise ValueError('Legacy host-call boundary changed; review absence proof before reclassifying')
    legacy_proof=dict(status='not-proved',reclassified_edges=0,
        retained_edges=sum(r['outcome']=='caller-owner-unresolved' for r in rows),
        reason='The app installs a typed legacy world dependency that forwards original game addresses into resources.invoke. Absence of canonical ownership alone does not establish absence of emitted host calls.',
        source_inputs={p:digest(root/p) for p in ('Sources/ClawNativeMenuInterface.swift','Sources/WorldFileRuntime.cpp')},
        adapter_sha256=hashlib.sha256(adapter.encode()).hexdigest(),
        legacy_call_sha256=hashlib.sha256(legacy.encode()).hexdigest())
    return dict(selected_edges=len(cohort),served_edges=len(served),
        scope='Retail native routing only; legacy destination effects, allocation/value domains and full call closure remain separate.',
        served_routes=sorted({a['route'] for _,_,a in served}),
        remaining_edges=len(remaining),remaining_targets=sorted({hex(e['target']) for e in remaining}),
        queued_edges=sum('recovery_task' in e for e in remaining),
        unqueued_edges=[e['original_site'] for e in remaining if 'recovery_task' not in e],
        # Queue coverage helps schedule recovery; it does not supply a compiled
        # destination for an admitted caller. Closure requires no such edges.
        completion_obligation_met=not remaining,
        multiplayer_exclusion=multiplayer,
        legacy_caller_proof=legacy_proof,
        native_rectangle_checks=dict(positive=[dict(request=q,answer=a) for q,a in zip(rect_queries,rect_answers)],
                                     malformed_refusals=5),
        negative_controls=[dict(request=q,expected=expected,answer=a) for (q,expected),a in zip(controls,control_answers)],
        probe=str(binary))
