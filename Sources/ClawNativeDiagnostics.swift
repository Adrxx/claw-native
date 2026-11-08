import Foundation
#if os(macOS)
import AppKit
#elseif canImport(UIKit)
import UIKit
import AudioToolbox
#endif

// One native owner for the two recovered policies. Original text stays in the
// locally prepared asset; flags retain their independent original identities.
final class ClawNativeDiagnostics {
    struct Effect: Codable, Equatable {
        let kind: String
        let arguments: [UInt32]
        let text: String
        let caption: String
    }
    struct Effects {
        var beep: ((UInt32) -> Bool)?
        var log: ((String) -> Bool)?
        var dialog: ((String, String, UInt32, UInt32) -> Bool)?
        static var native: Effects {
            Effects(beep: { kind in
                guard kind == 0x30 else { return false }
                #if os(macOS)
                onMain { NSSound.beep() }
                #elseif canImport(UIKit)
                AudioServicesPlayAlertSound(1007)
                #else
                return false
                #endif
                return true
            }, log: { text in
                NSLog("%@", text)
                return true
            }, dialog: { text, caption, parent, flags in
                guard parent == 0, flags == 0x30 else { return false }
                return onMain {
                    #if os(macOS)
                    let alert = NSAlert()
                    alert.messageText = caption
                    alert.informativeText = text
                    alert.alertStyle = .warning
                    alert.addButton(withTitle: "OK")
                    // Synchronous acknowledgement preserves the original callback order.
                    _ = alert.runModal()
                    return true
                    #elseif canImport(UIKit)
                    guard let scene = UIApplication.shared.connectedScenes.first(where: { $0.activationState == .foregroundActive }) as? UIWindowScene,
                          var presenter = scene.windows.first(where: { $0.isKeyWindow })?.rootViewController else { return false }
                    while let presented = presenter.presentedViewController { presenter = presented }
                    let alert = UIAlertController(title: caption, message: text, preferredStyle: .alert)
                    alert.addAction(UIAlertAction(title: "OK", style: .default))
                    presenter.present(alert, animated: true)
                    return true
                    #else
                    return false
                    #endif
                }
            })
        }
    }
    static let shared = ClawNativeDiagnostics()
    var effects: Effects
    // Observer is for focused join evidence; production effects are still required.
    var observe: ((Effect) -> Void)?
    private(set) var fault: UInt32 = 0
    private(set) var faultAddress: UInt32 = 0
    private(set) var entries: [UInt32: UInt64] = [:]
    private let flags = UnsafeMutablePointer<UInt32>.allocate(capacity: 8)
    private var literals: [UInt32: (UnsafeMutablePointer<UInt8>, Int)] = [:]
    private var loaded = false
    private var activeHost: UnsafeMutablePointer<ClawHost>?
    private var stack: UnsafeMutablePointer<UInt8>?
    private var externalBytes: ((UInt32, UInt32) -> UnsafeMutablePointer<UInt8>?)?
    private var formatFrame: UInt32 = UInt32(CLAW_STACK_TOP)
    var assetURL: URL

