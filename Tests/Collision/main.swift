import Foundation

let root = URL(fileURLWithPath: CommandLine.arguments[1])
let world = try ClawWorld(data: Data(contentsOf: root.appendingPathComponent("LEVEL1/WORLDS/WORLD.WWD")))
let collision = try ClawCollisionMap(world: world)
let action = world.planes.first { $0.flags & 1 != 0 }!
var seed: UInt32 = 19971212
func next() -> UInt32 { seed = seed &* 1664525 &+ 1013904223; return seed }
func rectWords(_ r: ClawPlayerRect) -> [UInt32] { [r.left, r.top, r.right, r.bottom] }
func words(_ a: ClawCollisionActor) -> [UInt32] {
    [a.flags, a.x, a.y, a.mode, a.type, a.stepX, a.stepY, a.supportToken, a.token, a.deltaX, a.deltaY]
        + rectWords(a.moveRect) + rectWords(a.hitRect)
}
var entries: [[String: Any]] = []
for index in 0..<1024 {
    var actor = ClawCollisionActor()
    actor.x = next() % UInt32(action.width * action.tileWidth)
    actor.y = next() % UInt32(action.height * action.tileHeight)
    actor.mode = UInt32(index % 9); actor.type = 2
    actor.stepX = 16; actor.stepY = 16; actor.token = 1
    actor.flags = index % 7 == 0 ? 0x400000 : 0
    actor.moveRect = ClawPlayerRect(left: UInt32(bitPattern: -16), top: UInt32(bitPattern: -52), right: 16, bottom: 60)
    let before = words(actor)
    let x = actor.x &+ next() % 257 &- 128
    let y = actor.y &+ next() % 129 &- 64
    let options = UInt32(index % 32)
    let isMove = index % 2 == 0
    var result: Any = NSNull()
    if isMove { collision.move(actor: &actor, x: x, y: y, options: options) }
    else { result = collision.resolve(actor: &actor, x: x, y: y, options: options) }
    entries.append(["before": before, "target": [x, y, options], "after": words(actor),
        "operation": isMove ? "move" : "resolve", "result": result])
}
for index in 0..<256 {
    var actor = ClawCollisionActor()
    actor.x = index == 0 ? UInt32(world.startX) : next() % UInt32(action.width * action.tileWidth)
    actor.y = index == 0 ? UInt32(world.startY) : next() % UInt32(action.height * action.tileHeight)
    actor.mode = 1; actor.type = 2; actor.token = 1; actor.stepX = 16; actor.stepY = 16
    actor.moveRect = ClawPlayerRect(left: index % 13 == 12 ? 0x80000000 : UInt32(bitPattern: -16),
        top: UInt32(bitPattern: -52), right: 16, bottom: 60)
    let before = words(actor)
    let result = collision.placeOnGround(actor: &actor)
    if index == 0 { precondition(result == 1 && actor.x == 689 && actor.y == 4730) }
    entries.append(["before": before, "target": [0, 0, 0], "after": words(actor),
        "operation": "place", "result": result])
}
try JSONSerialization.data(withJSONObject: entries, options: [.sortedKeys])
    .write(to: URL(fileURLWithPath: CommandLine.arguments[2]))
print("PASS: Swift/C adapter runs 1024 movement and 256 ground placement cases; original comparison is performed by compare_collision_response.py")
