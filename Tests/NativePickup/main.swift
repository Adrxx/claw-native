import Foundation
import Darwin
setbuf(stdout,nil)
let root = URL(fileURLWithPath:CommandLine.arguments[1])
let level = try ClawLevelScene(root:root),assets = try ClawPlayerAssets(root:root)
let player = try ClawNativePlayer(world:level.world,assets:assets)
let scene = ClawNativeScene(player:player,clock:{1000})
try scene.loadRecoveredObjects(world:level.world,root:root)
let loot = try ClawNativeLoot(scene:scene,resources:scene.objectResources!)
precondition(loot.globals.pointee.itemCount == 62 && loot.word(340) == 1)
print("PASS actual4719e0/62 rows/raw341 words; missing images",(0..<62).filter{loot.word($0) == 0})
var time:UInt32 = 1000
loot.frameClock = { (time:time,animationDelta:17,stageDelta:17) }
let loader = ClawNativeObjectLoader(scene:scene,resources:scene.objectResources!)
let records = level.world.planes.flatMap(\.objects).filter{["Officer","Soldier","Rat"].contains($0.logic)}
precondition(records.count == 54)
var owners:[ClawNativeHumanoid] = []
var expectedItems = 0
for record in records {
    let inventory = [35,37,36,38,39,41,40,42,15].map{record.words[$0]}.filter{$0 != 0}
    if record.logic == "Rat" { precondition(inventory.isEmpty);continue }
    let snapshot = try loader.load(record,world:level.world)!;scene.adopt(snapshot)
    let body = try ClawNativeHumanoid(kind:record.logic == "Officer" ? .officer : .soldier,snapshot:snapshot,scene:scene,resources:scene.objectResources!)
    body.frameClock = { (time:time,delta:17) };body.tick();precondition(body.failure == nil)
    precondition(loot.lootDrop(receiver:body.generic.pointee.enemyToken+0x128),loot.failure ?? "Drop failed")
    expectedItems += inventory.count;owners.append(body)
}
precondition(expectedItems == 137 && loot.goodies.count == 137)
for body in loot.goodies.values {
    body.refresh();precondition(body.failure == nil,"Goodie \(body.token): \(body.failure ?? "") image=\(body.state.pointee.actor.92)/\(body.state.pointee.actor.93) item=\(withUnsafeBytes(of:&body.state.pointee.enemy){$0.load(fromByteOffset:0x184,as:UInt32.self)}) lootFailure=\(loot.failure ?? "") fault=\(body.context.pointee.fault) primary=\(body.state.pointee.primary.4) /\(body.state.pointee.primary.7)")
    precondition(scene.heap.lookup(body.generic.pointee.enemyToken,words:104) != nil && scene.heap.lookup(body.generic.pointee.enemyToken,words:105) == nil)
    let gravity = withUnsafeBytes(of:&body.state.pointee.enemy) { $0.loadUnaligned(fromByteOffset:0x40,as:Double.self) }
    precondition(gravity == 800)
}
print("PASS54 WWD inventories/137 actualGoodie creator/startup/launch104")
var nativePlayer = player.runtime
loot.readPlayer = { nativePlayer }
loot.writePlayer = { value in
    nativePlayer = value
    scene.writePlayerRuntime(value)
    precondition(scene.player.runtime.privateWords.28 == value.privateWords.28 && scene.player.runtime.privateWords.29 == value.privateWords.29)
}
var rebound = 0, ordinaryAwards = 0, unsupportedCatnip = 0
let ordered = loot.goodies.values.sorted{$0.token < $1.token}
for body in ordered {
    // Real initial launch and tile-flight callbacks remain source driven.
    for _ in 0..<8 { time &+= 17;body.tick() }
    // Explicit synthetic ground election isolates the source four-bounce path.
    // Ordinary updates still execute original ANI/collision/geometry bodies.
    for _ in 0..<5 where loot.pickups[body.token] == nil {
        body.refresh();body.state.pointee.actor.51 = 1;body.flush()
        time &+= 17;body.tick()
    }
    precondition(body.failure == nil,"Bounce \(body.failure ?? "")")
    guard let pickup = loot.pickups[body.token] else { fatalError("Four-bounce rebind failed") }
    rebound += 1
    precondition(pickup.failure == nil && pickup.snapshot()?.primary.7 == 5)
    nativePlayer.actor.67 = 50;nativePlayer.privateWords.28 = 40;nativePlayer.privateWords.29 = 40
    let old = nativePlayer
    if pickup.snapshot()!.actor.52 == 0x10000 && pickup.snapshot()!.actor.63 > 100 {
        precondition(!pickup.electedPlayerHit() && pickup.unresolved.contains(0x41f990));unsupportedCatnip += 1
        let privateToken = body.generic.pointee.enemyToken
        _ = loot.privateDestructor(receiver:privateToken,flags:1);loot.remove(body.token);continue
    }
    precondition(pickup.electedPlayerHit(),pickup.failure ?? "Ordinary award unsupported");ordinaryAwards += 1
    let item = pickup.snapshot()!
    let value = item.actor.63
    switch item.actor.52 {
    case 0x40000: precondition(nativePlayer.actor.62 == old.actor.62 &+ value && item.actor.89 & 0x200 != 0)
    case 0x10000: precondition(nativePlayer.actor.67 == min(100,old.actor.67 &+ value) && item.actor.2 & 0x10000 != 0)
    case 0x800000: precondition(nativePlayer.privateWords.28 == min(99,old.privateWords.28 &+ value))
    case 0x100000: precondition(nativePlayer.privateWords.29 == min(99,old.privateWords.29 &+ value))
    default: fatalError("Unexpected dropped category")
    }
    if item.actor.52 == 0x40000 {
        for _ in 0..<27 { time &+= 17;pickup.tick() }
        precondition(pickup.snapshot()!.actor.2 & 0x10000 != 0 && pickup.unresolved.contains(0x4737c0))
    }
    let privateToken = body.generic.pointee.enemyToken
    precondition(loot.privateDestructor(receiver:privateToken,flags:1) == privateToken)
    precondition(scene.heap.lookup(privateToken,words:1) == nil)
    loot.remove(body.token)
}
precondition(rebound == 137 && ordinaryAwards == 134 && unsupportedCatnip == 3 && loot.goodies.isEmpty && loot.pickups.isEmpty)
print("PASS137 spawn→real flight→synthetic grounded bounces→rebind;134ordinary awards/lifecycles;3explicit Catnip boundaries")
// Real table aliases and caps; the scene contact election is explicit here.
func ordinary(_ id:Int32) throws -> ClawNativePickup {
    var fault:UInt32 = 0
    let token = claw_scene_actor_create(scene.containerToken,ClawSceneActorCreate(id:0,x:700,y:4500,z:1000,entryToken:scene.entry(named:"TreasurePowerup"),flags:0x40000),scene.actorHost,&fault)
    precondition(token != 0 && fault == 0)
    let rootToken = loot.word(Int(id))
    let raw = scene.heap.lookup(rootToken+0x24,words:1)!
    _ = try loot.bindImage(token,name:String(cString:UnsafeRawPointer(raw).assumingMemoryBound(to:CChar.self)))
    precondition(loot.rebind(token,item:id));return loot.pickups[token]!
}
let laterHealth = try ordinary(61)
precondition(laterHealth.snapshot()!.actor.1 == 24 && laterHealth.snapshot()!.actor.63 == 5)
nativePlayer.actor.67 = 100
precondition(laterHealth.electedPlayerHit() && laterHealth.snapshot()!.actor.2 & 0x10000 == 0 && nativePlayer.actor.67 == 100)
nativePlayer.actor.67 = 98
precondition(laterHealth.electedPlayerHit() && nativePlayer.actor.67 == 100 && laterHealth.snapshot()!.actor.2 & 0x10000 != 0)
let ammo = try ordinary(20);nativePlayer.privateWords.28 = 98
precondition(ammo.electedPlayerHit() && nativePlayer.privateWords.28 == 99)
let magic = try ordinary(28);nativePlayer.privateWords.29 = 98
precondition(magic.electedPlayerHit() && nativePlayer.privateWords.29 == 99)
let sound = try ordinary(33)
loot.itemContext.pointee.lastSoundTick = 0;loot.itemContext.pointee.lastSoundToken = 0
let requests = player.audio!.playRequests
_ = sound.callback(0x41d6f0);_ = sound.callback(0x41d6f0)
precondition(player.audio!.playRequests == requests+1)
time &+= 1;_ = sound.callback(0x41d6f0);precondition(player.audio!.playRequests == requests+2)
let beforeInvalid = sound.snapshot()!
precondition(!loot.rebind(sound.token,item:-1))
var afterInvalid = sound.snapshot()!,copyBefore = beforeInvalid
precondition(withUnsafeBytes(of:&afterInvalid){Array($0)} == withUnsafeBytes(of:&copyBefore){Array($0)})
print("PASS first-match health61→24; full-health retention/caps; shared tick+sound dedup; invalid signed rebind")
// Private allocator failure is a declared platform service. World release must
// stop before launch writes/RNG and report the native pre-null diagnostic.
let failing = try ClawNativeLoot(scene:scene,resources:scene.objectResources!)
failing.onCreated = { body in body.context.pointee.scene.allocate = {_,_ in 0} }
precondition(!failing.lootDrop(receiver:owners[0].generic.pointee.enemyToken+0x128))
precondition(failing.failure != nil && failing.context.pointee.fault != 0 && failing.goodies.count == 1)
let failed = failing.goodies.values.first!
precondition(failed.state.pointee.primary.7 == 1000 && failed.state.pointee.primary.6 == 0 && failed.context.pointee.fault == 2)
print("PASS allocator failure preserves startup1000 and stops release before launch")
