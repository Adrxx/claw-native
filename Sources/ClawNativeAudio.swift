import Foundation
import AVFoundation
import AudioToolbox
import CryptoKit

// Original resource/voice routines own metadata and list behavior. This host
// replaces Windows allocation, mapped files and DirectSound output. Its Float
// resampling/mixing and CoreAudio timing are not original DirectSound proof.
private final class ClawAudioHeap {
    struct Block {
        let pointer: UnsafeMutableRawPointer
        let size: Int
    }
    fileprivate var blocks: [UInt32: Block] = [:]
    fileprivate var next: UInt32 = 0x20000000
    private let shared: ClawTokenHeap?
    private var sharedAllocations: [UInt32: (count: UInt32, identity: ClawTokenHeap.AllocationIdentity)] = [:]
    init(shared: ClawTokenHeap? = nil) { self.shared = shared }
    func allocate(_ bytes: UInt32) -> UInt32 {
        if let shared {
            let token = shared.allocate(bytes: max(bytes, 4))
            if token != 0, let identity = shared.allocationIdentity(at: token, count: max(bytes, 4)) {
                sharedAllocations[token] = (max(bytes, 4), identity)
            }
            return token
        }
        let size = max(Int(bytes), 4), span = (size + 15) & ~15
        guard span < 0x10000000, UInt64(next) + UInt64(span) + 16 < 0xf0000000 else { return 0 }
        let token = next
        next += UInt32(span + 16)
        let pointer = UnsafeMutableRawPointer.allocate(byteCount: size, alignment: 16)
        memset(pointer, 0, size)
        blocks[token] = Block(pointer: pointer, size: size)
        return token
    }
    func bytes(_ token: UInt32, _ count: UInt32) -> UnsafeMutablePointer<UInt8>? {
        if let shared { return shared.lookupBytes(token, count: count) }
        if let block = blocks[token], Int(count) <= block.size {
            return block.pointer.assumingMemoryBound(to: UInt8.self)
        }
        for (base, block) in blocks where token >= base {
            let offset = Int(token - base)
            if offset <= block.size && Int(count) <= block.size - offset {
                return block.pointer.advanced(by: offset).assumingMemoryBound(to: UInt8.self)
            }
        }
        return nil
    }
    func words(_ token: UInt32) -> UnsafeMutablePointer<UInt32>? {
        if let shared { return shared.lookup(token, words: 1) }
        guard let block = blocks[token], block.size >= 4 else { return nil }
        return block.pointer.assumingMemoryBound(to: UInt32.self)
    }
    func free(_ token: UInt32) {
        if let shared {
            if let allocation = sharedAllocations.removeValue(forKey: token),
                shared.allocationIdentity(at: token, count: allocation.count) === allocation.identity
            {
                shared.free(token)
            }
            return
        }
        blocks.removeValue(forKey: token)?.pointer.deallocate()
    }
    var validOwnedStorage: Bool {
        guard let shared else { return true }
        return sharedAllocations.allSatisfy {
            shared.allocationIdentity(at: $0.key, count: $0.value.count) === $0.value.identity
        }
    }
    func savedAllocations() throws -> [UInt32: ClawSnapshotWitness] {
        guard let shared, blocks.isEmpty else { throw ClawSnapshotError.invalidState }
        return Dictionary(
            uniqueKeysWithValues: sharedAllocations.map { token, span in
                (token, ClawSnapshotWitness(heap: shared, token: token, count: span.count, identity: span.identity))
            })
    }
    func prepareRestore(_ value: [UInt32: ClawSnapshotWitness], plan: ClawTokenHeap.RestorePlan) throws -> () throws ->
        Void
    {
        guard let shared, blocks.isEmpty else { throw ClawSnapshotError.invalidState }
        try shared.validateRestore(plan)
        var restored: [UInt32: (count: UInt32, identity: ClawTokenHeap.AllocationIdentity)] = [:]
        for (token, witness) in value {
            guard witness.reference.token == token, !witness.reference.interior, witness.reference.count >= 4
            else { throw ClawSnapshotError.invalidState }
            restored[token] = (witness.reference.count, try witness.resolve(in: plan))
        }
        return { [self] in
            try shared.validateInstalledRestore(plan)
            sharedAllocations = restored
        }
    }
    deinit {
        for (token, allocation) in sharedAllocations
        where shared?.allocationIdentity(at: token, count: allocation.count) === allocation.identity {
            shared?.free(token)
        }
        for block in blocks.values { block.pointer.deallocate() }
    }
}

private final class ClawAudioSamples {
    let heap: ClawAudioHeap, token: UInt32, bytes: UInt32, channels: Int, bits: Int, sampleRate: UInt32
    var decoded: [Float] = []
    var digest = ""
    private var ownsStorage = true
    init(heap: ClawAudioHeap, bytes: UInt32, channels: Int, bits: Int, sampleRate: UInt32) {
        self.heap = heap
        self.bytes = bytes
        self.channels = channels
        self.bits = bits
        self.sampleRate = sampleRate
        token = heap.allocate(bytes)
    }
    init(restoring token: UInt32, heap: ClawAudioHeap, bytes: UInt32, channels: Int, bits: Int, sampleRate: UInt32) {
        self.heap = heap
        self.token = token
        self.bytes = bytes
        self.channels = channels
        self.bits = bits
        self.sampleRate = sampleRate
        ownsStorage = false
    }
    func acquireRestoredStorage() { ownsStorage = true }
    func relinquishRestoredStorage() { ownsStorage = false }
    func decode() -> Bool {
        guard let source = heap.bytes(token, bytes) else { return false }
        return decode(source: source)
    }
    func decode(source: UnsafePointer<UInt8>) -> Bool {
        let width = bits / 8
        guard width > 0, channels > 0,
            Int(bytes) % (width * channels) == 0
        else { return false }
        if ProcessInfo.processInfo.environment["CLAW_AUDIO_EVIDENCE"] == "1" {
            digest = SHA256.hash(data: Data(bytes: source, count: Int(bytes))).map { String(format: "%02x", $0) }
                .joined()
        }
        decoded = (0..<(Int(bytes) / width)).map { index in
            let p = source.advanced(by: index * width)
            if bits == 8 { return Float(Int(p[0]) - 128) / 128 }
            var word: UInt32 = 0
            for byte in 0..<width { word |= UInt32(p[byte]) << (byte * 8) }
            if bits < 32 && word & (1 << (bits - 1)) != 0 { word |= UInt32.max << bits }
            return Float(Int32(bitPattern: word)) / Float(pow(2.0, Double(bits - 1)))
        }
        return true
    }
    deinit { if ownsStorage { heap.free(token) } }
}

private final class ClawAudioBuffer {
    let samples: ClawAudioSamples
    var volume: Int32 = 0, pan: Int32 = 0, frequency: UInt32
    var playing = false, looping = false, cursor: Double = 0
    init(samples: ClawAudioSamples) {
        self.samples = samples
        frequency = samples.sampleRate
    }
}

final class ClawNativeAudio {
    // A resource loaded by another owner on the shared heap must be released
    // through that owner's ledger when recovered PCM loading consumes it.
    var releaseSharedAllocation: ((UInt32) -> Bool)?
    var observePhysical: (([String: Any]) -> Void)?
    private let sharedHeap: ClawTokenHeap?
    fileprivate var canonicalVoiceOwners: [UInt32: ClawNativeCanonicalHost.AudioAllocationProvider] = [:]
    fileprivate let heap: ClawAudioHeap
    fileprivate let pcm: UnsafeMutablePointer<ClawAudioPCMContext>
    fileprivate let lock = NSLock()
    fileprivate var buffers: [UInt32: ClawAudioBuffer] = [:]
    fileprivate var sounds: [String: ClawAudioSound] = [:]
    fileprivate var soundByToken: [UInt32: ClawAudioSound] = [:]
    fileprivate var tokensByName: [String: UInt32] = [:]
    fileprivate var namesByToken: [UInt32: String] = [:]
    fileprivate var nextName: UInt32 = 1
    fileprivate var soundTokens: [UInt32] = []
    fileprivate var engine: AVAudioEngine?
    fileprivate var sourceNode: AVAudioSourceNode?
    // Agent launches (--mute or any automated check) stay inaudible; mixing continues.
    // This check uses a real, unmuted AVAudioEngine graph in manual offline
    // mode. Its output never connects to a device, even with --mute present.
    static let offlineCheckpointCheck = ProcessInfo.processInfo.arguments.contains("--checkpoint-audio-offline")
    private(set) var outputMuted = !offlineCheckpointCheck && (
        ProcessInfo.processInfo.arguments.contains {
            ["--mute", "--menu-check", "--menu-live-check", "--play-script", "--long-trace"].contains($0)
        }
        || ProcessInfo.processInfo.environment["CLAW_REAL_SPEED_LOG"] != nil)
    // Deterministic app checks keep device output off: the output thread ends
    // voices in real time, which GetStatus would expose to the game clock.
    static let deterministicCheck = !offlineCheckpointCheck && ProcessInfo.processInfo.arguments.contains {
        [
            "--menu-check", "--menu-live-check", "--play-script", "--fast-clock", "--new-game-clock",
            "--menu-input-script", "--music-render"
        ].contains($0)
    }
    fileprivate var framesRendered: UInt64 = 0, nonzeroFrames: UInt64 = 0
    fileprivate(set) var reports: [(UInt32, UInt32)] = []
    private(set) var playRequests: UInt64 = 0
    private var interfaceVtable: UInt32 = 0
    private var sourceVolumeIdentity: ClawTokenHeap.AllocationIdentity?
    private let sourceVolumeTable = UnsafeMutablePointer<UInt32>.allocate(capacity: 101)
    fileprivate var lifecycleResourceActive = false
    fileprivate(set) var lifecycleFault: UInt32 = 0
    private(set) var lifecycleCounts: [UInt32: UInt64] = [:]
    var routing = ClawAudioRouting()
    var requestTick: UInt32 = 0
    var soundRepeatInterval: UInt32 = 0
    let diagnostics: ClawNativeDiagnostics
    let outputEnabled: Bool
    // MARK: - Snapshot persistence

