import Foundation

struct Profile: Decodable {
    let label: String
    let events: [ClawNativeWindowInputQueue.Event]
    let message: UInt32
    let maximum: UInt32
    let windows: [UInt32]
}
struct Witness: Encodable {
    let label: String
    let survivors: [ClawNativeWindowInputQueue.Event]
    let queries: [UInt32]
}
let profiles = try JSONDecoder().decode([Profile].self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
var witnesses: [Witness] = []
for profile in profiles {
    let queue = ClawNativeWindowInputQueue()
    precondition(queue.openWindow() == 1 && queue.openWindow() == 2)
    for event in profile.events { try queue.capture(event) }
    var queries: [UInt32] = []
    try queue.drain(message: profile.message, maximum: profile.maximum) {
        let window = profile.windows[min(queries.count, profile.windows.count - 1)]
        queries.append(window)
        return window
    }
    witnesses.append(.init(label: profile.label, survivors: queue.pending, queries: queries))
}
func rejects(_ operation: () throws -> Void) {
    do { try operation(); preconditionFailure("Missing rejection") } catch {}
}
let queue = ClawNativeWindowInputQueue()
let input = ClawNativeWindowInput(queue: queue), other = ClawNativeWindowInput(queue: queue)
input.key(mask: 1, down: true)
input.primary(mask: 2, down: true)
input.key(mask: 4, down: false)
other.key(mask: 8, down: true)
let before = queue.pending
rejects { try queue.drain(message: 0x999, maximum: 64) { input.window } }
for invalid: UInt32 in [0, .max, 99] {
    rejects { try queue.drain(message: 0, maximum: 64) { invalid } }
}
precondition(queue.pending == before)
try queue.drain(message: 0x100, maximum: 64) { input.window }
precondition(input.held == 3 && queue.pending.count == 3)
let delivered = input.frameInput()
precondition(delivered.held == 3 && delivered.pressed == 2)
precondition(queue.pending.count == 1 && queue.pending[0].window == other.window)
precondition(other.frameInput().pressed == 8)
// Both input sources can hold the same action independently.
input.primary(mask: 1, down: true)
input.key(mask: 1, down: false)
precondition(input.held == 3)
input.primary(mask: 1, down: false)
precondition(input.held == 2)
// Removal never invokes delivery; a later pump cannot observe discarded events.
input.key(mask: 16, down: true)
try queue.drain(message: 0, maximum: 64) { input.window }
var dispatches = 0
try queue.deliver(window: input.window) { _ in dispatches += 1 }
precondition(dispatches == 0 && input.held == 18)
let dead = queue.openWindow()
queue.closeWindow(dead)
rejects { try queue.capture(.init(window: dead, message: .keyDown, mask: 0, pressed: false)) }
rejects { try queue.drain(message: 0x100, maximum: 1) { dead } }
// Nonpositive counts do not resolve the receiver or consult event mapping.
for maximum: UInt32 in [0, .max, 0x80000000] {
    try queue.drain(message: 0x999, maximum: maximum) { preconditionFailure("Unexpected receiver read") }
}
try JSONEncoder().encode(witnesses).write(to: URL(fileURLWithPath: CommandLine.arguments[2]))
print("PASS native input mapping, held-state independence, no dispatch, unsupported identities and lifecycle")
