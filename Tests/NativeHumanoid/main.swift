import Foundation
import Darwin
setbuf(stdout,nil)
let root = URL(fileURLWithPath:CommandLine.arguments[1])
let level = try ClawLevelScene(root:root), assets = try ClawPlayerAssets(root:root)
let player = try ClawNativePlayer(world:level.world,assets:assets)
var clock: UInt32 = 1000
let scene = ClawNativeScene(player:player,clock:{clock})
try scene.loadRecoveredObjects(world:level.world,root:root)
let resources = scene.objectResources!
let loader = ClawNativeObjectLoader(scene:scene,resources:resources)
let records = level.world.planes.flatMap(\.objects).filter { $0.logic == "Soldier" || $0.logic == "Officer" }
precondition(records.filter{$0.logic == "Soldier"}.count == 16 && records.filter{$0.logic == "Officer"}.count == 26)
var humanoids: [ClawNativeHumanoid] = []
for record in records {
    guard let value = try loader.load(record,world:level.world) else { fatalError("Uncreated humanoid") }
    scene.adopt(value)
    let body = try ClawNativeHumanoid(kind:record.logic == "Soldier" ? .soldier : .officer,snapshot:value,scene:scene,resources:resources)
    body.tick()
    precondition(body.failure == nil,"Startup \(record.logic): \(body.failure ?? "")")
    precondition(body.generic.pointee.enemyToken != 0 && scene.heap.lookup(body.generic.pointee.enemyToken,words:UInt32(body.privateWords)) != nil)
    precondition(body.state.pointee.primary.6 == body.generic.pointee.enemyToken)
    precondition(body.state.pointee.actor.28 != 0 && body.state.pointee.actor.30 != 0)
    precondition(body.state.pointee.actor.100 != 0 && body.state.pointee.actor.93 != 0)
    humanoids.append(body)
}
precondition(humanoids.allSatisfy{$0.globals === humanoids[0].globals} && humanoids[0].strikeCounter == 1)
print("PASS42 actual WWD Human startup/resource/binding allocations/shared globals")
for body in humanoids { body.tick();precondition(body.failure == nil,"Tick \(body.kind): \(body.failure ?? "")") }
print("PASS42 retained real controllers")
// An explicit lab frame service runs components directly while root alone owns
// registration of the production scene controller/destruction dictionaries.
var componentTime: UInt32 = 1000
var componentDelta: UInt32 = 17
var children: [ClawNativeBullet] = []
var suppliedCalls: [UInt32:Int] = [:]
for body in humanoids {
    body.frameClock = { (time:componentTime,delta:componentDelta) }
    body.onBulletCreated = { children.append($0) }
    body.externalService = { event in
        // Exact missing leaf addresses are retained; no FX or loot is claimed.
        suppliedCalls[event.function,default:0] += 1; return nil
    }
    if body.kind == .soldier {
        _ = body.callback(0x48b880)
    }
}
let soldiers = humanoids.filter{$0.kind == .soldier}
for frame in 0..<120 {
    componentTime &+= 17
    for body in soldiers where body.bullets.isEmpty { _ = body.callback(0x48ba00) }
    if soldiers.allSatisfy({!$0.bullets.isEmpty}) { print("PASS16 actual ANI-driven Soldier shots at frame \(frame)");break }
}
precondition(children.count == 16,"Actual ANI did not produce all16 shots: \(children.count)")
for child in children {
    child.refresh()
    precondition(child.failure == nil && child.generic.pointee.enemyToken != 0)
    precondition(scene.heap.lookup(child.generic.pointee.enemyToken,words:84) != nil)
    precondition(scene.heap.lookup(child.generic.pointee.enemyToken,words:85) == nil)
    precondition(child.state.pointee.actor.65 == 10 && child.state.pointee.actor.52 == 0x40)
    let velocity = withUnsafeBytes(of:&child.state.pointee.enemy) { $0.loadUnaligned(fromByteOffset:0x50,as:Double.self) }
    precondition(velocity == 500 || velocity == -500)
    for _ in 0..<4 { componentTime &+= 17;child.tick();precondition(child.failure == nil) }
    // The fixture explicitly elects CaptainClawHit; production scene election
    // is the already recovered ActorInteractions host, not this test loop.
    child.electedPlayerHit()
    precondition(child.state.pointee.actor.2 & 0x10000 != 0)
    let privateToken = child.generic.pointee.enemyToken
    _ = child.callback(0x484d90,argument:1)
    precondition(scene.heap.lookup(privateToken,words:1) == nil)
}
precondition(soldiers.allSatisfy{$0.failure == nil})
print("PASS16 Bullet84 allocation/launch/retained flight/elected CaptainClawHit/private-free")
print("EXPLICIT humanoid services:",humanoids.flatMap{Array($0.unresolved)}.sorted().map{String($0,radix:16)})
// Retain typed-hit/death controllers with an explicitly supplied player attack
// counter at the component view boundary. The particle and loot leaves remain
// unsupported and must be exposed by their original addresses.
var lootBoundaries = 0
var attacker = children[0].snapshot()
attacker.actor.52 = 0x10;attacker.actor.65 = 2;attacker.actor.78 = 0x80000000;attacker.actor.2 &= ~UInt32(0x10000)
withUnsafeMutableBytes(of:&attacker.actor) { $0.storeBytes(of:UInt32(0),toByteOffset:0x164,as:UInt32.self) }
scene.write(attacker)
for body in humanoids {
    body.state.pointee.actor.29 = attacker.token;body.flush()
    var shot: UInt32 = 0
    while Int32(bitPattern:body.state.pointee.actor.67) > 0 {
        shot += 1;precondition(shot <= 4);componentTime &+= 401
        body.refresh();body.common.pointee.playerPrivate.58 = shot
        precondition(body.entry(0x4dc830,argument:0) != nil);body.flush()
        precondition(body.failure == nil,"Typed hit \(body.kind): \(body.failure ?? "")")
    }
    precondition(body.state.pointee.primary.7 == body.states.ids["LS_DEAD"])
    precondition(body.unresolved.contains(0x42df90));lootBoundaries += 1
    _ = body.callback(0x44e0c0,argument:1);componentTime &+= 1001;body.tick()
    precondition(body.failure == nil && body.state.pointee.actor.2 & 0x10000 != 0)
    let privateToken = body.generic.pointee.enemyToken
    _ = body.callback(body.kind == .officer ? 0x462a00 : 0x48afd0,argument:1)
    precondition(scene.heap.lookup(privateToken,words:1) == nil && scene.fault == 0)
}
precondition(lootBoundaries == 42 && suppliedCalls[0x42df90] == 42)
print("PASS42 retained typed combat→death→Delete/private teardown;42explicit loot boundaries")
let addresses = Set(humanoids.flatMap{Array($0.unresolved)}).sorted().map{String($0,radix:16)}
print("PASS address services retained:",addresses)