    // Playback participant. Resource/sample construction and allocator/provider
    // ownership are separate graph participants; a topology mismatch rejects.
    // The current output mute is a native preference and remains in effect.
    struct PlaybackSavedState: Codable, Equatable {
        struct Voice: Codable, Equatable {
            let token: UInt32, sampleToken: UInt32, sampleBytes: UInt32, sampleRate: UInt32
            let channels: Int, bits: Int
            let volume: Int32, pan: Int32, frequency: UInt32
            let playing: Bool, looping: Bool
            let cursorBits: UInt64
        }
        struct Report: Codable, Equatable { let line: UInt32, result: UInt32 }
        let pcm: ClawSnapshotValue<ClawAudioPCMContext>
        let routing: ClawSnapshotValue<ClawAudioRouting>
        let voices: [Voice]
        let volumeTable: [UInt32]
        let framesRendered: UInt64, nonzeroFrames: UInt64, playRequests: UInt64
        let reports: [Report]
        let lifecycleFault: UInt32
        let lifecycleCounts: [UInt32: UInt64]
        let requestTick: UInt32, soundRepeatInterval: UInt32
    }
    func savedPlaybackState() throws -> PlaybackSavedState {
        lock.lock()
        defer { lock.unlock() }
        return try savedPlaybackStateLocked()
    }
    private func savedPlaybackStateLocked() throws -> PlaybackSavedState {
        guard !lifecycleResourceActive else { throw ClawSnapshotError.activeFrame }
        return PlaybackSavedState(
            pcm: ClawSnapshotValue(pcm.pointee), routing: ClawSnapshotValue(routing),
            voices: buffers.keys.sorted().map { token in
                let voice = buffers[token]!, samples = voice.samples
                return .init(
                    token: token, sampleToken: samples.token, sampleBytes: samples.bytes,
                    sampleRate: samples.sampleRate, channels: samples.channels, bits: samples.bits,
                    volume: voice.volume, pan: voice.pan, frequency: voice.frequency,
                    playing: voice.playing, looping: voice.looping, cursorBits: voice.cursor.bitPattern)
            }, volumeTable: Array(UnsafeBufferPointer(start: sourceVolumeTable, count: 101)),
            framesRendered: framesRendered, nonzeroFrames: nonzeroFrames, playRequests: playRequests,
            reports: reports.map { .init(line: $0.0, result: $0.1) },
            lifecycleFault: lifecycleFault, lifecycleCounts: lifecycleCounts,
            requestTick: requestTick, soundRepeatInterval: soundRepeatInterval)
    }
    func restorePlaybackState(_ value: PlaybackSavedState) throws {
        lock.lock()
        defer { lock.unlock() }
        guard !lifecycleResourceActive else { throw ClawSnapshotError.activeFrame }
        try validatePlaybackState(
            value, buffers: buffers, manager: pcm.pointee.resource.managerToken,
            device: pcm.pointee.resource.deviceToken)
        applyPlaybackStateLocked(value)
    }
    private func validatePlaybackState(
        _ value: PlaybackSavedState, buffers: [UInt32: ClawAudioBuffer], manager: UInt32, device: UInt32
    ) throws {
        guard value.volumeTable.count == 101, value.voices.count == buffers.count,
            Set(value.voices.map(\.token)) == Set(buffers.keys),
            value.pcm.value.resource.managerToken == manager, value.pcm.value.resource.deviceToken == device
        else { throw ClawSnapshotError.invalidState }
        for saved in value.voices {
            guard let voice = buffers[saved.token] else { throw ClawSnapshotError.invalidState }
            let samples = voice.samples, cursor = Double(bitPattern: saved.cursorBits)
            guard saved.sampleToken == samples.token, saved.sampleBytes == samples.bytes,
                saved.sampleRate == samples.sampleRate, saved.channels == samples.channels, saved.bits == samples.bits,
                cursor.isFinite, cursor >= 0, cursor <= Double(samples.decoded.count / samples.channels),
                !saved.playing
                    || (cursor < Double(samples.decoded.count / samples.channels) && !samples.decoded.isEmpty)
            else { throw ClawSnapshotError.invalidState }
        }
    }
    private func applyPlaybackStateLocked(_ value: PlaybackSavedState) {
        pcm.pointee = value.pcm.value
        routing = value.routing.value
        value.volumeTable.withUnsafeBufferPointer { sourceVolumeTable.update(from: $0.baseAddress!, count: 101) }
        framesRendered = value.framesRendered
        nonzeroFrames = value.nonzeroFrames
        playRequests = value.playRequests
        reports = value.reports.map { ($0.line, $0.result) }
        lifecycleFault = value.lifecycleFault
        lifecycleCounts = value.lifecycleCounts
        requestTick = value.requestTick
        soundRepeatInterval = value.soundRepeatInterval
        for saved in value.voices {
            let voice = buffers[saved.token]!
            voice.volume = saved.volume
            voice.pan = saved.pan
            voice.frequency = saved.frequency
            voice.playing = saved.playing
            voice.looping = saved.looping
            voice.cursor = Double(bitPattern: saved.cursorBits)
        }
    }
    struct SavedState: Codable, Equatable {
        struct Sound: Codable, Equatable { let resource: UInt32, pool: UInt32 }
        struct Samples: Codable, Equatable {
            let allocation: ClawTokenHeap.AllocationReference
            let bytes: UInt32, channels: Int, bits: Int, sampleRate: UInt32
            let decoded: Bool, digest: String, pcmHash: Data
        }
        let allocations: [UInt32: ClawSnapshotWitness]
        let playback: PlaybackSavedState, samples: [Samples]
        let sounds: [String: Sound], byToken: [UInt32: Sound]
        let tokensByName: [String: UInt32], namesByToken: [UInt32: String], nextName: UInt32, soundTokens: [UInt32]
        let interfaceVtable: UInt32, volumeWitness: ClawSnapshotWitness?
        let voiceProviders: [UInt32: String], requiresSharedRelease: Bool
    }
    func savedState(providers: [String: ClawNativeCanonicalHost.AudioAllocationProvider] = [:]) throws -> SavedState {
        lock.lock()
        defer { lock.unlock() }
        guard let sharedHeap, !lifecycleResourceActive else { throw ClawSnapshotError.activeFrame }
        var providerNames: [ObjectIdentifier: String] = [:]
        for (key, provider) in providers {
            guard !key.isEmpty, providerNames.updateValue(key, forKey: ObjectIdentifier(provider)) == nil else {
                throw ClawSnapshotError.invalidState
            }
        }
        var voiceProviders: [UInt32: String] = [:]
        for (token, provider) in canonicalVoiceOwners {
            guard let name = providerNames[ObjectIdentifier(provider)] else { throw ClawSnapshotError.incompleteOwners }
            voiceProviders[token] = name
        }
        var samples: [UInt32: ClawAudioSamples] = [:]
        for buffer in buffers.values {
            if let prior = samples[buffer.samples.token], prior !== buffer.samples {
                throw ClawSnapshotError.invalidState
            }
            samples[buffer.samples.token] = buffer.samples
        }
        let records = try samples.keys.sorted().map { token -> SavedState.Samples in
            let sample = samples[token]!
            guard let identity = sharedHeap.allocationIdentity(at: token, count: max(sample.bytes, 4)),
                let reference = sharedHeap.snapshotReference(
                    at: token, count: max(sample.bytes, 4), identity: identity),
                let bytes = sharedHeap.lookupBytes(token, count: sample.bytes)
            else { throw ClawSnapshotError.invalidState }
            return .init(
                allocation: reference, bytes: sample.bytes, channels: sample.channels, bits: sample.bits,
                sampleRate: sample.sampleRate,
                decoded: !sample.decoded.isEmpty, digest: sample.digest,
                pcmHash: Data(SHA256.hash(data: Data(bytes: bytes, count: Int(sample.bytes)))))
        }
        return SavedState(
            allocations: try heap.savedAllocations(), playback: try savedPlaybackStateLocked(), samples: records,
            sounds: sounds.mapValues { .init(resource: $0.resourceToken, pool: $0.voicePoolToken) },
            byToken: soundByToken.mapValues { .init(resource: $0.resourceToken, pool: $0.voicePoolToken) },
            tokensByName: tokensByName, namesByToken: namesByToken, nextName: nextName, soundTokens: soundTokens,
            interfaceVtable: interfaceVtable,
            volumeWitness: sourceVolumeIdentity.map {
                ClawSnapshotWitness(heap: sharedHeap, token: 0x541178, count: 404, identity: $0, interior: true)
            }, voiceProviders: voiceProviders, requiresSharedRelease: releaseSharedAllocation != nil)
    }
    func prepareRestore(
        _ value: SavedState, heap plan: ClawTokenHeap.RestorePlan,
        providers: [String: ClawNativeCanonicalHost.AudioAllocationProvider] = [:]
    ) throws -> () throws -> Void {
        guard let sharedHeap, !lifecycleResourceActive, engine == nil,
            value.requiresSharedRelease == (releaseSharedAllocation != nil)
        else { throw ClawSnapshotError.invalidState }
        try sharedHeap.validateRestore(plan)
        guard Set(value.samples.map { $0.allocation.token }).count == value.samples.count,
            Set(value.playback.voices.map(\.token)).count == value.playback.voices.count,
            value.byToken.allSatisfy({ $0.key == $0.value.resource }),
            value.sounds.values.allSatisfy({ value.byToken[$0.resource] == $0 }),
            value.tokensByName.allSatisfy({ value.namesByToken[$0.value] == $0.key }),
            value.namesByToken.allSatisfy({ value.tokensByName[$0.value] == $0.key }),
            value.samples.count <= 16384, value.playback.voices.count <= 65536
        else { throw ClawSnapshotError.invalidState }
        let applyHeap = try heap.prepareRestore(value.allocations, plan: plan)
        var samples: [UInt32: ClawAudioSamples] = [:], restoredBuffers: [UInt32: ClawAudioBuffer] = [:]
        for record in value.samples {
            guard [1, 2].contains(record.channels), [8, 16, 24, 32].contains(record.bits), record.sampleRate > 0,
                record.bytes > 0, record.bytes <= 4 << 20, record.allocation.count == max(record.bytes, 4),
                !record.allocation.interior, Int(record.bytes) % (record.channels * record.bits / 8) == 0,
                let pointer = plan.bytes(for: record.allocation),
                record.pcmHash == Data(SHA256.hash(data: Data(bytes: pointer, count: Int(record.bytes)))),
                value.allocations[record.allocation.token]?.reference == record.allocation
            else { throw ClawSnapshotError.invalidState }
            let sample = ClawAudioSamples(
                restoring: record.allocation.token, heap: heap, bytes: record.bytes,
                channels: record.channels, bits: record.bits, sampleRate: record.sampleRate)
            if record.decoded, !sample.decode(source: pointer) { throw ClawSnapshotError.invalidState }
            sample.digest = record.digest
            samples[record.allocation.token] = sample
        }
        for voice in value.playback.voices {
            guard let sample = samples[voice.sampleToken], let allocation = value.allocations[voice.token],
                allocation.live, allocation.reference.count == 16, plan.resolve(allocation.reference) != nil
            else { throw ClawSnapshotError.invalidState }
            restoredBuffers[voice.token] = ClawAudioBuffer(samples: sample)
        }
        try validatePlaybackState(
            value.playback, buffers: restoredBuffers, manager: value.playback.pcm.value.resource.managerToken,
            device: value.playback.pcm.value.resource.deviceToken)
        var voiceProviders: [UInt32: ClawNativeCanonicalHost.AudioAllocationProvider] = [:]
        for (token, name) in value.voiceProviders {
            guard let provider = providers[name], plan.reference(at: token, count: 0x38) != nil else {
                throw ClawSnapshotError.incompleteOwners
            }
            voiceProviders[token] = provider
        }
        if let witness = value.volumeWitness {
            guard witness.reference.token == 0x541178, witness.reference.count == 404 else {
                throw ClawSnapshotError.invalidState
            }
        }
        let volumeIdentity = try value.volumeWitness?.resolve(in: plan)
        return { [self] in
            lock.lock()
            defer { lock.unlock() }
            guard !lifecycleResourceActive, engine == nil else { throw ClawSnapshotError.activeFrame }
            try sharedHeap.validateInstalledRestore(plan)
            // Heap replacement has already retired the old backing. Even an
            // in-memory plan retaining witness identities must not let old
            // sample destructors release the newly installed allocation.
            for voice in buffers.values { voice.samples.relinquishRestoredStorage() }
            buffers.removeAll()
            try applyHeap()
            for sample in samples.values { sample.acquireRestoredStorage() }
            buffers = restoredBuffers
            canonicalVoiceOwners = voiceProviders
            sounds = value.sounds.mapValues { .init(resourceToken: $0.resource, voicePoolToken: $0.pool) }
            soundByToken = value.byToken.mapValues { .init(resourceToken: $0.resource, voicePoolToken: $0.pool) }
            tokensByName = value.tokensByName
            namesByToken = value.namesByToken
            nextName = value.nextName
            soundTokens = value.soundTokens
            interfaceVtable = value.interfaceVtable
            sourceVolumeIdentity = volumeIdentity
            applyPlaybackStateLocked(value.playback)
            audioEvents.removeAll()
            audioEventCount = 0
        }
    }
    // MARK: - Output diagnostics and comparison inputs

