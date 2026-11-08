import Foundation

// Shared original Claw/NPC speech globals and registered dialog callbacks.
// Voice-pool metadata and CoreAudio output remain the existing audio transport.
final class ClawNativeSpeech {
    static let callbacks: Set<UInt32> = [0x48cc60, 0x48c630]
    static let services: Set<UInt32> = [0x48ce40, 0x48ceb0, 0x420370, 0x48cf50, 0x48cf90, 0x48c820, 0x48c8a0]
    weak var scene: ClawNativeScene?
    let globals = UnsafeMutablePointer<ClawEnemySpeechGlobals>.allocate(capacity: 1)
    private(set) var actorTokens: [UInt32] = []
    private(set) var fault: UInt32 = 0
    private(set) var unresolved: Set<UInt32> = []
    private(set) var serviceCounts: [UInt32: Int] = [:]
    private(set) var playRequests: [(pool: UInt32, volume: UInt32)] = []
    init(scene: ClawNativeScene) {
        self.scene = scene
        globals.initialize(to: ClawEnemySpeechGlobals())
        globals.pointee.managerToken = scene.heap.lookup(scene.ownerIdentity, words: 2)![1]
        globals.pointee.playerToken = 0x10002000
        globals.pointee.audioManagerToken = scene.player.audio?.managerIdentity ?? 0
    }
    deinit { globals.deinitialize(count: 1); globals.deallocate() }
    private func context() -> ClawEnemySpeechContext {
        globals.pointee.stageDelta = scene?.stageDelta ?? 0
        return ClawEnemySpeechContext(scene: actorHost, globals: globals, nameHint: nil, fault: 0)
    }
    @discardableResult func createControllers() -> Bool {
        guard let scene else { fault = 1; return false }
        for enemyProfile in [UInt32(0), 1] {
            var context = context()
            let token = scene.heap.withStableFreedStorage {
                claw_enemy_speech_create(scene.containerToken, enemyProfile, &context,
                    nativeSpeechDependency, Unmanaged.passUnretained(self).toOpaque())
            }
            fault = max(fault, context.fault)
            guard token != 0, fault == 0 else { return false }
            actorTokens.append(token)
        }
        return true
    }
    func service(_ function: UInt32, receiver: UInt32 = 0, arguments: [UInt32], name: String? = nil) -> UInt32? {
        guard Self.services.contains(function) || Self.callbacks.contains(function), let scene else { return nil }
        serviceCounts[function, default: 0] += 1
        var context = context(), result: UInt32 = 0
        func execute(_ hint: UnsafePointer<CChar>?) -> UInt32 {
            context.nameHint = hint
            let supported = scene.heap.withStableFreedStorage {
                arguments.withUnsafeBufferPointer {
                    claw_enemy_speech_entry(function, receiver, $0.baseAddress, UInt32($0.count), &context,
                        nativeSpeechDependency, Unmanaged.passUnretained(self).toOpaque(), &result)
                }
            }
            fault = max(fault, context.fault)
            if supported != 1 { unresolved.insert(function) }
            return result
        }
        let hint = name ?? ((function == 0x48ceb0) ? arguments.dropFirst().first.flatMap { clawOriginalResourceNames[$0] }
            : (function == 0x48c8a0 ? arguments.first.flatMap { clawOriginalResourceNames[$0] } : nil))
        if let hint { return hint.withCString { execute($0) } }
        return execute(nil)
    }
    var actorHost: ClawSceneActorHost {
        ClawSceneActorHost(context: Unmanaged.passUnretained(self).toOpaque(), lookup: { user, token, count in
            guard let user else { return nil }
            let speech = Unmanaged<ClawNativeSpeech>.fromOpaque(user).takeUnretainedValue()
            return speech.scene?.heap.lookup(token, words: count) ?? speech.scene?.player.audio?.speechMetadata(token: token, words: count)
        }, allocate: { user, bytes in
            guard let user else { return 0 }
            return Unmanaged<ClawNativeSpeech>.fromOpaque(user).takeUnretainedValue().scene?.heap.allocate(bytes: bytes) ?? 0
        }, free: { user, token in
            guard let user else { return }
            Unmanaged<ClawNativeSpeech>.fromOpaque(user).takeUnretainedValue().scene?.heap.free(token)
        }, call: { user, call in
            guard let user else { return 0 }
            let speech = Unmanaged<ClawNativeSpeech>.fromOpaque(user).takeUnretainedValue()
            let arguments = withUnsafeBytes(of: call.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(call.argumentCount))) }
            return speech.dependency(function: call.function, receiver: call.receiver, arguments: arguments,
                name: arguments.first.flatMap { ClawNativeSpeech.literalNames[$0] })
        }, readClock: { user in
            guard let user else { return 0 }
            let scene = Unmanaged<ClawNativeSpeech>.fromOpaque(user).takeUnretainedValue().scene
            return scene?.actorHost.readClock?(scene?.actorHost.context) ?? 0
        })
    }
    fileprivate func dependency(function: UInt32, receiver: UInt32, arguments: [UInt32], name: String?) -> UInt32 {
        guard let scene else { fault = 1; return 0 }
        switch function {
        case 0x4f6286:
            guard let token = arguments.first, let name = name ?? Self.literalNames[token] ?? clawOriginalResourceNames[token] else {
                unresolved.insert(function); fault = 1; return 0
            }
            if name == "ClawDialogSound" || name == "EnemyDialogSound" { return scene.entry(named: name) }
            do {
                if name == "GAME_EXCLAMATION" { return try scene.objectResources?.images(name: name)?.token ?? 0 }
                return scene.player.audio?.resolve(name: name)?.resourceToken ?? 0
            } catch { fault = 1; return 0 }
        case 0x4b45f0:
            guard arguments.count == 4 else { fault = 2; return 0 }
            playRequests.append((receiver, arguments[0]))
            return scene.player.audio?.playVoicePool(receiver, request: ClawAudioRequest(volume: arguments[0],
                pan: arguments[1], pitchPercent: arguments[2], looping: arguments[3])) ?? 0
        case 0x4a3050: return scene.nextRandom()
        default:
            if let value = service(function, receiver: receiver, arguments: arguments, name: name) { return value }
            // All remaining creation/lifetime callbacks retain their exact
            // SceneActorHost arguments and run through the owning scene.
            guard arguments.count <= 4 else { fault = 2; return 0 }
            var call = ClawSceneActorCall(); call.function = function; call.receiver = receiver
            call.argumentCount = UInt32(arguments.count)
            withUnsafeMutableBytes(of: &call.arguments) { raw in
                for (i, value) in arguments.enumerated() { raw.storeBytes(of: value, toByteOffset: i * 4, as: UInt32.self) }
            }
            return scene.actorHost.call?(scene.actorHost.context, call) ?? 0
        }
    }
    private static let literalNames: [UInt32: String] = [0x5223b8: "EnemyDialogSound", 0x5223cc: "ClawDialogSound", 0x52c580: "GAME_EXCLAMATION"]
}
private let nativeSpeechDependency: ClawEnemySpeechDependency = { _, event, user in
    guard let event, let user else { return 0 }
    let e = event.pointee
    let arguments = withUnsafeBytes(of: e.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(e.argumentCount))) }
    return Unmanaged<ClawNativeSpeech>.fromOpaque(user).takeUnretainedValue().dependency(function: e.function,
        receiver: e.receiver, arguments: arguments, name: e.name.map { String(cString: $0) })
}

extension ClawNativeSpeech {
    struct SavedState: Codable, Equatable {
        struct Play: Codable, Equatable { let pool: UInt32, volume: UInt32 }
        let globals: ClawSnapshotValue<ClawEnemySpeechGlobals>
        let actorTokens: [UInt32], fault: UInt32, unresolved: Set<UInt32>, serviceCounts: [UInt32: Int], playRequests: [Play]
    }
    func savedState() -> SavedState {
        .init(globals: ClawSnapshotValue(globals.pointee), actorTokens: actorTokens, fault: fault, unresolved: unresolved,
            serviceCounts: serviceCounts, playRequests: playRequests.map { .init(pool: $0.pool, volume: $0.volume) })
    }
    func restoreState(_ saved: SavedState) {
        globals.pointee = saved.globals.value; actorTokens = saved.actorTokens; fault = saved.fault; unresolved = saved.unresolved
        serviceCounts = saved.serviceCounts; playRequests = saved.playRequests.map { ($0.pool, $0.volume) }
    }
}
extension ClawEnemySpeechGlobals: ClawSnapshotNativeValue {}