    init(assetURL: URL? = nil, effects: Effects = .native) {
        self.assetURL = assetURL ?? (Bundle.main.resourceURL ?? URL(fileURLWithPath: "."))
            .appendingPathComponent("GameData/DiagnosticPolicy.json")
        self.effects = effects
        flags.initialize(repeating: 0, count: 8)
    }
    deinit {
        flags.deinitialize(count: 8); flags.deallocate()
        for (_, value) in literals { value.0.deallocate() }
    }
    func setFlags(display: Bool, _ words: [UInt32]) {
        precondition(words.count == 4)
        for index in 0..<4 { flags[(display ? 4 : 0) + index] = words[index] }
    }
    func flagWords(display: Bool) -> [UInt32] {
        (0..<4).map { flags[(display ? 4 : 0) + $0] }
    }
    // The composed menu executes policy on its existing host and stack. Only
    // the physical formatter, beep and dialog borrow this owner synchronously.
    func sharedMetadata() throws -> [UInt32:Data] {
        let values = try JSONDecoder().decode([String:[UInt8]].self,from:Data(contentsOf:assetURL))
        var metadata:[UInt32:Data] = [:]
        guard !values.isEmpty else {throw NSError(domain:"ClawDiagnosticMetadata",code:1)}
        for (key,value) in values {
            guard let address = UInt32(key,radix:16),!value.isEmpty else {throw NSError(domain:"ClawDiagnosticMetadata",code:2)}
            metadata[address] = Data(value)
        }
        return metadata
    }
    func sharedService(_ q:ClawCall,frame:UInt32,
                       bytes:@escaping (UInt32,UInt32)->UnsafeMutablePointer<UInt8>?)->UInt32? {
        guard [UInt32(0x4a3920),0x546ca4,0x546a08,0x4bc110,0x546d48].contains(q.function) else {return nil}
        guard activeHost == nil,externalBytes == nil,fault == 0 else {return fail(q.function)}
        externalBytes = bytes;formatFrame = frame
        defer {externalBytes = nil;formatFrame = UInt32(CLAW_STACK_TOP)}
        return call(q)
    }
    private func loadLiterals() -> Bool {
        if loaded { return true }
        guard let data = try? Data(contentsOf: assetURL),
              let values = try? JSONDecoder().decode([String: [UInt8]].self, from: data) else { return false }
        for (key, bytes) in values {
            guard let address = UInt32(key, radix: 16), !bytes.isEmpty else { return false }
            let pointer = UnsafeMutablePointer<UInt8>.allocate(capacity: bytes.count)
            bytes.withUnsafeBufferPointer { pointer.initialize(from: $0.baseAddress!, count: bytes.count) }
            literals[address] = (pointer, bytes.count)
        }
        loaded = true
        return true
    }
    private func fail(_ address: UInt32, code: UInt32 = UInt32(CLAW_FAULT_HOST)) -> UInt32 {
        if fault == 0 { fault = code; faultAddress = address }
        if let host = activeHost, host.pointee.fault == 0 {
            host.pointee.fault = fault; host.pointee.faultAddress = faultAddress
        }
        return 0
    }
    fileprivate func bytes(_ token: UInt32, _ count: UInt32) -> UnsafeMutablePointer<UInt8>? {
        let end = UInt64(token) + UInt64(count)
        for (base, index) in [(UInt32(0x54130c), 0), (UInt32(0x54139c), 4)] {
            if token >= base, end <= UInt64(base) + 16 {
                return UnsafeMutableRawPointer(flags.advanced(by: index)).assumingMemoryBound(to: UInt8.self).advanced(by: Int(token-base))
            }
        }
        if token >= UInt32(CLAW_STACK_BASE), end <= UInt64(CLAW_STACK_END), let stack {
            return stack.advanced(by: Int(token-UInt32(CLAW_STACK_BASE)))
        }
        if let external = externalBytes?(token, count) { return external }
        if !loaded, !loadLiterals() { return nil }
        for (base, value) in literals where token >= base && end <= UInt64(base)+UInt64(value.1) {
            return value.0.advanced(by: Int(token-base))
        }
        return nil
    }
    private func string(_ token: UInt32) -> String? {
        var value: [UInt8] = []
        for offset: UInt32 in 0..<4096 {
            guard token <= UInt32.max-offset, let byte = bytes(token+offset, 1)?.pointee else { return nil }
            if byte == 0 { return String(bytes: value, encoding: .windowsCP1252) }
            value.append(byte)
        }
        return nil
    }
    @discardableResult func report(display: Bool, filename: UInt32, line: UInt32, result: UInt32,
                                  bytes: ((UInt32, UInt32) -> UnsafeMutablePointer<UInt8>?)? = nil) -> Bool {
        let function: UInt32 = display ? 0x4bd260 : 0x4b4ed0
        guard activeHost == nil, fault == 0 else { _ = fail(function); return false }
        entries[function, default: 0] &+= 1
        let storage = UnsafeMutablePointer<UInt8>.allocate(capacity: Int(CLAW_STACK_END-CLAW_STACK_BASE))
        storage.initialize(repeating: 0, count: Int(CLAW_STACK_END-CLAW_STACK_BASE))
        stack = storage; externalBytes = bytes
        defer { stack = nil; externalBytes = nil; storage.deallocate() }
        let args = [filename, line, result]
        for (index, word) in args.enumerated() {
            UnsafeMutableRawPointer(storage.advanced(by: Int(CLAW_STACK_TOP-CLAW_STACK_BASE)+4+index*4)).storeBytes(of: word, as: UInt32.self)
        }
        var host = ClawHost()
        host.user = Unmanaged.passUnretained(self).toOpaque()
        host.bytes = diagnosticBytes
        host.call = diagnosticCall
        var output: UInt32 = 0
        let accepted = withUnsafeMutablePointer(to: &host) { pointer in
            activeHost = pointer
            defer { activeHost = nil }
            return args.withUnsafeBufferPointer {
                claw_menu_diagnostic_policy_entry(function, 0, $0.baseAddress, 3, pointer, &output)
            }
        }
        if host.fault != 0 { fault = host.fault; faultAddress = host.faultAddress }
        return accepted == 1 && fault == 0
    }
    fileprivate func call(_ call: ClawCall) -> UInt32 {
        guard call.receiver == 0, call.argumentCount <= 7 else { return fail(call.function) }
        let args = withUnsafeBytes(of: call.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(call.argumentCount))) }
        switch call.function {
        case 0x4a3920:
            guard [2,5,7].contains(args.count), let format = string(args[1]) else { return fail(call.function) }
            var output = "", index = 2, iterator = format.makeIterator()
            while let character = iterator.next() {
                if character != "%" { output.append(character); continue }
                guard let conversion = iterator.next() else { return fail(call.function) }
                if conversion == "%" { output.append("%"); continue }
                guard index < args.count else { return fail(call.function) }
                switch conversion {
                case "s": guard let text = string(args[index]) else { return fail(args[index]) }; output += text
                case "i", "d": output += String(Int32(bitPattern: args[index]))
                default: return fail(call.function)
                }
                index += 1
            }
            let capacity: Int
            if args[0] == formatFrame-0x340 {capacity = 64}
            else if args[0] == formatFrame-0x200 {capacity = 512}
            else {return fail(args[0])}
            guard index == args.count, let encoded = output.data(using: .windowsCP1252), encoded.count < capacity,
                  // All three original local buffers: 64-byte name, 256-byte description, 512-byte output.
                  let destination = bytes(args[0], UInt32(encoded.count+1)),
                  args[0] >= formatFrame-0x340,
                  UInt64(args[0])+UInt64(encoded.count+1) <= UInt64(formatFrame) else { return fail(call.function) }
            encoded.copyBytes(to: destination, count: encoded.count); destination[encoded.count] = 0
            observe?(Effect(kind: "format", arguments: args, text: output, caption: ""))
            return UInt32(encoded.count)
        case 0x546ca4:
            guard args == [0x30], let beep = effects.beep, beep(args[0]) else { return fail(call.function) }
            observe?(Effect(kind: "beep", arguments: args, text: "", caption: "")); return 1
        case 0x546a08:
            guard args.count == 1, let text = string(args[0]), let log = effects.log, log(text) else { return fail(call.function) }
            observe?(Effect(kind: "log", arguments: args, text: text, caption: "")); return 0
        case 0x4bc110:
            guard args.count == 1 else { return fail(call.function) }
            // Original body is RET: no log, and no dereference of its argument.
            observe?(Effect(kind: "display-sink", arguments: args, text: "", caption: "")); return 0
        case 0x546d48:
            guard args.count == 4, args[0] == 0, args[3] == 0x30,
                  let text = string(args[1]), let caption = string(args[2]),
                  let dialog = effects.dialog, dialog(text, caption, args[0], args[3]) else { return fail(call.function) }
            observe?(Effect(kind: "dialog", arguments: args, text: text, caption: caption)); return 1
        default: return fail(call.function)
        }
    }
}
private func onMain<T>(_ body: () -> T) -> T {
    if Thread.isMainThread { return body() }
    return DispatchQueue.main.sync(execute: body)
}
private let diagnosticBytes: @convention(c) (UnsafeMutableRawPointer?, UInt32, UInt32) -> UnsafeMutablePointer<UInt8>? = { user, token, count in
    guard let user else { return nil }
    return Unmanaged<ClawNativeDiagnostics>.fromOpaque(user).takeUnretainedValue().bytes(token, count)
}
private let diagnosticCall: @convention(c) (UnsafeMutableRawPointer?, UnsafePointer<ClawCall>?) -> UInt32 = { user, call in
    guard let user, let call else { return 0 }
    return Unmanaged<ClawNativeDiagnostics>.fromOpaque(user).takeUnretainedValue().call(call.pointee)
}