    var renderStatistics: (UInt64, UInt64) {
        lock.lock()
        defer { lock.unlock() }
        return (framesRendered, nonzeroFrames)
    }
    /// Output engine state for logs: running, final mixer volume, music attached.
    var outputState: [String: Any] {
        let (frames, nonzero) = renderStatistics
        let offline = offlineQueue.sync { (offlineNonzeroSamples, offlineRenderFailures) }
        return [
            "enabled": outputEnabled, "running": engine?.isRunning ?? false, "muted": outputMuted,
            "sample_rate": engine?.outputNode.inputFormat(forBus: 0).sampleRate ?? 0,
            "mixer_volume": Double(engine?.mainMixerNode.outputVolume ?? -1), "music_attached": music?.engine != nil,
            "frames_rendered": frames, "nonzero_frames": nonzero, "play_requests": playRequests,
            "offline": Self.offlineCheckpointCheck, "offline_nonzero_samples": offline.0, "offline_failures": offline.1
        ]
    }
    var activeVoiceCount: Int {
        lock.lock()
        defer { lock.unlock() }
        return buffers.values.filter { $0.playing }.count
    }
    // Opt-in live callback evidence. The render callback and game thread share
    // this bounded history under the buffer lock; ordinary play records nothing.
    private let captureAudio = ProcessInfo.processInfo.environment["CLAW_AUDIO_EVIDENCE"] == "1"
    private var audioEvents: [[String: Any]] = []
    private var audioEventCount: UInt64 = 0
    private func recordAudio(_ service: String, _ token: UInt32, _ fields: [String: Any] = [:]) {
        guard captureAudio else { return }
        audioEventCount &+= 1
        var event = fields
        event["service"] = service
        event["buffer"] = token
        event["index"] = audioEventCount
        event["render_frame"] = framesRendered
        event["uptime_ms"] = ProcessInfo.processInfo.systemUptime * 1000
        event["pcm_sha256"] = buffers[token]?.samples.digest ?? ""
        audioEvents.append(event)
        if audioEvents.count > 2048 { audioEvents.removeFirst(512) }
    }
    var lifetimeEvidence: [String: Any] {
        lock.lock()
        defer { lock.unlock() }
        return [
            "count": audioEventCount, "events": audioEvents,
            "buffers": buffers.keys.sorted().compactMap { token -> [String: Any]? in
                guard let b = buffers[token] else { return nil }
                return [
                    "buffer": token, "pcm_sha256": b.samples.digest, "playing": b.playing, "looping": b.looping,
                    "cursor": b.cursor, "sample_frames": b.samples.decoded.count / b.samples.channels,
                    "frequency": b.frequency, "volume": b.volume, "pan": b.pan
                ]
            }
        ]
    }

