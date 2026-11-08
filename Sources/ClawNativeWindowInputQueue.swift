import Foundation
import GameController

// One native joystick port. The game still owns dead zones, masks, remapping
// and edge latches; this adapter supplies only WinMM's physical data layout.
struct ClawNativeJoystickSample: Equatable, Codable {
    var x: UInt32 = 32767
    var y: UInt32 = 32767
    var buttons: UInt32 = 0
    var buttonCount: UInt32 = 9

    static func axis(_ value: Float) -> UInt32 {
        UInt32((Double(max(-1, min(1, value))) + 1) * 32767.5)
    }
    static func connected() -> Self? {
        // Prefer a full pad, but keep remotes and older standard profiles usable.
        let devices = GCController.controllers()
        if let pad = devices.compactMap({ $0.extendedGamepad }).first { return sample(pad) }
        if let pad = devices.compactMap({ $0.microGamepad }).first {
            return Self(x:axis(pad.dpad.xAxis.value), y:axis(-pad.dpad.yAxis.value),
                        buttons:(pad.buttonA.isPressed ? 1:0) | (pad.buttonX.isPressed ? 2:0) |
                            (pad.buttonMenu.isPressed ? 256:0), buttonCount:9)
        }
        if let device = devices.first(where: { $0.gamepad != nil }), let pad = device.gamepad {
            let inputs = [pad.buttonA,pad.buttonB,pad.buttonX,pad.buttonY,pad.leftShoulder,pad.rightShoulder]
            var buttons:UInt32 = device.physicalInputProfile.buttons[GCInputButtonMenu]?.isPressed == true ? 256:0
            for (index,button) in inputs.enumerated() where button.isPressed {buttons |= 1 << index}
            return Self(x:axis(pad.dpad.xAxis.value),y:axis(-pad.dpad.yAxis.value),buttons:buttons)
        }
        return nil
    }
    static func sample(_ pad: GCExtendedGamepad) -> Self {
        let dpad = pad.dpad
        let x = dpad.xAxis.value != 0 ? dpad.xAxis.value : pad.leftThumbstick.xAxis.value
        let y = dpad.yAxis.value != 0 ? dpad.yAxis.value : pad.leftThumbstick.yAxis.value
        let inputs = [pad.buttonA, pad.buttonB, pad.buttonX, pad.buttonY,
                      pad.leftShoulder, pad.rightShoulder, pad.leftTrigger, pad.rightTrigger, pad.buttonMenu]
        var buttons: UInt32 = 0
        for (index, button) in inputs.enumerated() where button.isPressed {
            buttons |= 1 << index
        }
        return Self(x: axis(x), y: axis(-y), buttons: buttons)
    }
    var capabilities: [UInt32] {
        var words = [UInt32](repeating: 0, count: 101)
        words[10] = 65535
        words[12] = 65535 // X/Y min 0, max 65535.
        words[15] = buttonCount
        return words
    }
    func position(size: UInt32, flags: UInt32) -> [UInt32] {
        [size, flags, x, y, 0, 0, 0, 0, buttons, 0, 0, 0, 0]
    }
}

// Menu navigation uses the same window key messages as a keyboard. Taps avoid
// releasing a real keyboard key when a pad direction is released or unplugged.
struct ClawControllerNavigation {
    private var previous:ClawNativeJoystickSample?
    private var held:Set<UInt32> = []
    private var repeatAt:Double = 0
    mutating func keys(sample:ClawNativeJoystickSample?, playing:Bool, now:Double) -> [UInt32] {
        defer {previous = sample}
        guard let sample else {
            held = [];repeatAt = 0
            return previous != nil && playing ? [27]:[]
        }
        var current:Set<UInt32> = []
        if sample.buttons & 256 != 0 {current.insert(27)}
        do {
            // Track every held control across menu/play boundaries, even when
            // only Menu is eligible to emit a message during play.
            // Half travel for menu steps keeps analog jitter from moving focus.
            if sample.x < 16384 {current.insert(37)}
            if sample.x > 49151 {current.insert(39)}
            if sample.y < 16384 {current.insert(38)}
            if sample.y > 49151 {current.insert(40)}
            if sample.buttons & 1 != 0 {current.insert(13)}
            if sample.buttons & 2 != 0 {current.insert(27)}
        }
        let edges = current.subtracting(held)
        let directions = current.intersection([37,38,39,40])
        let repeating = edges.isEmpty && !directions.isEmpty && now >= repeatAt
        if !edges.isEmpty {repeatAt = now + 0.35}
        else if repeating {repeatAt = now + 0.12}
        held = current
        let result = repeating ? directions:edges
        if playing {
            return sample.buttons & 256 != 0 && (previous?.buttons ?? 0) & 256 == 0 ? [27]:[]
        }
        return result.sorted()
    }
}

