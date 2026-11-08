import Foundation

// Mutable recovered CRT/bootstrap registry with a bounded native arena.
// Platform startup, metadata ownership and physical allocator policy are adapters.
final class ClawNativeStateRegistry {
    let registry = UnsafeMutablePointer<ClawLogicStateRegistry>.allocate(capacity: 1)
    let context = UnsafeMutablePointer<ClawLogicStateContext>.allocate(capacity: 1)
    private let arena = UnsafeMutablePointer<UInt8>.allocate(capacity: 1 << 20)
    static let classTables: [String: UInt32] = ["CEnemy": 0x537638, "Human": 0x537878,
        "Officer": 0x537ba0, "Rat": 0x53c0e8, "RatBomb": 0x53c118, "Projectile": 0x538428,
        "PowderKeg":0x537ea0,"Crate":0x537308]
    init(afterInitialize: ((UnsafeMutablePointer<ClawLogicStateRegistry>) -> Bool)? = nil) throws {
        registry.initialize(to: ClawLogicStateRegistry()); context.initialize(to: ClawLogicStateContext())
        arena.initialize(repeating: 0, count: 1 << 20)
        context.pointee.heap = arena; context.pointee.heapBase = 0x65000000; context.pointee.heapCapacity = 1 << 20
        claw_logic_state_context_defaults(registry, context)
        guard claw_logic_state_initialize(registry, context, nil, nil) == 1,
            afterInitialize?(registry) ?? true,
            claw_logic_state_bootstrap(registry, context, nil, nil) == 1, context.pointee.fault == 0 else {
            throw AssetError.invalid("Original state registry bootstrap fault \(context.pointee.fault)")
        }
    }
    deinit {
        arena.deinitialize(count: 1 << 20); arena.deallocate()
        registry.deinitialize(count: 1); registry.deallocate(); context.deinitialize(count: 1); context.deallocate()
    }
    func resolve(_ state: Int32, table: UInt32 = 0) -> ClawLogicStateView {
        var view = ClawLogicStateView()
        precondition(claw_logic_state_resolve(registry, context, table, state, &view, nil, nil) == 1 && context.pointee.fault == 0)
        return view
    }
    func rawTable(_ token:UInt32) -> [UInt32]? {
        for index in 0..<claw_logic_state_table_count(registry) {
            guard let table = claw_logic_state_table_at(registry,index),table.pointee.token == token else { continue }
            return withUnsafeBytes(of:table.pointee.words){Array($0.bindMemory(to:UInt32.self).prefix(10))}
        }
        return nil
    }
    func rawMemory(_ token:UInt32,words:UInt32) -> UnsafeMutablePointer<UInt32>? {
        let base = context.pointee.heapBase,end = UInt64(token)+UInt64(words)*4
        guard token & 3 == 0,token >= base,end <= UInt64(base)+UInt64(context.pointee.heapUsed) else { return nil }
        return UnsafeMutableRawPointer(arena.advanced(by:Int(token-base))).assumingMemoryBound(to:UInt32.self)
    }