    // Read-only inputs to the original pool selector, for the audio-options
    // comparison. Read the physical status directly; do not invoke GetStatus
    // or alter the pool, voice list, playback cursor or invocation counts.
    func poolInputEvidence(_ token: UInt32) -> [String: Any] {
        lock.lock()
        defer { lock.unlock() }
        guard let pool = heap.words(token), let manager = heap.words(pool[4]) else {
            return ["error": "unmapped pool or manager"]
        }
        var node = pool[12], visited: Set<UInt32> = []
        var voices: [[String: Any]] = []
        while node != 0, visited.insert(node).inserted, visited.count <= 256 {
            guard node >= 4, let voice = heap.words(node - 4), let buffer = buffers[voice[3]] else {
                return ["error": "unmapped voice or physical buffer"]
            }
            voices.append(["eligible": voice[12] != 0, "playing": buffer.playing])
            node = voice[1]
        }
        guard node == 0 else { return ["error": "invalid or oversized voice list"] }
        return ["manager_enabled": manager[30] != 0, "voices": voices]
    }

    // MARK: - Audio manager lifetime

    init(
        root: URL, outputEnabled: Bool, sharedHeap: ClawTokenHeap? = nil, preload: Bool = true, level: UInt32 = 1,
        diagnostics: ClawNativeDiagnostics = .shared
    ) throws {
        self.diagnostics = diagnostics
        self.sharedHeap = sharedHeap
        heap = ClawAudioHeap(shared: sharedHeap)
        self.outputEnabled = outputEnabled
        pcm = .allocate(capacity: 1)
        pcm.initialize(to: ClawAudioPCMContext())
        sourceVolumeTable.initialize(repeating: 0, count: 101)
        // Original scene allocates 0x80 bytes. Whole 0x4b4710 owns its initialized fields;
        // allocator bytes and DirectSound identities remain native transport.
        pcm.pointee.resource.managerToken = heap.allocate(128)
        pcm.pointee.resource.deviceToken = heap.allocate(16)
        let deviceTable = heap.allocate(28)
        heap.words(deviceTable)![2] = 0x71020008
        heap.words(deviceTable)![5] = 0x71020014
        heap.words(deviceTable)![6] = 0x71020018
        heap.words(pcm.pointee.resource.deviceToken)![0] = deviceTable
        guard sourceManagerEntry(0x4b4710) == managerIdentity,
            sourceManagerEntry(0x4b47e0, arguments: [0x70000000, 1]) == 1, lifecycleFault == 0
        else {
            throw AssetError.invalid("Source audio manager initialization \(lifecycleFault)")
        }
        if let sharedHeap {
            let table = sharedHeap.store(token: 0x541178, words: 101)
            table.update(from: sourceVolumeTable, count: 101)
            sourceVolumeIdentity = sharedHeap.containingAllocationIdentity(at: 0x541178, count: 404)
        }
        pcm.pointee.resource.deviceAvailable = heap.words(managerIdentity)![30]
        routing.managerAvailable = pcm.pointee.resource.deviceAvailable
        routing.masterVolume = 100
        for prefix in (preload ? ["CLAW", "GAME", "LEVEL\(level)"] : []) {
            let directory = root.appendingPathComponent("\(prefix)/SOUNDS")
            guard FileManager.default.fileExists(atPath: directory.path) else { continue }
            guard let enumerator = FileManager.default.enumerator(at: directory, includingPropertiesForKeys: nil) else {
                throw AssetError.invalid("Cannot enumerate original sound directory")
            }
            let files = enumerator.compactMap { $0 as? URL }.filter { $0.pathExtension.uppercased() == "WAV" }.sorted {
                $0.path < $1.path
            }
            for file in files {
                // Explicit filesystem namespace transport. Real caller names
                // include nested groups, e.g. LEVEL_OFFICER_00340014.
                let relative = String(file.deletingPathExtension().path.dropFirst(directory.path.count + 1))
                let name =
                    ([prefix == "LEVEL\(level)" ? "LEVEL" : prefix] + relative.split(separator: "/").map(String.init))
                    .joined(separator: "_").uppercased()
                guard sounds[name] == nil else { throw AssetError.invalid("Ambiguous sound namespace \(name)") }
                try load(name: name, data: Data(contentsOf: file))
            }
        }
    }
    // Menu image metadata predates the source audio startup. Its zero table
    // must not replace the live table already produced by 0x4b47e0.
    func acceptsInitialVolumeMetadata(_ data: Data, in ownerHeap: ClawTokenHeap) -> Bool {
        guard data.count == 404, data.allSatisfy({ $0 == 0 }), sharedHeap === ownerHeap,
            lifecycleFault == 0, let identity = sourceVolumeIdentity,
            ownerHeap.containingAllocationIdentity(at: 0x541178, count: 404) === identity,
            let table = ownerHeap.lookup(0x541178, words: 101)
        else { return false }
        return (0...100).allSatisfy { table[$0] == sourceVolumeTable[$0] }
    }
    deinit {
        // Quiesce the native render thread before releasing its shared buffers.
        // Source 0x4b4790 still owns resource/controller/device teardown ordering.
        offlineTimer?.cancel()
        engine?.stop()
        // A rejected/replaced allocation never grants destructor writes to the
        // replacement. Each ledger still retires its remaining live identities.
        if heap.validOwnedStorage
            && canonicalVoiceOwners.allSatisfy({ $0.value.ownsObjectAllocation($0.key, count: 0x38) })
        {
            _ = sourceManagerEntry(0x4b4790)
        }
        pcm.deinitialize(count: 1)
        pcm.deallocate()
        sourceVolumeTable.deinitialize(count: 101)
        sourceVolumeTable.deallocate()
    }
    // MARK: - Borrowed synchronous host callbacks

    // C callbacks borrow this owner; they neither retain it nor transfer ownership.
    fileprivate var opaque: UnsafeMutableRawPointer { Unmanaged.passUnretained(self).toOpaque() }
    var resourceHost: ClawAudioResourceHost {
        ClawAudioResourceHost(
            context: opaque, lookup: audioLookup, allocate: audioAllocate,
            createBuffer: audioCreate, duplicateBuffer: audioDuplicate, get: audioGet, set: audioSet,
            report: audioReport)
    }
    fileprivate var pcmHost: ClawAudioPCMHost {
        ClawAudioPCMHost(
            resource: resourceHost, lookupBytes: audioBytes, free: audioFree,
            seek: audioSeek, read: audioRead, retry: audioRetry, lock: audioLock, unlock: audioUnlock,
            release: audioRelease)
    }
    fileprivate var host: ClawAudioHost { ClawAudioHost(context: opaque, resolve: audioResolve, play: audioPlay) }
    var backend: ClawAudioBackend {
        ClawAudioBackend(context: opaque, selectVoice: audioSelect, directSound: audioMethod, report: audioReport)
    }

    // MARK: - Source resource and manager services

