import Foundation

struct Mutation: Decodable {
    let kind: String
    let occurrence: Int
    let flags: [UInt32]
}
struct Profile: Decodable {
    let name: String
    let display: Bool
    let flags: [UInt32]
    let filename: UInt32
    let line: UInt32
    let result: UInt32
    let mutations: [Mutation]
    let events: [ClawNativeDiagnostics.Effect]
    let finalFlags: [UInt32]
}
struct Reference: Decodable {
    let originalSHA256: String
    let rows: [Profile]
}
func require(_ condition: @autoclosure () -> Bool, _ message: String) {
    if !condition() { fatalError(message) }
}
let reference = try JSONDecoder().decode(Reference.self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
require(reference.originalSHA256 == "350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263", "wrong reference original")
let assetURL = URL(fileURLWithPath: CommandLine.arguments[2])
let filename = Array("C:\\join\\café.cpp".data(using: .windowsCP1252)!) + [UInt8(0)]
let filenameMemory = UnsafeMutablePointer<UInt8>.allocate(capacity: filename.count)
filenameMemory.initialize(from: filename, count: filename.count)
defer { filenameMemory.deallocate() }
func filenameBytes(_ token: UInt32, _ count: UInt32) -> UnsafeMutablePointer<UInt8>? {
    guard token >= 0x3000000, UInt64(token)+UInt64(count) <= 0x3000000+UInt64(filename.count) else { return nil }
    return filenameMemory.advanced(by: Int(token-0x3000000))
}
let untouched: [UInt32] = [9,8,7,6]
var totalPhysical = 0
for row in reference.rows {
    var observed: [ClawNativeDiagnostics.Effect] = []
    var physical: [String] = []
    let effects = ClawNativeDiagnostics.Effects(
        beep: { kind in require(kind == 0x30, "beep kind"); physical.append("beep"); return true },
        log: { _ in physical.append("log"); return true },
        dialog: { _, _, parent, flags in
            require(parent == 0 && flags == 0x30, "dialog physical arguments")
            physical.append("dialog"); return true
        })
    let owner = ClawNativeDiagnostics(assetURL: assetURL, effects: effects)
    owner.setFlags(display: !row.display, untouched)
    owner.setFlags(display: row.display, row.flags)
    owner.observe = { effect in
        observed.append(effect)
        let occurrence = observed.filter { $0.kind == effect.kind }.count
        for mutation in row.mutations where mutation.kind == effect.kind && mutation.occurrence == occurrence {
            owner.setFlags(display: row.display, mutation.flags)
        }
    }
    let result = owner.report(display: row.display, filename: row.filename, line: row.line, result: row.result, bytes: filenameBytes)
    require(result && owner.fault == 0, "\(row.name): native fault \(owner.fault) at \(String(owner.faultAddress, radix: 16))")
    if observed != row.events {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let actual = String(data: try encoder.encode(observed), encoding: .utf8)!
        let expected = String(data: try encoder.encode(row.events), encoding: .utf8)!
        fatalError("\(row.name): event mismatch\nnative: \(actual)\noriginal: \(expected)")
    }
    require(owner.flagWords(display: row.display) == row.finalFlags, "\(row.name): final flags")
    require(owner.flagWords(display: !row.display) == untouched, "\(row.name): independent owner flags")
    let entry: UInt32 = row.display ? 0x4bd260 : 0x4b4ed0
    require(owner.entries == [entry: 1], "\(row.name): entry accounting")
    require(physical == row.events.map(\.kind).filter { ["beep","log","dialog"].contains($0) }, "\(row.name): physical effects exactly once and ordered")
    totalPhysical += physical.count
    owner.observe = nil
}

// Native service failure is a host fault, separate from original game outcomes.
// Both absent and rejecting services must stop the policy without later effects.
var failureControls = 0
for display in [false, true] {
    for kind in ["beep", "log", "dialog"] {
        if display && kind == "log" { continue }
        for absent in [false, true] {
            var physical: [String] = []
            var observed: [ClawNativeDiagnostics.Effect] = []
            let baseline = reference.rows.first { $0.display == display && $0.name == "\(display ? "display" : "audio")-flags-15" }!
            var effects = ClawNativeDiagnostics.Effects(
                beep: { _ in physical.append("beep"); return kind != "beep" },
                log: { _ in physical.append("log"); return kind != "log" },
                dialog: { _, _, _, _ in physical.append("dialog"); return kind != "dialog" })
            if absent {
                switch kind {
                case "beep": effects.beep = nil
                case "log": effects.log = nil
                default: effects.dialog = nil
                }
            }
            let owner = ClawNativeDiagnostics(assetURL: assetURL, effects: effects)
            owner.setFlags(display: display, [1,1,1,1])
            owner.observe = { observed.append($0) }
            require(!owner.report(display: display, filename: baseline.filename, line: baseline.line, result: baseline.result, bytes: filenameBytes), "\(kind) missing effect accepted")
            let address: UInt32 = kind == "beep" ? 0x546ca4 : kind == "log" ? 0x546a08 : 0x546d48
            require(owner.fault == UInt32(CLAW_FAULT_HOST) && owner.faultAddress == address, "\(kind) wrong sticky host fault")
            let failedIndex = baseline.events.firstIndex { $0.kind == kind }!
            let expectedPrefix = Array(baseline.events.prefix(failedIndex))
            require(observed == expectedPrefix, "failed effect did not stop at the original event prefix")
            let expectedPhysical = expectedPrefix.map(\.kind).filter { ["beep","log","dialog"].contains($0) } + (absent ? [] : [kind])
            require(physical == expectedPhysical, "missing/rejecting effect executed the wrong physical prefix")
            let snapshot = physical
            let eventSnapshot = observed
            require(!owner.report(display: display, filename: 0, line: 1, result: 1), "sticky fault accepted retry")
            require(physical == snapshot && observed == eventSnapshot, "sticky fault repeated physical effects")
            owner.observe = nil
            failureControls += 1
        }
    }
}
// The display sink is a real RET-only call; no logger is needed even when enabled.
let displaySink = ClawNativeDiagnostics(assetURL: assetURL, effects: .init(beep: nil, log: nil, dialog: nil))
displaySink.setFlags(display: true, [1,0,0,0])
var displayEvents: [String] = []
displaySink.observe = { displayEvents.append($0.kind) }
require(displaySink.report(display: true, filename: 0, line: 0, result: 1), "display RET sink required a logger")
require(displayEvents.last == "display-sink", "display RET sink omitted")
displaySink.observe = nil

print("{\"nativeDiagnosticJoin\":\"pass\",\"originalProfiles\":\(reference.rows.count),\"failureControls\":\(failureControls),\"physicalSpyCalls\":\(totalPhysical),\"displayRetSinkControl\":true,\"liveEffects\":false,\"familyAdmission\":false,\"visibleUIAcceptance\":false}")
