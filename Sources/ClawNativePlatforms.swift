import Foundation

// Original Level1 profile and Elevator-family callbacks over the live scene.
// Rider election remains the source collision/player frame, not a host signal.
final class ClawNativePlatforms {
    static let callbacks: Set<UInt32> = [0x49e2a0,0x49daf0,0x49db10,0x49db30,0x49db50,0x49db70]
    weak var scene: ClawNativeScene?
    let globals = UnsafeMutablePointer<ClawElevatorGlobals>.allocate(capacity: 1)
    let profile = UnsafeMutablePointer<ClawElevatorLevelProfile>.allocate(capacity: 1)
    private(set) var tokens: Set<UInt32> = []
    private(set) var fault: UInt32 = 0
    private(set) var unresolved: Set<UInt32> = []
    private(set) var callbackCount: UInt64 = 0
    init(scene: ClawNativeScene) {
        self.scene = scene
        globals.initialize(to: ClawElevatorGlobals()); profile.initialize(to: ClawElevatorLevelProfile())
        guard claw_elevator_initialize_profile(1, profile, nil, nil) == 1 else { fault = 1; return }
        // One source48-word configuration span and adjacent pointer/level
        // aliases. The raw537964 word is preserved without inferring a label.
        let raw = scene.heap.store(token: 0x5378a0, words: 50)
        withUnsafeBytes(of: &profile.pointee.words) { UnsafeMutableRawPointer(raw).copyMemory(from: $0.baseAddress!, byteCount: 192) }
        raw[48] = profile.pointee.selectedToken; raw[49] = profile.pointee.levelWord
        let scales = scene.heap.store(token: 0x5262b0, words: 3)
        withUnsafeBytes(of: &profile.pointee.scaleWords) { UnsafeMutableRawPointer(scales).copyMemory(from: $0.baseAddress!, byteCount: 12) }
        globals.pointee.defaultsToken = profile.pointee.selectedToken; globals.pointee.playerToken = 0x10002000
    }
    deinit { globals.deinitialize(count: 1); globals.deallocate(); profile.deinitialize(count: 1); profile.deallocate() }
    func attach(_ token: UInt32) { tokens.insert(token) }
    func remove(_ token: UInt32) { tokens.remove(token) }
    @discardableResult func callback(_ function: UInt32, actor: UInt32) -> UInt32 {
        guard let scene else { fault = 1; return 0 }
        globals.pointee.managerToken = scene.heap.lookup(scene.ownerIdentity, words: 2)![1]
        globals.pointee.tick = scene.gameTime; globals.pointee.animationDelta = scene.animationDelta
        var context = ClawElevatorContext(scene: scene.actorHost, globals: globals, fault: 0)
        var argument = actor, result: UInt32 = 0
        let supported = withUnsafePointer(to: &argument) {
            claw_elevator_entry(function, 0, $0, 1, &context, nativePlatformDependency,
                Unmanaged.passUnretained(self).toOpaque(), &result)
        }
        callbackCount &+= 1; fault = max(fault, context.fault)
        if supported != 1 { unresolved.insert(function) }; return result
    }
    fileprivate func dependency(_ event: ClawElevatorCall) -> UInt32 {
        guard let scene else { fault = 1; return 0 }
        if event.function == 0x4f6286, let name = event.name {
            do { return try scene.objectResources?.images(name: String(cString: name))?.token ?? 0 }
            catch { fault = 1; return 0 }
        }
        unresolved.insert(event.function); fault = 1; return 0
    }
}
private let nativePlatformDependency: ClawElevatorDependency = { _, event, user in
    guard let event, let user else { return 0 }
    return Unmanaged<ClawNativePlatforms>.fromOpaque(user).takeUnretainedValue().dependency(event.pointee)
}

extension ClawNativePlatforms {
    struct SavedState: Codable, Equatable {
        let globals: ClawSnapshotValue<ClawElevatorGlobals>, profile: ClawSnapshotValue<ClawElevatorLevelProfile>
        let tokens: Set<UInt32>, fault: UInt32, unresolved: Set<UInt32>, callbackCount: UInt64
    }
    func savedState() -> SavedState {
        .init(globals: ClawSnapshotValue(globals.pointee), profile: ClawSnapshotValue(profile.pointee),
            tokens: tokens, fault: fault, unresolved: unresolved, callbackCount: callbackCount)
    }
    func restoreState(_ saved: SavedState) {
        globals.pointee = saved.globals.value; profile.pointee = saved.profile.value
        tokens = saved.tokens; fault = saved.fault; unresolved = saved.unresolved; callbackCount = saved.callbackCount
    }
}
extension ClawElevatorGlobals: ClawSnapshotNativeValue {}
extension ClawElevatorLevelProfile: ClawSnapshotNativeValue {}