    func load(name: String, data: Data) throws {
        let source = heap.allocate(UInt32(data.count))
        guard let destination = heap.bytes(source, UInt32(data.count)) else {
            throw AssetError.invalid("Cannot allocate original audio")
        }
        data.copyBytes(to: destination, count: data.count)
        let archive = heap.allocate(48), file = heap.allocate(48), scene = heap.allocate(48), sound = heap.allocate(64)
        heap.words(archive)![8] = source
        heap.words(file)![5] = UInt32(data.count)
        heap.words(file)![9] = archive
        heap.words(scene)![8] = pcm.pointee.resource.managerToken
        heap.words(sound)![3] = scene
        var fault: UInt32 = 0
        guard claw_audio_load_sound(pcm, sound, file, pcmHost, &fault) != 0, fault == 0 else {
            throw AssetError.invalid("Cannot load original PCM \(name), fault \(fault)")
        }
        heap.words(sound)![5] = 0
        heap.words(sound)![6] = soundRepeatInterval
        let value = ClawAudioSound(resourceToken: sound, voicePoolToken: heap.words(sound)![4])
        sounds[name] = value
        soundByToken[sound] = value
        soundTokens.append(sound)
        heap.words(managerIdentity)![1] = pcm.pointee.resource.resourceHead
        heap.words(managerIdentity)![2] = pcm.pointee.resource.resourceTail
    }
    // The menu's canonical sound and mapped resource are already in this heap.
    // Keep the original load/unload routines in charge of PCM and list lifetime.
    func loadSceneSound(_ sound: UInt32, resource: UInt32, fault: inout UInt32) -> UInt32 {
        let result = claw_audio_load_sound(pcm, sound, resource, pcmHost, &fault)
        if let manager = heap.words(managerIdentity) {
            manager[1] = pcm.pointee.resource.resourceHead
            manager[2] = pcm.pointee.resource.resourceTail
        }
        return result
    }
    func unloadSceneSound(_ sound: UInt32, fault: inout UInt32) {
        // The shared menu graph can create fades through the canonical owner.
        // Import its live list before the typed PCM destructor unlinks a voice.
        if releaseSharedAllocation != nil, let manager = heap.words(managerIdentity) {
            pcm.pointee.fadeHead = manager[3]
            pcm.pointee.fadeTail = manager[4]
        }
        claw_audio_unload_sound(pcm, sound, pcmHost, &fault)
        if let manager = heap.words(managerIdentity) {
            manager[1] = pcm.pointee.resource.resourceHead
            manager[2] = pcm.pointee.resource.resourceTail
            manager[3] = pcm.pointee.fadeHead
            manager[4] = pcm.pointee.fadeTail
        }
    }
    func sceneSoundPCM(_ sound: UInt32) -> [UInt8]? {
        guard let entry = heap.words(sound), let pool = heap.words(entry[4]),
            let buffer = buffers[pool[3]], let bytes = heap.bytes(buffer.samples.token, buffer.samples.bytes)
        else { return nil }
        return Array(UnsafeBufferPointer(start: bytes, count: Int(buffer.samples.bytes)))
    }
    @discardableResult func stopSceneSound(_ sound: UInt32) -> Bool {
        lock.lock();defer {lock.unlock()}
        guard let entry = heap.words(sound),let pool = heap.words(entry[4]) else {return false}
        var node = pool[12],seen = Set<UInt32>()
        while node != 0,seen.insert(node).inserted,seen.count <= 256 {
            guard node >= 4,let voice = heap.words(node-4),let buffer = buffers[voice[3]] else {return false}
            buffer.playing = false;recordAudio("Stop",voice[3]);node = voice[1]
        }
        return node == 0
    }
    var loadedBufferCount: Int { buffers.count }
    var managerIdentity: UInt32 { pcm.pointee.resource.managerToken }
    @discardableResult func sourceManagerEntry(_ function: UInt32, arguments: [UInt32] = []) -> UInt32 {
        var context = ClawAudioManagerLifecycleContext(scene: lifecycleHost, maximumTraversal: 0, fault: 0),
            result: UInt32 = 0
        lifecycleCounts[function, default: 0] &+= 1
        let accepted = arguments.withUnsafeBufferPointer {
            claw_audio_manager_lifecycle_entry(
                function, managerIdentity, $0.baseAddress, UInt32($0.count), &context, nativeAudioLifecycleDependency,
                opaque, &result)
        }
        lifecycleFault = max(lifecycleFault, context.fault)
        if accepted != 1 && lifecycleFault == 0 { lifecycleFault = 1 }
        if let manager = heap.words(managerIdentity) {
            pcm.pointee.resource.deviceAvailable = manager[30]
            routing.managerAvailable = manager[30]
        }
        return result
    }
    fileprivate var lifecycleHost: ClawSceneActorHost {
        ClawSceneActorHost(
            context: opaque,
            lookup: { user, token, count in
                let owner = audio(user)
                owner.publishPCMManager()
                if token >= 0x541178 && UInt64(token) + UInt64(count) * 4 <= 0x541178 + 404, token & 3 == 0 {
                    return owner.sourceVolumeTable.advanced(by: Int((token - 0x541178) / 4))
                }
                return owner.ambientMetadata(token: token, words: count)
            }, allocate: { user, count in audio(user).heap.allocate(count) },
            free: { user, token in audio(user).heap.free(token) }, call: nil, readClock: nil)
    }
    fileprivate func publishPCMManager() {
        guard lifecycleResourceActive, let manager = heap.words(managerIdentity) else { return }
        manager[1] = pcm.pointee.resource.resourceHead
        manager[2] = pcm.pointee.resource.resourceTail
        manager[3] = pcm.pointee.fadeHead
        manager[4] = pcm.pointee.fadeTail
    }
    func lifecycleDependency(_ event: ClawAudioManagerLifecycleCall) -> UInt32 {
        lifecycleCounts[event.function, default: 0] &+= 1
        if event.deviceMethod != 0 {
            guard event.function == (0x71020000 | event.deviceMethod),
                event.arguments.0 == pcm.pointee.resource.deviceToken
            else {
                lifecycleFault = 1
                return 0x80004005
            }
            if event.deviceMethod == 8 { engine?.stop() }
            return 0  // Native cooperative-level/device lifetime transport.
        }
        switch event.function {
        case 0x4f4480:
            guard let output = event.outputWord else {
                lifecycleFault = 1
                return 0x80004005
            }
            output.pointee = pcm.pointee.resource.deviceToken
            return 0
        case 0x4b4ed0:
            return diagnosticReport(filename: event.arguments.0, line: event.arguments.1, result: event.arguments.2)
        case 0x4b4ae0:
            guard let manager = heap.words(event.receiver), event.receiver == managerIdentity else {
                lifecycleFault = 1
                return 0
            }
            pcm.pointee.resource.deviceToken = manager[5]
            pcm.pointee.resource.deviceAvailable = manager[30]
            pcm.pointee.resource.resourceHead = manager[1]
            pcm.pointee.resource.resourceTail = manager[2]
            pcm.pointee.fadeHead = manager[3]
            pcm.pointee.fadeTail = manager[4]
            var fault: UInt32 = 0
            lifecycleResourceActive = true
            claw_audio_destroy_resource(pcm, event.arguments.0, pcmHost, &fault)
            publishPCMManager()
            lifecycleResourceActive = false
            lifecycleFault = max(lifecycleFault, fault)
            return 0
        case 0x4b3e30:
            var backend = ClawAmbientAudioBackendContext(scene: lifecycleHost, maximumTraversal: 0, fault: 0),
                result: UInt32 = 0
            let accepted = claw_ambient_audio_backend_entry(
                event.function, event.receiver, nil, 0, &backend,
                { context, call, user in
                    guard let call else { return 0 }
                    let owner = audio(user)
                    if call.pointee.bufferMethod != 0 { return owner.ambientPhysical(call.pointee) }
                    if call.pointee.function == 0x4b4ed0 {
                        let result = owner.diagnosticReport(
                            filename: call.pointee.arguments.0, line: call.pointee.arguments.1,
                            result: call.pointee.arguments.2)
                        if owner.lifecycleFault != 0 { context?.pointee.fault = owner.lifecycleFault }
                        return result
                    }
                    owner.lifecycleFault = 1
                    return 0
                }, opaque, &result)
            lifecycleFault = max(lifecycleFault, backend.fault)
            if accepted != 1 && lifecycleFault == 0 { lifecycleFault = 1 }
            return result
        default:
            lifecycleFault = 1
            return 0
        }
    }
    @discardableResult func diagnosticReport(filename: UInt32 = 0x53228c, line: UInt32, result: UInt32) -> UInt32 {
        reports.append((line, result))
        if !diagnostics.report(
            display: false, filename: filename, line: line, result: result,
            bytes: { [unowned self] in self.heap.bytes($0, $1) })
        {
            lifecycleFault = max(lifecycleFault, diagnostics.fault)
        }
        return 0
    }
    // Only the original sound+10 pool and pool+28 duration spans are exposed
    // to the shared speech heap. Other backend buffer graphs stay private.
    func speechMetadata(token: UInt32, words: UInt32) -> UnsafeMutablePointer<UInt32>? {
        guard token & 3 == 0, words > 0, words <= 11 else { return nil }
        let end = UInt64(token) + UInt64(words) * 4
        for sound in sounds.values {
            let inRoot = token >= sound.resourceToken && end <= UInt64(sound.resourceToken) + 20
            let inPool = token >= sound.voicePoolToken && end <= UInt64(sound.voicePoolToken) + 44
            if inRoot || inPool, let bytes = heap.bytes(token, words * 4) {
                return UnsafeMutableRawPointer(bytes).assumingMemoryBound(to: UInt32.self)
            }
        }
        return nil
    }
    // Bounded raw backend transport. PCM/resource/fade storage owns every
    // returned span; source callers retain their original token identities.
    func ambientMetadata(token: UInt32, words: UInt32) -> UnsafeMutablePointer<UInt32>? {
        guard token & 3 == 0, words > 0, words <= 1 << 20, let bytes = heap.bytes(token, words * 4) else { return nil }
        return UnsafeMutableRawPointer(bytes).assumingMemoryBound(to: UInt32.self)
    }
    func ambientAllocate(_ bytes: UInt32) -> UInt32 { heap.allocate(bytes) }
    func ambientFree(_ token: UInt32) { heap.free(token) }
    func ambientPhysical(_ event: ClawAmbientAudioBackendCall) -> UInt32 {
        guard event.bufferMethod != 0, event.function == (0x71010000 | event.bufferMethod), event.argumentCount >= 1
        else { return 0x80070057 }
        if let out = event.outputWord { return get(event.arguments.0, method: event.bufferMethod, out: out) }
        if event.bufferMethod == 0x30 {
            if outputEnabled && engine == nil { do { try startOutput() } catch { return 0x80004005 } }
            playRequests &+= 1
        }
        return method(event.arguments.0, event.bufferMethod, event.arguments.1, event.arguments.2, event.arguments.3)
    }
    private func installInterface(_ token: UInt32) {
        if interfaceVtable == 0 {
            interfaceVtable = heap.allocate(80)
            let table = heap.words(interfaceVtable)!
            // Native transport identities; DLL COM addresses are not portable.
            for method: UInt32 in [0x08, 0x18, 0x1c, 0x20, 0x24, 0x30, 0x3c, 0x40, 0x44, 0x48] {
                table[Int(method / 4)] = 0x71010000 | method
            }
        }
        heap.words(token)![0] = interfaceVtable
    }
    // MARK: - Sound lookup and playback requests

