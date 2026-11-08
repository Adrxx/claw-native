import Foundation
import CryptoKit

// App-owned super checkpoint plus pointer-free progress in the restarted map.
struct ClawCustomCheckpoint: Codable {
    static let format = 6
    enum Failure: LocalizedError {
        case invalidFile, unavailable, loadFailed, legacy
        var errorDescription: String? {
            switch self {
            case .legacy: return "Old world-state checkpoint ignored. Save a new checkpoint."
            case .invalidFile: return "Custom checkpoint is invalid."
            case .unavailable: return "No custom checkpoint for this level."
            case .loadFailed: return "Custom checkpoint level could not be loaded."
            }
        }
    }
    var version = format
    let level: UInt32
    let customPath: String?
    let mapSHA256: String?
    let values: [UInt32]
    let facing: UInt32, weapon: UInt32
    let removedPlacements: [ClawCheckpointPlacement]?
    let extraLifeThreshold: UInt32?
    let hudExtraLifeThreshold: UInt32?
    let livesLost: UInt32?
    let treasure: [UInt32]?, totalTreasure: [UInt32]?
    let powerKind: UInt32?, powerMilliseconds: UInt32?
    var mechanisms: [ClawCheckpointMechanism]? = nil
    var loot: [ClawCheckpointLoot]? = nil
    var progressLimits: [String]? = nil
    var bossStage: ClawCheckpointBossStage? = nil
    var framePhase: UInt32? = nil
    // The newest payload stays compatible with single-slot readers. Older
    // envelopes are flat, newest first; one atomic write rotates all slots.
    private struct Envelope: Codable {
        let payload: Data
        let digest: Data
        var previous: [Data]? = nil
        var savedAt: Date? = nil
    }
    static func slotDates(_ url: URL) throws -> [Date] {
        let envelope = try loadEnvelope(url)
        let fallback = (try? url.resourceValues(forKeys:[.contentModificationDateKey]).contentModificationDate) ?? .distantPast
        return try ([envelope] + (envelope.previous ?? []).map {
            try PropertyListDecoder().decode(Envelope.self,from:$0)
        }).map {$0.savedAt ?? fallback}
    }
    private static func loadEnvelope(_ url: URL) throws -> Envelope {
        let size = try url.resourceValues(forKeys:[.fileSizeKey]).fileSize ?? 0
        guard size > 0, size <= 48 << 20 else {throw Failure.invalidFile}
        let envelope = try PropertyListDecoder().decode(Envelope.self,from:Data(contentsOf:url))
        guard (envelope.previous?.count ?? 0) <= 2 else {throw Failure.invalidFile}
        return envelope
    }
    func push(_ url: URL) throws {
        let encoder = PropertyListEncoder(); encoder.outputFormat = .binary
        let payload = try encoder.encode(self)
        var previous: [Data] = []
        if FileManager.default.fileExists(atPath:url.path) {
            var old = try Self.loadEnvelope(url)
            previous = old.previous ?? []
            old.previous = nil
            if old.savedAt == nil {
                old.savedAt = (try? url.resourceValues(forKeys:[.contentModificationDateKey]).contentModificationDate) ?? Date()
            }
            previous.insert(try encoder.encode(old),at:0)
        }
        let envelope = Envelope(payload:payload,digest:Data(SHA256.hash(data:payload)),
            previous:Array(previous.prefix(2)),savedAt:Date())
        try FileManager.default.createDirectory(at:url.deletingLastPathComponent(),withIntermediateDirectories:true)
        try encoder.encode(envelope).write(to:url,options:.atomic)
    }
    func write(_ url: URL) throws {
        let encoder = PropertyListEncoder(); encoder.outputFormat = .binary
        let data = try encoder.encode(self)
        let envelope = Envelope(payload:data,digest:Data(SHA256.hash(data:data)))
        try FileManager.default.createDirectory(at:url.deletingLastPathComponent(),withIntermediateDirectories:true)
        try encoder.encode(envelope).write(to:url,options:.atomic)
    }
    static func read(_ url: URL, slot: Int = 0) throws -> Self {
        guard (0..<3).contains(slot) else {throw Failure.unavailable}
        var envelope = try loadEnvelope(url)
        if slot > 0 {
            guard let previous = envelope.previous, previous.indices.contains(slot-1) else {throw Failure.unavailable}
            envelope = try PropertyListDecoder().decode(Envelope.self,from:previous[slot-1])
        }
        guard Data(SHA256.hash(data:envelope.payload)) == envelope.digest else {throw Failure.invalidFile}
        let header = try PropertyListSerialization.propertyList(from:envelope.payload,format:nil) as? [String:Any]
        if header?["version"] as? Int == 2 {throw Failure.legacy}
        let saved = try PropertyListDecoder().decode(Self.self,from:envelope.payload)
        guard [3,4,5,format].contains(saved.version),(1...14).contains(saved.level),saved.values.count == 18,
              saved.values[1] > 0,saved.values[1] <= 100,
              saved.values[2] < 0x100000,saved.values[3] < 0x100000,
              saved.facing & ~UInt32(2) == 0,(1...3).contains(saved.weapon),
              (saved.customPath == nil) == (saved.mapSHA256 == nil) else {throw Failure.invalidFile}
        guard (saved.removedPlacements?.count ?? 0) < 100000,
              Set(saved.removedPlacements ?? []).count == (saved.removedPlacements?.count ?? 0),
              saved.treasure == nil || saved.treasure?.count == 10,
              saved.totalTreasure == nil || saved.totalTreasure?.count == 10,
              saved.powerKind == nil || saved.powerKind == 0 || (0x26b7...0x26bd).contains(saved.powerKind!) else {throw Failure.invalidFile}
        let mechanisms = saved.mechanisms ?? []
        guard mechanisms.count < 100000, Set(mechanisms.map(\.placement)).count == mechanisms.count,
              mechanisms.allSatisfy({$0.valid}) else {throw Failure.invalidFile}
        guard (saved.loot?.count ?? 0) < 100000,saved.loot?.allSatisfy({$0.valid}) ?? true else {throw Failure.invalidFile}
        guard (saved.progressLimits?.count ?? 0) <= 32,saved.progressLimits?.allSatisfy({$0.utf8.count <= 256}) ?? true else {throw Failure.invalidFile}
        guard saved.bossStage?.valid ?? true else {throw Failure.invalidFile}
        guard saved.framePhase == nil || saved.framePhase! < 3 else {throw Failure.invalidFile}
        if let path = saved.customPath {
            let digest = SHA256.hash(data:try Data(contentsOf:URL(fileURLWithPath:path))).map{String(format:"%02x",$0)}.joined()
            guard digest == saved.mapSHA256 else {throw ClawCrazyHookSaves.Failure.changedMap}
        }
        return saved
    }
}

