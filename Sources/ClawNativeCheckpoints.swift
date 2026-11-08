import Darwin
import Foundation

// Ordinary death-checkpoint and persistent super-checkpoint startup, scanner
// contact, save/cache and RISE/WAVE services remain owned by recovered code.
// The complete application startup/selected-save restoration remains separate.
final class ClawNativeCheckpoints {
    // MARK: - Actor registration and owned state

    static let callbacks: Set<UInt32> = [0x422ef0, 0x4232c0, 0x4232e0]
    weak var scene: ClawNativeScene?
    let globals = UnsafeMutablePointer<ClawCheckpointGlobals>.allocate(capacity: 1)
    private(set) var tokens: Set<UInt32> = []
    private(set) var originalRecords: [UInt32: ClawInteractionActor] = [:]
    private(set) var initialized: Set<UInt32> = [], contacted: Set<UInt32> = []
    private(set) var fault: UInt32 = 0, unresolved: Set<UInt32> = []
    private(set) var missingSpans: [(UInt32, UInt32)] = []
    var calendarTime: () -> UInt32 = {
        UInt32(truncatingIfNeeded: Int64(Date().timeIntervalSince1970))
    }
    // Guest token for nine calendar fields; globals is owned native storage.
    private let tmToken: UInt32
    private(set) var serviceCounts: [UInt32: UInt64] = [:]

    // MARK: - Lifecycle

    init(scene: ClawNativeScene) {
        self.scene = scene
        tmToken = scene.heap.allocate(bytes: 36)
        globals.initialize(to: ClawCheckpointGlobals())
        globals.pointee.playerToken = 0x1000_2000
        globals.pointee.timerBonus = 25000
    }
    deinit {
        globals.deinitialize(count: 1)
        globals.deallocate()
    }

    // MARK: - Actor registration and recovered entry

    func attach(_ snapshot: ClawInteractionActor) {
        tokens.insert(snapshot.token)
        originalRecords[snapshot.token] = snapshot
    }
    func remove(_ token: UInt32) { tokens.remove(token) }
    func callback(_ function: UInt32, actor: UInt32) {
        guard let scene, scene.speech != nil else {
            fault = 1
            return
        }
        globals.pointee.managerToken = scene.heap.lookup(scene.ownerIdentity, words: 2)![1]
        globals.pointee.animationDelta = scene.animationDelta
        globals.pointee.tick = scene.gameTime
        globals.pointee.audioPosition = scene.player.audio?.routing.masterVolume ?? 0
        var host = ClawSceneActorHost()
        // The synchronous entry borrows self; neither callback retains the host.
        host.context = Unmanaged.passUnretained(self).toOpaque()
        host.lookup = { user, token, wordCount in
            guard let user else { return nil }
            let checkpoints = Unmanaged<ClawNativeCheckpoints>.fromOpaque(user)
                .takeUnretainedValue()
            let span =
                checkpoints.scene?.heap.lookup(token, words: wordCount)
                ?? checkpoints.scene?.player.audio?.speechMetadata(token: token, words: wordCount)
            if span == nil { checkpoints.missingSpans.append((token, wordCount)) }
            return span
        }
        var context = ClawCheckpointContext(
            scene: host, globals: globals, composeAnimation: 1,
            composeContactBinding: 1, composeSave: 1, composeSaveCache: 1, fault: 0)
        var argument = actor
        var result: UInt32 = 0
        let wasUninitialized = scene.snapshotActor(actor)?.primary.7 == 0
        let supported = withUnsafePointer(to: &argument) {
            claw_checkpoint_entry(
                function, 0, $0, 1, &context, nativeCheckpointDependency,
                Unmanaged.passUnretained(self).toOpaque(), &result)
        }
        if context.fault != 0 {
            print(
                "CHECKPOINT SOURCE FAULT", String(function, radix: 16), String(actor, radix: 16),
                context.fault, missingSpans.map { (String($0.0, radix: 16), $0.1) }, unresolved)
        }
        fault = max(fault, context.fault)
        if supported != 1 { unresolved.insert(function) }
        if wasUninitialized && fault == 0 { initialized.insert(actor) }
        if [UInt32(0x422ff0), 0x4231a0].contains(function) && fault == 0 {
            contacted.insert(actor)
        }
    }

    // MARK: - Native resource, save, clock and audio services