    func resolve(name: String) -> ClawAudioSound? { sounds[name.uppercased()] }
    func sound(resource: UInt32) -> ClawAudioSound? { soundByToken[resource] }
    @discardableResult func playVoicePool(_ token: UInt32, request: ClawAudioRequest) -> UInt32 {
        play(pool: token, request: request)
    }
    func duration(resource: UInt32) -> UInt32 {
        guard let value = soundByToken[resource], let pool = heap.words(value.voicePoolToken) else { return 0 }
        return pool[10]
    }
    func nameToken(_ name: String) -> UInt32 {
        let name = name.uppercased()
        if let token = tokensByName[name] { return token }
        let token = nextName
        nextName += 1
        tokensByName[name] = token
        namesByToken[token] = name
        return token
    }
    @discardableResult func play(name: String, sourceX: UInt32? = nil) -> UInt32 {
        guard let value = resolve(name: name) else { return 0 }
        if let sourceX {
            var value = value, fault: UInt32 = 0
            return claw_audio_play_spatial(&routing, &value, sourceX, 0, 0, 0, host, &fault)
        }
        return play(resource: value.resourceToken, volume: routing.masterVolume)
    }
    @discardableResult func playSpatial(
        resource: UInt32, sourceX: UInt32, referenceX: UInt32 = 0, clampDistance: UInt32 = 0, panDistance: UInt32 = 0
    ) -> UInt32 {
        guard var sound = soundByToken[resource] else { return 0 }
        var fault: UInt32 = 0
        return claw_audio_play_spatial(&routing, &sound, sourceX, referenceX, clampDistance, panDistance, host, &fault)
    }
    @discardableResult func play(resource: UInt32, volume: UInt32) -> UInt32 {
        guard var value = soundByToken[resource], acceptNonPositional(resource) else { return 0 }
        return claw_audio_play_direct(
            &routing, &value, ClawAudioRequest(volume: volume, pan: 0, pitchPercent: 0, looping: 0), host)
    }
    @discardableResult func play(name: String, request: ClawAudioRequest) -> UInt32 {
        guard var value = resolve(name: name), acceptNonPositional(value.resourceToken) else { return 0 }
        return claw_audio_play_direct(&routing, &value, request, host)
    }
    // Resource-local v1.3 request policy. Positional and raw pool calls keep
    // their existing backend paths; acceptance precedes any backend failure.
    private func acceptNonPositional(_ resource: UInt32) -> Bool {
        guard routing.managerAvailable != 0, let bytes = heap.bytes(resource, 28) else { return false }
        if claw_native_v13_enabled() == 0 { return true }
        let words = UnsafeMutableRawPointer(bytes).assumingMemoryBound(to: UInt32.self)
        let now = sharedHeap?.lookup(0x537210, words: 1)?.pointee ?? requestTick
        guard claw_v13_sound_elapsed(now, words[5], words[6]) != 0 else { return false }
        words[5] = now
        return true
    }
    fileprivate func play(pool: UInt32, request: ClawAudioRequest) -> UInt32 {
        if outputEnabled && engine == nil {
            do { try startOutput() } catch {
                reports.append((0, 1))
                return 0
            }
        }
        playRequests += 1
        return claw_audio_play_pool(
            ClawAudioPool(token: pool, deviceAvailable: pcm.pointee.resource.deviceAvailable), request, backend)
    }
    // MARK: - Native output graph and mixer

    func stopAll() { _ = sourceManagerEntry(0x4b4b40) }
    private let offlineQueue = DispatchQueue(label: "claw.checkpoint.audio")
    private var offlineTimer: DispatchSourceTimer?
    private var offlineNonzeroSamples: UInt64 = 0
    private var offlineRenderFailures: UInt64 = 0
    func stopOutput() {
        offlineTimer?.cancel(); offlineTimer = nil
        offlineQueue.sync { engine?.stop() }
        sourceNode = nil
        engine = nil
    }
    //Temporary lab preference at the final output mixer. Source sound requests,
    //volume metadata, cursors and completion timing continue while inaudible.
    func setOutputMuted(_ muted: Bool) {
        outputMuted = muted
        engine?.mainMixerNode.outputVolume = muted ? 0 : 1
        if !muted {
            startMusicOutput()
            offlineQueue.sync { if engine?.isRunning == false {try? engine?.start()} }
        }
    }
    // Native General MIDI output for the original XMIDI sequences (the Windows
    // MIDI synth is platform layer). It joins this engine and its mute. While
    // muted it never starts an output engine, so nothing reaches the speakers.
    private var music: ClawMusicSynth?
    func attachMusic(_ synth: ClawMusicSynth) {
        music = synth
        startMusicOutput()
    }
    private func startMusicOutput() {
        guard let music, !outputMuted, music.engine == nil else { return }
        if let engine {
            music.attach(to: engine)
            music.preload()
        } else {
            try? startOutput()
        }
    }