// Only named scalar properties cross the disk boundary. Scene/list membership,
// callbacks, image groups and logic-private controllers belong to the new map.
struct ClawCheckpointMechanism: Codable {
    let placement: ClawCheckpointPlacement
    let logic: String
    let actor: [UInt32]
    let primary: [UInt32]
    var motion: [UInt32]? = nil
    var path: [UInt32]? = nil
    var switchPhase: [UInt32]? = nil
    var stone: [UInt32]? = nil
    var superFlags: UInt32? = nil
    var animation: ClawCheckpointAnimation? = nil
    static let supported: Set<String> = ["Elevator", "StartElevator", "TriggerElevator",
        "OneWayStartElevator", "OneWayTriggerElevator", "TogglePeg", "TogglePeg2",
        "TogglePeg3", "TogglePeg4", "ClawDialogSoundTrigger", "SmallSoundTrigger",
        "JumpSwitch", "PathElevator", "StartSteppingStone", "FirstSuperCheckpoint", "SecondSuperCheckpoint"]
    static let superLogics: Set<String> = ["FirstSuperCheckpoint", "SecondSuperCheckpoint"]
    static let actorOffsets: [UInt32] = [0x4c,0x50,0x40,0x148,0x14c,0x110,0x114,
        0xdc,0xe0,0x118,0x11c,0x120,0x124,0x128,0x12c,0x130,0x134,0x16c]
    static let primaryOffsets: [UInt32] = [0x1c,0x20,0x24,0x28,0xb8,0xbc]
    static let movingLogics: Set<String> = ["Elevator","StartElevator","TriggerElevator","OneWayStartElevator","OneWayTriggerElevator","PathElevator"]
    // Native movement phase, bounds and activation masks; none are references.
    static let motionActorOffsets: [UInt32] = [0x158,0x15c,0x164]
    static let motionPrimaryOffsets: [UInt32] = [0x2c,0x30,0x34,0x38,0x3c,0x40,0x44,0x48,0x4c,0x50,0x64]
    var valid: Bool {
        placement.plane < 16 && Self.supported.contains(logic) && actor.count == Self.actorOffsets.count && primary.count == Self.primaryOffsets.count && actor[0] < 0x100000 && actor[1] < 0x100000 &&
        (motion == nil || (Self.movingLogics.contains(logic) && motion?.count == Self.motionActorOffsets.count + Self.motionPrimaryOffsets.count)) &&
        (path == nil || (logic == "PathElevator" && path?.count == 3)) &&
        (switchPhase == nil || (logic == "JumpSwitch" && switchPhase?.count == 2)) &&
        (stone == nil || (logic == "StartSteppingStone" && stone?.count == 3)) &&
        (superFlags == nil || (Self.superLogics.contains(logic) && superFlags! & ~UInt32(5) == 0)) && (animation?.valid ?? true)
    }
}

