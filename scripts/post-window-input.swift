// Posts real window-server input events to one process (never the frontmost
// app): the same CGEvent path a physical keyboard or mouse takes into AppKit.
// Usage: post-window-input <pid> key <virtual-keycode> [option]
//        post-window-input <pid> press <virtual-keycode> down|up [option,shift,control]
//        post-window-input <pid> click
//        post-window-input <pid> serve  (JSON command arrays on stdin; EOF exits)
// Prints one JSON line with the system uptime at which the event was posted.
import AppKit
import CoreGraphics
import Foundation

let arguments = CommandLine.arguments
guard arguments.count >= 3, let pid = pid_t(arguments[1]) else {
    print(#"{"status": "fail", "error": "usage"}"#); exit(2)
}
func window(of pid: pid_t) -> (id: Int, bounds: CGRect)? {
    let list = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
    // The process's largest on-screen normal window (the game window).
    var best: (id: Int, bounds: CGRect)?
    for info in list where (info[kCGWindowOwnerPID as String] as? Int).map(pid_t.init) == pid
        && (info[kCGWindowLayer as String] as? Int) == 0 {
        guard let id = info[kCGWindowNumber as String] as? Int,
              let raw = info[kCGWindowBounds as String] as? NSDictionary,
              let bounds = CGRect(dictionaryRepresentation: raw), bounds.height > 100 else { continue }
        if best == nil || bounds.width * bounds.height > best!.bounds.width * best!.bounds.height { best = (id, bounds) }
    }
    return best
}
let source = CGEventSource(stateID: .hidSystemState)
func handle(_ arguments: [String], streaming: Bool = false) {
    var posted: [Double] = []
    func post(_ event: CGEvent?) {
        guard let event else { print(#"{"status": "fail", "error": "event"}"#); exit(1) }
        posted.append(ProcessInfo.processInfo.systemUptime)
        event.postToPid(pid)
    }
    switch arguments[2] {
    case "window": break // Read-only window ID for capturing this instance, including its video layer.
    case "key":
        guard arguments.count >= 4, let code = CGKeyCode(arguments[3]) else { exit(2) }
        let option = arguments.count >= 5 && arguments[4] == "option"
        for down in [true, false] {
            let event = CGEvent(keyboardEventSource: source, virtualKey: code, keyDown: down)
            if option { event?.flags = .maskAlternate }
            post(event); usleep(60_000)
        }
    case "press":
        // One key transition, as a keyboard sends it: a modifier key (Shift 56/60,
        // Control 59/62, Option 58/61) changes the flags (NSEventTypeFlagsChanged);
        // any other key is a key down or up carrying the held modifiers' flags.
        guard arguments.count >= 5, let code = CGKeyCode(arguments[3]), ["down", "up"].contains(arguments[4]) else { exit(2) }
        let down = arguments[4] == "down"
        let names: [String: CGEventFlags] = ["option": .maskAlternate, "shift": .maskShift, "control": .maskControl, "command": .maskCommand]
        var flags: CGEventFlags = []
        for name in (arguments.count >= 6 ? arguments[5].split(separator: ",").map(String.init) : []) {
            guard let flag = names[name] else { exit(2) }
            flags.insert(flag)
        }
        let modifiers: [CGKeyCode: CGEventFlags] = [56: .maskShift, 60: .maskShift, 59: .maskControl, 62: .maskControl,
                                                    58: .maskAlternate, 61: .maskAlternate]
        guard let event = CGEvent(keyboardEventSource: source, virtualKey: code, keyDown: down) else { exit(1) }
        // The event's own flags (device bits, and the arrow keys' numeric-pad and
        // function bits) stay, as a physical keyboard sends them.
        flags.formUnion(event.flags)
        if let modifier = modifiers[code] {
            event.type = .flagsChanged
            if down { flags.insert(modifier) } else { flags.remove([modifier, CGEventFlags(rawValue: 0xffff)]) }
        }
        event.flags = flags
        // Posting is asynchronous: exiting at once can lose the event.
        post(event)
        // Streaming callers acknowledge delivery before issuing another command.
        // Keep the process alive instead of sleeping before every process exit.
        if !streaming { usleep(60_000) }
    case "click":
        guard let (id, bounds) = window(of: pid) else { print(#"{"status": "fail", "error": "no window"}"#); exit(1) }
        let point = CGPoint(x: bounds.midX, y: bounds.midY)
        for type in [CGEventType.leftMouseDown, .leftMouseUp] {
            let event = CGEvent(mouseEventSource: source, mouseType: type, mouseCursorPosition: point, mouseButton: .left)
            event?.setIntegerValueField(.mouseEventWindowUnderMousePointer, value: Int64(id))
            event?.setIntegerValueField(.mouseEventWindowUnderMousePointerThatCanHandleThisEvent, value: Int64(id))
            event?.setIntegerValueField(.mouseEventClickState, value: 1)
            post(event); usleep(60_000)
        }
    default: exit(2)
    }
    let target = ["click", "window"].contains(arguments[2]) ? window(of: pid) : nil
    let detail = target.map { #", "window": \#($0.id), "bounds": [\#($0.bounds.minX), \#($0.bounds.minY), \#($0.bounds.width), \#($0.bounds.height)]"# } ?? ""
    let front = NSWorkspace.shared.frontmostApplication?.processIdentifier == pid
    print(#"{"status": "posted", "pid": \#(pid), "uptime": \#(posted.first ?? ProcessInfo.processInfo.systemUptime), "frontmost": \#(front)\#(detail)}"#)

    fflush(stdout)
}
if arguments[2] == "serve" {
    while let line = readLine() {
        guard let data = line.data(using: .utf8),
              let command = try? JSONDecoder().decode([String].self, from: data),
              command.first == "press" else { exit(2) }
        handle(Array(arguments.prefix(2)) + command, streaming: true)
    }
} else {
    handle(arguments)
}