    fileprivate func startOutput() throws {
        #if os(iOS) && !targetEnvironment(macCatalyst)
            try AVAudioSession.sharedInstance().setCategory(.playback, mode: .default, options: [.mixWithOthers])
            try AVAudioSession.sharedInstance().setActive(true)
        #endif
        let graph = AVAudioEngine()
        let rate = Self.offlineCheckpointCheck ? 44100 : graph.outputNode.inputFormat(forBus: 0).sampleRate
        guard rate > 0, let format = AVAudioFormat(standardFormatWithSampleRate: rate, channels: 2) else {
            throw AssetError.invalid("Native audio output unavailable")
        }
        if Self.offlineCheckpointCheck {
            try graph.enableManualRenderingMode(.offline, format: format, maximumFrameCount: 1024)
        }
        let source = AVAudioSourceNode(format: format) { [weak self] silence, _, count, output in
            // Read the C flexible array directly; the CoreAudio Swift list
            // overlay is unavailable in the Catalyst SDK used by this target.
            let countBuffers = Int(output.pointee.mNumberBuffers)
            let list = UnsafeMutableRawPointer(output)
                .advanced(by: MemoryLayout<AudioBufferList>.offset(of: \.mBuffers)!)
                .assumingMemoryBound(to: AudioBuffer.self)
            guard countBuffers == 2, let left = list[0].mData?.assumingMemoryBound(to: Float.self),
                let right = list[1].mData?.assumingMemoryBound(to: Float.self), let self
            else {
                for index in 0..<countBuffers {
                    let buffer = list[index]
                    if let data = buffer.mData { memset(data, 0, Int(buffer.mDataByteSize)) }
                }
                silence.pointee = true
                return 0
            }
            self.render(left: left, right: right, frames: Int(count), sampleRate: rate)
            silence.pointee = false
            return 0
        }
        // Voices render only for an output-enabled owner; music alone does not
        // advance their cursors.
        if outputEnabled {
            graph.attach(source)
            graph.connect(source, to: graph.mainMixerNode, format: format)
        }
        let synth = outputMuted ? nil : music
        synth?.attach(to: graph)
        graph.mainMixerNode.outputVolume = outputMuted ? 0 : 1
        graph.prepare()
        synth?.preload()
        try graph.start()
        sourceNode = outputEnabled ? source : nil
        engine = graph
        if Self.offlineCheckpointCheck {
            guard let output = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: 1024) else {
                throw AssetError.invalid("Checkpoint offline audio buffer")
            }
            let timer = DispatchSource.makeTimerSource(queue: offlineQueue)
            timer.schedule(deadline: .now(), repeating: .milliseconds(10))
            timer.setEventHandler { [weak self, weak graph] in
                guard let self, let graph, graph.isRunning else { return }
                do {
                    guard try graph.renderOffline(441, to: output) == .success else {
                        self.offlineRenderFailures += 1; return
                    }
                    for channel in 0..<2 {
                        for index in 0..<Int(output.frameLength) where output.floatChannelData![channel][index] != 0 {
                            self.offlineNonzeroSamples += 1
                        }
                    }
                } catch { self.offlineRenderFailures += 1 }
            }
            offlineTimer = timer
            timer.resume()
        }
    }
    // Native output adapter: full original frequency range, shared duplicate
    // samples, attenuation/pan, looping and live parameter changes. Linear
    // interpolation and Float clipping remain explicit presentation choices.
    func render(left: UnsafeMutablePointer<Float>, right: UnsafeMutablePointer<Float>, frames: Int, sampleRate: Double)
    {
        guard frames >= 0, sampleRate > 0 else { return }
        lock.lock()
        defer { lock.unlock() }
        for frame in 0..<frames {
            left[frame] = 0
            right[frame] = 0
        }
        for token in buffers.keys.sorted() {
            let voice = buffers[token]!
            guard voice.playing else { continue }
            let samples = voice.samples.decoded, channels = voice.samples.channels,
                total = samples.count / voice.samples.channels
            guard total > 0 else {
                voice.playing = false
                continue
            }
            let gain = voice.volume <= -10000 ? Float(0) : Float(pow(10, Double(voice.volume) / 2000))
            let leftGain = voice.pan > 0 ? gain * Float(pow(10, -Double(voice.pan) / 2000)) : gain
            let rightGain = voice.pan < 0 ? gain * Float(pow(10, Double(voice.pan) / 2000)) : gain
            let step = Double(voice.frequency) / sampleRate
            for frame in 0..<frames {
                let index = Int(voice.cursor), next = index + 1 < total ? index + 1 : (voice.looping ? 0 : index)
                let fraction = Float(voice.cursor - Double(index))
                let l0 = samples[index * channels], l1 = samples[next * channels]
                let r0 = channels == 1 ? l0 : samples[index * channels + 1],
                    r1 = channels == 1 ? l1 : samples[next * channels + 1]
                left[frame] += (l0 + (l1 - l0) * fraction) * leftGain
                right[frame] += (r0 + (r1 - r0) * fraction) * rightGain
                voice.cursor += step
                if voice.cursor >= Double(total) {
                    if voice.looping {
                        voice.cursor.formTruncatingRemainder(dividingBy: Double(total))
                    } else {
                        recordAudio("complete", token, ["completion_frame": framesRendered + UInt64(frame) + 1])
                        voice.cursor = 0
                        voice.playing = false
                        break
                    }
                }
            }
        }
        for frame in 0..<frames {
            left[frame] = max(-1, min(1, left[frame]))
            right[frame] = max(-1, min(1, right[frame]))
            if left[frame] != 0 || right[frame] != 0 { nonzeroFrames += 1 }
        }
        framesRendered += UInt64(frames)
    }

    // MARK: - DirectSound buffer transport

    fileprivate func create(format: UnsafePointer<UInt8>, bytes: UInt32, out: UnsafeMutablePointer<UInt32>) -> UInt32 {
        func u16(_ at: Int) -> Int { Int(format[at]) | Int(format[at + 1]) << 8 }
        func u32(_ at: Int) -> UInt32 {
            UInt32(format[at]) | UInt32(format[at + 1]) << 8 | UInt32(format[at + 2]) << 16 | UInt32(format[at + 3])
                << 24
        }
        let channels = u16(2), bits = u16(14), rate = u32(4)
        guard u16(0) == 1, [1, 2].contains(channels), [8, 16, 24, 32].contains(bits), rate > 0,
            u16(12) == channels * bits / 8, bytes > 0, Int(bytes) % u16(12) == 0
        else { return 0x80070057 }
        let samples = ClawAudioSamples(heap: heap, bytes: bytes, channels: channels, bits: bits, sampleRate: rate)
        let token = heap.allocate(16)
        installInterface(token)
        observePhysical?([
            "service": "IDirectSound::CreateSoundBuffer", "buffer": token, "length": bytes,
            "format": Data(bytes: format, count: 18)
        ])
        lock.lock()
        buffers[token] = ClawAudioBuffer(samples: samples)
        lock.unlock()
        out.pointee = token
        return 0
    }
    // IDirectSound::DuplicateSoundBuffer (+0x14) reached through the device
    // transport identity, as 0x4b42e0 calls it when every pool voice is busy.
    func deviceDuplicate(device: UInt32, source: UInt32, out: UnsafeMutablePointer<UInt32>) -> UInt32 {
        guard device == pcm.pointee.resource.deviceToken else { return 0x80070057 }
        return duplicate(source, out: out)
    }
    fileprivate func duplicate(_ source: UInt32, out: UnsafeMutablePointer<UInt32>) -> UInt32 {
        lock.lock()
        defer { lock.unlock() }
        guard let source = buffers[source] else { return 0x80070057 }
        let token = heap.allocate(16), duplicate = ClawAudioBuffer(samples: source.samples)
        installInterface(token)
        duplicate.volume = source.volume
        duplicate.pan = source.pan
        duplicate.frequency = source.frequency
        buffers[token] = duplicate
        out.pointee = token
        return 0
    }
    fileprivate func get(_ token: UInt32, method: UInt32, out: UnsafeMutablePointer<UInt32>) -> UInt32 {
        lock.lock()
        defer { lock.unlock() }
        guard let buffer = buffers[token] else { return 0x80070057 }
        switch method {
        case 0x20: out.pointee = buffer.frequency
        case 0x1c: out.pointee = UInt32(bitPattern: buffer.pan)
        case 0x18: out.pointee = UInt32(bitPattern: buffer.volume)
        case 0x24: out.pointee = buffer.playing ? (buffer.looping ? 5 : 1) : 0
        default: return 0x80070057
        }
        let names: [UInt32: String] = [0x20: "GetFrequency", 0x1c: "GetPan", 0x18: "GetVolume", 0x24: "GetStatus"]
        observePhysical?(["service": "IDirectSoundBuffer::" + names[method]!, "object": token])
        recordAudio(names[method]!, token, ["value": out.pointee])
        return 0
    }
    fileprivate func method(_ token: UInt32, _ method: UInt32, _ a: UInt32, _ b: UInt32, _ c: UInt32) -> UInt32 {
        lock.lock()
        defer { lock.unlock() }
        guard let buffer = buffers[token] else { return 0x80070057 }
        switch method {
        case 0x3c:
            guard Int32(bitPattern: a) >= -10000 && Int32(bitPattern: a) <= 0 else { return 0x80070057 }
            buffer.volume = Int32(bitPattern: a)
        case 0x40:
            guard Int32(bitPattern: a) >= -10000 && Int32(bitPattern: a) <= 10000 else { return 0x80070057 }
            buffer.pan = Int32(bitPattern: a)
        case 0x44:
            guard a == 0 || (100...100000).contains(a) else { return 0x80070057 }
            buffer.frequency = a == 0 ? buffer.samples.sampleRate : a
        case 0x30:
            guard a == 0 && b == 0 && !buffer.samples.decoded.isEmpty else { return 0x80070057 }
            buffer.looping = c & 1 != 0
            buffer.playing = true
        case 0x48: buffer.playing = false
        default: return 0x80070057
        }
        let names: [UInt32: String] = [
            0x3c: "SetVolume", 0x40: "SetPan", 0x44: "SetFrequency", 0x30: "Play", 0x48: "Stop"
        ]
        var effect: [String: Any] = ["service": "IDirectSoundBuffer::" + names[method]!, "object": token, "value": a]
        if method == 0x30 { effect["arguments"] = [a, b, c] }
        observePhysical?(effect)
        recordAudio(names[method]!, token, ["arguments": [a, b, c], "cursor": buffer.cursor])
        return 0
    }
    fileprivate func unlock(_ token: UInt32) -> UInt32 {
        lock.lock()
        defer { lock.unlock() }
        guard let voice = buffers[token] else { return 0x80070057 }
        return voice.samples.decode() ? 0 : 0x80070057
    }
    fileprivate func release(_ token: UInt32) -> UInt32 {
        lock.lock()
        buffers.removeValue(forKey: token)
        lock.unlock()
        observePhysical?(["service": "IDirectSoundBuffer::Release", "object": token])
        heap.free(token)
        return 0
    }
}

