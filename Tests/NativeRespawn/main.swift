import Foundation
import Darwin
setbuf(stdout, nil)
final class FixtureHost {
    let heap = ClawTokenHeap()
    var clock: UInt32 = 1000
    var host: ClawSceneActorHost {
        ClawSceneActorHost(context: Unmanaged.passUnretained(self).toOpaque(), lookup: { raw, token, words in
            guard let raw else { return nil }
            return Unmanaged<FixtureHost>.fromOpaque(raw).takeUnretainedValue().heap.lookup(token, words: words)
        }, allocate: { raw, bytes in
            guard let raw else { return 0 }
            return Unmanaged<FixtureHost>.fromOpaque(raw).takeUnretainedValue().heap.allocate(bytes: bytes)
        }, free: { raw, token in
            guard let raw else { return }
            Unmanaged<FixtureHost>.fromOpaque(raw).takeUnretainedValue().heap.free(token)
        }, call: { _, call in fatalError("Unexpected fixture service \(String(call.function, radix: 16))") }, readClock: { raw in
            guard let raw else { return 0 }
            return Unmanaged<FixtureHost>.fromOpaque(raw).takeUnretainedValue().clock
        })
    }
}
struct GridEvent: Decodable { let actor: UInt32, heap: String }
struct GridCase: Decodable { let before: String, after: String, events: [GridEvent], count: UInt32, callback: UInt32 }
let oracleURL = URL(fileURLWithPath: "work/native-respawn-agent/grid-oracle.json")
let cases = try JSONDecoder().decode([GridCase].self, from: Data(contentsOf: oracleURL))
var snapshots = 0
for test in cases {
    let fixture = FixtureHost(), before = Data(base64Encoded: test.before)!, expected = Data(base64Encoded: test.after)!
    let buffer = fixture.heap.store(token: 0x1000000, words: before.count / 4)
    before.withUnsafeBytes { UnsafeMutableRawPointer(buffer).copyMemory(from: $0.baseAddress!, byteCount: before.count) }
    var observed: [GridEvent] = []
    let hooks = ClawNativeRespawn.Hooks(playerPrimary: { _ in false }, actorFrame: { _, _ in false },
        service: { _ in nil }, captureTiming: { _ in }, publishTiming: { _ in }, importPlayer: {}, observe: { call in
            if call.function == 0x46e340 {
                observed.append(GridEvent(actor: call.arguments.0, heap: Data(bytes: buffer, count: before.count).base64EncodedString()))
            }
        })
    let component = ClawNativeRespawn(heap: fixture.heap, applicationToken: 0, globals: ClawPlayerDeathCommandGlobals(), host: fixture.host, hooks: hooks)
    precondition(component.scanDormant(grid: 0x1000100, callback: test.callback) == test.count && component.fault == 0)
    precondition(Data(bytes: buffer, count: before.count) == expected)
    precondition(observed.count == test.events.count)
    for (native, original) in zip(observed, test.events) {
        precondition(native.actor == original.actor && native.heap == original.heap)
        snapshots += 1
    }
}
print("PASS64 complete original dormant cleanup scans; \(snapshots) ordered full32KiB heap snapshots")
// Exact source constructors, with explicit physical clock/CRT-empty alias.
let profile = FixtureHost()
profile.heap.store(token: 0x52e1cc, words: 1)[0] = 0x52e1c4
profile.heap.store(token: 0x541328, words: 5)[3] = 99
let application = ClawNativeRespawn.constructApplication(heap: profile.heap, host: profile.host)!
let owner = ClawNativeRespawn.constructOwner(heap: profile.heap, host: profile.host)!
let appWords = profile.heap.lookup(application, words: 77)!, ownerWords = profile.heap.lookup(owner, words: 478)!
precondition(appWords[0] == 0x50bee4 && appWords[0x68/4] == 2 && appWords[0xc8/4] == 30)
precondition(ownerWords[0] == 0x50c264 && ownerWords[0x154/4] == 1)
precondition(profile.heap.lookup(0x541328, words: 5)![3] == 99)
let profileComponent = ClawNativeRespawn(heap: profile.heap, applicationToken: application, globals: ClawPlayerDeathCommandGlobals(), host: profile.host,
    hooks: .init(playerPrimary: { _ in false }, actorFrame: { _, _ in false }, service: { _ in nil }, captureTiming: { _ in }, publishTiming: { _ in }, importPlayer: {}))
