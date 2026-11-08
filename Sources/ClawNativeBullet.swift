import Foundation

// Ordinary Bullet only: the original84-word private allocation and controller.
final class ClawNativeBullet: ClawHumanoidActorServices {
    let context = UnsafeMutablePointer<ClawBulletContext>.allocate(capacity:1)
    private let ownedGeneric = UnsafeMutablePointer<ClawGenericEnemyContext>.allocate(capacity:1)
    private let ownedCommon = UnsafeMutablePointer<ClawGenericEnemyStatesContext>.allocate(capacity:1)
    init(snapshot: ClawInteractionActor, scene: ClawNativeScene, resources: ClawActorResources, restoring: Bool = false) {
        precondition(scene.stateRegistry != nil)
        let states = ClawEnemyStateView(registry:scene.stateRegistry!,inheritance:["Projectile"])
        context.initialize(to:ClawBulletContext());ownedGeneric.initialize(to:ClawGenericEnemyContext());ownedCommon.initialize(to:ClawGenericEnemyStatesContext())
        claw_generic_enemy_context_defaults(ownedGeneric)
        super.init(snapshot:snapshot,scene:scene,resources:resources,generic:ownedGeneric,common:ownedCommon,states:states)
        context.pointee.generic = generic;context.pointee.projectileStates = UnsafePointer(states.entries);context.pointee.projectileStateCount = states.count
        context.pointee.scene = scene.actorHost;claw_bullet_context_defaults(context)
        if !restoring && scene.heap.lookup(0x50b714,words:12) == nil {
            let table = scene.heap.store(token:0x50b714,words:12)
            withUnsafeBytes(of:&generic.pointee.virtualFunctions) { table.update(from:$0.bindMemory(to:UInt32.self).baseAddress!,count:12) }
        }
        reloadPrivate()
    }
    deinit { context.deinitialize(count:1);context.deallocate();ownedGeneric.deinitialize(count:1);ownedGeneric.deallocate();ownedCommon.deinitialize(count:1);ownedCommon.deallocate() }
    override func refresh() { super.refresh();reloadPrivate() }
    override func reloadPrivate() {
        guard let raw = scene?.heap.lookup(generic.pointee.enemyToken,words:84) else { return }
        withUnsafeMutableBytes(of:&state.pointee.enemy) { UnsafeMutableRawBufferPointer(rebasing:$0.prefix(336)).copyMemory(from:UnsafeRawBufferPointer(start:raw,count:336)) }
    }
    override func flush() {
        guard ownsActor else { return }
        super.flush()
        if let raw = scene?.heap.lookup(generic.pointee.enemyToken,words:84) {
            withUnsafeBytes(of:&state.pointee.enemy) { UnsafeMutableRawBufferPointer(start:raw,count:336).copyMemory(from:UnsafeRawBufferPointer(rebasing:$0.prefix(336))) }
        }
        if context.pointee.fault != 0 { fail("Bullet context fault \(context.pointee.fault)") }
    }
    func tick() { guard ownsActor else { fail("Retired bullet owner"); return }; refresh();if claw_bullet_tick(state,context,humanoidDependency,Unmanaged.passUnretained(self).toOpaque()) == 0 { fail("Bullet callback did not complete") };flush() }
    @discardableResult func callback(_ function: UInt32,argument: UInt32 = 0) -> UInt32 {
        guard ownsActor else { fail("Retired bullet owner"); return 0 }
        refresh();let result = entry(function,argument:argument)
        if result == nil { var event = ClawGenericEnemyCall();event.function = function;event.receiver = generic.pointee.enemyToken;event.arguments.0 = argument;_ = unsupported(event) }
        flush();return result ?? 0
    }
    override func entry(_ function: UInt32,argument: UInt32) -> UInt32? {
        var result: UInt32 = 0
        return claw_bullet_entry(state,context,function,argument,humanoidDependency,Unmanaged.passUnretained(self).toOpaque(),&result) == 1 ? result : nil
    }
    // Call only after the scene's actual interaction scanner elects41ce80 for
    // CaptainClaw and this token. The shared player owns input/death/audio state.
    func electedPlayerHit() {
        guard ownsActor else { fail("Retired bullet owner"); return }
        guard let scene else { fail("Missing Bullet hit scene");return }
        refresh();var object = ClawWorldObjectRuntime();object.actor = state.pointee.actor;object.logic = state.pointee.primary
        scene.player.receiveHit(from:&object,token:token);state.pointee.actor = object.actor;state.pointee.primary = object.logic
        scene.write(scene.player.sceneSnapshot());flush()
    }
    struct SavedState: Codable, Equatable {
        let service: ServiceSavedState
        let context: [String: Data]
    }
    func savedState() throws -> SavedState {
        guard context.pointee.imageFrames == nil, context.pointee.imageFrameCount == 0 else { throw ClawSnapshotError.invalidState }
        return SavedState(service: try savedServiceState(), context: Self.snapshotFields.capture(context.pointee))
    }
    static func restoring(_ saved: SavedState, scene: ClawNativeScene, resources: ClawActorResources,
                          heap plan: ClawTokenHeap.RestorePlan) throws -> ClawNativeBullet {
        let result = ClawNativeBullet(snapshot: savedActor(saved.service), scene: scene, resources: resources, restoring: true)
        result.context.pointee = try snapshotFields.restoring(saved.context, into: result.context.pointee)
        try result.restoreServiceState(saved.service, heap: plan)
        return result
    }
    private static let snapshotFields = ClawSnapshotFields<ClawBulletContext>(fields: [
        .init("imageRegistryToken", \.imageRegistryToken), .init("imageRootToken", \.imageRootToken),
        .init("imageRootHeader", \.imageRootHeader), .init("imageFrameOrigin", \.imageFrameOrigin),
        .init("imageLeafToken", \.imageLeafToken), .init("imageLeafHeader", \.imageLeafHeader), .init("fault", \.fault)
    ])
}
