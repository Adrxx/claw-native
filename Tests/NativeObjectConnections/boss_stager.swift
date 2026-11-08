import Foundation

// Legacy prerequisite diagnostic under BOSS_STAGER_AUDIO_AUDIT.
// The joined scene comparison is defined below for the normal connection runner.
// Rebuild from the repository root in zsh (current cache paths are discovered):
// objects=(${(f)"$(work/test-env/bin/python -m tools.claw.native_objects --dir work/native-player-check --jobs 1)"})
// sources=(${(f)"$(work/test-env/bin/python -c 'import re; from pathlib import Path; print("\n".join(dict.fromkeys(re.findall(r"Sources/[A-Za-z0-9]+\.swift", Path("scripts/check-native-player.sh").read_text()))))')"})
// adapters=(${(f)"$(work/test-env/bin/python Tests/NativeObjectConnections/compare.py adapters)"})
// sources=(${(u)sources} ${adapters:|sources} Sources/ClawNativeMfcLocks.swift Sources/ClawNativeMfcMemory.swift)
// xcrun swiftc -D BOSS_STAGER_AUDIO_AUDIT -import-objc-header Sources/Claw-Bridging-Header.h $sources Tests/NativeObjectConnections/boss_stager.swift $objects -lc++ -lz -o work/native-object-connections/boss_stager/audio-allocation-audit
// work/native-object-connections/boss_stager/audio-allocation-audit work/native-object-connections/boss_stager
#if BOSS_STAGER_AUDIO_AUDIT
@main struct BossStagerAudioAllocationAudit {
    static func main() throws {
        let directory = URL(fileURLWithPath: CommandLine.arguments[1])
        let heap = ClawTokenHeap()
        let audio = try ClawNativeAudio(root: URL(fileURLWithPath: "App/GameData"), outputEnabled: false, sharedHeap: heap)
        guard let sound = audio.resolve(name: "GAME_SDPT2"),
              let manager = heap.lookup(audio.managerIdentity, words: 32),
              let pool = heap.lookup(sound.voicePoolToken, words: 14) else { fatalError("Original GAME_SDPT2 resource required") }
        precondition(pool[12] == 0 && pool[13] == 0, "Fresh source voice list")
        let availability = manager[30]
        precondition(availability != 0)
        let imports = Dictionary(uniqueKeysWithValues: ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map {
            ($0.element, UInt32(0x710000 + $0.offset * 4))
        })
        var profiles: [[String: Any]] = []
        for enabled in [false, true] {
            manager[30] = enabled ? availability : 0
            let host = ClawNativeCanonicalHost(heap: heap)
            host.stacklessCallerReserve = 0x40
            let memory = try ClawNativeMfcMemory(host: host,
                sha256: "350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263",
                importTargets: imports, allocationBase: 0x68000000)
            var calls: [[String: Any]] = [], allocations: [[String: Any]] = []
            host.observer = { call in
                if [UInt32(0x4b45f0), 0x4b4430, 0x4b42e0, 0x4f63ec].contains(call.function) {
                    let arguments = withUnsafeBytes(of: call.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(call.argumentCount))) }
                    calls.append(["function": call.function, "receiver": call.receiver, "arguments": arguments])
                }
            }
            memory.afterService = { function, arguments, result in
                allocations.append(["function": function, "arguments": arguments, "result": result])
            }
            let ranges: [(UInt32, UInt32)] = [(audio.managerIdentity, 128), (sound.voicePoolToken, 56), (sound.resourceToken, 64)]
            let segments: [[String: Any]] = ranges.map { address, count in
                let p = heap.lookupBytes(address, count: count)!
                return ["address": address, "hex": UnsafeBufferPointer(start: p, count: Int(count)).map { String(format: "%02x", $0) }.joined()]
            }
            var call = ClawCall()
            call.function = 0x4b45f0; call.receiver = sound.voicePoolToken
            call.argumentCount = 4; call.arguments.0 = 100
            var completion: ClawNativeCanonicalHost.Completion?
            let accepted = host.withObjectAllocation(provider: memory) { completion = host.invoke(call) } != nil
            profiles.append(["name": enabled ? "fresh-enabled-pool" : "disabled-manager-control",
                "enabled": enabled, "root": call.function, "receiver": call.receiver,
                "arguments": [100, 0, 0, 0], "segments": segments,
                "native": ["scopeAccepted": accepted, "completed": completion?.completed ?? false,
                    "eax": completion?.eax as Any? ?? NSNull(), "faultAddress": host.fault?.address as Any? ?? NSNull(),
                    "diagnostic": host.fault.map { String(describing: $0.diagnostic) } ?? "",
                    "calls": calls, "allocations": allocations]])
        }
        manager[30] = availability
        try JSONSerialization.data(withJSONObject: ["command": "boss-stager-audio-allocation-audit",
            "nativeJoinExecuted": false, "resource": "GAME_SDPT2", "profiles": profiles], options: [.prettyPrinted, .sortedKeys])
            .write(to: directory.appendingPathComponent("audio-allocation-native.json"))
        print("Native BossStager audio prerequisite profiles: \(profiles.count)")
    }
}
#endif