precondition(profileComponent.consume(commands: [0x42,0x803a]) == [0x42])
precondition(profileComponent.fault == 0 && profileComponent.events.isEmpty && profileComponent.consumedCommands == [0x803a])
print("PASS source application/owner constructors and empty-state803a gate; unknown commands preserved")
// Rejected actual state type5 and missing palette:426e30 must gate the
// controller and preserve actor state; only the source8005 fallback is emitted.
let table = profile.heap.store(token: 0x50c264, words: 27)
table[4] = 0x4c9bd0 // Exact pure original probe returns5.
appWords[0x2c/4] = owner; ownerWords[1] = application
var fallbacks: [UInt32] = []
let gated = ClawNativeRespawn(heap: profile.heap, applicationToken: application, globals: ClawPlayerDeathCommandGlobals(), host: profile.host,
    hooks: .init(playerPrimary: { _ in preconditionFailure("Rejected type reached player") }, actorFrame: { _, _ in false },
        service: { call in if call.function == 0x429e10 { fallbacks.append(call.arguments.0); return 0 }; return nil },
        captureTiming: { _ in }, publishTiming: { _ in }, importPlayer: {}))
precondition(gated.handle(command: 0x803a) && gated.fault == 0 && gated.events.isEmpty)
table[4] = 0x40af90 // Source state3 is accepted, but no player/palette rejects46be40.
precondition(gated.handle(command: 0x803a) && gated.fault == 0 && fallbacks == [0x8005])
print("PASS rejected source type5 and missing-player/palette gates, including original8005 fallback")
final class DeathBoundary {
    var mode: UInt32 = 0
    var commands: [UInt32] = []
    func call(_ function: UInt32, _ a: UInt32, _ b: UInt32, _ c: UInt32) -> UInt32 {
        switch function {
        case 0x10: return mode
        case 0x4c82a0: return 0 // Explicit isolated animation boundary; completed frame is seeded.
        case 0x546d50: precondition(b == 0x111); commands.append(c); return 1
        default: preconditionFailure("Unexpected death-boundary service")
        }
    }
}
for lives: UInt32 in [0,1,2,3,0x80000000,0xffffffff] {
    for mode: UInt32 in [0,4] {
        for infinite: UInt32 in [0,1] {
            var state = ClawPlayerLocomotion(), damage = ClawPlayerDamageContext()
            let boundary = DeathBoundary(); boundary.mode = mode
            damage.infiniteLives = infinite
            claw_player_set_private_word(&state, 31, lives)
            claw_player_set_actor_word(&state, 0x1a4, 1)
            let dependency: ClawPlayerLocomotionDependency = { _, function, a, b, c, raw in
                Unmanaged<DeathBoundary>.fromOpaque(raw!).takeUnretainedValue().call(function,a,b,c)
            }
            claw_player_update_spike_death(&state, &damage, dependency, Unmanaged.passUnretained(boundary).toOpaque())
            let expectedLives = (mode == 4 ? lives : lives &- 1) &+ infinite
            precondition(claw_player_private_word(&state,31) == expectedLives && claw_player_private_word(&state,32) == 1)
            precondition(boundary.commands == [Int32(bitPattern: expectedLives) < 1 ? 0x8006 : 0x803a])
            claw_player_update_spike_death(&state, &damage, dependency, Unmanaged.passUnretained(boundary).toOpaque())
            precondition(boundary.commands.count == 1)
        }
    }
}
print("PASS24 life/configuration/infinite-life boundaries and once-only original death-command election")
for retained: UInt32 in [0,1] {
    let fixture = FixtureHost()
    fixture.heap.store(token: 0x52e1cc, words: 1)[0] = 0x52e1c4
    _ = fixture.heap.store(token: 0x541328, words: 5)
    let app = ClawNativeRespawn.constructApplication(heap: fixture.heap, host: fixture.host)!
    let state = ClawNativeRespawn.constructOwner(heap: fixture.heap, host: fixture.host)!
    let a = fixture.heap.lookup(app, words: 77)!, s = fixture.heap.lookup(state, words: 478)!
    let vt = fixture.heap.store(token: 0x50c264, words: 27)
    vt[0] = 0x429480; vt[4] = 0x40af90; vt[10] = 0x46ab30
    a[0x2c/4] = state; a[0x9c/4] = retained; a[0xa0/4] = 1
    var services: [ClawSceneActorCall] = []
    let component = ClawNativeRespawn(heap: fixture.heap, applicationToken: app, globals: ClawPlayerDeathCommandGlobals(), host: fixture.host,
        hooks: .init(playerPrimary: { _ in false }, actorFrame: { _, _ in false }, service: { call in
            services.append(call)
            if call.function == 0x46ab30 || call.function == 0x429480 { return 0 }
            return nil
        }, captureTiming: { _ in }, publishTiming: { _ in }, importPlayer: {}))
    precondition(component.handle(command: 0x8006) && component.fault == 0)
    precondition(a[0x2c/4] != state && fixture.heap.lookup(a[0x2c/4], words: 85)![0] == 0x50b4ec)
    precondition(services.first!.function == 0x46ab30 && services.first!.arguments.0 == (retained == 0 ? 5 : 12))
    if retained == 0 { precondition(s[0x38/4] == 1 && services.count == 2 && a[0xe4/4] == 0) }
    else { precondition(services.count == 1 && a[0xe4/4] == 1 && fixture.heap.lookup(a[0xe0/4], words: 1)![0] == state) }
}
print("PASS8006 state5 deletion/state12 retained-history order under explicit original app+a0 placeholder profile; UI lifecycle remains an adapter")
// Missing services stop the transferred batch. The attempted command must not
// be returned for replay after partial original mutations.
table[4] = 0x70000099
let unavailable = ClawNativeRespawn(heap: profile.heap, applicationToken: application, globals: ClawPlayerDeathCommandGlobals(), host: profile.host,
    hooks: .init(playerPrimary: { _ in false }, actorFrame: { _, _ in false }, service: { _ in nil }, captureTiming: { _ in }, publishTiming: { _ in }, importPlayer: {}))
