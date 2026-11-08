import Foundation

let root = URL(fileURLWithPath: CommandLine.arguments[1])
let palette = try Data(contentsOf: root.appendingPathComponent("LEVEL1/PALETTES/MAIN.PAL"))
let fm = FileManager.default
var sprites = 0
for url in try fm.contentsOfDirectory(at: root.appendingPathComponent("CLAW/IMAGES"), includingPropertiesForKeys: nil) where url.pathExtension.uppercased() == "PID" {
    let sprite = try ClawSprite(pid: Data(contentsOf: url), palette: palette)
    precondition(sprite.rgba.count == sprite.width * sprite.height * 4)
    sprites += 1
}
var animations = 0
for name in ["IDLE", "WALK", "JUMP", "SWIPE", "DUCK", "CLIMB"] {
    let url = root.appendingPathComponent("CLAW/ANIS/\(name).ANI")
    let animation = try ClawAnimation(data: Data(contentsOf: url))
    precondition(animation.frame(at: 0).imageID == animation.frames[0].imageID)
    precondition(animation.frame(at: animation.duration).imageID == animation.frames[0].imageID)
    for frame in animation.frames {
        let pid = root.appendingPathComponent(String(format: "CLAW/IMAGES/FRAME%03d.PID", frame.imageID))
        _ = try ClawSprite(pid: Data(contentsOf: pid), palette: palette)
    }
    animations += 1
    print("\(name): \(animation.frames.count) frames, \(animation.duration)s")
}
for input in [Data(), Data(repeating: 0, count: 32)] {
    do {
        _ = try ClawSprite(pid: input, palette: palette)
        fatalError("Malformed sprite accepted")
    } catch {}
    do {
        _ = try ClawAnimation(data: input)
        fatalError("Malformed animation accepted")
    } catch {}
}
print("PASS: \(sprites) original sprites, \(animations) animation sequences, malformed-input rejection")