struct ClawCheckpointLoot: Codable {
    static let supported: Set<String> = ["TreasurePowerup", "GlitterlessPowerup", "BouncingGoodie"]
    let owner: ClawCheckpointPlacement?
    let logic: String
    let identifier: UInt32, z: UInt32, flags: UInt32
    let actor: [UInt32]
    var bounce: ClawCheckpointBounce? = nil
    static let actorOffsets: [UInt32] = [4,0x4c,0x50,0x40,0x148,0x14c,0x110,0x114,0xf8,0xfc,0x100,0x104,0x108]
    var valid: Bool {(owner?.plane ?? 0) < 16 && Self.supported.contains(logic) && actor.count == Self.actorOffsets.count && actor[1] < 0x100000 && actor[2] < 0x100000 && flags & ~UInt32(0x1040000) == 0 && (bounce == nil || (logic == "BouncingGoodie" && bounce!.valid))}
}

struct ClawCheckpointBounce: Codable {
    let item: UInt32
    let gravity: Double, velocityX: Double, velocityY: Double
    var physics: [Double]? = nil
    var stopped: UInt32? = nil
    var phase: [UInt32]? = nil
    var dynamics: [UInt32]? = nil
    var animation: ClawCheckpointAnimation? = nil
    // ClawPlayerPhysics is numerical throughout. Skip the stopped/unused words
    // between delta and remainder; serialize no part of the adjacent owner.
    static let physicsOffsets: [UInt32] = Array(stride(from:0x28,through:0xc0,by:8)) + Array(stride(from:0xd0,through:0x110,by:8))
    static let phaseOffsets: [UInt32] = [0x190,0x194,0x198,0x19c,0x24]
    static let dynamicsOffsets: [UInt32] = [8,0xcc,0xd0,0x164,0x118,0x11c,0x120,0x124,0x128,0x12c,0x130,0x134,0x138,0x13c,0x140,0x144]
    var valid: Bool {item < 62 && [gravity,velocityX,velocityY].allSatisfy {$0.isFinite && abs($0) <= 100000} &&
        (physics == nil || (physics?.count == Self.physicsOffsets.count && physics!.allSatisfy(\.isFinite))) &&
        (phase == nil || phase?.count == Self.phaseOffsets.count+1) &&
        (dynamics == nil || dynamics?.count == Self.dynamicsOffsets.count) && (animation?.valid ?? true)}
}

struct ClawCheckpointAnimation: Codable {
    let name: String, index: UInt32
    let scalars: [UInt32]
    static let offsets: [UInt32] = [0x14,0x18,0x1c,0x20,0x24,0x28]
    var valid: Bool {!name.isEmpty && name.utf8.count <= 128 && index < 100000 && scalars.count == Self.offsets.count && Float(bitPattern:scalars[5]).isFinite && Float(bitPattern:scalars[5]) >= 0 && Float(bitPattern:scalars[5]) <= 1000}
}

// A completed staging sequence can leave a live boss and health meter. Resolve
// the boss by its WWD identity and construct a new meter; no old association is
// retained. Speech still in progress is deliberately outside this recipe.
struct ClawCheckpointBossStage: Codable {
    let phase: UInt32
    let boss: ClawCheckpointPlacement?
    let healthMeter: Bool
    var valid: Bool {phase == 2 && (boss?.plane ?? 0) < 16 && (!healthMeter || boss != nil)}
}