precondition(unavailable.consume(commands: [0x803a,0x8006]) == [0x8006])
precondition(unavailable.fault == 4 && unavailable.consumedCommands == [0x803a] && unavailable.unresolvedServices == [0x70000099])
print("PASS unavailable-service diagnostics consume the attempted command and preserve the unattempted batch tail")
// Actual Level1 native actor scheduler, retaining the live player and750ms
// primary delay. This first half of the trace needs no command interpretation.
let dataRoot = URL(fileURLWithPath: CommandLine.arguments[1])
let level = try ClawLevelScene(root: dataRoot), assets = try ClawPlayerAssets(root: dataRoot)
let player = try ClawNativePlayer(world: level.world, assets: assets)
var now: UInt32 = 1000
let scene = ClawNativeScene(player: player, clock: { now })
try scene.loadRecoveredObjects(world: level.world, root: dataRoot)
var attacker = ClawWorldObjectRuntime()
withUnsafeMutableBytes(of: &attacker.actor) { bytes in
    bytes.storeBytes(of: UInt32(4), toByteOffset: 0xd0, as: UInt32.self)
    bytes.storeBytes(of: UInt32(200), toByteOffset: 0x104, as: UInt32.self)
    bytes.storeBytes(of: UInt32(bitPattern: player.x - 30), toByteOffset: 0x4c, as: UInt32.self)
    bytes.storeBytes(of: UInt32(bitPattern: player.y), toByteOffset: 0x50, as: UInt32.self)
    bytes.storeBytes(of: UInt32(0x80000000), toByteOffset: 0x138, as: UInt32.self)
}
player.receiveHit(from: &attacker, token: 0x10010000)
scene.write(player.sceneSnapshot())
let lethalY = player.y
precondition(player.runtime.logicState == 5004 && scene.snapshotActor(0x10002000)!.primary.8 == 750)
for _ in 0..<46 {
    now &+= 16
    scene.advance(now: now, delta: 16, accumulated: now - 1000, held: 0, pressed: 0)
    precondition(player.y == lethalY && player.pendingCommands.isEmpty)
}
precondition(scene.snapshotActor(0x10002000)!.primary.8 == 14)
now &+= 16
scene.advance(now: now, delta: 16, accumulated: now - 1000, held: 0, pressed: 0)
precondition(scene.snapshotActor(0x10002000)!.primary.8 == 0 && player.y >= lethalY)
for _ in 0..<250 {
    now &+= 16
    scene.advance(now: now, delta: 16, accumulated: now - 1000, held: 0, pressed: 0)
}
precondition(player.pendingCommands == [0x803a] && player.runtime.privateWords.31 == 2 && player.runtime.privateWords.32 == 1)
precondition(scene.fault == 0 && player.failure == nil && player.unresolvedDependencies == Set([0x41ebd0,0x4b7aa0,0x41f990]))
print("PASS actualLevel1 lethal hit→750ms original scheduler delay→fall death→one queued803a; lives3→2 and death count1, explicit death-notice/audio-stop/powerup-reset boundaries")
// Source-initialized controller/application profile over the existing Level1
// world. Window/fade/music transport remains an explicit platform profile.
let heap = scene.heap
precondition(ClawNativeRespawn.installActorContainerMetadata(heap: heap))
heap.store(token: 0x52e1cc, words: 1)[0] = 0x52e1c4
_ = heap.store(token: 0x541328, words: 5)
let appToken = ClawNativeRespawn.constructApplication(heap: heap, host: scene.actorHost)!
let stateToken = ClawNativeRespawn.constructOwner(heap: heap, host: scene.actorHost)!
let app = heap.lookup(appToken, words: 77)!, state = heap.lookup(stateToken, words: 478)!
app[0x2c/4] = stateToken; app[0x30/4] = scene.sceneIdentity
app[0x7c/4] = 640; app[0x80/4] = 480
state[1] = appToken; state[3] = scene.sceneIdentity
state[0x2c/4] = heap.allocate(bytes: 4) // Opaque platform palette-presence token; fade service owns it.
state[0x44/4] = .max // Exact store in46aeb0 level-start profile.
let soundRegistry = heap.allocate(bytes: 52)
heap.lookup(scene.sceneIdentity, words: 12)![10] = soundRegistry
let dormant = scene.enemies.values.first!.token
heap.lookup(dormant, words: 128)![0x164/4] |= 0x2000
var deathGlobals = ClawPlayerDeathCommandGlobals()
deathGlobals.playerToken = 0x10002000; deathGlobals.masterVolume = 100
deathGlobals.keyboardToken = scene.camera!.inputToken
var fades: [ClawSceneActorCall] = [], primaryCalls = 0, actorPasses = 0
let frozenAmmo = (player.runtime.privateWords.28,player.runtime.privateWords.29,player.runtime.privateWords.30)
let renderCount = scene.rendering!.frameCount, presentCount = scene.frameRuntime!.presentationCount
let savedGameTime = scene.gameTime
var clockProfile = ClawPlayerDeathCommandGlobals()
scene.captureDeathTiming(&clockProfile)
clockProfile.clock.countdown = 123; clockProfile.clock.countdownReload = 321; clockProfile.clock.pacedFrameStart = 999
scene.publishDeathTiming(clockProfile)
let respawn = ClawNativeRespawn(heap: heap, applicationToken: appToken, globals: deathGlobals, host: scene.actorHost,
    hooks: .init(playerPrimary: { actor in
        precondition(actor == 0x10002000 && scene.snapshotActor(actor)!.primary.7 == 23)
        primaryCalls += 1
        var call = ClawSceneActorCall(); call.function = 0x415df0; call.argumentCount = 1; call.arguments.0 = actor
        _ = scene.actorHost.call!(scene.actorHost.context,call)
        return scene.fault == 0 && player.runtime.logicState == 24
    }, actorFrame: { container, refresh in
        precondition(container == scene.containerToken && refresh == 1); actorPasses += 1
        return scene.actorFrame(container: container, refresh: refresh)
    }, service: { call in
        switch call.function {
        case 0x4d2000,0x4d1fd0,0x4cb9b0,ClawNativeFrame.presentFunction:
            return scene.actorHost.call!(scene.actorHost.context,call)
        case 0x48fae0,0x48fbe0:
            fades.append(call); return 0 // Explicit fade-request transport, no simulated sleep/frames.
        case 0x4061b0:
            guard let name = clawOriginalResourceNames[call.arguments.0] else { return nil }
            return player.audio?.resolve(name: name)?.resourceToken ?? 0
        case 0x4208e0:
            return player.audio?.play(resource: call.receiver,volume: call.arguments.0) ?? 0
        default: return nil
        }
    }, captureTiming: { value in scene.captureDeathTiming(&value) }, publishTiming: { value in
        scene.publishDeathTiming(value)
        var clock = value.clock
        withUnsafeBytes(of: &clock) { UnsafeMutableRawPointer(heap.lookup(0x541328,words:5)!).copyMemory(from:$0.baseAddress!,byteCount:20) }
    }, importPlayer: { precondition(scene.importPlayerFromHeap()) }))
