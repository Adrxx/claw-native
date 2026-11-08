import Foundation

@main
struct NativeMenuInputCheck {
    static func main() throws {
        let queue = ClawNativeWindowInputQueue()
        let menu = ClawNativeWindowInput(queue: queue)
        let other = ClawNativeWindowInput(queue: queue)
        menu.menuKey(40, down: true)
        other.menuKey(65, down: true)
        menu.menuPointer(message: .primaryDown, x: 123, y: 234)
        menu.menuKey(40, down: true, repeatKey: true)
        menu.menuPointer(message: .primaryUp, x: 123, y: 234)
        let first = try queue.next(window: menu.window)
        precondition(first?.message == .keyDown && first?.wParam == 40 && first?.lParam == 1)
        // A handler's selective drain must still see later messages, leaving
        // mouse messages and another window untouched, without releasing keys.
        try queue.drain(message: 0x100, maximum: 64) { menu.window }
        precondition(menu.virtualKeys.contains(40))
        let down = try queue.next(window: menu.window)
        let up = try queue.next(window: menu.window)
        precondition(down?.message == .primaryDown && down?.wParam == 1)
        precondition(down?.lParam == (123 | (234 << 16)))
        precondition(up?.message == .primaryUp && up?.wParam == 0)
        let exhausted = try queue.next(window: menu.window)
        precondition(exhausted == nil)
        precondition(queue.pending.count == 1 && queue.pending[0].window == other.window)
        menu.menuPointer(message: .mouseMove, x: -7, y: -11)
        precondition(menu.cursorPosition.x == UInt32(bitPattern: -7))
        let move = try queue.next(window: menu.window)
        precondition(move?.lParam == (UInt32(UInt16(bitPattern: -7)) | UInt32(UInt16(bitPattern: -11)) << 16))
        menu.menuKey(38, down: true)
        menu.menuPointer(message: .primaryDown, x: 12, y: 34)
        menu.releaseMenuKeys()
        precondition(menu.virtualKeys.isEmpty && other.virtualKeys == [65])
        precondition(queue.pending.filter { $0.window == menu.window && $0.message == .keyUp }.count == 2)
        precondition(queue.pending.last?.message == .primaryUp)
        // Older queue evidence remains readable and byte-field compatible.
        let old = Data(#"{"window":1,"message":256,"mask":4,"pressed":true}"#.utf8)
        let event = try JSONDecoder().decode(ClawNativeWindowInputQueue.Event.self, from: old)
        precondition(event.wParam == 0 && event.lParam == 0)
        let encoded = try JSONSerialization.jsonObject(with: JSONEncoder().encode(event)) as! NSDictionary
        let oldObject = try JSONSerialization.jsonObject(with: old) as! NSDictionary
        precondition(encoded == oldObject)
        print("PASS menu message payloads, in-handler drains, window isolation, focus release and legacy evidence")
    }
}
