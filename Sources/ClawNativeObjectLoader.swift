import Foundation

// The complete WWD loader supplies original raw fields before gameplay starts.
// Spatial membership composes the native grid; physical resources remain services.
final class ClawNativeObjectLoader {
    unowned let scene: ClawNativeScene
    let resources: ClawActorResources
    private var failure: String?

    // MARK: - World record loading

    init(scene: ClawNativeScene, resources: ClawActorResources) {
        self.scene = scene
        self.resources = resources
    }
    func load(_ record: ClawWorld.Object, world: ClawWorld, planeToken: UInt32 = 0) throws -> ClawInteractionActor? {
        var state = ClawWorldObjectRuntime(), context = ClawWorldObjectContext(), info = ClawWorldObjectInfo()
        context.actorToken = scene.heap.allocate(bytes: 0x1b4)
        context.logicToken = scene.heap.allocate(bytes: 0x174)
        context.sceneToken = 0x10001000
        context.sceneDefaultType = 0x60003000
        context.registryToken = 0x62000010
        let plane = world.planes.first { $0.flags & 1 != 0 }!
        context.worldWidth = Int32(plane.width * plane.tileWidth)
        context.worldHeight = Int32(plane.height * plane.tileHeight)
        if planeToken != 0 {
            guard let plane = scene.heap.lookup(planeToken, words: 45), let grid = scene.heap.lookup(plane[44], words: 28) else {
                throw AssetError.invalid("WWD spatial layer graph")
            }
            context.worldWidth = Int32(bitPattern: plane[12])
            context.worldHeight = Int32(bitPattern: plane[13])
            context.layerTokens = (grid[1], grid[2], grid[3])
        }
        // The loader and record bytes are borrowed only for this synchronous
        // recovered call; callback context never transfers ownership.
        let result = record.encodedRecord.withUnsafeBytes {
            claw_world_object_load(
                $0.bindMemory(to: UInt8.self).baseAddress, $0.count, &state, &context,
                nativeWorldObjectDependency, Unmanaged.passUnretained(self).toOpaque(), &info)
        }
        if let failure { throw AssetError.invalid(failure) }
        guard result == record.encodedRecord.count else { throw AssetError.invalid("WWD actor load failed \(record.logic)") }
        if info.created == 0 {
            scene.heap.free(context.actorToken)
            scene.heap.free(context.logicToken)
            return nil
        }
        var snapshot = ClawInteractionActor()
        snapshot.token = context.actorToken
        snapshot.actor = state.actor
        snapshot.primary = state.logic
        return snapshot
    }

    // MARK: - Registry, resource and spatial services

    fileprivate func dependency(
        _ state: UnsafeMutablePointer<ClawWorldObjectRuntime>,
        context: UnsafeMutablePointer<ClawWorldObjectContext>, call: ClawWorldObjectCall
    ) -> UInt32 {
        switch call.function {
        case 0x4f6286:
            guard let name = call.text, let metadata = claw_logic_registry_find(name) else { return 0 }
            context.pointee.entryCallback = metadata.pointee.callback
            context.pointee.entryFlags = metadata.pointee.flags
            return scene.entry(named: String(cString: name))
        case 0x4c7970, 0x4c7900:
            do {
                guard let name = call.text, let images = try resources.images(name: String(cString: name)) else { return 0 }
                var binding = ClawActorResourceBindings()
                binding.actor = state.pointee.actor
                var bindingContext = ClawActorBindingContext()
                bindingContext.image = images.binding()
                let result =
                    call.function == 0x4c7970
                    ? claw_actor_bind_default_image(&binding, &bindingContext, name, nativeWorldImageLookup, nil)
                    : claw_actor_bind_indexed_image(
                        &binding, &bindingContext, name, Int32(bitPattern: call.arguments.0), nativeWorldImageLookup, nil)
                state.pointee.actor = binding.actor
                return result
            } catch {
                failure = String(describing: error)
                return 0
            }
        case 0x4c79e0, 0x4c7a40:
            guard let name = call.text else {
                failure = "Missing WWD resource name"
                return 0
            }
            var snapshot = ClawInteractionActor()
            snapshot.token = context.pointee.actorToken
            snapshot.actor = state.pointee.actor
            snapshot.primary = state.pointee.logic
            scene.write(snapshot)
            let result = scene.namedAnimation(
                function: call.function, actor: snapshot.token, name: String(cString: name),
                eager: call.function == 0x4c79e0 ? call.arguments.1 : 0)
            if let changed = scene.snapshotActor(snapshot.token) {
                state.pointee.actor = changed.actor
                state.pointee.logic = changed.primary
            }
            if scene.fault != 0 { failure = "WWD animation/resource binding fault" }
            return result
        case 0x4f4630:
            guard call.receiver != 0 else { return 0 }
            var snapshot = ClawInteractionActor()
            snapshot.token = context.pointee.actorToken
            snapshot.actor = state.pointee.actor
            snapshot.primary = state.pointee.logic
            scene.write(snapshot)
            let result = scene.spatial(call.function, receiver: call.receiver, arguments: [call.arguments.0])
            if let updated = scene.snapshotActor(snapshot.token) {
                state.pointee.actor = updated.actor
                state.pointee.logic = updated.primary
            }
            return result
        case 0x4c9be0: return 0  // Rejected unregistered allocation has no gameplay.
        default:
            failure = "WWD resource service \(String(call.function, radix: 16)) requires recovery"
            return 0
        }
    }
}
private let nativeWorldObjectDependency: ClawWorldObjectDependency = { state, context, call, user in
    guard let state, let context, let call, let user else { return 0 }
    return Unmanaged<ClawNativeObjectLoader>.fromOpaque(user).takeUnretainedValue().dependency(state, context: context, call: call.pointee)
}
private let nativeWorldImageLookup: ClawActorBindingDependency = { _, context, call, _ in
    guard let context, let call, call.pointee.function == 0x4f6286 else { return 0 }
    return context.pointee.image.token
}