let transferred = player.drainPendingCommands()
precondition(transferred == [0x803a] && respawn.consume(commands: transferred).isEmpty)
precondition(respawn.fault == 0 && respawn.unresolvedServices.isEmpty && primaryCalls == 1 && actorPasses == 2)
precondition(player.runtime.logicState == 24 && player.runtime.privateWords.18 == 100 && player.runtime.actor.67 == 100)
precondition(player.x == 689 && player.y == 4730 && player.runtime.privateWords.6 == 0)
precondition(player.runtime.privateWords.31 == 2 && player.runtime.privateWords.32 == 1)
precondition(player.runtime.privateWords.28 == frozenAmmo.0 && player.runtime.privateWords.29 == frozenAmmo.1 && player.runtime.privateWords.30 == frozenAmmo.2)
precondition(player.runtime.privateWords.72 == 20000 && heap.lookup(0x10005000,words:78)![72] == 20000)
precondition(scene.gameTime == savedGameTime && scene.currentClockSnapshot.deltaMilliseconds == 0 && scene.currentClockSnapshot.pacedFrameStart == 0 && scene.currentClockSnapshot.countdown == 123 && scene.currentClockSnapshot.countdownReload == 321)
precondition(scene.animationDelta == 0 && scene.rendering!.frameCount == renderCount + 1 && scene.frameRuntime!.presentationCount == presentCount + 1)
precondition(heap.lookup(dormant,words:128)![2] & 0x10000 != 0)
let ordered = respawn.events.map(\.function).filter { [UInt32(0x415df0),0x4d51f0,0x4d2000,0x4d1fd0,0x4c8fc0,0x4cb9b0,ClawNativeFrame.presentFunction].contains($0) }
precondition(ordered == [0x415df0,0x4d51f0,0x4d2000,0x4d1fd0,0x4c8fc0,0x4d2000,0x4d1fd0,0x4c8fc0,0x4cb9b0,ClawNativeFrame.presentFunction])
precondition(fades.count == 2 && fades[0].function == 0x48fae0 && fades[0].arguments.2 == 1250 && fades[1].function == 0x48fbe0 && fades[1].arguments.2 == 1000 && fades[1].arguments.3 == 500)
let resumedX = player.x
for index in 0..<10 {
    now &+= 16
    scene.advance(now: now,delta:16,accumulated:savedGameTime+UInt32(index+1)*16,held:0x02000000,pressed:index == 0 ? 0x02000000 : 0)
}
precondition(player.x > resumedX && player.runtime.logicState == 8 && scene.fault == 0 && player.failure == nil)
precondition(player.drainPendingCommands().isEmpty && respawn.consumedCommands == [0x803a])
print("PASS realLevel1 queued803a→source controller cleanup→original primary23→two plane/frame(refresh1) passes→render/present→clock reset→native walking continuation; retained world/ammo/lives/deaths")