// Synchronous canonical playback uses the same PCM/device/list owner. Memory
// retains authority over source-created voice storage through source teardown.
extension ClawNativeAudio: ClawNativeCanonicalHost.ObjectAudioProvider {
    func validAudioBinding(for host: ClawNativeCanonicalHost) -> Bool {
        guard sharedHeap === host.heap, lifecycleFault == 0, heap.validOwnedStorage,
            host.heap.containingAllocationIdentity(at: 0x541178, count: 404) === sourceVolumeIdentity,
            let manager = heap.words(managerIdentity), manager[5] == pcm.pointee.resource.deviceToken,
            let table = host.heap.lookup(0x541178, words: 101)
        else { return false }
        return (0...100).allSatisfy { table[$0] == sourceVolumeTable[$0] }
            && canonicalVoiceOwners.allSatisfy { $0.value.ownsObjectAllocation($0.key, count: 0x38) }
    }
    func ownsAudioPool(_ token: UInt32) -> Bool {
        guard let pool = heap.words(token), pool[0] == 0x51350c, pool[4] == managerIdentity,
            buffers[pool[3]] != nil
        else { return false }
        return soundByToken.values.contains { $0.voicePoolToken == token }
            || soundTokens.contains { heap.words($0)?[4] == token }
    }
    func retainAudioAllocation(_ token: UInt32, provider: ClawNativeCanonicalHost.ObjectAllocationProvider) -> Bool {
        guard let memory = provider as? ClawNativeCanonicalHost.AudioAllocationProvider,
            canonicalVoiceOwners[token] == nil,
            memory.ownsObjectAllocation(token, count: 0x38)
        else { return false }
        canonicalVoiceOwners[token] = memory
        return true
    }
    func audioPhysical(_ call: ClawCall, host: ClawNativeCanonicalHost) -> UInt32? {
        guard validAudioBinding(for: host), call.receiver == 0, call.receiver2 == 0 else { return nil }
        if call.function == 0x4a30e0 {
            guard call.argumentCount == 0, call.x87Operation == 0 else { return nil }
            if call.x87ArgumentCount == 1 {
                // BossStager's admitted call_x87 carries the already-rounded
                // binary64 operand. The existing service truncates it exactly.
                guard call.x87State == nil else { return nil }
            } else {
                guard call.x87ArgumentCount == UInt32(CLAW_X87_EXACT), let state = call.x87State,
                    state.pointee.popCount == 1, state.pointee.pushCount == 0
                else { return nil }
            }
            var request = call, result: UInt32 = 0
            return claw_native_menu_math_service(&request, &result) == 1 ? result : nil
        }
        guard call.x87ArgumentCount == 0, call.x87State == nil, call.x87Operation == 0 else { return nil }
        let a = withUnsafeBytes(of: call.arguments) {
            Array($0.bindMemory(to: UInt32.self).prefix(Int(call.argumentCount)))
        }
        if call.function == 0x71020014 {
            guard a.count == 3, let output = host.bytes(a[2], count: 4) else { return nil }
            return deviceDuplicate(
                device: a[0], source: a[1], out: UnsafeMutableRawPointer(output).assumingMemoryBound(to: UInt32.self))
        }
        let method = call.function & 0xffff
        let counts: [UInt32: Int] = [
            0x08: 1, 0x18: 2, 0x1c: 2, 0x20: 2, 0x24: 2, 0x30: 4, 0x3c: 2, 0x40: 2, 0x44: 2, 0x48: 1
        ]
        guard call.function == (0x71010000 | method), counts[method] == a.count else { return nil }
        if method == 0x08 { return release(a[0]) }
        var event = ClawAmbientAudioBackendCall()
        event.function = call.function
        event.bufferMethod = method
        event.argumentCount = call.argumentCount
        withUnsafeMutableBytes(of: &event.arguments) { dst in a.withUnsafeBytes { dst.copyBytes(from: $0) } }
        if [UInt32(0x18), 0x1c, 0x20, 0x24].contains(method) {
            guard let output = host.bytes(a[1], count: 4) else { return nil }
            event.outputWord = UnsafeMutableRawPointer(output).assumingMemoryBound(to: UInt32.self)
        }
        return ambientPhysical(event)
    }
}

private func audio(_ context: UnsafeMutableRawPointer?) -> ClawNativeAudio {
    Unmanaged<ClawNativeAudio>.fromOpaque(context!).takeUnretainedValue()
}
private let audioLookup: @convention(c) (UnsafeMutableRawPointer?, UInt32) -> UnsafeMutablePointer<UInt32>? = {
    let owner = audio($0)
    owner.publishPCMManager()
    return owner.heap.words($1)
}
private let audioAllocate: @convention(c) (UnsafeMutableRawPointer?, UInt32) -> UInt32 = { audio($0).heap.allocate($1) }
private let audioBytes: @convention(c) (UnsafeMutableRawPointer?, UInt32, UInt32) -> UnsafeMutablePointer<UInt8>? = {
    audio($0).heap.bytes($1, $2)
}
private let audioFree: @convention(c) (UnsafeMutableRawPointer?, UInt32) -> Void = {
    let owner = audio($0)
    if let memory = owner.canonicalVoiceOwners[$1] {
        if memory.releaseAudioAllocation($1) {
            owner.canonicalVoiceOwners.removeValue(forKey: $1)
        } else {
            owner.lifecycleFault = max(owner.lifecycleFault, 1)
        }
    } else if owner.releaseSharedAllocation?($1) != true {
        owner.heap.free($1)
    }
}
private let nativeAudioLifecycleDependency: ClawAudioManagerLifecycleDependency = { context, event, user in
    guard let event else { return 0 }
    let owner = audio(user)
    let result = owner.lifecycleDependency(event.pointee)
    if owner.lifecycleFault != 0 { context?.pointee.fault = owner.lifecycleFault }
    return result
}
private let audioCreate:
    @convention(c) (UnsafeMutableRawPointer?, UInt32, UnsafePointer<UInt8>?, UInt32, UnsafeMutablePointer<UInt32>?) ->
        UInt32 = { c, _, f, n, out in
            guard let f, let out else { return 0x80070057 }
            return audio(c).create(format: f, bytes: n, out: out)
        }
private let audioDuplicate:
    @convention(c) (UnsafeMutableRawPointer?, UInt32, UInt32, UnsafeMutablePointer<UInt32>?) -> UInt32 = {
        c, _, t, out in
        guard let out else { return 0x80070057 }
        return audio(c).duplicate(t, out: out)
    }
private let audioGet:
    @convention(c) (UnsafeMutableRawPointer?, UInt32, UInt32, UnsafeMutablePointer<UInt32>?) -> UInt32 = {
        c, t, m, out in
        guard let out else { return 0x80070057 }
        return audio(c).get(t, method: m, out: out)
    }
private let audioSet: @convention(c) (UnsafeMutableRawPointer?, UInt32, UInt32, UInt32) -> UInt32 = {
    audio($0).method($1, $2, $3, 0, 0)
}
private let audioReport: @convention(c) (UnsafeMutableRawPointer?, UInt32, UInt32) -> Void = {
    audio($0).diagnosticReport(line: $1, result: $2)
}
private let audioSeek: @convention(c) (UnsafeMutableRawPointer?, UInt32, UInt32, UInt32) -> UInt32 = { _, _, _, _ in 1 }
private let audioRead: @convention(c) (UnsafeMutableRawPointer?, UInt32, UInt32, UInt32, UInt32) -> UInt32 = {
    _, _, _, _, _ in 0
}
private let audioRetry: @convention(c) (UnsafeMutableRawPointer?, UInt32) -> UInt32 = { _, _ in 0 }
private let audioLock:
    @convention(c) (UnsafeMutableRawPointer?, UInt32, UInt32, UInt32, UInt32, UnsafeMutablePointer<ClawAudioPCMLock>?)
        -> UInt32 = { c, t, offset, n, _, out in
            let owner = audio(c)
            owner.lock.lock()
            defer { owner.lock.unlock() }
            guard let out, let buffer = owner.buffers[t], UInt64(offset) + UInt64(n) <= UInt64(buffer.samples.bytes)
            else { return 0x80070057 }
            owner.observePhysical?(["service": "IDirectSoundBuffer::Lock", "object": t, "offset": offset, "length": n])
            out.pointee = ClawAudioPCMLock(
                firstToken: buffer.samples.token + offset, firstBytes: n, secondToken: 0, secondBytes: 0)
            return 0
        }
private let audioUnlock: @convention(c) (UnsafeMutableRawPointer?, UInt32, ClawAudioPCMLock) -> UInt32 = {
    context, token, _ in
    let owner = audio(context)
    if let buffer = owner.buffers[token], let bytes = owner.heap.bytes(buffer.samples.token, buffer.samples.bytes) {
        owner.observePhysical?([
            "service": "IDirectSoundBuffer::Unlock", "object": token,
            "pcm": Data(bytes: bytes, count: Int(buffer.samples.bytes))
        ])
    }
    return owner.unlock(token)
}
private let audioRelease: @convention(c) (UnsafeMutableRawPointer?, UInt32) -> UInt32 = { audio($0).release($1) }
private let audioSelect: @convention(c) (UnsafeMutableRawPointer?, UInt32) -> UnsafeMutablePointer<ClawAudioVoice>? = {
    c, pool in
    let owner = audio(c)
    var fault: UInt32 = 0
    let token = claw_audio_select_voice(&owner.pcm.pointee.resource, pool, owner.resourceHost, &fault)
    guard fault == 0, let pointer = owner.heap.words(token) else { return nil }
    return UnsafeMutableRawPointer(pointer).assumingMemoryBound(to: ClawAudioVoice.self)
}
private let audioMethod: @convention(c) (UnsafeMutableRawPointer?, UInt32, UInt32, UInt32, UInt32, UInt32) -> UInt32 = {
    audio($0).method($1, $2, $3, $4, $5)
}
private let audioResolve:
    @convention(c) (UnsafeMutableRawPointer?, UInt32, UInt32, UnsafeMutablePointer<ClawAudioSound>?) -> Void = {
        c, _, name, out in
        guard let out else { return }
        let owner = audio(c)
        out.pointee = owner.namesByToken[name].flatMap { owner.sounds[$0] } ?? ClawAudioSound()
    }
private let audioPlay: @convention(c) (UnsafeMutableRawPointer?, UInt32, ClawAudioRequest) -> UInt32 = {
    audio($0).play(pool: $1, request: $2)
}

extension ClawAudioPCMContext: ClawSnapshotNativeValue {}
extension ClawAudioRouting: ClawSnapshotNativeValue {}
