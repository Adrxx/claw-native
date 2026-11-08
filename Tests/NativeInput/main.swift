import Foundation

struct Event: Codable, Equatable {
    let function: UInt32
    let arguments: [UInt32]
    let stackPointer: UInt32
}
struct Reference: Decodable {
    let function: UInt32
    let before: String
    let after: String
    let events: [Event]
    let rawEAX: UInt32
}
func unhex(_ text: String) -> Data {
    let values = Array(text.utf8)
    precondition(values.count % 2 == 0)
    return Data(stride(from: 0, to: values.count, by: 2).map {
        UInt8(String(decoding: values[$0..<$0+2], as: UTF8.self), radix: 16)!
    })
}
guard CommandLine.arguments.count == 2 else { fatalError("Usage: native-input reference.json") }
let rows = try JSONDecoder().decode([Reference].self,
    from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
for row in rows {
    let heap = ClawTokenHeap(), before = unhex(row.before)
    let token = heap.allocate(bytes: UInt32(before.count))
    before.copyBytes(to: heap.lookupBytes(token, count: UInt32(before.count))!, count: before.count)
    var events: [Event] = []
    let owner = ClawNativeCanonicalHost(heap: heap) { owner, call in
        precondition(call.receiver == 0 && call.receiver2 == 0 && call.x87ArgumentCount == 0)
        let args = withUnsafeBytes(of: call.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(call.argumentCount))) }
        events.append(Event(function: call.function, arguments: args, stackPointer: call.stackPointer))
        switch call.function {
        case 0x546cd0:
            precondition(args.count == 1)
            guard let point = owner.bytes(args[0], count: 8) else { return nil }
            var words: [UInt32] = [300, 400]
            words.withUnsafeMutableBytes { UnsafeMutableRawPointer(point).copyMemory(from: $0.baseAddress!, byteCount: 8) }
            return 1
        case 0x546ce4:
            precondition(args.count == 1)
            return 0
        case 0x546d9c:
            precondition(args.count == 2)
            return 1
        default: return nil
        }
    }
    var call = ClawCall(); call.function = row.function; call.receiver = token
    let result = owner.invoke(call)
    precondition(result.completed && result.eax == 0 && result.fault == nil)
    precondition(Data(bytes: heap.lookupBytes(token, count: UInt32(before.count))!, count: before.count) == unhex(row.after))
    precondition(events == row.events)
}
print("{\"status\":\"pass\",\"cases\":4,\"scope\":\"Native input buffer/default initializers and mouse polling match fresh original bytes and exact import entry stacks; physical API fixtures only. No keyboard/controller UI or game-flow claim.\"}")
