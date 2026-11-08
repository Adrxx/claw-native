import Foundation
let root = URL(fileURLWithPath: CommandLine.arguments[1])
let data = try Data(contentsOf: root.appendingPathComponent("LEVEL1/WORLDS/WORLD.WWD"))
let world = try ClawWorld(data: data)
precondition(world.name == "Claw - Level 1" && world.startX == 689 && world.startY == 4723)
precondition(world.planes.map { $0.name } == ["Background", "Action", "Front"])
precondition(world.planes.map { $0.tiles.count } == [576, 36864, 2880])
precondition(world.planes.map { $0.objectCount } == [0, 1479, 0])
precondition(world.tileDescriptions.count == 938)
precondition(world.tileDescriptions.filter { $0.type == 1 }.count == 905)
precondition(world.tileDescriptions.filter { $0.type == 2 }.count == 33)
let firstObject = world.planes[1].objects[0]
precondition(firstObject.id == 179 && firstObject.x == 5377 && firstObject.y == 4374)
precondition(firstObject.logic == "Rat" && firstObject.imageSet == "LEVEL_RAT")
// Optional complete dump for independent raw-WWD and original-instruction comparisons.
if CommandLine.arguments.count > 2 {
    let collision = try ClawCollisionMap(world: world)
    var seed: UInt32 = 1997
    func next() -> UInt32 { seed = seed &* 1664525 &+ 1013904223; return seed }
    var samples: [[String: UInt32]] = []
    for index in 0..<1024 {
        let x = index % 2 == 0 ? next() : next() % 24576
        let y = index % 2 == 0 ? next() : next() % 6144
        let bottom: UInt32 = index % 3 == 0 ? next() : 60
        let offset = index % 3 == 0 ? next() : UInt32(bitPattern: Int32(index % 3 - 1) * 16)
        samples.append(["x": x, "y": y, "bottom": bottom, "offset": offset,
            "attribute": collision.footAttribute(x: x, y: y, bottom: bottom, xOffset: offset)])
    }
    let dump: [String: Any] = ["name": world.name, "startX": world.startX, "startY": world.startY,
        "footSamples": samples,
        "planes": world.planes.map { plane -> [String: Any] in
            ["name": plane.name, "flags": plane.flags, "movementX": plane.movementPercentX,
             "movementY": plane.movementPercentY, "z": plane.z, "width": plane.width,
             "height": plane.height, "tileWidth": plane.tileWidth, "tileHeight": plane.tileHeight,
             "tiles": plane.tiles.map { UInt32(bitPattern: Int32($0)) }, "imageSets": plane.imageSets,
             "objects": plane.objects.map { ["words": $0.words,
                 "strings": [$0.name, $0.logic, $0.imageSet, $0.sound]] as [String: Any] }]
        },
        "descriptions": world.tileDescriptions.map { tile -> [String: Any] in
            ["type": tile.type, "unknown": tile.unknown, "width": tile.width, "height": tile.height,
             "inside": tile.insideAttribute, "outside": tile.outsideAttribute,
             "rect": tile.rect.map { [$0.left, $0.top, $0.right, $0.bottom] } as Any? ?? NSNull()]
        }]
    try JSONSerialization.data(withJSONObject: dump, options: [.sortedKeys])
        .write(to: URL(fileURLWithPath: CommandLine.arguments[2]))
}
let palette = try Data(contentsOf: root.appendingPathComponent("LEVEL1/PALETTES/MAIN.PAL"))
var checked = 0
for plane in world.planes {
    guard let set = plane.imageSets.first else { fatalError("Missing image set") }
    let urls = try FileManager.default.contentsOfDirectory(at: root.appendingPathComponent("LEVEL1/TILES/\(set)"), includingPropertiesForKeys: nil)
    var sprites: [Int: ClawSprite] = [:]
    for url in urls where url.pathExtension == "PID" {
        if let id = Int(url.deletingPathExtension().lastPathComponent) {
            sprites[id] = try ClawSprite(pid: Data(contentsOf: url), palette: palette); checked += 1
        }
    }
    for id in Set(plane.tiles) where id >= 0 { precondition(sprites[id] != nil, "Missing tile \(id)") }
}
for bad in [Data(), Data(data.prefix(1524)), Data(data.prefix(data.count - 10))] {
    do { _ = try ClawWorld(data: bad); fatalError("Accepted truncated WWD") } catch {}
}
print("PASS: CD-rip Level 1, 3 planes, 40320 tile cells, 1479 objects, 938 collision descriptions, \(checked) decoded tiles; truncated inputs rejected")
