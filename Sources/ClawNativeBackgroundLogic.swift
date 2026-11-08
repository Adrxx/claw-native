import Foundation

/// Native storage for the original BackgroundLogic helper. The per-actor
/// allocation witness prevents an old helper surviving a recycled actor token.
final class ClawNativeBackgroundLogic {
    private struct State {
        let identity: ClawTokenHeap.AllocationIdentity
        var cameraX: UInt32
        var cameraY: UInt32
        var activeX = false
        var activeY = false
    }
    private let heap: ClawTokenHeap
    private let resources: ClawNativeMenuResources
    private let scene: UInt32
    private var states: [UInt32: State] = [:]

    init(heap: ClawTokenHeap, resources: ClawNativeMenuResources, scene: UInt32) {
        self.heap = heap
        self.resources = resources
        self.scene = scene
    }
    private func word(_ at: UInt32) -> UInt32 { heap.lookup(at, words: 1)?.pointee ?? 0 }
    private func put(_ at: UInt32, _ value: UInt32) { heap.lookup(at, words: 1)?.pointee = value }
    private func signed(_ value: UInt32) -> Int32 { Int32(bitPattern: value) }
    private func center() -> (UInt32, UInt32)? {
        let world = word(scene + 0x24), plane = word(world + 0x5c)
        guard world != 0, plane != 0, heap.lookup(plane + 0x84, words: 2) != nil else { return nil }
        return (word(plane + 0x84), word(plane + 0x88))
    }
    private func activation(_ value: UInt32, _ origin: UInt32, _ low: UInt32, _ high: UInt32) -> Bool {
        (low == 0x80000000 || signed(value) >= signed(origin &+ low)) &&
        (high == 0x7fffffff || signed(value) <= signed(origin &+ high))
    }
    private func bounded(_ value: UInt32, _ low: UInt32, _ high: UInt32) -> Bool {
        (low == 0x80000000 || signed(value) >= signed(low)) &&
        (high == 0x7fffffff || signed(value) <= signed(high))
    }
    private func shifted(_ position: UInt32, _ speed: UInt32, _ delta: UInt32) -> UInt32 {
        // Original x87 expression multiplies signed integers before -0.01,
        // then _ftol truncates toward zero. Camera deltas are bounded to 32.
        let change = Int64((Double(signed(speed)) * Double(signed(delta)) * -0.01).rounded(.towardZero))
        return position &- UInt32(truncatingIfNeeded: change)
    }
    func service(_ function: UInt32, _ receiver: UInt32, _ arguments: [UInt32]) -> UInt32? {
        guard function == 0x409090 else { return nil }
        guard receiver == 0, arguments.count == 1 else { return resources.fail(function) }
        let actor = arguments[0], logic = word(actor + 0x6c)
        guard let identity = heap.allocationIdentity(at: actor, count: 0x1b4),
              heap.lookup(logic, words: 93) != nil, let (cx, cy) = center() else {
            return resources.fail(function)
        }
        let mode = word(logic + 0x1c)
        // The original hit, attack and constructor-wait methods are empty.
        if mode == 29 || mode == 30 || mode == 1000 { return 1 }
        if mode == 0 {
            put(logic + 0x1c, 1000)
            _ = resources.invoke(0x4c7fa0, actor, [0x522d54])
            _ = resources.invoke(0x4c8060, actor, [0x522d48])
            let left = word(logic + 0xf0), top = word(logic + 0xf4)
            let right = word(logic + 0xf8), bottom = word(logic + 0xfc)
            if signed(right) <= signed(left) || signed(bottom) <= signed(top) {
                put(logic + 0xf0, 0x80000000)
                put(logic + 0xf4, 0x80000000)
                put(logic + 0xf8, 0x7fffffff)
                put(logic + 0xfc, 0x7fffffff)
            }
            let defaults: [(UInt32, UInt32)] = [(0x2c, 0x80000000), (0x30, 0x7fffffff), (0x34, 0x80000000), (0x38, 0x7fffffff)]
            for (offset, fallback) in defaults {
                if word(logic + offset) == 0 { put(logic + offset, fallback) }
            }
            let image = word(actor + 0x174)
            if image != 0 {
                put(actor + 0x118, word(image + 0x20) &- word(image + 0x18))
                put(actor + 0x11c, word(image + 0x24) &- word(image + 0x1c))
                put(actor + 0x120, word(image + 0x20) &+ word(image + 0x18) &- 1)
                put(actor + 0x124, word(image + 0x24) &+ word(image + 0x1c) &- 1)
            }
            if word(actor + 0x64) == 0 {
                put(actor + 0x64, .max)
                put(actor + 8, word(actor + 8) | 0x20000)
            }
            let result = resources.allocate(4)
            defer { resources.release(result) }
            put(result, 0)
            var lookup = ClawCall()
            lookup.function = 0x4f6286
            lookup.receiver = word(scene + 0x2c) + 0x10
            lookup.argumentCount = 2
            lookup.arguments.0 = 0x523778
            lookup.arguments.1 = result
            _ = resources.service(lookup)
            let animation = word(result)
            _ = resources.invoke(0x4c8220, actor + 0x188, [animation])
            _ = resources.invoke(0x4c82a0, actor + 0x188, [word(0x5430c4)])
            // ES_IDLE is the shared initial state registered as 2000.
            put(logic + 0x1c, 2000)
            states[actor] = State(identity: identity, cameraX: cx, cameraY: cy)
            return resources.fault == 0 ? 1 : resources.fail(function)
        }
        guard var state = states[actor], state.identity === identity, mode == 2000 else {
            return resources.fail(function)
        }
        _ = resources.invoke(0x4c82a0, actor + 0x188, [word(0x5430c4)])
        if activation(cx, word(actor + 0x4c), word(logic + 0xf0), word(logic + 0xf8)) { state.activeX = true }
        if activation(cy, word(actor + 0x50), word(logic + 0xf4), word(logic + 0xfc)) { state.activeY = true }
        let dx = cx &- state.cameraX, dy = cy &- state.cameraY
        if state.activeX && state.activeY && (-32...32).contains(signed(dx)) {
            let x = shifted(word(actor + 0x4c), word(actor + 0x148), dx)
            if bounded(x, word(logic + 0x2c), word(logic + 0x30)) { put(actor + 0x4c, x) }
            else { state.activeX = false }
        }
        if state.activeX && state.activeY && (-32...32).contains(signed(dy)) {
            let y = shifted(word(actor + 0x50), word(actor + 0x14c), dy)
            if bounded(y, word(logic + 0x34), word(logic + 0x38)) { put(actor + 0x50, y) }
            else { state.activeY = false }
        }
        state.cameraX = cx
        state.cameraY = cy
        states[actor] = state
        return resources.fault == 0 ? 1 : resources.fail(function)
    }
}