// One native event queue can be shared by the menu and every scene belonging
// to a window. Capture and consumers run on the owning serial UI lane. Event
// payloads are data, never dispatch/translation callbacks.
final class ClawNativeWindowInputQueue {
    // MARK: - Event payload and stable message identities

    enum Failure: Error { case missingWindow, unsupportedMessage }
    enum Message: UInt32, Codable {
        case keyDown = 0x100, keyUp = 0x101
        case mouseMove = 0x200
        case primaryDown = 0x201, primaryUp = 0x202
    }
    struct Event: Equatable, Codable {
        let window: UInt32
        let message: Message
        let mask: UInt32
        let pressed: Bool
        var wParam: UInt32 = 0
        var lParam: UInt32 = 0
        /// Shift 4, Control 8 and Alt 0x10 held when the key went down (the
        /// accelerator flag bits TranslateAcceleratorA compares with GetKeyState).
        var modifiers: UInt32 = 0

        init(window: UInt32, message: Message, mask: UInt32, pressed: Bool,
             wParam: UInt32 = 0, lParam: UInt32 = 0, modifiers: UInt32 = 0) {
            self.window = window
            self.message = message
            self.mask = mask
            self.pressed = pressed
            self.wParam = wParam
            self.lParam = lParam
            self.modifiers = modifiers
        }
        private enum CodingKeys: String, CodingKey { case window, message, mask, pressed, wParam, lParam, modifiers }
        init(from decoder: Decoder) throws {
            let values = try decoder.container(keyedBy: CodingKeys.self)
            window = try values.decode(UInt32.self, forKey: .window)
            message = try values.decode(Message.self, forKey: .message)
            mask = try values.decode(UInt32.self, forKey: .mask)
            pressed = try values.decode(Bool.self, forKey: .pressed)
            wParam = try values.decodeIfPresent(UInt32.self, forKey: .wParam) ?? 0
            lParam = try values.decodeIfPresent(UInt32.self, forKey: .lParam) ?? 0
            modifiers = try values.decodeIfPresent(UInt32.self, forKey: .modifiers) ?? 0
        }
        func encode(to encoder: Encoder) throws {
            var values = encoder.container(keyedBy: CodingKeys.self)
            try values.encode(window, forKey: .window)
            try values.encode(message, forKey: .message)
            try values.encode(mask, forKey: .mask)
            try values.encode(pressed, forKey: .pressed)
            if wParam != 0 {
                try values.encode(wParam, forKey: .wParam)
            }
            if lParam != 0 {
                try values.encode(lParam, forKey: .lParam)
            }
            if modifiers != 0 {
                try values.encode(modifiers, forKey: .modifiers)
            }
        }
    }
    private var windows: Set<UInt32> = []
    private var nextWindow: UInt32 = 1
    private(set) var pending: [Event] = []
    private(set) var closeRequests: [UInt32] = []
    var yieldWindowEvents: (() -> Void)?
    var observePhysical: (([String: Any]) -> Void)?

    // MARK: - Snapshot persistence

    struct SavedState: Codable, Equatable {
        let windows: Set<UInt32>, nextWindow: UInt32
        let pending: [Event], closeRequests: [UInt32]
    }
    func savedState() -> SavedState {
        .init(windows: windows, nextWindow: nextWindow, pending: pending, closeRequests: closeRequests)
    }
    static func validate(_ value: SavedState) throws {
        guard value.nextWindow > 0, value.windows.allSatisfy({ $0 > 0 && $0 < value.nextWindow }),
              value.pending.allSatisfy({ value.windows.contains($0.window) }),
              value.closeRequests.allSatisfy(value.windows.contains)
        else {
            throw ClawSnapshotError.invalidState
        }
    }
    func restoreState(_ value: SavedState) throws {
        try Self.validate(value)
        windows = value.windows
        nextWindow = value.nextWindow
        pending = value.pending
        closeRequests = value.closeRequests
    }

    // MARK: - Window lifecycle

    func openWindow() -> UInt32 {
        precondition(nextWindow < UInt32.max)
        let identity = nextWindow
        nextWindow += 1
        windows.insert(identity)
        return identity
    }
    func closeWindow(_ identity: UInt32) {
        windows.remove(identity)
        pending.removeAll { $0.window == identity }
        closeRequests.removeAll { $0 == identity }
    }
    // Application shutdown posts asynchronously, like its original WM_CLOSE.
    // It must not discard input or destroy the window during the callback.
    func postClose(window: UInt32) throws {
        guard windows.contains(window) else {
            throw Failure.missingWindow
        }
        closeRequests.append(window)
    }
    func takeCloseRequest(window: UInt32) throws -> Bool {
        guard windows.contains(window) else {
            throw Failure.missingWindow
        }
        guard let index = closeRequests.firstIndex(of: window) else {
            return false
        }
        closeRequests.remove(at: index)
        return true
    }