// CrazyHook's two per-map super checkpoints are independent of the app's
// manual super checkpoint and retail CLAW.USR. Only data is decoded; saved Lua is never run.
struct ClawCrazyHookSaves: Codable {
    static let format = 1
    var version = format
    var mapSHA256: String
    var slots: [Int: [UInt32]] = [:]
    var completion: [UInt32]? = nil
    enum Failure: LocalizedError {
        case invalid, version, changedMap
        var errorDescription: String? {
            switch self {
            case .invalid: return "Custom checkpoint is corrupt or has an invalid checksum."
            case .version: return "Custom checkpoint version is unsupported."
            case .changedMap: return "Custom checkpoint belongs to a different version of this map. Start a new game."
            }
        }
    }
    static func scriptOwned(_ package:ClawCustomAssets) -> Bool {package.files["LOGICS/SAVESYSTEM.LUA"] != nil}
    private struct Envelope: Codable { let payload: Data; let digest: Data }
    static func read(_ url: URL, map: String) throws -> Self {
        let size = try url.resourceValues(forKeys:[.fileSizeKey]).fileSize ?? 0
        guard size > 0, size < 65536 else {throw Failure.invalid}
        do {
            let envelope = try PropertyListDecoder().decode(Envelope.self,from:Data(contentsOf:url))
            guard Data(SHA256.hash(data:envelope.payload)) == envelope.digest else {throw Failure.invalid}
            let saved = try PropertyListDecoder().decode(Self.self,from:envelope.payload)
            guard saved.version == format else {throw Failure.version}
            guard saved.mapSHA256 == map else {throw Failure.changedMap}
            guard saved.slots.count <= 2, saved.slots.allSatisfy({ key,v in
                (1...2).contains(key) && v.count == 18 && v[1] > 0 && v[1] <= 100 && v[2] < 0x100000 && v[3] < 0x100000
            }), saved.completion == nil || saved.completion!.count == 2 else {throw Failure.invalid}
            return saved
        } catch let error as Failure {throw error} catch {throw Failure.invalid}
    }
    func write(_ url: URL) throws {
        let encoder = PropertyListEncoder();encoder.outputFormat = .binary
        let payload = try encoder.encode(self)
        let data = try encoder.encode(Envelope(payload:payload,digest:Data(SHA256.hash(data:payload))))
        try FileManager.default.createDirectory(at:url.deletingLastPathComponent(),withIntermediateDirectories:true)
        try data.write(to:url,options:.atomic)
    }
    static func checkStore(_ folder:URL) throws -> [String:Any] {
        let url = folder.appendingPathComponent("fixture.plist")
        var saved = Self(mapSHA256:"fixture")
        let values:[UInt32] = [12345,73,320,480,7,8,9,4,1,2,3,4,5,6,7,8,9,45678]
        guard saved.save(values,slot:1),saved.save(values,slot:2) else {throw Failure.invalid}
        var worse = values;worse[0] -= 1
        guard !saved.save(worse,slot:1) else {throw Failure.invalid}
        worse = values;worse[7] -= 1
        guard !saved.save(worse,slot:1),saved.save(values,slot:1) else {throw Failure.invalid}
        try saved.write(url)
        guard try read(url,map:"fixture").slots == saved.slots else {throw Failure.invalid}
        do {_ = try read(url,map:"changed");throw Failure.invalid} catch Failure.changedMap {}
        var bad = saved;bad.version += 1;try bad.write(url)
        do {_ = try read(url,map:"fixture");throw Failure.invalid} catch Failure.version {}
        try saved.write(url)
        let data = try Data(contentsOf:url)
        var envelope = try PropertyListDecoder().decode(Envelope.self,from:data)
        envelope = Envelope(payload:envelope.payload+Data([0]),digest:envelope.digest)
        try PropertyListEncoder().encode(envelope).write(to:url)
        do {_ = try read(url,map:"fixture");throw Failure.changedMap} catch Failure.invalid {}
        try Data(data.prefix(20)).write(to:url)
        do {_ = try read(url,map:"fixture");throw Failure.changedMap} catch Failure.invalid {}
        guard !saved.complete(collected:45,total:45,cheated:true),saved.completion == nil,
              saved.complete(collected:40,total:45,cheated:false),
              !saved.complete(collected:39,total:45,cheated:false),
              saved.complete(collected:45,total:45,cheated:false) else {throw Failure.invalid}
        try saved.write(url)
        guard try read(url,map:"fixture").completion == [45,45] else {throw Failure.invalid}
        try FileManager.default.removeItem(at:url)
        return ["two_slots_and_score_lives_precedence":true,"roundtrip_player_treasure_time":true,
                "changed_map_version_checksum_truncation_rejected":true,"completion_best_perfect_and_cheat_exclusion":true]
    }
    // The release replaces a checkpoint only for a higher score, or equal
    // score with at least as many lives. Elapsed time is the 1.4.5.4 addition.
    mutating func save(_ values:[UInt32], slot:Int) -> Bool {
        guard values.count == 18,(1...2).contains(slot) else {return false}
        if let old = slots[slot],values[0] < old[0] || (values[0] == old[0] && values[7] < old[7]) {return false}
        slots[slot] = values;return true
    }
    mutating func complete(collected:UInt32,total:UInt32,cheated:Bool) -> Bool {
        guard !cheated, completion == nil || collected > completion![0] else {return false}
        completion = [collected,total];return true
    }
}
