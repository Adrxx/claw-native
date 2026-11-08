import Foundation

// Prepared bounded source data, never original executable instructions. The
// Runtime owners validate their supported address inventories on installation.
struct ClawNativeApplicationMetadata: Sendable {
    enum Failure: Error { case schema, source, address, bytes }
    let sha256: String
    let strings: [UInt32: [UInt8]]
    let discStrings: [UInt32: [UInt8]]
    let textStrings: [UInt32: [UInt8]]
    let initialGlobals: [UInt32: UInt32]
    let textInitialGlobals: [UInt32: UInt32]
    let pregraphicsInitialGlobals: [UInt32: UInt32]

    static func load(from file: URL) throws -> Self {
        struct Encoded: Decodable {
            let schema: Int, sha256: String
            let strings: [String: String]
            let discStrings: [String: String]?
            let textStrings: [String: String]?
            let initialGlobals: [String: UInt32]
            let textInitialGlobals: [String: UInt32]?
            let pregraphicsInitialGlobals: [String: UInt32]?
        }
        let data = try JSONDecoder().decode(Encoded.self, from: Data(contentsOf: file))
        guard data.schema == 1 else { throw Failure.schema }
        guard data.sha256 == "350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263" else {
            throw Failure.source
        }
        func address(_ key: String) throws -> UInt32 {
            guard let value = UInt32(key), String(value) == key, value & 3 == 0 else { throw Failure.address }
            return value
        }
        func decodeStrings(_ encoded: [String: String]) throws -> [UInt32: [UInt8]] {
            var strings: [UInt32: [UInt8]] = [:]
            for (key, hex) in encoded {
                let token = try address(key)
                let digits = Array(hex.utf8)
                guard !digits.isEmpty, digits.count <= 512, digits.count % 2 == 0 else { throw Failure.bytes }
                func nibble(_ byte: UInt8) throws -> UInt8 {
                    switch byte {
                    case 48...57: return byte - 48
                    case 97...102: return byte - 87
                    default: throw Failure.bytes
                    }
                }
                var bytes: [UInt8] = []
                for index in stride(from: 0, to: digits.count, by: 2) {
                    bytes.append(try nibble(digits[index]) << 4 | nibble(digits[index + 1]))
                }
                guard bytes.last == 0, !bytes.dropLast().contains(0) else { throw Failure.bytes }
                strings[token] = bytes
            }
            return strings
        }
        func decodeGlobals(_ encoded: [String: UInt32]) throws -> [UInt32: UInt32] {
            var globals: [UInt32: UInt32] = [:]
            for (key, word) in encoded { globals[try address(key)] = word }
            return globals
        }
        return Self(sha256: data.sha256, strings: try decodeStrings(data.strings),
                    discStrings: try decodeStrings(data.discStrings ?? [:]),
                    textStrings: try decodeStrings(data.textStrings ?? [:]),
                    initialGlobals: try decodeGlobals(data.initialGlobals),
                    textInitialGlobals: try decodeGlobals(data.textInitialGlobals ?? [:]),
                    pregraphicsInitialGlobals: try decodeGlobals(data.pregraphicsInitialGlobals ?? [:]))
    }
}
