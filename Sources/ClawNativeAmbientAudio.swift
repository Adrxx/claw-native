import Foundation

// Complete source ambient object/list/voice/fade graph. PCM buffers, multimedia
// clock and COM calls remain named native transports, not replacement timers.
final class ClawNativeAmbientAudio {
    weak var scene:ClawNativeScene?
    private(set) var managerToken:UInt32 = 0
    private let backend = UnsafeMutablePointer<ClawAmbientAudioBackendContext>.allocate(capacity:1)
    private(set) var fault:UInt32 = 0, unresolved:Set<UInt32> = []
    private(set) var serviceCounts:[UInt32:UInt64] = [:]
    private(set) var physicalMethods:[UInt32:UInt64] = [:]
    private(set) var reports:[(line:UInt32,result:UInt32)] = []
    init(scene:ClawNativeScene) {
        self.scene = scene;backend.initialize(to:ClawAmbientAudioBackendContext())
        // Derived tables are actual source identities and method ordering.
        let tables:[(UInt32,[UInt32])] = [(0x50b004,[0x4022d0,0x402720]),(0x50b01c,[0x4022d0,0x402ac0]),(0x50b02c,[0x4022d0,0x402f10]),(0x513520,[0x4b4d80,0x4b4df0]),(0x513518,[0x4a3910,0x4a3910])]
        for (token,words) in tables {
            if scene.heap.lookup(token,words:UInt32(words.count)) == nil {
                let raw = scene.heap.store(token:token,words:words.count);words.withUnsafeBufferPointer{raw.update(from:$0.baseAddress!,count:words.count)}
            }
        }
        managerToken = scene.heap.allocate(bytes:48)
        guard scene.soundTriggers!.constructAmbientManager(managerToken,host:actorHost) else { fault = 1;return }
        let soundController = scene.heap.lookup(scene.sceneIdentity,words:12)![10]
        _ = scene.soundTriggers!.service(0x402240,receiver:managerToken,arguments:[soundController,100],host:actorHost)
        // Controller+2c is the actual existing audio collection identity.
        scene.heap.lookup(soundController,words:13)![11] = scene.player.audio?.managerIdentity ?? 0
        let application = scene.heap.lookup(scene.ownerIdentity,words:2)![1], app = scene.heap.lookup(application,words:77)!
        let previousBounds = app[23];app[23] = managerToken
        scene.heap.free(previousBounds)
        backend.pointee.scene = backendHost
    }
    deinit { backend.deinitialize(count:1);backend.deallocate() }
    var actorHost:ClawSceneActorHost {
        ClawSceneActorHost(context:Unmanaged.passUnretained(self).toOpaque(),lookup:ambientLookup,allocate:{user,bytes in
            guard let user else { return 0 };return Unmanaged<ClawNativeAmbientAudio>.fromOpaque(user).takeUnretainedValue().scene?.heap.allocate(bytes:bytes) ?? 0
        },free:{user,token in
            guard let user else { return };Unmanaged<ClawNativeAmbientAudio>.fromOpaque(user).takeUnretainedValue().scene?.heap.free(token)
        },call:nil,readClock:nil)
    }
    private var backendHost:ClawSceneActorHost {
        var host = actorHost
        host.allocate = {user,bytes in
            guard let user else { return 0 };return Unmanaged<ClawNativeAmbientAudio>.fromOpaque(user).takeUnretainedValue().scene?.player.audio?.ambientAllocate(bytes) ?? 0
        }
        host.free = {user,token in
            guard let user else { return };Unmanaged<ClawNativeAmbientAudio>.fromOpaque(user).takeUnretainedValue().scene?.player.audio?.ambientFree(token)
        }
        return host
    }
    fileprivate func lookup(_ token:UInt32,words:UInt32) -> UnsafeMutablePointer<UInt32>? {
        scene?.heap.lookup(token,words:words) ?? scene?.player.audio?.ambientMetadata(token:token,words:words)
    }
    func frame(_ receiver:UInt32,x:UInt32,y:UInt32) -> UInt32 {
        guard let scene,receiver == managerToken else { fault = 1;return 0 }
        return scene.soundTriggers!.service(0x4025c0,receiver:receiver,arguments:[x,y],host:actorHost)
    }
    func service(_ event:ClawSoundTriggerCall) -> UInt32? {
        let args = withUnsafeBytes(of:event.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(event.argumentCount)))}
        if event.function == 0x4a3050 { return scene?.nextRandom() ?? 0 }
        let functions:Set<UInt32> = [0x4f51c5,0x4f5212,0x4f5172,0x4b3dc0,0x4b3e30,0x4b3f40,0x4b3fe0,0x4b4110,0x4b4b80,0x4b4c10]
        guard functions.contains(event.function) else { return nil }
        serviceCounts[event.function,default:0] &+= 1
        var result:UInt32 = 0
        let accepted = args.withUnsafeBufferPointer {
            claw_ambient_audio_backend_entry(event.function,event.receiver,$0.baseAddress,UInt32($0.count),backend,
                nativeAmbientBackendDependency,Unmanaged.passUnretained(self).toOpaque(),&result)
        }
        fault = max(fault,backend.pointee.fault);if accepted != 1 { unresolved.insert(event.function) };return result
    }
    fileprivate func dependency(_ event:ClawAmbientAudioBackendCall) -> UInt32 {
        guard let scene else { fault = 1;return 0 }
        if event.bufferMethod != 0 {
            physicalMethods[event.bufferMethod,default:0] &+= 1
            return scene.player.audio?.ambientPhysical(event) ?? 0x80004005
        }
        if event.function == 0x546df0 { return scene.actorHost.readClock?(scene.actorHost.context) ?? 0 }
        if event.function == 0x4b4ed0 {
            reports.append((event.arguments.1,event.arguments.2))
            guard let audio = scene.player.audio else {fault = 1;return 0}
            audio.diagnosticReport(filename:event.arguments.0,line:event.arguments.1,result:event.arguments.2)
            fault = max(fault,audio.lifecycleFault)
            backend.pointee.fault = max(backend.pointee.fault,fault)
            return 0
        }
        unresolved.insert(event.function);fault = 1;return 0
    }
}
private let ambientLookup:@convention(c)(UnsafeMutableRawPointer?,UInt32,UInt32)->UnsafeMutablePointer<UInt32>? = {user,token,count in
    guard let user else { return nil };return Unmanaged<ClawNativeAmbientAudio>.fromOpaque(user).takeUnretainedValue().lookup(token,words:count)
}
private let nativeAmbientBackendDependency:ClawAmbientAudioBackendDependency = {_,event,user in
    guard let event,let user else { return 0 };return Unmanaged<ClawNativeAmbientAudio>.fromOpaque(user).takeUnretainedValue().dependency(event.pointee)
}

extension ClawNativeAmbientAudio {
    struct SavedState: Codable, Equatable {
        struct Report: Codable, Equatable { let line: UInt32, result: UInt32 }
        let manager: UInt32, fault: UInt32, unresolved: Set<UInt32>
        let maximumTraversal: UInt32, backendFault: UInt32
        let serviceCounts: [UInt32: UInt64], physicalMethods: [UInt32: UInt64], reports: [Report]
    }
    func savedState() -> SavedState {
        .init(manager: managerToken, fault: fault, unresolved: unresolved, maximumTraversal: backend.pointee.maximumTraversal,
            backendFault: backend.pointee.fault, serviceCounts: serviceCounts, physicalMethods: physicalMethods,
            reports: reports.map { .init(line: $0.line, result: $0.result) })
    }
    func restoreState(_ saved: SavedState) throws {
        guard saved.manager == managerToken else { throw ClawSnapshotError.invalidState }
        fault = saved.fault; unresolved = saved.unresolved; backend.pointee.maximumTraversal = saved.maximumTraversal
        backend.pointee.fault = saved.backendFault; serviceCounts = saved.serviceCounts; physicalMethods = saved.physicalMethods
        reports = saved.reports.map { ($0.line, $0.result) }
    }
}