    fileprivate func dependency(_ event: ClawCheckpointCall) -> UInt32 {
        guard let scene else {
            fault = 1
            return 0
        }
        serviceCounts[event.function, default: 0] &+= 1
        switch event.function {
        case 0x4f6286:
            guard let name = event.name else {
                fault = 1
                return 0
            }
            let resourceName = String(cString: name)
            if resourceName == "CheckpointAttack" || resourceName == "SuperCheckpointAttack" {
                return scene.entry(named: resourceName)
            }
            do { return try scene.objectResources?.sequence(name: resourceName)?.token ?? 0 } catch
            {
                fault = 1
                return 0
            }
        case 0x4f63ec: return scene.heap.allocate(bytes: event.arguments.0)
        case 0x4f6428:
            scene.heap.free(event.arguments.0)
            return 0
        case 0x49bbc0:
            guard let saves = scene.saves, event.receiver == saves.managerToken else {
                fault = 1
                return 0
            }
            let result = saves.entry(event.function)
            fault = max(fault, saves.fault)
            return result
        case 0x42abf0: return scene.resetSourceClock(application: event.receiver)
        case 0x42af70:
            guard let messages = scene.statusMessages else {
                fault = 1
                return 0
            }
            let result = messages.entry(
                event.function, receiver: event.receiver, arguments: [event.arguments.0])
            fault = max(fault, messages.fault)
            return result
        case 0x4a3b10:
            // Calendar seconds use the original signed 32-bit bit pattern below.
            let value = calendarTime()
            event.buffers.0?.pointee = value
            return value
        case 0x4a5c60:
            guard let value = event.buffers.0?.pointee,
                let calendarWords = scene.heap.lookup(tmToken, words: 9)
            else {
                fault = 1
                return 0
            }
            var seconds = time_t(Int32(bitPattern: value))
            var date = tm()
            guard localtime_r(&seconds, &date) != nil else {
                fault = 1
                return 0
            }
            let fields = [
                date.tm_sec, date.tm_min, date.tm_hour, date.tm_mday, date.tm_mon, date.tm_year,
                date.tm_wday, date.tm_yday, date.tm_isdst,
            ]
            for (fieldIndex, field) in fields.enumerated() {
                calendarWords[fieldIndex] = UInt32(bitPattern: field)
            }
            return tmToken
        case 0x4b45f0:
            return scene.player.audio?.playVoicePool(
                event.receiver,
                request: ClawAudioRequest(
                    volume: event.arguments.0,
                    pan: event.arguments.1, pitchPercent: event.arguments.2,
                    looping: event.arguments.3)) ?? 0
        case 0x4208e0:
            return scene.player.audio?.play(resource: event.receiver, volume: event.arguments.0)
                ?? 0
        case 0x4c88e0:
            return scene.player.audio?.playSpatial(
                resource: event.receiver, sourceX: event.arguments.0,
                referenceX: event.arguments.1, clampDistance: event.arguments.2,
                panDistance: event.arguments.3) ?? 0
        default:
            unresolved.insert(event.function)
            fault = 1
            return 0
        }
    }
}
private let nativeCheckpointDependency: ClawCheckpointDependency = { _, event, user in
    guard let event, let user else { return 0 }
    return Unmanaged<ClawNativeCheckpoints>.fromOpaque(user).takeUnretainedValue().dependency(
        event.pointee)
}

// MARK: - Snapshot persistence (property names are saved keys)

extension ClawNativeCheckpoints {
    struct SavedState: Codable, Equatable {
        struct Span: Codable, Equatable { let token: UInt32, words: UInt32 }
        let globals: ClawSnapshotValue<ClawCheckpointGlobals>
        let tokens: Set<UInt32>, initialized: Set<UInt32>, contacted: Set<UInt32>, fault: UInt32,
            unresolved: Set<UInt32>
        let originalRecords: [UInt32: ClawSnapshotValue<ClawInteractionActor>]
        let missingSpans: [Span], serviceCounts: [UInt32: UInt64], tmToken: UInt32
    }
    func savedState() -> SavedState {
        .init(
            globals: ClawSnapshotValue(globals.pointee), tokens: tokens, initialized: initialized,
            contacted: contacted,
            fault: fault, unresolved: unresolved,
            originalRecords: originalRecords.mapValues(ClawSnapshotValue.init),
            missingSpans: missingSpans.map { .init(token: $0.0, words: $0.1) },
            serviceCounts: serviceCounts, tmToken: tmToken)
    }
    func restoreState(_ saved: SavedState) throws {
        guard saved.tmToken == tmToken else { throw ClawSnapshotError.invalidState }
        globals.pointee = saved.globals.value
        tokens = saved.tokens
        initialized = saved.initialized
        contacted = saved.contacted
        fault = saved.fault
        unresolved = saved.unresolved
        originalRecords = saved.originalRecords.mapValues(\.value)
        missingSpans = saved.missingSpans.map { ($0.token, $0.words) }
        serviceCounts = saved.serviceCounts
        // calendarTime is an external calendar provider, rebound by the scene
        // factory. No closure or host address belongs in this state image.
    }
}
extension ClawCheckpointGlobals: ClawSnapshotNativeValue {}
