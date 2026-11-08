import Foundation

// Native owner for the additional v1.3 LogicBump callback record.
final class ClawNativeBumpLogic {
    private let storage: UnsafeMutableRawPointer
    init(identity: UInt32, scene: UInt32) {
        var fault: UInt32 = 0
        let value = claw_v13_bump_create(identity, scene, &fault)
        precondition(value != nil && fault == 0, "v1.3 bump binding transport")
        storage = value!
    }
    deinit { claw_v13_bump_destroy(storage) }
    func invoke() -> UInt32 {
        var fault: UInt32 = 0
        let result = claw_v13_bump_invoke(storage, &fault)
        precondition(fault == 0, "v1.3 bump virtual transport")
        return result
    }
}

// Native storage adapter for recovered original world-point and movement queries.
// Gameplay actor construction and player state transitions remain separate work.
struct ClawCollisionMap {
    private let cells: [UInt32]
    private let rowOffsets: [UInt32]
    private let descriptions: [ClawTileDescription]
    private let width: Int32
    private let height: Int32
    private let shiftX: UInt32
    private let shiftY: UInt32
    private var maximumStep: UInt32 = 64
    // Engine startup flag 0x20 elects manager bit 4. Shipped single-player
    // startup leaves it clear; scene owners can supply the new bump records.
    var contactManagerFlags: UInt32 = 0
    var contactActors: (() -> [ClawV13ContactActor])?
    var contactCallback: ClawV13BumpCallback?
    var contactContext: UnsafeMutableRawPointer?
    var publishContacts: (([ClawV13ContactActor]) -> Void)?
    var savedMaximumStep: UInt32 { maximumStep }
    mutating func restoreMaximumStep(_ value: UInt32) throws {
        guard value == 14 || value == 64 else { throw ClawSnapshotError.invalidState }
        maximumStep = value
    }
    mutating func setGameStageSteps() { maximumStep = 14 } // Original42ce90 mode8/16.

    init(world: ClawWorld) throws {
        guard let plane = world.planes.first(where: { $0.flags & 1 != 0 }),
              plane.tileWidth.nonzeroBitCount == 1, plane.tileHeight.nonzeroBitCount == 1,
              plane.width * plane.tileWidth <= Int(Int32.max),
              plane.height * plane.tileHeight <= Int(Int32.max),
              !world.tileDescriptions.isEmpty else {
            throw AssetError.invalid("Invalid action collision plane")
        }
        cells = plane.tiles.map { UInt32(bitPattern: Int32($0)) }
        for cell in cells where cell != 0xffffffff && cell != 0xeeeeeeee {
            guard Int(cell & 0xffff) < world.tileDescriptions.count else {
                throw AssetError.invalid("Unknown tile collision description")
            }
        }
        rowOffsets = (0..<plane.height).map { UInt32($0 * plane.width) }
        descriptions = world.tileDescriptions.map(\.native)
        width = Int32(plane.width * plane.tileWidth)
        height = Int32(plane.height * plane.tileHeight)
        shiftX = UInt32(plane.tileWidth.trailingZeroBitCount)
        shiftY = UInt32(plane.tileHeight.trailingZeroBitCount)
    }

    func footAttribute(x: UInt32, y: UInt32, bottom: UInt32, xOffset: UInt32) -> UInt32 {
        cells.withUnsafeBufferPointer { cells in
            rowOffsets.withUnsafeBufferPointer { rows in
                descriptions.withUnsafeBufferPointer { descriptions in
                    claw_world_point_attribute(cells.baseAddress, rows.baseAddress, width, height,
                        shiftX, shiftY, descriptions.baseAddress, UInt32(descriptions.count),
                        x, y, bottom, xOffset)
                }
            }
        }
    }

    private func withWorld<T>(actors: [ClawCollisionActor], body: (inout ClawCollisionWorld) -> T) -> T {
        cells.withUnsafeBufferPointer { cells in
            rowOffsets.withUnsafeBufferPointer { rows in
                descriptions.withUnsafeBufferPointer { descriptions in
                    actors.withUnsafeBufferPointer { actors in
                        // Original manager constructor 0x4cad42 sets both steps to 64.
                        var world = ClawCollisionWorld(cells: cells.baseAddress, rowOffsets: rows.baseAddress,
                            width: width, height: height, shiftX: shiftX, shiftY: shiftY,
                            descriptions: descriptions.baseAddress, descriptionCount: UInt32(descriptions.count),
                            actors: actors.baseAddress, actorCount: UInt32(actors.count), maximumStepX: maximumStep, maximumStepY: maximumStep)
                        return body(&world)
                    }
                }
            }
        }
    }

    func resolve(actor: inout ClawCollisionActor, x: UInt32, y: UInt32, options: UInt32,
        otherActors: [ClawCollisionActor] = []) -> UInt32 {
        if claw_native_v13_enabled() != 0, contactManagerFlags & 4 != 0 {
            return contactMove(actor: &actor, x: x, y: y, options: options, split: false, otherActors: otherActors)
        }
        return withWorld(actors: otherActors) { world in claw_collision_resolve(&world, &actor, x, y, options) }
    }

    @discardableResult func move(actor: inout ClawCollisionActor, x: UInt32, y: UInt32, options: UInt32,
        otherActors: [ClawCollisionActor] = []) -> UInt32 {
        if claw_native_v13_enabled() != 0, contactManagerFlags & 4 != 0 {
            return contactMove(actor: &actor, x: x, y: y, options: options, split: true, otherActors: otherActors)
        }
        return withWorld(actors: otherActors) { world in claw_collision_move(&world, &actor, x, y, options) }
    }
    private func contactMove(actor: inout ClawCollisionActor, x: UInt32, y: UInt32, options: UInt32,
        split: Bool, otherActors: [ClawCollisionActor]) -> UInt32 {
        var records = contactActors?() ?? otherActors.map { ClawV13ContactActor(actor: $0, mask: 0, otherToken: 0, hasCallback: 0) }
        let index: Int
        if let found = records.firstIndex(where: { $0.actor.token == actor.token }) {
            index = found; records[index].actor = actor
        } else {
            index = records.count
            records.append(ClawV13ContactActor(actor: actor, mask: 0, otherToken: 0, hasCallback: 0))
        }
        var fault: UInt32 = 0
        let result = withWorld(actors: otherActors) { world in
            records.withUnsafeMutableBufferPointer { buffer in
                let entry = split ? claw_v13_collision_move : claw_v13_collision_resolve
                return entry(&world, contactManagerFlags, buffer.baseAddress, UInt32(buffer.count), UInt32(index),
                    x, y, options, contactCallback, contactContext, &fault)
            }
        }
        precondition(fault == 0, "v1.3 contact transport fault")
        actor = records[index].actor
        publishContacts?(records)
        return result
    }
    func horizontalClear(x: UInt32, y: UInt32, targetX: UInt32, step: UInt32) -> (result: UInt32, fault: UInt32) {
        var fault: UInt32 = 0
        let result = withWorld(actors: []) { world in
            claw_collision_horizontal_clear(&world, x, y, targetX, step, &fault)
        }
        return (result, fault)
    }

    func placeOnGround(actor: inout ClawCollisionActor) -> UInt32 {
        withWorld(actors: []) { world in claw_collision_place_on_ground(&world, &actor) }
    }
}