#if !BOSS_STAGER_AUDIO_AUDIT
private func bsHex(_ data: Data) -> String {
    let digits = Array("0123456789abcdef".utf8)
    var output = [UInt8](repeating:0,count:data.count*2)
    for (i,b) in data.enumerated() { output[i*2]=digits[Int(b >> 4)];output[i*2+1]=digits[Int(b & 15)] }
    return String(decoding:output,as:UTF8.self)
}
private final class StagerAudioWitness: ClawNativeCanonicalHost.ObjectAudioProvider {
    let audio: ClawNativeAudio
    var events: [[String: Any]] = []
    init(_ audio: ClawNativeAudio) { self.audio = audio }
    func validAudioBinding(for host: ClawNativeCanonicalHost) -> Bool { audio.validAudioBinding(for:host) }
    func ownsAudioPool(_ token: UInt32) -> Bool { audio.ownsAudioPool(token) }
    func retainAudioAllocation(_ token: UInt32, provider: ClawNativeCanonicalHost.ObjectAllocationProvider) -> Bool { audio.retainAudioAllocation(token,provider:provider) }
    func audioPhysical(_ call: ClawCall, host: ClawNativeCanonicalHost) -> UInt32? {
        let a = withUnsafeBytes(of:call.arguments) { Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount))) }
        let result = audio.audioPhysical(call,host:host)
        if call.function != 0x4a30e0 {
            var event: [String:Any] = ["function":call.function,"arguments":a,"result":result as Any? ?? NSNull()]
            if call.function == 0x71020014 || [UInt32(0x71010018),0x7101001c,0x71010020,0x71010024].contains(call.function),
               let output = host.bytes(a.last!,count:4) { event["output"] = UnsafeRawPointer(output).loadUnaligned(as:UInt32.self) }
            events.append(event)
        }
        return result
    }
}
func runConnection(_ directory: URL) throws {
    let root = URL(fileURLWithPath:"App/GameData"), level = try ClawLevelScene(root:URL(fileURLWithPath:"App/GameData"),level:2)
    let assets = try ClawPlayerAssets(root:root)
    let runtime = ClawNativeScene(player:try ClawNativePlayer(world:level.world,assets:assets,level:2),clock:{1000})
    try runtime.loadRecoveredObjects(world:level.world,root:root,level:2)
    let connections = runtime.objectConnections!, body = connections.adapter("boss_stager") as! ClawNativeBossStager
    connections.recordsTrace = true
    let record = level.world.planes.flatMap(\.objects).first { $0.logic == "BossStager" }!
    func attach() -> UInt32 {
        let before = body.tokens, plane = runtime.heap.lookup(runtime.worldIdentity,words:24)![23]
        _ = runtime.loadGridObject(record,world:level.world,plane:plane)
        guard let actor = body.tokens.subtracting(before).first else { fatalError("BossStager attachment: \(runtime.fault) \(String(describing:connections.host.fault))") }
        return actor
    }
    let actor = attach(), heap = runtime.heap, state = heap.lookup(actor+0x6c,words:1)![0]
    // The existing Raux owner creates the live boss and publishes 5349dc.
    let raux = (connections.adapter("raux") as! ClawNativeRaux).tokens.first!
    runtime.gameplay[0x47e210]?(raux)
    precondition(runtime.fault == 0 && heap.lookup(0x5349dc,words:1)![0] == raux)
    // Preload physical assets before exporting the original boundary graph.
    for name in ClawNativeBossStager.names.values {
        if name == "LEVEL_BOSSNAME" || name == "GAME_BOSSBAR" { _ = try runtime.objectResources?.images(name:name) }
        else if name == "CLAW_STAND" { _ = try runtime.objectResources?.sequence(name:name) }
        else { _ = runtime.player.audio?.resolve(name:name) }
    }
    precondition(body.synchronize())
    let audio = StagerAudioWitness(runtime.player.audio!); body.audioProvider = audio
    var allocations: [[String:UInt32]] = []
    body.memory!.afterService = { f,a,t in if f == 0x4a48e0 { allocations.append(["token":t,"count":a[0]]) } }
    var profiles: [[String:Any]] = []
    func segment(_ token:UInt32,_ count:UInt32)->[String:Any] {
        ["address":token,"hex":bsHex(Data(bytes:heap.lookupBytes(token,count:count)!,count:Int(count))) ]
    }
    func dispatch(_ f:UInt32,_ target:UInt32) {
        var q = ClawSceneActorCall();q.function=f;q.argumentCount=1;q.arguments.0=target
        _ = runtime.actorHost.call!(runtime.actorHost.context,q)
    }
    var failed = false
    let scenarios: [(UInt32,UInt32,UInt32,UInt32,UInt32)] = [
        (0x48ded0,0,0,0,0),(0x48ded0,8000,960,160,0),
        (0x48ded0,8001,960,100,0),(0x48ded0,8001,960,160,0),
        (0x48ded0,8002,100,160,0),(0x48ded0,8002,960,160,0),
        (0x48ded0,8003,960,160,0),(0x48ded0,8003,960,160,1),
        (0x48ded0,8004,960,160,0),(0x48ded0,8005,960,160,0),(0x48ded0,8006,960,160,0),
        (0x48ded0,8007,960,160,0),(0x48ded0,8007,960,160,1),
        (0x48ded0,8008,960,160,0),(0x48ded0,8008,960,160,1),
        (0x48e430,1,960,160,0),(0x48e430,2,960,160,0),(0x48e430,3,960,160,0)]
    for (function,mode,x,y,option) in scenarios {
        if function == 0x48ded0 { heap.lookup(state+0x1c,words:1)![0]=mode }
        else {
            heap.lookup(0x10002000+0xcc,words:1)![0]=mode
            if mode == 1 { runtime.hud!.timerRemaining=UInt32.max-15 }
        }
        let profile=heap.lookup(0x537960,words:1)![0]
        heap.lookup(profile+0xbc,words:1)![0]=option
        heap.lookup(actor+0x50,words:1)![0]=y;heap.lookup(actor+0x4c,words:1)![0]=x
        precondition(body.synchronize())
        var timing=ClawPlayerDeathCommandGlobals();runtime.captureDeathTiming(&timing)
        timing.animation.deltaMilliseconds=17;runtime.publishDeathTiming(timing)
        heap.lookup(0x5430c4,words:1)![0]=17
        let image=try heap.checkpoint().image
        // Physical pixels and PCM payloads are not read by this callback graph.
        // All token metadata, tables and source globals retain exact native bytes.
        let initial=image.allocations.filter { $0.byteCount <= 65536 }.map { ["address":$0.token,"hex":bsHex($0.bytes.prefix(Int($0.byteCount)))] as [String:Any] }
        let callStart=connections.calls.count, bindingStart=body.resourceBindings.count
        allocations=[];audio.events=[]
        dispatch(function,actor)
        print("BossStager state \(mode): fault \(runtime.fault) \(String(describing:connections.host.fault))")
        let calls=connections.calls.dropFirst(callStart).map { c -> [String:Any] in
            let count=c.function == 0x4f6286 ? 1:Int(c.argumentCount)
            return ["function":c.function,"receiver":c.receiver,"arguments":withUnsafeBytes(of:c.arguments){Array($0.bindMemory(to:UInt32.self).prefix(count))}]
        }
        var finalRanges: [(UInt32,UInt32)] = [(actor,0x1b4),(state,0x174),(raux,0x1b4),(0x10002000,0x1b4),
            (0x10003000,0x174),(0x10005000,0x174),(runtime.ownerIdentity,0x778),
            (0x52be14,8),(0x53c9c0,4),(0x53c9a0,4),(0x53c9a4,4),(0x53c9a8,4),(0x53c9ac,4),(0x53c9b0,4),(0x53c9f8,4),(0x53c260,4),(0x52c6f0,8),(0x534e60,24)]
        // Distinct pre-existing projected words may occupy different allocations.
        finalRanges.removeAll { heap.lookupBytes($0.0,count:$0.1) == nil }
        for a in allocations where a["token"]! != 0 { finalRanges.append((a["token"]!,a["count"]!)) }
        for token in runtime.speech!.actorTokens {
            finalRanges.append((token,0x1b4));finalRanges.append((heap.lookup(token+0x6c,words:1)![0],0x174))
        }
        profiles.append(["mode":mode,"function":function,"eax":body.callbackCompletion?.eax as Any? ?? NSNull(),"actor":actor,"initial":initial,"bindings":Array(body.resourceBindings.dropFirst(bindingStart)),
            "calls":calls,"allocations":allocations,"audio":audio.events,"final":finalRanges.map {segment($0.0,$0.1)},
            "fault":runtime.fault,"completed":body.callbackCompletion?.completed ?? false])
        if connections.host.fault != nil {failed=true;break}
        if mode == 0 { _=heap.allocate(bytes:64) } // Real intervening scene allocation must not collide with a voice.
    }
    var controls:[String:Bool]=[:]
    controls["shared_scene_heap"] = heap === connections.host.heap && runtime.player.audio!.validAudioBinding(for:connections.host)
    controls["real_boss_published"] = heap.lookup(0x5349dc,words:1)![0] == raux
    controls["shared_hud_timer"] = runtime.hud!.timerRemaining == heap.lookup(0x53c9f8,words:1)![0]
    let acceptedFaults=runtime.fault, acceptedUnresolved=runtime.unresolvedDependencies.sorted()
    if !failed {
        let secondary=heap.lookup(actor+0x78,words:1)![0]
        controls["real_contact_binding"] = secondary != 0 && heap.lookup(secondary+0x10,words:1)?[0] == 0x48e430
        controls["contact_timer_wraps"] = heap.lookup(0x53c9f8,words:1)![0] == (UInt32.max-15) &+ 240000
        controls["real_meter_children"] = body.childTokens.count == 2 && body.childTokens.allSatisfy {
            let state=heap.lookup($0+0x6c,words:1)![0]
            return body.memory!.ownsObjectAllocation($0,count:0x1b4) && body.memory!.ownsObjectAllocation(state,count:0x174) && heap.lookup(state+0x10,words:1)![0] == 0x491fa0
        }
        var forged=ClawCall();forged.function=0x4f6286;forged.argumentCount=2
        controls["out_of_callback_service_rejected"] = body.service(forged) == nil
        let children=body.childTokens
        func destroy(_ token:UInt32) {
            let member=token+0x88
            if heap.lookup(member+12,words:1)![0] != 0 {
                let plane=heap.lookup(runtime.worldIdentity+0x5c,words:1)![0], grid=heap.lookup(plane+0xb0,words:1)![0]
                let flags=heap.lookup(token+8,words:1)![0], index:UInt32=flags & 0x800000 != 0 ? 1:flags & 0x1000000 != 0 ? 2:0
                let layer=heap.lookup(grid+(index+1)*4,words:1)![0]
                _=runtime.spatial(0x4f4680,receiver:layer,arguments:[member])
            }
            var q=ClawSceneActorCall();q.function=0x4c9be0;q.receiver=token;q.argumentCount=1;q.arguments.0=1
            _=runtime.performService(q)
        }
        destroy(actor)
        controls["parent_retirement_preserves_children"] = runtime.fault == 0 && !body.tokens.contains(actor) && body.childTokens == children && children.allSatisfy { body.memory!.ownsObjectAllocation($0,count:0x1b4) }
        // Keep unrelated actors waiting at this controlled frame boundary.
        // The real scheduler then unlinks/deletes the flagged meter children.
        for token in runtime.actorTokens {
            let state=heap.lookup(token+0x6c,words:1)![0]
            heap.lookup(state+0x20,words:1)![0]=UInt32.max
        }
        for child in children { heap.lookup(child+8,words:1)![0] |= 0x10000 }
        let deleted=runtime.actorFrame(container:runtime.containerToken,refresh:0)
        controls["meter_teardown_releases_scene_ledger"] = deleted && runtime.fault == 0 && body.childTokens.isEmpty && children.allSatisfy { heap.lookup($0,words:1) == nil }
        let recreated=attach()
        dispatch(0x48ded0,recreated)
        print("BossStager recreation actor \(actor) -> \(recreated), owner \(String(describing:connections.owner(of:recreated))), fault \(runtime.fault), canonical \(String(describing:connections.host.fault))")
        controls["recreation_has_fresh_owner"] = runtime.fault == 0 && recreated != actor && body.tokens.contains(recreated) && connections.owner(of:recreated) == "boss_stager"
        let recreatedState=heap.lookup(recreated+0x6c,words:1)![0]
        heap.lookup(recreatedState+0x1c,words:1)![0]=8000
        connections.host.dependency=nil
        dispatch(0x48ded0,recreated)
        controls["missing_service_fault"] = connections.host.fault?.diagnostic == .missingDependency && connections.host.fault?.address == 0x4f6286 && runtime.fault != 0
    }
    if !failed {
        let isolated=ClawNativeScene(player:try ClawNativePlayer(world:level.world,assets:assets,level:2),clock:{1000})
        let election=ClawNativeObjectConnections.elections.first { $0.family == "boss_stager" }!
        try isolated.loadRecoveredObjects(world:level.world,root:root,level:2,objectElections:[election])
        let bridge=isolated.objectConnections!, adapter=bridge.adapter("boss_stager") as! ClawNativeBossStager
        let before=adapter.tokens, plane=isolated.heap.lookup(isolated.worldIdentity,words:24)![23]
        _=isolated.loadGridObject(record,world:level.world,plane:plane)
        let target=adapter.tokens.subtracting(before).first!, privateToken=isolated.heap.lookup(target+0x6c,words:1)![0]
        let bytes=Data(bytes:isolated.heap.lookupBytes(privateToken,count:0x174)!,count:0x174)
        isolated.heap.free(privateToken)
        bytes.withUnsafeBytes { isolated.heap.storeBytes(token:privateToken,count:0x174).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:0x174) }
        var q=ClawSceneActorCall();q.function=0x48ded0;q.argumentCount=1;q.arguments.0=target
        _=isolated.performService(q)
        controls["replacement_private_identity_rejected"] = bridge.host.fault?.diagnostic == .unsupportedABI && isolated.fault != 0
    }
    try JSONSerialization.data(withJSONObject:["profiles":profiles,"trace":connections.trace,"controls":controls,
        "faults":acceptedFaults,"unresolvedDependencies":acceptedUnresolved],options:[.sortedKeys])
        .write(to:directory.appendingPathComponent("native-connection.json"))
    precondition(!failed,"Joined callback must complete")
}
#endif