    struct SavedState: Codable, Equatable {
        let registry: ClawSnapshotValue<ClawLogicStateRegistry>
        let context: [String: Data]
        let arena: Data
    }
    private static let snapshotFields = ClawSnapshotFields<ClawLogicStateContext>(fields: [
        .init("heapBase", \.heapBase), .init("heapCapacity", \.heapCapacity), .init("heapUsed", \.heapUsed),
        .init("emptyStringToken", \.emptyStringToken), .init("metadataReceiverToken", \.metadataReceiverToken),
        .init("metadataFunctionToken", \.metadataFunctionToken), .init("errorLocation", \.errorLocation), .init("fault", \.fault)
    ])
    func savedState() -> SavedState {
        SavedState(registry: ClawSnapshotValue(registry.pointee), context: Self.snapshotFields.capture(context.pointee),
            arena: Data(bytes: arena, count: Int(context.pointee.heapUsed)))
    }
    // Restore the registry before constructing any actor's state views. CString
    // pointers in those views must point into this arena, never the old scene.
    func restoreState(_ value: SavedState) throws {
        let restored = try Self.snapshotFields.restoring(value.context, into: context.pointee)
        guard restored.heapBase == 0x65000000, restored.heapCapacity == 1 << 20,
              restored.heapUsed <= restored.heapCapacity, value.arena.count == Int(restored.heapUsed),
              value.registry.value.tableCount <= 96, value.registry.value.literalCount <= 256,
              value.registry.value.nextId >= 2000, value.registry.value.nextId <= 100000
        else { throw ClawSnapshotError.invalidState }
        registry.pointee = value.registry.value; context.pointee = restored
        arena.update(repeating: 0, count: 1 << 20)
        value.arena.withUnsafeBytes { bytes in
            if let base = bytes.baseAddress { UnsafeMutableRawPointer(arena).copyMemory(from: base, byteCount: bytes.count) }
        }
    }
}
final class ClawEnemyStateView {
    let entries: UnsafeMutablePointer<ClawGenericEnemyState>
    let count: Int
    private let registry: ClawNativeStateRegistry
    private(set) var ids: [String: UInt32] = [:]
    init(registry: ClawNativeStateRegistry, inheritance: [String]) {
        self.registry = registry
        let states = [Int32(1000)] + Array(Int32(2000)..<Int32(registry.registry.pointee.nextId))
        // Grow each original dynamic array to its final bounds once. The native
        // arena retains replaced blocks; growing one slot per lookup wastes it.
        let upperBound = states.last!
        _ = registry.resolve(upperBound)
        _ = registry.resolve(states[0])
        for table in inheritance {
            let token = ClawNativeStateRegistry.classTables[table]!
            _ = registry.resolve(upperBound, table: token)
            _ = registry.resolve(states[0], table: token)
        }
        count = states.count; entries = .allocate(capacity: count)
        entries.initialize(repeating: ClawGenericEnemyState(), count: count)
        for (index, state) in states.enumerated() {
            let name = registry.resolve(state)
            var function: UInt32 = 0
            for table in inheritance.reversed() {
                let resolved = registry.resolve(state, table: ClawNativeStateRegistry.classTables[table]!)
                if resolved.function != 0 { function = resolved.function; break }
            }
            entries[index] = ClawGenericEnemyState(state: state, function: function, nameToken: name.nameToken, name: name.name)
            ids[String(cString: name.name!)] = UInt32(bitPattern: state)
        }
    }
    deinit { entries.deinitialize(count: count); entries.deallocate() }

    struct SavedState: Codable, Equatable {
        struct Entry: Codable, Equatable { let state: Int32; let function: UInt32; let nameToken: UInt32; let name: String }
        let entries: [Entry]
        let ids: [String: UInt32]
    }
    func savedState() -> SavedState {
        SavedState(entries: (0..<count).map { i in
            let value = entries[i]
            return .init(state: value.state, function: value.function, nameToken: value.nameToken,
                name: value.name.map { String(cString: $0) } ?? "")
        }, ids: ids)
    }
    func restoreState(_ value: SavedState) throws {
        guard value.entries.count == count, Set(value.entries.map(\.state)).count == count else { throw ClawSnapshotError.invalidState }
        var restored: [ClawGenericEnemyState] = []
        for entry in value.entries {
            let name = registry.resolve(entry.state)
            guard name.nameToken == entry.nameToken, let pointer = name.name, String(cString: pointer) == entry.name
            else { throw ClawSnapshotError.invalidState }
            restored.append(ClawGenericEnemyState(state: entry.state, function: entry.function, nameToken: entry.nameToken, name: pointer))
        }
        restored.withUnsafeBufferPointer { entries.update(from: $0.baseAddress!, count: count) }
        ids = value.ids
    }
}

extension ClawLogicStateRegistry: ClawSnapshotNativeValue {}
