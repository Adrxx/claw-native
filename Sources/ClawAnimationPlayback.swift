import Foundation

/// Native adapter for the recovered v1.0 animation routine. Scheduling and sound
/// playback are supplied by the caller; this does not implement the game loop.
struct ClawAnimationPlayback {
    let records: [ClawAnimationRecord]
    let imageTokens: [UInt32]
    let eventNames: [UInt32: String]
    let firstImage: Int32
    let lastImage: Int32
    private(set) var state = ClawAnimationState()
    private(set) var actor = ClawAnimationActor()
    private(set) var event = ClawAnimationEvent()
    private(set) var result: UInt32 = 0

    struct SavedState: Codable, Equatable {
        struct EventName: Codable, Equatable { let token: UInt32; let name: String }
        let records: [ClawSnapshotValue<ClawAnimationRecord>]
        let imageTokens: [UInt32]
        let eventNames: [EventName]
        let firstImage: Int32, lastImage: Int32
        let state: ClawSnapshotValue<ClawAnimationState>
        let actor: ClawSnapshotValue<ClawAnimationActor>
        let event: ClawSnapshotValue<ClawAnimationEvent>
        let result: UInt32
    }
    func savedState() -> SavedState {
        SavedState(records: records.map(ClawSnapshotValue.init), imageTokens: imageTokens,
            eventNames: eventNames.keys.sorted().map { .init(token: $0, name: eventNames[$0]!) }, firstImage: firstImage, lastImage: lastImage,
            state: ClawSnapshotValue(state), actor: ClawSnapshotValue(actor), event: ClawSnapshotValue(event), result: result)
    }
    init(savedState value: SavedState) throws {
        guard !value.records.isEmpty, value.records.count <= 100000,
              value.firstImage >= 0, value.lastImage >= value.firstImage,
              Int(value.lastImage) < value.imageTokens.count,
              Set(value.eventNames.map(\.token)).count == value.eventNames.count else { throw ClawSnapshotError.invalidState }
        records = value.records.map(\.value); imageTokens = value.imageTokens
        eventNames = Dictionary(uniqueKeysWithValues: value.eventNames.map { ($0.token, $0.name) })
        firstImage = value.firstImage; lastImage = value.lastImage
        state = value.state.value; actor = value.actor.value; event = value.event.value; result = value.result
    }

    init(animation: ClawAnimation, availableImages: [Int], startImmediately: Bool = true,
        imageIdentities: [Int: UInt32]? = nil) throws {
        guard !animation.frames.isEmpty,
              let first = availableImages.min(), let last = availableImages.max(),
              first >= 0, last < 100_000 else { throw AssetError.invalid("Invalid animation images") }
        firstImage = Int32(first); lastImage = Int32(last)
        var tokens = [UInt32](repeating: 0, count: last + 1)
        for id in availableImages {
            if let imageIdentities {
                guard let token = imageIdentities[id], token != 0 else { throw AssetError.invalid("Missing image identity \(id)") }
                tokens[id] = token
            } else { tokens[id] = UInt32(id + 1) }
        }
        imageTokens = tokens
        var names: [UInt32: String] = [:]
        records = animation.frames.enumerated().map { index, frame in
            var record = frame.record
            if let name = frame.event, !name.isEmpty {
                let token = UInt32(index + 1)
                record.event = token
                names[token] = name
            }
            return record
        }
        eventNames = names
        actor.imageID = UInt32(first)
        actor.imageToken = tokens[first]
        restart(updateImmediately: startImmediately)
    }

    mutating func restart(updateImmediately: Bool = true) {
        state.hasSequence = 1
        state.recordIndex = 0; state.remaining = 0; state.stopped = 0
        state.code = records[0].code; state.previousCode = records[0].code
        state.rate = 1
        if updateImmediately { update(delta: 0) }
    }

    // A player sequence selection can leave the current image in place until
    // the original caller asks to advance it. Presentation preview keeps its
    // immediate first-frame behavior through the default initializer argument.
    mutating func synchronize(actor: ClawAnimationActor, rate: Float) {
        self.actor = actor
        state.rate = rate
    }

    mutating func update(delta: UInt32, masterVolume: UInt32 = 0) {
        records.withUnsafeBufferPointer { records in
            imageTokens.withUnsafeBufferPointer { images in
                result = claw_animation_update(&state, &actor, records.baseAddress,
                    UInt32(records.count), images.baseAddress, firstImage, lastImage,
                    delta, masterVolume, &event)
            }
        }
    }
}

extension ClawAnimationRecord: ClawSnapshotNativeValue {}
extension ClawAnimationState: ClawSnapshotNativeValue {}
extension ClawAnimationActor: ClawSnapshotNativeValue {}
extension ClawAnimationEvent: ClawSnapshotNativeValue {}
