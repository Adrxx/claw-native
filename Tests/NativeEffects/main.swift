import Foundation
import Darwin
setbuf(stdout,nil)
let root = URL(fileURLWithPath:CommandLine.arguments[1])
let level = try ClawLevelScene(root:root),assets = try ClawPlayerAssets(root:root)
let player = try ClawNativePlayer(world:level.world,assets:assets)
var wall:UInt32 = 1000
let scene = ClawNativeScene(player:player,clock:{wall})
try scene.loadRecoveredObjects(world:level.world,root:root)
let effects = ClawNativeEffects(scene:scene,resources:scene.objectResources!)
var frameDelta:UInt32 = 16
effects.frameClock = {(frameDelta,100)}
var immediateRegistered = 0
var pointsRegistered = 0
var onCreateState:[UInt32:UInt32] = [:]
effects.onCreated = { actor in
    let snapshot = actor.snapshot()!;onCreateState[actor.token] = snapshot.primary.7
    precondition(scene.actorTokens.contains(actor.token))
    if snapshot.primary.4 == 0x4485a0 { precondition(snapshot.primary.7 == 0);immediateRegistered += 1 }
    if snapshot.primary.4 == 0x473a70 { pointsRegistered += 1 }
}
for fn in ClawNativeEffects.callbacks { scene.gameplay[fn] = { token in _ = effects.callback(token,function:fn) } }
var scheduler = ClawSceneActorGlobals()
scheduler.animation.deltaMilliseconds = 16
// Explicit adapter for unrelated player/camera/enemy callbacks; the C scene
// list/countdown/destruction bodies and every FX callback execute normally.
effects.externalService = { _ in 0 }
func sweep(delta:UInt32 = 16) {
    frameDelta = delta;scheduler.animation.deltaMilliseconds = delta;var fault:UInt32 = 0
    claw_scene_actor_update(scene.containerToken,&scheduler,0,effects.actorHost,&fault)
    precondition(fault == 0 && effects.failure == nil,effects.failure ?? "Source scene scheduler")
}
func destroy(_ token:UInt32) {
    scene.heap.lookup(token,words:128)![2] |= 0x10000
    sweep()
    precondition(effects.actors[token] == nil && scene.heap.lookup(token,words:1) == nil && !scene.actorTokens.contains(token))
}
let item = scene.heap.allocate(bytes:512);let raw = scene.heap.lookup(item,words:128)!;raw[3] = scene.sceneIdentity;raw[19] = 900;raw[20] = 4800
for (value,frame) in [(100,1),(500,2),(1500,3),(2500,4),(5000,5),(7500,6),(10000,7),(15000,8),(25000,9),(0,0)] {
    raw[63] = UInt32(value);let before = Set(effects.actors.keys)
    precondition(effects.points(item:item),effects.failure ?? "Points failed")
    let token = Set(effects.actors.keys).subtracting(before).first!;let body = effects.actors[token]!
    precondition(body.snapshot()!.actor.91 == UInt32(frame) && body.snapshot()!.actor.92 != 0 && body.snapshot()!.actor.93 != 0 && body.snapshot()!.actor.2 & 0x40000 != 0)
    body.tick();for _ in 0..<60 where body.snapshot()!.actor.2 & 0x10000 == 0 { body.tick() }
    precondition(body.snapshot()!.actor.2 & 0x10000 != 0,effects.failure ?? "ANI didn't stop");destroy(token)
}
print("PASS10 sourcePoints wrappers/actualGAME_POINTS frames+ANI/delete/generic free")
let owner = player.sceneSnapshot().token
let playerRaw = scene.heap.lookup(owner,words:128)!;playerRaw[70] = UInt32(bitPattern:-20);playerRaw[71] = UInt32(bitPattern:-25);playerRaw[72] = 20;playerRaw[73] = 25
let mother = effects.mother(owner:owner)
precondition(mother != 0 && effects.failure == nil)
let motherRaw = scene.heap.lookup(mother,words:128)!;let motherLogic = scene.heap.lookup(motherRaw[27],words:93)!
precondition(motherLogic[92] == owner && motherRaw[2] & 0x40000 == 0, "Mother flags \(motherRaw[2]) owner \(motherLogic[92])/\(owner)")
effects.actors[mother]!.tick();precondition(motherLogic[7] == 10)
let manager = scene.heap.lookup(effects.managerToken,words:77)!
for enabled in [UInt32(0),1] {
    manager[73] = enabled;let before = Set(effects.actors.keys)
    effects.actors[mother]!.tick()
    let babies = Set(effects.actors.keys).subtracting(before)
    precondition(babies.count == Int(enabled+1) && motherLogic[8] == 15 && effects.failure == nil)
    // Callback isolation during destructor sweeps: use an explicit source
    // frame-counter fixture to defer this unrelated Mother while verifying
    // each elected Baby lifecycle. A separate test checks the real15ms timer.
    motherLogic[9] = 0xffffffff
    for token in babies {
        let body = effects.actors[token]!,snapshot = body.snapshot()!
        precondition(onCreateState[token] == 0 && snapshot.primary.7 == 5 && snapshot.actor.2 & 0x240020 == 0x240020)
        precondition(snapshot.actor.100 != 0 && snapshot.actor.92 != 0)
        for _ in 0..<40 where body.snapshot()!.actor.2 & 0x10000 == 0 { body.tick() }
        precondition(body.snapshot()!.actor.2 & 0x10000 != 0);destroy(token)
    }
    motherLogic[9] = 0
}
precondition(immediateRegistered == 3 && pointsRegistered == 10)
print("PASSsourceMother owner identity/shared RNG/one+twoBaby/immediate pre-callback registration/retailGLITTER1 lifetimes")
// Real generic timer:14ms leaves1,1ms expires and executes exactly one
// emission; the resulting callback resets the timer to15.
manager[73] = 0;motherLogic[8] = 15
let countBeforeTimer = immediateRegistered
sweep(delta:14);precondition(motherLogic[8] == 1 && immediateRegistered == countBeforeTimer)
sweep(delta:1);precondition(motherLogic[8] == 15 && immediateRegistered == countBeforeTimer+1)
print("PASS originalgeneric15ms countdown + source node removal/destruction")
print("PASS smoke initial graphs",effects.events.count,"events",effects.allocations.count,"allocations")
// Ordinary pickup creation uses rich six-argument service and source470110.
var ordinaryCall = ClawItemPickupCall();ordinaryCall.function = 0x4c8da0;ordinaryCall.receiver = scene.containerToken;ordinaryCall.argumentCount = 6
ordinaryCall.arguments.0 = 1;ordinaryCall.arguments.1 = 700;ordinaryCall.arguments.2 = 4800;ordinaryCall.arguments.3 = 0;ordinaryCall.arguments.4 = 0x522950;ordinaryCall.arguments.5 = 0x40000
let ordinary = effects.itemService(ordinaryCall)!
precondition(ordinary != 0);let ordinaryBody = effects.actors[ordinary]!
ordinaryBody.tick();let ordinarySnapshot = ordinaryBody.snapshot()!
precondition(ordinarySnapshot.primary.7 == 5 && ordinarySnapshot.actor.25 == 1001 && ordinarySnapshot.actor.2 & 0x20000 != 0)
precondition(ordinarySnapshot.actor.100 != 0 && ordinarySnapshot.actor.92 != 0)
for _ in 0..<30 { ordinaryBody.tick() }
precondition(ordinaryBody.snapshot()!.actor.2 & 0x10000 == 0)
destroy(ordinary)
print("PASS ordinaryPowerupGlitter richcreator/GAME_GLITTER/CYCLE100/depth+random delay/source removal")
// Frozen setter calls its own448400 implementation and forwards only the
// named creator boundary into Effects. Globals are explicit test-owned source
// aliases; RootPlayerServices owns the live production aliases/write-back.
var power = ClawPlayerPowerupGlobals();power.managerToken = effects.managerToken;power.playerToken = owner;power.musicDisabled = 1
func powerCall(_ function:UInt32,_ args:[UInt32]) {
    var result:UInt32 = 0
    let status = withUnsafeMutablePointer(to:&power) { globals in
        var context = ClawPlayerPowerupRuntimeContext(scene:scene.actorHost,globals:globals,fault:0)
        let status = args.withUnsafeBufferPointer { arguments in
            claw_player_powerup_entry(function,0,arguments.baseAddress,UInt32(arguments.count),&context,{context,event,user in
                guard let event,let user else { return 0 };let effects = Unmanaged<ClawNativeEffects>.fromOpaque(user).takeUnretainedValue()
                guard let result = effects.service(event.pointee) else { context?.pointee.fault = 1;return 0 };return result
            },Unmanaged.passUnretained(effects).toOpaque(),&result)
        }
        precondition(context.fault == 0);return status
    }
    precondition(status == 1 && effects.failure == nil)
}
let privateToken = player.sceneSnapshot().primary.5,primaryToken = player.sceneSnapshot().actor.27
let privateRaw = scene.heap.lookup(privateToken,words:78)!
powerCall(0x41f990,[owner,primaryToken,privateToken,0x26bc,30]);let catMother = privateRaw[76]
precondition(power.powerup == 0x26bc && power.remaining == 30 && catMother != 0 && effects.actors[catMother] != nil)
let catRaw = scene.heap.lookup(catMother,words:128)!,catLogic = scene.heap.lookup(catRaw[27],words:93)!
precondition(catLogic[92] == owner);effects.actors[catMother]!.tick()
powerCall(0x41fc30,[owner,primaryToken,privateToken,29]);precondition(power.remaining == 1 && privateRaw[76] == catMother && catRaw[2] & 0x10000 == 0)
powerCall(0x41fc30,[owner,primaryToken,privateToken,1]);precondition(power.powerup == 0 && privateRaw[76] == 0 && catRaw[2] & 0x10000 != 0)
// Pause unrelated Mother to isolate source scene deletion; source marked
// Catnip Mother still receives its final callback before deferred destruction.
motherLogic[9] = 0xffffffff;sweep();precondition(effects.actors[catMother] == nil)
powerCall(0x41f990,[owner,primaryToken,privateToken,0x26bc,30000]);let resetMother = privateRaw[76]
precondition(resetMother != 0 && power.powerup == 0x26bc)
powerCall(0x41f990,[owner,primaryToken,privateToken,0,0]);precondition(power.powerup == 0 && privateRaw[76] == 0 && scene.heap.lookup(resetMother,words:128)![2] & 0x10000 != 0)
sweep();precondition(effects.actors[resetMother] == nil)
print("PASS actualCatnip setter→Effects owner/rawprivate→timer expiry and reset→MotherDelete/generic node removal")
// Gameplay allocator injection preserves source observable prefix. Resources
// and metadata are already materialized; this policy applies only scene malloc.
let componentCount = effects.actors.count
var count = 0
effects.allocationAllowed = { _ in count += 1;return count != 1 }
raw[63] = 100;precondition(!effects.points(item:item) && effects.fault == 2 && effects.actors.count == componentCount)
effects.resetDiagnostic();count = 0
effects.allocationAllowed = { _ in count += 1;return count != 2 }
precondition(!effects.points(item:item) && effects.fault == 2 && count == 2)
effects.allocationAllowed = nil;effects.resetDiagnostic()
precondition(effects.unresolved.isEmpty)
print("PASS actor/primary allocator failure diagnostics; explicit native safety extension to original fault prefixes")
// Unrelated paused Mother and remaining emitted children still have valid
// identities. Root removal hook handles any generic destructor it owns.
print("PASS nativeEffects",effects.events.count,"ordered service events",effects.allocations.count,"allocations",effects.freed.count,"frees; no device or playback activation")