    // MARK: - Capture, discard and delivery

    func capture(_ event: Event) throws {
        guard windows.contains(event.window) else {
            throw Failure.missingWindow
        }
        pending.append(event)
    }

    // Remove only the next event: a recovered handler can drain messages that
    // are still pending, just as it can inside the Windows dispatch loop.
    func next(window: UInt32) throws -> Event? {
        guard windows.contains(window) else {
            throw Failure.missingWindow
        }
        yieldWindowEvents?()
        let read = { () -> [UInt32] in
            guard let index = self.pending.firstIndex(where: { $0.window == window }) else { return [] }
            let e = self.pending.remove(at: index)
            return [e.window,e.message.rawValue,e.mask,e.pressed ? 1:0,e.wParam,e.lParam,e.modifiers]
        }
        let words = read()
        guard words.count == 7, let message = Message(rawValue: words[1]) else { return nil }
        return Event(window: words[0], message: message, mask: words[2], pressed: words[3] != 0,
                     wParam: words[4], lParam: words[5], modifiers: words[6])
    }

    // Native replacement for 0x4b8910: thiscall2, semantic void. The read
    // closure resolves receiver+4 anew for every query, including the empty one.
    // Window zero/thread-only selectors are deliberately unsupported. Message
    // zero selects every supported queued event for the specified live window.
    func drain(message: UInt32, maximum: UInt32, readWindow: () throws -> UInt32) throws {
        guard Int32(bitPattern: maximum) > 0 else {
            return
        }
        guard message == 0 || Message(rawValue: message) != nil else {
            throw Failure.unsupportedMessage
        }
        for _ in 0..<Int(maximum) {
            let window = try readWindow()
            guard windows.contains(window) else {
                throw Failure.missingWindow
            }
            yieldWindowEvents?()
            observePhysical?(["service": "PeekMessageA", "window": window, "minimum": message, "maximum": message, "remove": 1, "queued": pending.count])
            let remove = { () -> UInt32 in
                guard let index = self.pending.firstIndex(where: {
                    $0.window == window && (message == 0 || $0.message.rawValue == message)
                }) else { return 0 }
                self.pending.remove(at: index); return 1
            }
            if remove() == 0 { return }
        }
    }

    // Ordinary frame delivery is separate from discard. The queue is removed
    // before delivery so a consumer may call the compatibility route safely.
    func deliver(window: UInt32, consume: (Event) -> Void) throws {
        guard windows.contains(window) else {
            throw Failure.missingWindow
        }
        let events = pending.filter { $0.window == window }
        pending.removeAll { $0.window == window }
        for event in events {
            consume(event)
        }
    }
}

// Physical held state is independent of pending messages. Discarding a down
// event suppresses its later pressed delivery but never releases a held key.
final class ClawNativeWindowInput {
    // A diagnostic may replace the physical sampler; ordinary launches always
    // discover GameController devices. Sampling stays on the window's UI lane.
    var joystickSampler: () -> ClawNativeJoystickSample? = ClawNativeJoystickSample.connected
    private(set) var joystick: ClawNativeJoystickSample?
    func sampleJoystick() { joystick = joystickSampler() }

    func asyncKeyState(_ key: UInt32) -> UInt32 {
        if virtualKeys.contains(key) {
            return 0x8000
        }
        if let mouse = GCMouse.current?.mouseInput {
            if key == 1 && mouse.leftButton.isPressed {
                return 0x8000
            }
            if key == 2 && mouse.rightButton?.isPressed == true {
                return 0x8000
            }
        }
        return 0
    }
    private(set) var virtualKeys: Set<UInt32> = []
    var cursorPosition: (x: UInt32, y: UInt32) = (320, 240)
    private(set) var cursorDisplayCount: Int32 = 0
    func virtualKey(_ key: UInt32, down: Bool) {
        guard key < 256 else {
            return
        }
        if down {
            virtualKeys.insert(key)
        } else {
            virtualKeys.remove(key)
        }
    }

    // MARK: - Menu messages and physical state

