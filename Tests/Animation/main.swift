import Foundation

let root = URL(fileURLWithPath: CommandLine.arguments[1])
let files = try FileManager.default.contentsOfDirectory(at: root.appendingPathComponent("CLAW/IMAGES"), includingPropertiesForKeys: nil)
let ids = files.compactMap { url -> Int? in
    let name = url.deletingPathExtension().lastPathComponent
    return name.hasPrefix("FRAME") ? Int(name.dropFirst(5)) : nil
}
func animation(_ name: String) throws -> ClawAnimation {
    try ClawAnimation(data: Data(contentsOf: root.appendingPathComponent("CLAW/ANIS/\(name).ANI")))
}
let swipe = try animation("SWIPE")
var attack = try ClawAnimationPlayback(animation: swipe, availableImages: ids)
precondition(attack.actor.imageID == UInt32(swipe.frames[0].imageID))
precondition(attack.state.recordIndex == 1)
precondition(attack.eventNames[1] == swipe.frames[0].event)
for _ in 1..<swipe.frames.count { attack.update(delta: 1000) }
precondition(swipe.frames.last!.record.controlCommand == 9)
precondition(attack.state.stopped == 1)
precondition(attack.actor.imageID == UInt32(swipe.frames.last!.imageID))
let finalImage = attack.actor.imageID
for _ in 0..<10 { attack.update(delta: 1000) }
precondition(attack.actor.imageID == finalImage && attack.state.stopped == 1)
attack.restart()
precondition(attack.state.stopped == 0 && attack.actor.imageID == UInt32(swipe.frames[0].imageID))
let walk = try animation("WALK")
var walking = try ClawAnimationPlayback(animation: walk, availableImages: ids)
for _ in 0..<walk.frames.count { walking.update(delta: 1000) }
precondition(walking.state.stopped == 0)
precondition(walking.actor.imageID == UInt32(walk.frames[0].imageID))
precondition(walking.state.recordIndex == 1)
var deferred = try ClawAnimationPlayback(animation: walk, availableImages: ids, startImmediately: false)
precondition(deferred.state.recordIndex == 0 && deferred.state.remaining == 0)
let retainedActor = ClawAnimationActor(imageID: finalImage, imageToken: finalImage &+ 1,
    flags: 2, x: 689, y: 4730, moveX: 0, moveY: 0)
deferred.synchronize(actor: retainedActor, rate: 1)
precondition(deferred.actor.imageID == finalImage && deferred.state.recordIndex == 0)
deferred.update(delta: 16)
precondition(deferred.actor.imageID == UInt32(walk.frames[0].imageID))
precondition(deferred.state.recordIndex == 1)
precondition(deferred.state.remaining == walk.frames[0].record.duration)
print("PASS: Swift/C integration selects initial frames, stops SWIPE, preserves its final frame, replays and loops WALK")
print("PASS: deferred player sequence selection retains the previous image until first update and does not consume its delay early")
