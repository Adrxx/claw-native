import Foundation
import CryptoKit

// An owner can outlive its actor's token and coexist with a later owner of that
// same token. Graph edges therefore name the allocation witness as well.
struct ClawSnapshotOwnerKey: Codable, Equatable, Hashable {
    let token: UInt32
    let allocation: UUID
}

// Explicit scalar projections for native contexts that also contain borrowed
// pointers. Each schema lists only integers, floats and their fixed C arrays.
// Restore leaves the fresh candidate's pointer fields intact. In particular,
// this never copies an entire pointer-bearing context or a ClawCall.
struct ClawSnapshotFields<Root> {
    struct Field {
        let name: String
        let read: (Root) -> Data
        let write: (inout Root, Data) throws -> Void
        init<Value>(_ name: String, _ path: WritableKeyPath<Root, Value>) {
            self.name = name
            read = { root in var value = root[keyPath: path]; return withUnsafeBytes(of: &value) { Data($0) } }
            write = { root, bytes in
                guard bytes.count == MemoryLayout<Value>.size else { throw ClawSnapshotError.invalidState }
                var value = root[keyPath: path]
                _ = withUnsafeMutableBytes(of: &value) { bytes.copyBytes(to: $0) }
                root[keyPath: path] = value
            }
        }
    }
    let fields: [Field]
    func capture(_ root: Root) -> [String: Data] {
        Dictionary(uniqueKeysWithValues: fields.map { ($0.name, $0.read(root)) })
    }
    func restoring(_ saved: [String: Data], into root: Root) throws -> Root {
        guard Set(saved.keys) == Set(fields.map(\.name)) else { throw ClawSnapshotError.invalidState }
        var candidate = root
        for field in fields { try field.write(&candidate, saved[field.name]!) }
        return candidate
    }
}

// This envelope deliberately separates the original token image from Swift
// owner state. A complete scene decoder must consume every named owner before
// committing; a heap image on its own must never be presented as a saved game.
struct ClawSnapshotImage: Codable, Equatable {
    static let version = 1
    let format: Int
    let build: String
    let level: UInt32
    let heap: ClawTokenHeap.Image
    let owners: [String: Data]

    init(build: String, level: UInt32, heap: ClawTokenHeap.Image, owners: [String: Data]) {
        format = Self.version; self.build = build; self.level = level
        self.heap = heap; self.owners = owners
    }
    func validate(build: String) throws {
        guard format == Self.version, (1...14).contains(level), !self.build.isEmpty,
              !owners.isEmpty, owners.count <= 4096,
              owners.values.reduce(0, { $0 + $1.count }) <= 128 << 20,
              owners.keys.allSatisfy({ !$0.isEmpty && $0.utf8.count <= 256 })
        else { throw ClawSnapshotError.invalidState }
        guard self.build == build else { throw ClawSnapshotError.incompatibleBuild }
    }
}

// Decoding/validation is fallible and mutation-free. The caller builds a fresh
// scene/owner graph off screen, consumes every owner, then swaps the scene at a
// frame boundary. In-place heap replacement alone is intentionally insufficient.
struct ClawSnapshotOwnerDecoder {
    private var remaining: [String: Data]
    init(_ owners: [String: Data], requiring expected: Set<String>) throws {
        guard !expected.isEmpty, Set(owners.keys) == expected else { throw ClawSnapshotError.incompleteOwners }
        remaining = owners
    }
    mutating func decode<T: Decodable>(_ type: T.Type, key: String) throws -> T {
        guard let bytes = remaining[key] else { throw ClawSnapshotError.incompleteOwners }
        let value = try PropertyListDecoder().decode(type, from: bytes)
        remaining.removeValue(forKey: key)
        return value
    }
    func finish() throws {
        guard remaining.isEmpty else { throw ClawSnapshotError.incompleteOwners }
    }
    static func encode<T: Encodable>(_ value: T) throws -> Data {
        let encoder = PropertyListEncoder(); encoder.outputFormat = .binary
        return try encoder.encode(value)
    }
}

// Quick slot and three numbered slots, in the app's private support directory.
// The build identifier should be the installed executable's SHA-256, rather
// than CFBundleVersion (development builds often share that version).
final class ClawSnapshotSlots {
    enum Slot: Int, CaseIterable, Codable { case quick = 0, one, two, three }
    private struct Envelope: Codable {
        let magic: String
        let payload: Data
        let checksum: Data
    }
    let directory: URL
    let build: String
    private var memory: [Slot: ClawSnapshotImage] = [:]
    private static let maximumFileBytes = 768 << 20

    init(directory: URL, build: String) {
        self.directory = directory; self.build = build
    }
    static func applicationSupportDirectory() throws -> URL {
        try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask,
            appropriateFor: nil, create: true).appendingPathComponent("Claw/Snapshots", isDirectory: true)
    }
    static func executableBuildIdentifier(_ executable: URL) throws -> String {
        let data = try Data(contentsOf: executable, options: .mappedIfSafe)
        return SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }
    func file(_ slot: Slot) -> URL { directory.appendingPathComponent("slot-\(slot.rawValue).clawsnapshot") }

    func save(_ image: ClawSnapshotImage, to slot: Slot) throws {
        try image.validate(build: build)
        // Reject malformed heap topology before replacing a previous good slot.
        try image.heap.validate()
        let payload = try ClawSnapshotOwnerDecoder.encode(image)
        let envelope = Envelope(magic: "CLAW-SNAPSHOT-1", payload: payload, checksum: Data(SHA256.hash(data: payload)))
        let data = try ClawSnapshotOwnerDecoder.encode(envelope)
        guard data.count <= Self.maximumFileBytes else { throw ClawSnapshotError.invalidState }
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        try data.write(to: file(slot), options: .atomic)
        // A failed disk write leaves both the old on-disk and in-memory slot.
        memory[slot] = image
    }
    func load(_ slot: Slot) throws -> ClawSnapshotImage {
        if let cached = memory[slot] { return cached }
        let path = file(slot)
        let size = try path.resourceValues(forKeys: [.fileSizeKey]).fileSize ?? 0
        guard size > 0, size <= Self.maximumFileBytes else { throw ClawSnapshotError.invalidState }
        let data = try Data(contentsOf: path)
        guard data.count <= Self.maximumFileBytes else { throw ClawSnapshotError.invalidState }
        let envelope = try PropertyListDecoder().decode(Envelope.self, from: data)
        guard envelope.magic == "CLAW-SNAPSHOT-1",
              envelope.checksum == Data(SHA256.hash(data: envelope.payload)) else { throw ClawSnapshotError.invalidState }
        let image = try PropertyListDecoder().decode(ClawSnapshotImage.self, from: envelope.payload)
        try image.validate(build: build)
        try image.heap.validate()
        memory[slot] = image
        return image
    }
    func occupied() -> [Slot] {
        Slot.allCases.filter { memory[$0] != nil || FileManager.default.fileExists(atPath: file($0).path) }
    }
}