    func menuKey(_ key: UInt32, down: Bool, repeatKey: Bool = false) {
        virtualKey(key, down: down)
        var modifiers: UInt32 = 0
        for (held, bit) in [(UInt32(0x10), UInt32(4)), (0x11, 8), (0x12, 0x10)] where virtualKeys.contains(held) {
            modifiers |= bit
        }
        try! queue.capture(.init(window: window, message: down ? .keyDown : .keyUp,
                                 mask: 0, pressed: down, wParam: key,
                                 lParam: down ? (repeatKey ? 0x40000001 : 1) : 0xc0000001, modifiers: modifiers))
    }
    func menuPointer(message: ClawNativeWindowInputQueue.Message, x: Int32, y: Int32) {
        precondition([.mouseMove, .primaryDown, .primaryUp].contains(message))
        cursorPosition = (UInt32(bitPattern: x), UInt32(bitPattern: y))
        if message == .primaryDown {
            virtualKey(1, down: true)
        }
        if message == .primaryUp {
            virtualKey(1, down: false)
        }
        // Win32 packs signed coordinates into two truncated 16-bit words.
        let point = UInt32(UInt16(truncatingIfNeeded: x)) | UInt32(UInt16(truncatingIfNeeded: y)) << 16
        try! queue.capture(.init(window: window, message: message, mask: 0,
                                 pressed: message == .primaryDown, wParam: virtualKeys.contains(1) ? 1 : 0, lParam: point))
    }
    func releaseMenuKeys() {
        for key in virtualKeys where key != 1 {
            menuKey(key, down: false)
        }
        if virtualKeys.contains(1) {
            menuPointer(message: .primaryUp, x: Int32(bitPattern: cursorPosition.x), y: Int32(bitPattern: cursorPosition.y))
        }
    }
    func showCursor(_ visible: Bool) -> UInt32 {
        cursorDisplayCount += visible ? 1 : -1
        return UInt32(bitPattern: cursorDisplayCount)
    }
    let queue: ClawNativeWindowInputQueue
    let window: UInt32
    private var keyboardHeld: UInt32 = 0, primaryHeld: UInt32 = 0

    // MARK: - Snapshot persistence and window ownership

    struct SavedState: Codable, Equatable {
        let window: UInt32
        let keyboardHeld: UInt32, primaryHeld: UInt32
        let virtualKeys: Set<UInt32>
        let cursorX: UInt32, cursorY: UInt32, cursorDisplayCount: Int32
        let joystick: ClawNativeJoystickSample?
    }
    func savedState() -> SavedState {
        .init(window: window, keyboardHeld: keyboardHeld, primaryHeld: primaryHeld, virtualKeys: virtualKeys,
              cursorX: cursorPosition.x, cursorY: cursorPosition.y, cursorDisplayCount: cursorDisplayCount, joystick: joystick)
    }
    // The queue is a separate, shared graph owner. Restore it once, then bind
    // every input to that queue. Do not sample a live controller during decode.
    init(restoring value: SavedState, queue: ClawNativeWindowInputQueue) throws {
        try ClawNativeWindowInputQueue.validate(queue.savedState())
        guard queue.savedState().windows.contains(value.window), value.virtualKeys.allSatisfy({ $0 < 256 })
        else {
            throw ClawSnapshotError.invalidState
        }
        self.queue = queue
        window = value.window
        keyboardHeld = value.keyboardHeld
        primaryHeld = value.primaryHeld
        virtualKeys = value.virtualKeys
        cursorPosition = (value.cursorX, value.cursorY)
        cursorDisplayCount = value.cursorDisplayCount
        joystick = value.joystick
    }
    var held: UInt32 { keyboardHeld | primaryHeld }
    func primaryIsHeld(_ mask: UInt32) -> Bool { primaryHeld & mask != 0 }

    init(queue: ClawNativeWindowInputQueue = ClawNativeWindowInputQueue()) {
        self.queue = queue
        window = queue.openWindow()
    }
    deinit { queue.closeWindow(window) }

    // MARK: - Gameplay input edges

    func key(mask: UInt32, down: Bool) {
        capture(mask: mask, down: down, primary: false)
    }
    func primary(mask: UInt32 = 0, down: Bool) {
        capture(mask: mask, down: down, primary: true)
    }
    private func capture(mask: UInt32, down: Bool, primary: Bool) {
        let wasHeld = held & mask != 0
        if primary {
            primaryHeld = down ? primaryHeld | mask : primaryHeld & ~mask
        } else {
            keyboardHeld = down ? keyboardHeld | mask : keyboardHeld & ~mask
        }
        let message: ClawNativeWindowInputQueue.Message = primary
            ? (down ? .primaryDown : .primaryUp) : (down ? .keyDown : .keyUp)
        // This endpoint owns the live window for its entire lifetime.
        try! queue.capture(.init(window: window, message: message, mask: mask, pressed: down && !wasHeld))
    }
    func frameInput() -> (held: UInt32, pressed: UInt32) {
        var pressed: UInt32 = 0
        try! queue.deliver(window: window) {
            if $0.pressed {
                pressed |= $0.mask
            }
        }
        return (held, pressed)
    }
}
