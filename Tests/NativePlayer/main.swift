import Foundation
import Darwin

setbuf(stdout, nil)

let root = URL(fileURLWithPath: CommandLine.arguments[1])
if CommandLine.arguments.contains("--snapshot-adapters-only") {
    do {
        let directory = URL(fileURLWithPath: ProcessInfo.processInfo.environment["CLAW_NATIVE_CHECK_DIR"] ?? "work/native-player-check")
            .appendingPathComponent("snapshot-adapters", isDirectory: true)
        try verifySnapshotAdapters(root: root, directory: directory, relaunch: CommandLine.arguments.contains("--relaunch"))
    } catch { print("FAIL snapshot adapters", error); exit(1) }
    exit(0)
}
if CommandLine.arguments.contains("--snapshot-bindings-only") {
    do {
        let directory = URL(fileURLWithPath: ProcessInfo.processInfo.environment["CLAW_NATIVE_CHECK_DIR"] ?? "work/native-player-check")
            .appendingPathComponent("snapshot-bindings", isDirectory: true)
        try verifySnapshotCanonicalBindings(root: root, directory: directory, relaunch: CommandLine.arguments.contains("--relaunch"))
    }
    catch { print("FAIL snapshot canonical bindings", error); exit(1) }
    exit(0)
}
if CommandLine.arguments.contains("--snapshot-actors-only") {
    do {
        let directory = URL(fileURLWithPath: ProcessInfo.processInfo.environment["CLAW_NATIVE_CHECK_DIR"] ?? "work/native-player-check")
            .appendingPathComponent("snapshot-actors", isDirectory: true)
        try verifySnapshotDynamicActors(root: root, directory: directory, relaunch: CommandLine.arguments.contains("--relaunch"))
    } catch { print("FAIL snapshot actors", error); exit(1) }
    exit(0)
}
if CommandLine.arguments.contains("--snapshot-owners-only") {
    do {
        let directory = URL(fileURLWithPath: ProcessInfo.processInfo.environment["CLAW_NATIVE_CHECK_DIR"] ?? "work/native-player-check")
            .appendingPathComponent("snapshot-owners", isDirectory: true)
        try verifySnapshotInfrastructure(root: root, directory: directory, relaunch: CommandLine.arguments.contains("--relaunch"))
    } catch { print("FAIL snapshot infrastructure", error); exit(1) }
    exit(0)
}
if CommandLine.arguments.contains("--snapshot-player-only") {
    do { try verifySnapshotPlayer(root: root) }
    catch { print("FAIL snapshot player", error); exit(1) }
    exit(0)
}
if CommandLine.arguments.contains("--raw-actor-only") {
    try verifyNativeRawActor()
    exit(0)
}
if CommandLine.arguments.contains("--raw-pid-only") {
    try verifyNativeRawPID()
    exit(0)
}
if CommandLine.arguments.contains("--diagnostic-routes-only") {
    try verifyNativeDiagnosticRoutes()
    exit(0)
}
if CommandLine.arguments.contains("--window-input-only") {
    let path = ProcessInfo.processInfo.environment["CLAW_NATIVE_INPUT_LITERALS"]!
    let raw = try JSONDecoder().decode([String: [UInt8]].self, from: Data(contentsOf: URL(fileURLWithPath: path)))
    let literals = Dictionary(uniqueKeysWithValues: raw.map { (UInt32($0.key, radix: 16)!, Data($0.value)) })
    try verifyNativeWindowInputRoutes(root: root, literals: literals)
    exit(0)
}
// Keep this focused entry ahead of all Level 1 and player asset loading.
if CommandLine.arguments.contains("--menu-base-only") || CommandLine.arguments.contains("--menu-interface-only") {
    let path = ProcessInfo.processInfo.environment["CLAW_NATIVE_MENU_LITERALS"]!
    let raw = try JSONDecoder().decode([String:[UInt8]].self,from:Data(contentsOf:URL(fileURLWithPath:path)))
    let literals = Dictionary(uniqueKeysWithValues:raw.map{(UInt32($0.key,radix:16)!,Data($0.value))})
    if CommandLine.arguments.contains("--menu-interface-only") {try verifyNativeMenuInterface(root:root,literals:literals)}
    else {try verifyNativeMenuBase(root:root,literals:literals)}
    exit(0)
}
if let option = CommandLine.arguments.firstIndex(of: "--level") {
    guard option + 1 < CommandLine.arguments.count,
          let level = UInt32(CommandLine.arguments[option + 1]), (1...14).contains(level) else {
        print("FAIL level must be in 1...14"); exit(2)
    }
    let selected = try ClawLevelScene(root: root, level: level)
    if CommandLine.arguments.contains("--world-only") {
        print("PASS Level \(level) world", selected.layers.count, "planes; all visible tiles resolved using its own palette")
        exit(0)
    }
    let player = try ClawNativePlayer(world: selected.world,
        assets: ClawPlayerAssets(root: root, level: level), level: level)
    let runtime = ClawNativeScene(player: player, clock: { 1000 })
    try runtime.loadRecoveredObjects(world: selected.world, root: root, level: level)
    let records = selected.world.planes.reduce(0) { $0 + $1.objects.count }
    print("LEVEL LOAD", level, "planes", selected.layers.count, "WWD objects", records,
          "uninstantiated", runtime.uninstantiatedObjectCount,
          "missing logics", runtime.uninstantiatedLogics.sorted { $0.key < $1.key },
          "fault", runtime.fault, "unresolved", runtime.unresolvedDependencies.sorted())
    guard runtime.uninstantiatedObjectCount == 0, runtime.fault == 0,
          runtime.unresolvedDependencies.isEmpty, player.unresolvedDependencies.isEmpty,
          player.failure == nil else { print("FAIL Level \(level) has unresolved object dependencies"); exit(1) }
    print("PASS Level \(level) world and every placed object loaded with no unresolved dependency; gameplay acceptance is separate")
    exit(0)
}
let scene = try ClawLevelScene(root: root)
let assets = try ClawPlayerAssets(root: root)
func verifyNativeSharedRandom() {
    let heap = ClawTokenHeap(),random:ClawNativeRandom
    random = ClawNativeRandom(heap:heap)
    precondition(random.initialized && random.fault == 0)
    let token = random.threadToken,thread = random.heap.lookup(token,words:29)!
    precondition(thread[0] != 0 && thread[1] == .max && thread[5] == 1 && thread[20] == 0x5312e8)
    let initial = Array(UnsafeBufferPointer(start:thread,count:29))
    random.call(0x4a3040,arguments:[111567])
    // Values/final raw state captured by unchanged original instructions in
    // work/crt-random-agent/retail-random-golden.json (pinned v1.0 SHA).
    let golden:[UInt32] = [3921,30214,25191,24688,28355,29877,12690,10896,7619,8915,19477,27053,15550,6193,16211,14125]
    for (index,expected) in golden.enumerated() {
        precondition(random.threadToken == token && random.seedPointer == thread.advanced(by:5))
        let actual = index%2 == 0 ? random.call(0x4a3050) : claw_world_loot_next_random(random.seedPointer)
        precondition(actual == expected)
    }
    precondition(thread[5] == 925729567)
    for index in 0..<29 where index != 5 { precondition(thread[index] == initial[index]) }
    random.call(0x4a7e40,arguments:[0]);precondition(random.heap.lookup(token,words:1) == nil)
    let fresh = random.threadToken;precondition(fresh != token && random.seedPointer?.pointee == 1)
    precondition(random.fault == 0 && random.unresolved.isEmpty)
    print("PASS native shared CRT: actual29-word TLS object → source srand →16 original-executed golden outputs interleaved with WorldLoot alias → preserved fields → source cleanup/lazy reallocation; startup ordering outside fixture")
}
verifyNativeSharedRandom()
func verifyNativeDiskSave() throws {
    let directory = URL(fileURLWithPath:"work/native-save-check/"+UUID().uuidString,isDirectory:true)
    let heap = ClawTokenHeap(),random = ClawNativeRandom(heap:heap)
    let save = try ClawNativeSave(heap:heap,random:random,storageDirectory:directory)
    let record = save.playerRecord
    precondition(record != 0 && heap.lookup(record,words:2450)![0] == 0x50feac)
    precondition(!FileManager.default.fileExists(atPath:save.saveURL.path))
    var globals = ClawCheckpointGlobals(),result:UInt32 = 0
    let host = ClawSceneActorHost(context:Unmanaged.passUnretained(heap).toOpaque(),lookup:{user,token,words in
        guard let user else { return nil };return Unmanaged<ClawTokenHeap>.fromOpaque(user).takeUnretainedValue().lookup(token,words:words)
    },allocate:nil,free:nil,call:nil,readClock:nil)
    withUnsafeMutablePointer(to:&globals){g in
        var ctx = ClawCheckpointContext(scene:host,globals:g,composeAnimation:0,composeContactBinding:0,composeSave:0,composeSaveCache:1,fault:0)
        let packet = heap.allocate(bytes:176),p = heap.lookup(packet,words:44)!
        for level:UInt32 in 0..<15 { for kind:UInt32 in 1...3 {
            for index in 0..<44 { p[index] = 0 }
            // Declared complete44-word source-cache input fixture; original
            // cache write owns the flags and all45 actual record destinations.
            let quantity = level*3+kind
            p[1] = 100+quantity;p[2] = 200+quantity;p[4] = quantity*100;p[10] = quantity
            p[21] = quantity*100;p[27] = quantity;p[37] = 60+kind;p[38] = 10+level;p[41] = 3
            let args:[UInt32] = [level,packet,kind]
            let done = args.withUnsafeBufferPointer{claw_checkpoint_entry(0x49a860,record,$0.baseAddress,3,&ctx,nil,nil,&result)}
            precondition(done == 1 && result == 1 && ctx.fault == 0)
        }}
    }
    let original = Data(bytes:heap.lookup(record+4,words:2449)!,count:0x2644)
    let beforeDraws = random.calls[0x4a3050] ?? 0
    precondition(save.entry(0x49bbc0) == 1 && save.fault == 0 && save.physicalWrites == 2)
    precondition((random.calls[0x4a3050] ?? 0) == beforeDraws+3)
    let disk = try Data(contentsOf:save.saveURL)
    precondition(disk.count == 32+0x2644 && disk.suffix(0x2644) != original)
    let otherHeap = ClawTokenHeap(),otherRandom = ClawNativeRandom(heap:otherHeap)
    let loaded = try ClawNativeSave(heap:otherHeap,random:otherRandom,storageDirectory:directory)
    let restored = loaded.playerRecord
    precondition(restored != 0 && loaded.physicalReads == 2 && loaded.fault == 0 && loaded.unresolved.isEmpty)
    precondition(Data(bytes:otherHeap.lookup(restored+4,words:2449)!,count:0x2644) == original)
    precondition(loaded.entry(0x49a8f0,receiver:restored) == 1)
    let evidence = URL(fileURLWithPath:"work/native-save-check/latest-CLAW.USR")
    try disk.write(to:evidence)
    try original.write(to:URL(fileURLWithPath:"work/native-save-check/latest-player-payload.bin"))
    precondition(save.fault == 0 && save.unresolved.isEmpty && random.fault == 0)
    print("PASS native physical disk: source default Player2450words → all45 original checkpoint-cache writes → whole writer/shared RNG/encrypted9828bytes → fresh heap/source reader → byte-identical2449-word payload and valid scores; CString/ASCII/path/file transports explicit")
}
if CommandLine.arguments.contains("--save-only") { try verifyNativeDiskSave();exit(0) }
func verifyNativeSaveSeedBoundary() throws {
    let emptyDirectory = URL(fileURLWithPath:"work/native-save-seed-check/empty-"+UUID().uuidString,isDirectory:true)
    let savedDirectory = URL(fileURLWithPath:"work/native-save-seed-check/saved-"+UUID().uuidString,isDirectory:true)
    try FileManager.default.createDirectory(at:savedDirectory,withIntermediateDirectories:true)
    try Data(contentsOf:URL(fileURLWithPath:"work/native-save-check/latest-CLAW.USR")).write(to:savedDirectory.appendingPathComponent("CLAW.USR"))
    let first = ClawNativeScene(player:try ClawNativePlayer(world:scene.world,assets:assets),clock:{1000})
    let second = ClawNativeScene(player:try ClawNativePlayer(world:scene.world,assets:assets),clock:{1000})
    try first.loadRecoveredObjects(world:scene.world,root:root,saveDirectory:emptyDirectory)
    try second.loadRecoveredObjects(world:scene.world,root:root,saveDirectory:savedDirectory)
    precondition(first.saves!.physicalReads == 0 && second.saves!.physicalReads == 2)
    precondition(first.random.seedPointer!.pointee == second.random.seedPointer!.pointee)
    precondition(second.random.calls[0x4a3040]! == first.random.calls[0x4a3040]!+2)
    for _ in 0..<16 { precondition(first.nextRandom() == second.nextRandom()) }
    print("PASS native save-before-level RNG order: source file decode consumes shared RNG; later recovered level reseed yields identical post-load native stream for absent/existing files; wider retail startup draw order separate")
}
if CommandLine.arguments.contains("--save-seed-only") { try verifyNativeDiskSave();try verifyNativeSaveSeedBoundary();exit(0) }
func verifyNativeSuperCheckpointStartup() throws {
    let player = try ClawNativePlayer(world:scene.world,assets:assets)
    var now:UInt32 = 1000
    let runtime = ClawNativeScene(player:player,clock:{now})
    try runtime.loadRecoveredObjects(world:scene.world,root:root)
    let records = runtime.checkpoints!.originalRecords.values.filter{$0.primary.4 != 0x422ef0}.sorted{$0.token<$1.token}
    precondition(records.count == 2 && runtime.uninstantiatedObjectCount == 0 && runtime.checkpoints!.tokens.count == 9)
    for original in records {
        var visitor = player.sceneSnapshot(),physics = player.runtime.physics
        // Suppress contact only for this startup fixture; ordinary source
        // scanner contact/save is verified by the separate retained fixture.
        visitor.actor.19 = original.actor.19 &- 180;visitor.actor.20 = original.actor.20
        visitor.actor.52 = 0;visitor.actor.53 = 0;visitor.primary.7 = 24
        physics.velocity.0 = 0;physics.velocity.1 = 0
        player.acceptSceneSnapshot(visitor,physics:physics)
        runtime.camera!.entry(0x42d5f0,receiver:0x60003000,argument0:original.actor.19,argument1:original.actor.20)
        for _ in 0..<4 { now &+= 16;runtime.advance(now:now,delta:16,accumulated:now-1000,held:0,pressed:0) }
        if runtime.fault != 0 { print("SUPER STARTUP FAULT",runtime.fault,runtime.unresolvedDependencies,runtime.checkpoints!.fault,runtime.checkpoints!.missingSpans,runtime.checkpoints!.unresolved) }
        precondition(runtime.fault == 0 && runtime.checkpoints!.fault == 0)
        let current = runtime.snapshotActor(original.token)!
        precondition(runtime.checkpoints!.initialized.contains(original.token) && current.primary.7 == 5)
        precondition(current.actor.52 == 0x800 && current.actor.54 == 2 && current.contact.4 == 0x4231a0)
    }
    precondition(!FileManager.default.fileExists(atPath:runtime.saves!.saveURL.path) && runtime.checkpoints!.contacted.isEmpty)
    print("PASS both actual supercheckpoint records: original grid activation → bound4231a0/contact type/bounds → retained startup callbacks; all1479 WWD records admitted; placement/type0/mask0 are synthetic, save contact separate")
}
if CommandLine.arguments.contains("--super-startup-only") { try verifyNativeSuperCheckpointStartup();exit(0) }
func verifyNativePistolLaunch() throws {
    for facing:UInt32 in 0...1 {
        let player = try ClawNativePlayer(world:scene.world,assets:assets)
        var now:UInt32 = 1000
        let runtime = ClawNativeScene(player:player,clock:{now})
        try runtime.loadRecoveredObjects(world:scene.world,root:root)
        precondition(player.runtime.privateWords.12 == 1 && player.runtime.privateWords.28 == 10)
        func step(_ held:UInt32 = 0,_ pressed:UInt32 = 0) {
            now &+= 16;runtime.advance(now:now,delta:16,accumulated:now-1000,held:held,pressed:pressed)
            if runtime.fault != 0 { print("PISTOL FAULT",runtime.fault,runtime.unresolvedDependencies,runtime.projectiles!.fault,runtime.projectiles!.unresolved,player.unresolvedDependencies,player.failure as Any) }
            precondition(runtime.fault == 0 && runtime.projectiles!.fault == 0 && player.unresolvedDependencies.isEmpty)
        }
        let direction:UInt32 = facing == 0 ? 0x01000000 : 0x02000000
        step(direction,direction);step(direction)
        for _ in 0..<3 { step() }
        precondition(player.runtime.privateWords.0 == facing)
        step(0x40,0x40)
        var frames = 0
        while runtime.projectiles!.tokens.isEmpty && frames < 90 { step();frames += 1 }
        let component = runtime.projectiles!
        precondition(component.tokens.count == 1 && player.runtime.privateWords.28 == 9)
        let token = component.tokens.first!,created = runtime.snapshotActor(token)!
        print("PISTOL LAUNCH",facing,frames,created.primary.7,created.actor.19,created.actor.20,created.actor.82,created.actor.65,component.unresolved)
        precondition(created.actor.65 == 8 && created.actor.52 == 0x20 && created.actor.53 == 4)
        precondition(created.actor.82 == (facing == 0 ? UInt32(bitPattern:-700) : 700))
        precondition(created.primary.46 == player.runtime.privateWords.58)
        precondition(component.creationArguments[token]![5] == 0x40000)
        // Original scheduler may initialize this newly inserted actor in the
        // same pass; all launch writes were committed before it could do so.
        for _ in 0..<4 { step() }
        precondition(component.initialized.contains(token))
        let active = runtime.snapshotActor(token)!
        precondition(active.primary.7 == 2001 && active.actor.93 != 0)
        let privateToken = active.primary.6
        precondition(runtime.heap.lookup(privateToken,words:84) != nil && runtime.heap.lookup(privateToken,words:85) == nil)
        var iterations = 0
        while runtime.heap.lookup(token,words:1) != nil && iterations < 400 { step();iterations += 1 }
        precondition(runtime.heap.lookup(token,words:1) == nil && runtime.heap.lookup(privateToken,words:1) == nil && !component.tokens.contains(token))
        print("PASS native Pistol source input/actual CLAW ANI marker2 → deferred named creator/full launch writes/ammo/repeat → whole original84-word constructor/FALLING → ordinary collision or hit → source scheduler/private cleanup; facing",facing,"frames",iterations,"source compiler/registry/resource/physical transports explicit")
    }
}
if CommandLine.arguments.contains("--pistol-only") { try verifyNativePistolLaunch();exit(0) }
func verifyNativeDynamiteLaunch() throws {
    let player = try ClawNativePlayer(world:scene.world,assets:assets)
    var now:UInt32 = 1000
    let runtime = ClawNativeScene(player:player,clock:{now})
    try runtime.loadRecoveredObjects(world:scene.world,root:root)
    func step(_ held:UInt32 = 0,_ pressed:UInt32 = 0) {
        now &+= 16;runtime.advance(now:now,delta:16,accumulated:now-1000,held:held,pressed:pressed)
        if runtime.fault != 0 { print("DYNAMITE FAULT",runtime.fault,runtime.unresolvedDependencies,runtime.projectiles!.fault,runtime.projectiles!.unresolved,player.unresolvedDependencies,player.failure as Any) }
        precondition(runtime.fault == 0 && runtime.projectiles!.fault == 0 && player.unresolvedDependencies.isEmpty)
    }
    for _ in 0..<3 { step() }
    step(0x100,0x100)
    for _ in 0..<48 { step(0x100) }
    for _ in 0..<100 where runtime.projectiles!.tokens.isEmpty { step() }
    let component = runtime.projectiles!
    precondition(component.tokens.count == 1 && player.runtime.privateWords.30 == 2)
    let token = component.tokens.first!,born = runtime.snapshotActor(token)!
    print("DYNAMITE LAUNCH",born.primary.7,born.actor.86,born.actor.65,player.runtime.privateWords.64)
    precondition(born.actor.65 == 15 && born.actor.86 > 0 && born.actor.86 <= 200)
    precondition(component.creationArguments[token]![5] == 0x40000)
    var explosion = false,marker = false,privateToken:UInt32 = 0,steps = 0
    while let current = runtime.snapshotActor(token),steps < 300 {
        if current.primary.6 != 0 { privateToken = current.primary.6 }
        if current.primary.7 == 2002 { explosion = true }
        if privateToken != 0,let raw = runtime.heap.lookup(privateToken,words:98),raw[0x180/4] != 0 { marker = true }
        step();steps += 1
    }
    precondition(component.initialized.contains(token) && privateToken != 0 && explosion && marker)
    precondition(runtime.heap.lookup(token,words:1) == nil && runtime.heap.lookup(privateToken,words:1) == nil && !component.tokens.contains(token))
    precondition((runtime.effects?.actors.count ?? 0) > 0 || runtime.effects?.events.contains(where:{$0.name == "GlitterBaby"}) == true)
    print("PASS native Dynamite real spawn/input/select/held charge/release/actual CLAW ANI marker2 → deferred source creator/full98-word constructor → ordinary retained bounce/fuse/EXPLODING marker/shake → actual GlitterBaby and source scheduler/private cleanup; physical/resource transports explicit, clock fixture16ms")
}
if CommandLine.arguments.contains("--dynamite-only") { try verifyNativeDynamiteLaunch();exit(0) }
func verifyNativeMagicLaunch() throws {
    let player = try ClawNativePlayer(world:scene.world,assets:assets)
    var now:UInt32 = 1000
    let runtime = ClawNativeScene(player:player,clock:{now})
    try runtime.loadRecoveredObjects(world:scene.world,root:root)
    let app = runtime.heap.lookup(runtime.ownerIdentity,words:2)![1]
    precondition(runtime.heap.lookup(app,words:77)![0x124/4] == 1)
    func step(_ held:UInt32 = 0,_ pressed:UInt32 = 0) {
        now &+= 16;runtime.advance(now:now,delta:16,accumulated:now-1000,held:held,pressed:pressed)
        if runtime.fault != 0 || runtime.flares!.fault != 0 { print("MAGIC FAULT",runtime.fault,runtime.unresolvedDependencies,runtime.projectiles!.fault,runtime.projectiles!.unresolved,runtime.flares!.fault,runtime.flares!.unresolved,runtime.flares!.missingSpans,runtime.flares!.failure as Any,player.unresolvedDependencies,player.failure as Any) }
        precondition(runtime.fault == 0 && runtime.projectiles!.fault == 0 && runtime.flares!.fault == 0 && player.unresolvedDependencies.isEmpty)
    }
    for _ in 0..<3 { step() }
    step(0x80,0x80)
    for _ in 0..<100 where runtime.projectiles!.tokens.isEmpty { step() }
    let component = runtime.projectiles!
    precondition(component.tokens.count == 1 && player.runtime.privateWords.29 == 4)
    let token = component.tokens.first!
    for _ in 0..<4 { step() }
    let current = runtime.snapshotActor(token)!,privateToken = current.primary.6
    let raw = runtime.heap.lookup(privateToken,words:86)!
    precondition(component.initialized.contains(token) && raw[0x150/4] == 2)
    let flare = raw[0x154/4]
    precondition(flare != 0 && runtime.flares!.tokens.contains(flare) && runtime.flares!.initialized.contains(flare))
    let light = runtime.snapshotActor(flare)!,lightPrivate = light.primary.6
    precondition(runtime.heap.lookup(lightPrivate,words:19) != nil && runtime.heap.lookup(lightPrivate,words:20) == nil)
    precondition(light.primary.7 == 2000 && light.actor.52 == 1 && light.actor.100 != 0)
    let image = runtime.heap.lookup(light.actor.93,words:13)!
    let compressed = runtime.heap.lookup(image[12],words:10)!
    precondition(compressed[0x14/4] == 2 && compressed[0x1c/4] == runtime.palettes!.tables[0])
    precondition(current.actor.65 == 25 && current.actor.52 == 0x2000000)
    let initialBabyCount = runtime.effects!.events.filter{$0.name == "GlitterBaby"}.count
    var steps = 0,retained = 0
    while runtime.snapshotActor(token) != nil,steps < 400 {
        //410d60 places the child from private physics coordinates before the
        //source post-update advances the parent. Preserve that frame ordering.
        let physics = runtime.heap.lookup(privateToken,words:86)!
        func position(_ offset:Int) -> UInt32 {
            let bits = UInt64(physics[offset/4]) | UInt64(physics[offset/4+1]) << 32
            return UInt32(bitPattern:Int32(Double(bitPattern:bits).rounded(.towardZero)))
        }
        let expectedX = position(104),expectedY = position(112)
        step();steps += 1
        if runtime.snapshotActor(token) != nil,let child = runtime.snapshotActor(flare) {
            precondition(expectedX == child.actor.19 && expectedY == child.actor.20)
            retained += 1
        }
    }
    for _ in 0..<3 { step() }
    precondition(retained > 0 && runtime.effects!.events.filter{$0.name == "GlitterBaby"}.count > initialBabyCount)
    precondition(runtime.heap.lookup(token,words:1) == nil && runtime.heap.lookup(privateToken,words:1) == nil)
    precondition(runtime.heap.lookup(flare,words:1) == nil && runtime.heap.lookup(lightPrivate,words:1) == nil)
    precondition((runtime.rendering!.effectWrites[2] ?? 0) > 0)
    print("PASS native Magic real spawn/input/actual CLAW ANI marker2 → full86-word source constructor/default graphics gate → actual19-word Flare/FSM/double ANI selection/live LIGHT table/indexed source lighting writes → retained parent placement/GlitterBaby RNG → source parent/child cleanup; physical DD/palette presentation remains transport, clock16ms")
}
if CommandLine.arguments.contains("--magic-only") { try verifyNativeMagicLaunch();exit(0) }
func verifyNativeDuckRanged() throws {
    let down:UInt32 = 0x08000000
    for (mask,helper,ammoIndex,expectedAmmo) in [(UInt32(0x40),UInt32(0x41c9f0),28,9),(0x80,0x41cab0,29,4),(0x100,0x41cb80,30,2)] {
        let player = try ClawNativePlayer(world:scene.world,assets:assets)
        var now:UInt32 = 1000
        let runtime = ClawNativeScene(player:player,clock:{now})
        try runtime.loadRecoveredObjects(world:scene.world,root:root)
        let component = runtime.projectiles!
        func step(_ held:UInt32 = down,_ pressed:UInt32 = 0) {
            now &+= 16;runtime.advance(now:now,delta:16,accumulated:now-1000,held:held,pressed:pressed)
            if runtime.fault != 0 { print("DUCK RANGED FAULT",String(helper,radix:16),runtime.fault,runtime.unresolvedDependencies,component.fault,component.unresolved,player.unresolvedDependencies,player.failure as Any) }
            precondition(runtime.fault == 0 && component.fault == 0 && player.unresolvedDependencies.isEmpty)
        }
        for _ in 0..<3 { step(0) }
        step(down,down)
        for _ in 0..<4 { step() }
        precondition(player.runtime.logicState == 26)
        step(down|mask,mask)
        if mask == 0x100 { for _ in 0..<48 { step(down|mask) } }
        for _ in 0..<100 where component.tokens.isEmpty { step() }
        print("DUCK RANGED LAUNCH",String(helper,radix:16),player.runtime.logicState,player.sequence,component.tokens.count,component.emitCounts)
        precondition(component.tokens.count == 1 && component.emitCounts[helper] == 1)
        let ammo = withUnsafeBytes(of:player.runtime.privateWords){$0.bindMemory(to:UInt32.self)[ammoIndex]}
        precondition(ammo == UInt32(expectedAmmo))
        let token = component.tokens.first!
        for _ in 0..<4 { step() }
        precondition(component.initialized.contains(token))
        let priv = runtime.snapshotActor(token)!.primary.6
        var frames = 0
        while runtime.snapshotActor(token) != nil && frames < 400 { step();frames += 1 }
        for _ in 0..<3 { step() }
        precondition(runtime.heap.lookup(token,words:1) == nil && runtime.heap.lookup(priv,words:1) == nil)
        precondition(player.runtime.logicState == 26)
        step(0)
        for _ in 0..<6 { step(0) }
        precondition(player.runtime.logicState == 24)
        print("PASS native duck weapon",String(helper,radix:16),"real spawn/input/actual ANI → complete original cdecl emit with live actor/private/global borrow → ammo/source full controller → retained flight or fuse/effects/collision → scheduler cleanup → input release/stand;16ms clock")
    }
}
if CommandLine.arguments.contains("--duck-ranged-only") { try verifyNativeDuckRanged();exit(0) }
func verifyNativeRangedRepeat() throws {
    for down:UInt32 in [0,0x08000000] {
        for mask:UInt32 in [0x40,0x80] {
            let player = try ClawNativePlayer(world:scene.world,assets:assets)
            var now:UInt32 = 1000
            let runtime = ClawNativeScene(player:player,clock:{now})
            try runtime.loadRecoveredObjects(world:scene.world,root:root)
            let component = runtime.projectiles!
            func step(_ held:UInt32 = 0,_ pressed:UInt32 = 0) {
                now &+= 16;runtime.advance(now:now,delta:16,accumulated:now-1000,held:held,pressed:pressed)
                if runtime.fault != 0 { print("REPEAT FAULT",down,mask,runtime.fault,runtime.unresolvedDependencies,component.unresolved,player.unresolvedDependencies,player.failure as Any) }
                precondition(runtime.fault == 0 && component.fault == 0 && player.unresolvedDependencies.isEmpty)
            }
            for _ in 0..<3 { step() }
            if down != 0 { step(down,down);for _ in 0..<4 { step(down) } }
            let initialRepeat = player.runtime.privateWords.58
            var frames = 0
            //Alternating pressed/released physical-key samples elect the source
            //marker3 repeat. No private-word or ANI-pointer injection is used.
            while component.creationArguments.count < 3 && frames < 300 {
                let fire = frames%2 == 0
                step(down|(fire ? mask : 0),fire ? mask : 0);frames += 1
            }
            print("RANGED REPEAT",down,mask,frames,component.creationArguments.count,runtime.animationCounts[0x420970] ?? 0,player.runtime.privateWords.58)
            precondition(component.creationArguments.count == 3)
            let seekCount = runtime.animationCounts[0x420970] ?? 0
            //Retail PISTOL/DUCKPISTOL contain marker3 repeat windows. Magic
            //sequences end after marker2 and reselect through ordinary input.
            precondition(mask == 0x40 ? seekCount >= 2 : seekCount == 0)
            precondition(player.runtime.privateWords.58 >= initialRepeat+2)
            let ammo = mask == 0x40 ? player.runtime.privateWords.28 : player.runtime.privateWords.29
            precondition(ammo == (mask == 0x40 ? 7 : 2))
            for _ in 0..<350 { step(down) }
            precondition(component.tokens.isEmpty && runtime.flares!.tokens.isEmpty)
            precondition(component.initialized.count == 3)
            if down != 0 { step();for _ in 0..<6 { step() } }
            precondition(player.runtime.logicState == 24)
            print("PASS native",down == 0 ? "standing" : "duck","weapon",mask,"alternating input →",mask == 0x40 ? "actual ANI marker3/source420970 seek" : "actual ANI end/input reselect","→ source repeat counter/three launches/ammo changes → ordinary flight/collision/effect and whole cleanup;16ms clock")
        }
    }
}
if CommandLine.arguments.contains("--ranged-repeat-only") { try verifyNativeRangedRepeat();exit(0) }
func verifyNativePalette() throws {
    let player = try ClawNativePlayer(world:scene.world,assets:assets)
    let runtime = ClawNativeScene(player:player,clock:{1000})
    try runtime.loadRecoveredObjects(world:scene.world,root:root)
    let palettes = runtime.palettes!,tables = palettes.tables
    let resources = runtime.paletteResources!,resourceWrapper = resources.wrapperToken,backendToken = resources.backendToken
    let parent = runtime.heap.lookup(runtime.sceneIdentity,words:12)!,owner = runtime.heap.lookup(runtime.ownerIdentity,words:478)!
    precondition(resources.fault == 0 && resources.unresolved.isEmpty && parent[6] == resources.managerToken && parent[7] == resources.backendManagerToken)
    precondition(owner[0x2c/4] == resourceWrapper && runtime.heap.lookup(resourceWrapper,words:5)![0] == 0x513d78)
    let backend = runtime.heap.lookup(backendToken,words:14)!,physical = backend[1],base = backend[3],backup = backend[4]
    let originalPAL = try Data(contentsOf:root.appendingPathComponent("LEVEL1/PALETTES/MAIN.PAL"))
    var expectedEntries = Data()
    for i in 0..<256 { expectedEntries.append(contentsOf:[originalPAL[i*3],originalPAL[i*3+1],originalPAL[i*3+2],0]) }
    precondition(Data(bytes:owner.advanced(by:0x360/4),count:1024) == expectedEntries)
    precondition(Data(bytes:runtime.heap.lookup(base,words:256)!,count:1024) == expectedEntries && Data(bytes:runtime.heap.lookup(backup,words:256)!,count:1024) == expectedEntries)
    precondition(resources.physicalEntries(physical) == expectedEntries && resources.attachedPalette == physical)
    precondition(resources.calls[0x6e100014] == 1 && resources.calls[0x6e100110] == 2 && resources.calls[0x6e10027c] == 1)
    precondition(resources.resourceLocks.values.allSatisfy{$0 == 0})
    precondition(resources.graphicsCalls[0x546850] == 1 && resources.graphicsCalls[0x6e110050] == 1 && resources.graphicsCalls[0x6e110020] == 1 && resources.graphicsCalls[0x6e11002c] == 1 && resources.graphicsCalls[0x6e110054] == 1 && resources.graphicsCalls[0x6e110030] == 1)
    precondition(resources.graphicsState.cooperativeHolder == resources.backendManagerToken && runtime.heap.lookup(0x541374,words:1)!.pointee == resources.backendManagerToken)
    precondition(runtime.heap.lookup(0x541398,words:1)!.pointee == 0 && runtime.heap.lookup(0x541378,words:5)![1] == 0)
    precondition(Array(UnsafeBufferPointer(start:runtime.heap.lookup(0x54135c,words:6)!,count:6)) == [.max,.max,.max,8,8,8])
    let modes = runtime.heap.lookup(resources.backendManagerToken+0x3f0,words:5)!
    precondition(modes[0] == 0x51079c && modes[2] == 1)
    let modeRecord = runtime.heap.lookup(runtime.heap.lookup(modes[1],words:1)!.pointee,words:27)!
    precondition(modeRecord[0] == 108 && modeRecord[2] == 480 && modeRecord[3] == 640 && modeRecord[21] == 8)
    let modeAllocations = [modes[1],runtime.heap.lookup(modes[1],words:1)!.pointee]
    let display = resources.display!
    let sourceParent = runtime.heap.lookup(runtime.sceneIdentity,words:15)!,holder = runtime.heap.lookup(display.holderToken,words:7)!
    precondition(sourceParent[0] == 0x513ab8 && sourceParent[1] == display.holderToken && sourceParent[12] == runtime.sceneIdentity && sourceParent[14] == 0)
    precondition(holder[0] == 0x513c68 && holder[3] == runtime.sceneIdentity)
    let primary = runtime.heap.lookup(display.primaryToken,words:12)!,back = runtime.heap.lookup(display.backToken,words:13)!,spare = runtime.heap.lookup(display.spareToken,words:13)!
    precondition(primary[0] == 0x5138d8 && primary[4] == 640 && primary[5] == 480 && primary[6] == 8)
    precondition(back[0] == 0x50e8e4 && back[1] == 1 && spare[0] == 0x50e8e4 && spare[1] == 2)
    precondition(back[4] == 640 && back[5] == 480 && spare[4] == 640 && spare[5] == 480 && runtime.rendering!.targetToken == display.backToken)
    let surfaces = [primary[11],back[11],spare[11]]
    precondition(Set(surfaces).count == 3 && surfaces.allSatisfy{runtime.heap.lookup($0,words:47) != nil})
    precondition(runtime.heap.lookup(surfaces[1],words:47)![12] == runtime.rendering!.indexedToken && runtime.heap.lookup(surfaces[1],words:47)![30]&1 == 1)
    let sharedDD = runtime.heap.lookup(surfaces[1],words:47)![2],ddTable = runtime.heap.lookup(runtime.heap.lookup(sharedDD,words:1)!.pointee,words:33)!
    precondition(ddTable[11] == ClawNativeDisplay.flip && ddTable[17] == ClawNativeStatusMessages.getDC && ddTable[26] == ClawNativeStatusMessages.releaseDC && ddTable[2] == ClawNativeDisplay.release)
    let surfaceList = runtime.heap.lookup(resources.backendManagerToken+0x3b8,words:7)!
    precondition(surfaceList[0] == 0x51000c && surfaceList[3] == 3)
    let sourceObjects = [display.holderToken,display.primaryToken,display.backToken,display.spareToken]+surfaces
    let allSourceAllocations = resources.sourceAllocations.union(display.sourceAllocations)
    precondition((sourceObjects+modeAllocations).allSatisfy{allSourceAllocations.contains($0)})
    precondition(display.calls[ClawNativeDisplay.create] == 2 && display.calls[ClawNativeDisplay.attached] == 1 && display.calls[ClawNativeDisplay.describe] == 3)
    let paletteList = runtime.heap.lookup(resources.backendManagerToken+0x3d4,words:7)!
    precondition(paletteList[0] == 0x51000c && paletteList[3] == 1 && backend[0] != 0)
    _ = resources.entry(0x4bb910,receiver:backendToken,args:[0,256,17,34,51,0])
    runtime.advance(now:1016,delta:16,accumulated:16,held:0,pressed:0)
    precondition(runtime.fault == 0 && resources.fault == 0 && runtime.rendering!.palettePresentations == 1)
    let colored = runtime.rendering!.commands.last!.image
    let bytes = colored.dataProvider!.data! as Data
    precondition(colored.width == 640 && colored.height == 480 && bytes.count == 640*480*4)
    for i in stride(from:0,to:bytes.count,by:4) { precondition(bytes[i] == 17 && bytes[i+1] == 34 && bytes[i+2] == 51 && bytes[i+3] == 255) }
    //Restore every source base entry, including its reserved byte. A zero-count
    //source update also reaches the physical call with no entry buffer.
    let restored = runtime.heap.allocate(bytes:1024)
    expectedEntries.withUnsafeBytes{UnsafeMutableRawPointer(runtime.heap.lookup(restored,words:256)!).copyMemory(from:$0.baseAddress!,byteCount:1024)}
    _ = resources.entry(0x4bb800,receiver:backendToken,args:[0,0,restored,0])
    _ = resources.entry(0x4bb800,receiver:backendToken,args:[0,256,restored,0]);runtime.heap.free(restored)
    runtime.advance(now:1032,delta:16,accumulated:32,held:0,pressed:0)
    precondition(runtime.fault == 0 && resources.fault == 0 && runtime.rendering!.palettePresentations == 1 && resources.physicalEntries(physical) == expectedEntries)
    precondition(resources.calls[0x6e110058] == 2) //Both source4bb800 updates elect live cooperative device wait.
    precondition(palettes.fault == 0 && palettes.unresolved.isEmpty && tables.count == 3 && tables.allSatisfy{$0 != 0})
    precondition(runtime.heap.lookup(palettes.managerToken,words:6)![3] == 3)
    var payloads:[UInt32] = []
    for (i,name) in ["LIGHT","AVERAGE"].enumerated() {
        let source = try Data(contentsOf:root.appendingPathComponent("LEVEL1/PALETTES/"+name+".CLT"))
        let table = runtime.heap.lookup(tables[i],words:3)!
        precondition(table[0] == 1 && table[1] == source.count-4)
        let payload = runtime.heap.lookup(table[2],words:table[1]/4)!
        precondition(Data(bytes:payload,count:Int(table[1])) == source.dropFirst(4))
        payloads.append(table[2])
    }
    let rank = runtime.heap.lookup(tables[2],words:3)!,data = runtime.heap.lookup(rank[2],words:128)!
    precondition(rank[0] == 1 && rank[1] == 512);payloads.append(rank[2])
    let order = UnsafeRawBufferPointer(start:data,count:512)
    precondition(Set(order.prefix(256)).count == 256)
    for i in 0..<256 { precondition(order[256+Int(order[i])] == UInt8(i)) }
    let effects = runtime.rendering!.sourceImageGlobals.pointee.compressedEffect
    precondition(effects.0 == tables[1] && effects.1 == tables[1] && effects.2 == 0 && effects.3 == tables[2])
    palettes.shutdown()
    precondition(palettes.fault == 0 && palettes.tables == [0,0,0])
    precondition(runtime.heap.lookup(palettes.managerToken,words:1) == nil)
    precondition((tables+payloads).allSatisfy{runtime.heap.lookup($0,words:1) == nil})
    resources.shutdown()
    precondition(resources.fault == 0 && resources.unresolved.isEmpty && resources.sourceAllocations.isEmpty)
    precondition([resourceWrapper,backendToken,base,backup,resources.managerToken,resources.backendManagerToken,physical].allSatisfy{runtime.heap.lookup($0,words:1) == nil})
    precondition(owner[0x2c/4] == 0 && parent[6] == 0 && parent[7] == 0)
    precondition(resources.graphicsCalls[0x6e11004c] == 1 && resources.graphicsCalls[0x6e110008] == 1 && runtime.heap.lookup(0x541374,words:1)!.pointee == 0)
    precondition(modeAllocations.allSatisfy{runtime.heap.lookup($0,words:1) == nil})
    precondition(display.fault == 0 && display.unresolved.isEmpty && display.sourceAllocations.isEmpty && sourceObjects.allSatisfy{runtime.heap.lookup($0,words:1) == nil} && parent[1] == 0)
    print("PASS native whole source60-byte scene ctor/28-byte holder/48+52+52 wrappers/3actual188-byte surfaces/back indexed storage/source surface-list ownership+cleanup")
    print("PASS native graphics source4bc220/true640x480x8 coop11 profile → actual global mode CArray/source descriptor enumeration+sort → source empty indexed masks/aliases → PAL cooperative wait58 → whole4bc1b0/4bc100 modes/lists/device teardown; logical window/DD memory descriptors remain explicit transports")
    print("PASS native palette source manager ctor/activate → whole4d4420/PAL source expansion/CreatePalette44/source list/owner GetEntries prefix/backup/display attachment → whole46e160/actual LIGHT+AVERAGE CLTs/source rank+installers → source palette/list/wrapper removal +light cleanup; physical DD/file/map/CMemFile and outer manager lifetimes are explicit transports")
}
func verifyNativeDisplayAutomaticRelease() throws {
    weak var sceneRef:ClawNativeScene?,paletteRef:ClawNativePaletteResources?
    var retainedDisplay:ClawNativeDisplay?,retainedHeap:ClawTokenHeap?,sourceTokens:[UInt32] = []
    do {
        let scene = try ClawLevelScene(root:root),assets = try ClawPlayerAssets(root:root)
        let player = try ClawNativePlayer(world:scene.world,assets:assets)
        let runtime = ClawNativeScene(player:player,clock:{1000})
        try runtime.loadRecoveredObjects(world:scene.world,root:root)
        sceneRef = runtime;paletteRef = runtime.paletteResources
        retainedDisplay = runtime.paletteResources!.display;retainedHeap = runtime.heap
        sourceTokens = Array(runtime.paletteResources!.sourceAllocations.union(retainedDisplay!.sourceAllocations))
        sourceTokens += [runtime.paletteResources!.managerToken,runtime.paletteResources!.backendManagerToken]
    }
    precondition(sceneRef == nil && paletteRef == nil)
    precondition(retainedDisplay!.fault == 0 && retainedDisplay!.unresolved.isEmpty && retainedDisplay!.sourceAllocations.isEmpty)
    precondition(sourceTokens.allSatisfy{retainedHeap!.lookup($0,words:1) == nil})
    let parent = retainedHeap!.lookup(0x10001000,words:15)!
    precondition(parent[1] == 0 && parent[6] == 0 && parent[7] == 0)
    precondition(retainedDisplay!.entry(0x4cf730,receiver:retainedDisplay!.holderToken) == 0 && retainedDisplay!.fault == 3)
    print("PASS automatic scene/PAL owner release → original holder/surface/list/device cleanup while destructor context is live → all source allocations gone; retained closed display rejects later entry without touching freed owner")
}
if CommandLine.arguments.contains("--source-display-lifetime-only") {try verifyNativePalette();try verifyNativeDisplayAutomaticRelease();exit(0)}
if CommandLine.arguments.contains("--palette-only") { try verifyNativePalette();exit(0) }
func verifyNativePaletteFade() throws {
    let player = try ClawNativePlayer(world:scene.world,assets:assets)
    let runtime = ClawNativeScene(player:player,clock:{1000})
    try runtime.loadRecoveredObjects(world:scene.world,root:root)
    let palettes = runtime.paletteResources!,heap = runtime.heap
    let backend = heap.lookup(palettes.backendToken,words:14)!,physical = backend[1],backup = backend[4]
    let baseline = palettes.physicalEntries(physical)!,allocations = palettes.sourceAllocations
    let target = heap.allocate(bytes:1024)
    var targetData = baseline
    for i in 0..<256 {for k in 0..<3 {targetData[i*4+k] = UInt8((i*13+k*71+33)%256)};targetData[i*4+3] = 7}
    targetData.withUnsafeBytes {UnsafeMutableRawPointer(heap.lookup(target,words:256)!).copyMemory(from:$0.baseAddress!,byteCount:1024)}
    //Keep original menu1000ms/Story750ms durations. Clock stepping is an
    //explicit headless profile, not the application's ordinary wall clock.
    for duration:UInt32 in [1000,750] {
        var tick:UInt32 = 1000,samples:[Data] = []
        _ = palettes.fadeEntry(0x4bbd90,args:[0,4,target,duration],clock:{let now = tick;tick &+= 250;return now},observe:{start,count,data in
            precondition(start == 0 && count == 4);samples.append(data)
        })
        precondition(palettes.fadeFault == 0 && palettes.fault == 0 && palettes.sourceAllocations == allocations)
        let elapsed:[Int] = duration == 1000 ? [10,250,500,750]:[10,250,500]
        precondition(samples.count == elapsed.count+1)
        for (sample,time) in zip(samples,elapsed) {
            var expected = baseline
            for i in 0..<4 {for k in 0..<3 {
                let old = Int(baseline[i*4+k]),to = Int(targetData[i*4+k])
                expected[i*4+k] = UInt8(old+(to-old)*time/Int(duration))
            }};precondition(sample == expected)
        }
        var final = baseline;final.replaceSubrange(0..<16,with:targetData.prefix(16))
        precondition(samples.last == final && palettes.physicalEntries(physical) == final && Data(bytes:heap.lookup(backend[3],words:256)!,count:1024) == final)
        _ = palettes.fadeEntry(0x4bb8c0,args:[0])
        precondition(palettes.fadeFault == 0 && palettes.physicalEntries(physical) == baseline && Data(bytes:heap.lookup(backup,words:256)!,count:1024) == baseline)
    }
    let clocks = palettes.calls[0x546df0],sets = palettes.calls[0x6e100118]
    precondition(backend[13] == 0 && palettes.fadeEntry(0x4bbb70) == 0)
    _ = palettes.fadeEntry(0x4bbd20)
    precondition(palettes.fadeFault == 0 && palettes.calls[0x546df0] == clocks && palettes.calls[0x6e100118] == sets)
    //Zero duration still performs the source initial clock read, final copy,
    //and snapshot destruction using the ordinary monotonic transport.
    _ = palettes.fadeEntry(0x4bbd90,args:[0,4,target,0]);precondition(palettes.fadeFault == 0 && palettes.calls[0x546df0] == (clocks ?? 0)+1)
    _ = palettes.fadeEntry(0x4bb8c0,args:[0]);heap.free(target)
    runtime.advance(now:1016,delta:16,accumulated:16,held:0,pressed:0)
    precondition(runtime.fault == 0 && palettes.physicalEntries(physical) == baseline && palettes.fadeDiagnostics.isEmpty)
    palettes.shutdown();precondition(palettes.sourceAllocations.isEmpty && palettes.fault == 0 && palettes.unresolved.isEmpty)
    print("PASS native whole blocking palette fades at original1000/750ms → stepped-clock integer RGB/reserved bytes/physical range updates/final whole-entry copy → source snapshot free/backup restoration/inactive scheduler → ordinary monotonic zero-duration call → frame/full graph cleanup; live menu/Story election and sensory identity remain pending")
}
if CommandLine.arguments.contains("--palette-fade-only") {try verifyNativePaletteFade();exit(0)}
func verifyNativePCX() throws {
    let factory = CommandLine.arguments.contains("--pcx-factory-only")
    struct Profile:Decodable {
        var index:Int,path:String,width:UInt32,height:UInt32,planes:UInt32,padding:UInt32,inputBytes:UInt32,fileBytes:UInt32
    }
    let original = URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
    let capture = original.appendingPathComponent("work/root-pcx-spans")
    let profiles = try JSONDecoder().decode([Profile].self,from:Data(contentsOf:capture.appendingPathComponent("profiles.json")))
    let player = try ClawNativePlayer(world:scene.world,assets:assets)
    let runtime = ClawNativeScene(player:player,clock:{1000})
    try runtime.loadRecoveredObjects(world:scene.world,root:root)
    let resources = runtime.paletteResources!,display = resources.display!
    let sourceList = runtime.heap.lookup(resources.backendManagerToken+0x3b8,words:7)!
    let originalOwners = display.sourceAllocations
    var count = 0,stateScreens = 0
    for p in profiles where p.planes == 1 {
        precondition(p.inputBytes == p.fileBytes)
        let raw = try Data(contentsOf:original.appendingPathComponent(p.path))
        let expected = try Data(contentsOf:capture.appendingPathComponent("\(p.index).surface"))
        let input = runtime.heap.allocate(bytes:UInt32(raw.count))
        raw.withUnsafeBytes{UnsafeMutableRawPointer(runtime.heap.lookup(input,words:UInt32((raw.count+3)/4))!).copyMemory(from:$0.baseAddress!,byteCount:raw.count)}
        let surface = factory ? display.createPCX(data:input,byteCount:UInt32(raw.count)) : display.createSurface(width:p.width,height:p.height)
        precondition(surface != 0 && display.fault == 0 && sourceList[3] == 4,"PCX \(p.path) surface\(surface) fault\(display.fault)/\(display.lastPCXFault) list\(sourceList[3]) unresolved\(display.unresolved)")
        if !factory {precondition(display.decodePCX(surface:surface,data:input,byteCount:UInt32(raw.count)) == 1 && display.lastPCXFault == 0)}
        guard let pixels = display.surfacePixels(surface) else {preconditionFailure("Native source PCX pixels")}
        precondition(pixels.width == p.width && pixels.height == p.height && pixels.stride == p.width)
        for y in 0..<Int(p.height) {
            let start = y*Int(p.width+p.padding)
            precondition(pixels.bytes[y*Int(p.width)..<(y+1)*Int(p.width)] == expected[start..<start+Int(p.width)])
        }
        //Retain and decode again through source Lock/Unlock on the same surface.
        if factory {
            let repeated = display.createPCX(data:input,byteCount:UInt32(raw.count))
            precondition(repeated != 0 && repeated != surface && sourceList[3] == 5 && display.surfacePixels(repeated)!.bytes == pixels.bytes)
            display.removeSurface(repeated)
        }else {precondition(display.decodePCX(surface:surface,data:input,byteCount:UInt32(raw.count)) == 1 && display.surfacePixels(surface)!.bytes == pixels.bytes)}
        display.removeSurface(surface);runtime.heap.free(input)
        precondition(runtime.heap.lookup(surface,words:1) == nil && sourceList[3] == 3)
        count += 1;if p.path.contains("/STATES/") {stateScreens += 1}
        if count%40 == 0 {print("Native PCX profiles",count,"of313")}
    }
    precondition(count == 313 && display.pcxLoads == 626 && display.sourceAllocations == originalOwners)
    //The heap rounds words upward; the file callback must still reject a read
    //at its exact130-byte end, preserving the original two-pixel prefix.
    var shortFile = Data(repeating:0,count:130)
    shortFile[8] = 3;shortFile[65] = 1;shortFile[128] = 7;shortFile[129] = 8
    let shortToken = runtime.heap.allocate(bytes:130),shortSurface = display.createSurface(width:4,height:1)
    shortFile.withUnsafeBytes{UnsafeMutableRawPointer(runtime.heap.lookup(shortToken,words:33)!).copyMemory(from:$0.baseAddress!,byteCount:130)}
    precondition(display.decodePCX(surface:shortSurface,data:shortToken,byteCount:130) == 0 && display.lastPCXFault == 1)
    precondition(display.surfacePixels(shortSurface)!.bytes == Data([7,8,0,0]))
    display.removeSurface(shortSurface);runtime.heap.free(shortToken)
    precondition(sourceList[3] == 3 && display.sourceAllocations == originalOwners && display.fault == 0)
    if factory {
        shortFile[65] = 0
        let rejected = runtime.heap.allocate(bytes:130)
        shortFile.withUnsafeBytes{UnsafeMutableRawPointer(runtime.heap.lookup(rejected,words:33)!).copyMemory(from:$0.baseAddress!,byteCount:130)}
        precondition(display.createPCX(data:rejected,byteCount:130) == 0 && display.lastPCXFault == 0)
        runtime.heap.free(rejected)
        precondition(sourceList[3] == 3 && display.sourceAllocations == originalOwners)
    }
    runtime.advance(now:1016,delta:16,accumulated:16,held:0,pressed:0)
    precondition(runtime.fault == 0 && display.fault == 0 && resources.fault == 0)
    resources.shutdown()
    precondition(display.sourceAllocations.isEmpty && display.fault == 0 && display.unresolved.isEmpty)
    if factory {
        print("PASS native PCX factory313 indexed files/\(stateScreens) state images → whole4bc520/4bf9c0(type2)/4be810 header-derived dimensions/actual188-byte construction → source list insertion/DD descriptor/Lock/Unlock/every original pixel → distinct repeated factory objects → source removal/destruction and rejected-plane cleanup → exact130-byte direct-load EOF prefix → normal frame/full graph cleanup; live image-controller/menu/story and three-plane/16-bit transport remain pending")
    }else {print("PASS native PCX313 exact retail indexed files including\(stateScreens) state images → whole source surface factory/dynamic memory descriptors/list → whole4bebc0 and Lock/Unlock → every original-captured visible pixel/repeated decode → exact130-byte EOF prefix despite word padding → source remove/destruction → normal frame and full graph cleanup; no live menu/story dispatch or three-plane transport acceptance claimed")}
}
if CommandLine.arguments.contains("--pcx-only") {try verifyNativePCX();exit(0)}
if CommandLine.arguments.contains("--pcx-factory-only") {try verifyNativePCX();exit(0)}
func verifyNativeSurfaceCopies() throws {
    let player = try ClawNativePlayer(world:scene.world,assets:assets)
    let runtime = ClawNativeScene(player:player,clock:{1000})
    try runtime.loadRecoveredObjects(world:scene.world,root:root)
    let display = runtime.paletteResources!.display!,heap = runtime.heap
    let src = display.createSurface(width:8,height:6),dst = display.createSurface(width:16,height:12)
    let sw = heap.lookup(src,words:47)!,dw = heap.lookup(dst,words:47)!
    let sp = UnsafeMutableRawPointer(heap.lookup(sw[12],words:12)!).assumingMemoryBound(to:UInt8.self)
    let dp = UnsafeMutableRawPointer(heap.lookup(dw[12],words:48)!).assumingMemoryBound(to:UInt8.self)
    for i in 0..<48 {sp[i] = UInt8(i%11)}
    let sr:[UInt32] = [1,1,7,5],dr:[UInt32] = [3,4,9,8]
    func reset(){dp.update(repeating:0x79,count:192)}
    func expected(_ fx:UInt32,key:ClosedRange<UInt32>? = nil)->Data {
        var bytes = Data(repeating:0x79,count:192)
        for y in 0..<4 {for x in 0..<6 {
            let pixel = sp[(1+(fx&4 == 0 ? y:3-y))*8+1+(fx&2 == 0 ? x:5-x)]
            if key?.contains(UInt32(pixel)) == true {continue}
            bytes[(4+y)*16+3+x] = pixel
        }};return bytes
    }
    reset()
    precondition(display.surfaceOperation(0x4b9d80,surface:dst,args:[3,4,src,0,0x10],source:sr) == 0 && display.lastSurfaceFault == 0)
    precondition(display.surfacePixels(dst)!.bytes == expected(0))
    _ = display.surfaceOperation(0x4b9990,surface:src,args:[0])
    precondition(display.lastSurfaceFault == 0 && sw[46] == 1 && display.calls[ClawNativeDisplay.setColorKey] == 1)
    for fx:UInt32 in [0,2,4,6] {
        reset();runtime.rendering!.sourceImageGlobals.pointee.directDrawFX.1 = fx
        precondition(display.surfaceOperation(0x4b9ce0,surface:dst,args:[0,src,0,0x01008800,0x543108],destination:dr,source:sr) == 0 && display.lastSurfaceFault == 0)
        precondition(display.surfacePixels(dst)!.bytes == expected(fx,key:0...0))
    }
    reset();precondition(display.surfaceOperation(0x4b9950,surface:src,args:[9,0],source:[2,5]) == 0)
    precondition(display.surfaceOperation(0x4b9d80,surface:dst,args:[3,4,src,0,0x11],source:sr) == 0)
    precondition(display.surfacePixels(dst)!.bytes == expected(0,key:2...5))
    reset();_ = display.surfaceOperation(0x4b9990,surface:src,args:[UInt32.max])
    precondition(display.lastSurfaceFault == 0 && sw[46] == 0)
    precondition(display.surfaceOperation(0x4b9d80,surface:dst,args:[3,4,src,0,0x10],source:sr) == 0 && display.surfacePixels(dst)!.bytes == expected(0))
    //Raw heap rectangle pointers and null/full rectangles retain their original
    //meaning; local buffers are not the only accepted transport.
    let rect = heap.allocate(bytes:16);sr.withUnsafeBufferPointer {heap.lookup(rect,words:4)!.update(from:$0.baseAddress!,count:4)}
    reset();precondition(display.surfaceOperation(0x4b9d80,surface:dst,args:[3,4,src,rect,0x10]) == 0 && display.surfacePixels(dst)!.bytes == expected(0));heap.free(rect)
    let missing = display.createSurface(width:8,height:6)
    reset();precondition(display.surfaceOperation(0x4b9ce0,surface:dst,args:[0,missing,0,0x8000,0],destination:dr,source:sr) == 0x887600d7)
    precondition(display.lastSurfaceFault == 0 && display.surfacePixels(dst)!.bytes == Data(repeating:0x79,count:192) && display.surfaceDiagnostics.last == [0x5324dc,0x48e,0x887600d7])
    reset();precondition(display.surfaceOperation(0x4b9d80,surface:dst,args:[13,4,src,0,0x10],source:sr) == 0x88760096)
    precondition(display.lastSurfaceFault == 0 && display.surfaceDiagnostics.last == [0x5324dc,0x4b8,0x88760096] && display.surfacePixels(dst)!.bytes == Data(repeating:0x79,count:192))
    //Overlapping same-surface copy uses a declared native memory snapshot.
    var before = Data(bytes:sp,count:48)
    precondition(display.surfaceOperation(0x4b9d80,surface:src,args:[2,2,src,0,0x10],source:[0,0,4,3]) == 0)
    for y in 0..<3 {for x in 0..<4 {before[(2+y)*8+2+x] = UInt8((y*8+x)%11)}}
    precondition(display.surfacePixels(src)!.bytes == before)
    for t in [src,dst,missing] {display.removeSurface(t)}
    runtime.paletteResources!.shutdown()
    precondition(display.sourceAllocations.isEmpty && display.fault == 0 && display.unresolved.isEmpty)
    print("PASS native whole surface Blt/Fast/key wrappers → physical indexed exact/plain/key/range/all4mirrors/raw+localRECT/overlap pixels → source diagnosticHRESULTs preserve unchanged output → source surface/list/full graph cleanup; physical raster transport explicit, live actor/menu election remains pending")
}
func verifyNativePIDFactory() throws {
    struct Profile:Decodable {let index:Int,path:String,width:UInt32,height:UInt32,flags:UInt32,fileBytes:UInt32}
    let original = URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
    let capture = original.appendingPathComponent("work/root-native-pid-surfaces")
    let profiles = try JSONDecoder().decode([Profile].self,from:Data(contentsOf:capture.appendingPathComponent("profiles.json")))
    precondition(profiles.count == 6423)
    let player = try ClawNativePlayer(world:scene.world,assets:assets)
    let runtime = ClawNativeScene(player:player,clock:{1000})
    try runtime.loadRecoveredObjects(world:scene.world,root:root)
    let display = runtime.paletteResources!.display!,heap = runtime.heap
    let list = heap.lookup(runtime.paletteResources!.backendManagerToken+0x3b8,words:7)!,baseline = list[3],owners = display.sourceAllocations
    let dst = display.createSurface(width:32,height:24),d = heap.lookup(dst,words:47)!
    let dp = UnsafeMutableRawPointer(heap.lookup(d[12],words:192)!).assumingMemoryBound(to:UInt8.self)
    for (index,p) in profiles.enumerated() {
        let raw = try Data(contentsOf:original.appendingPathComponent(p.path))
        let expected = try Data(contentsOf:capture.appendingPathComponent("\(p.index).surface"))
        precondition(raw.count == p.fileBytes && expected.count == p.width*p.height && p.flags&32 == 0)
        let input = heap.allocate(bytes:UInt32(raw.count))
        raw.withUnsafeBytes {UnsafeMutableRawPointer(heap.lookup(input,words:UInt32((raw.count+3)/4))!).copyMemory(from:$0.baseAddress!,byteCount:raw.count)}
        let surface = display.createPID(data:input,byteCount:UInt32(raw.count))
        precondition(surface != 0 && display.lastPCXFault == 0 && display.lastSurfaceFault == 0 && list[3] == baseline+2,"PID \(p.path) sourceFactory\(surface) fault\(display.lastPCXFault)/\(display.lastSurfaceFault) unresolved\(display.unresolved)")
        precondition(display.surfacePixels(surface)!.bytes == expected && display.surfacePixels(surface)!.width == p.width && display.surfacePixels(surface)!.height == p.height)
        let w = min(Int(p.width),16),h = min(Int(p.height),12)
        dp.update(repeating:0x79,count:768)
        let sourceRect:[UInt32] = [0,0,UInt32(w),UInt32(h)]
        let flags:UInt32 = p.flags&1 == 0 ? 0x10:0x11
        precondition(display.surfaceOperation(0x4b9d80,surface:dst,args:[3,4,surface,0,flags],source:sourceRect) == 0 && display.lastSurfaceFault == 0)
        var copied = Data(repeating:0x79,count:768)
        for y in 0..<h {for x in 0..<w {let pixel = expected[y*Int(p.width)+x];if p.flags&1 != 0 && pixel == 0 {continue};copied[(4+y)*32+3+x] = pixel}}
        precondition(display.surfacePixels(dst)!.bytes == copied)
        display.removeSurface(surface);heap.free(input)
        precondition(list[3] == baseline+1 && display.lastPCXFault == 0 && display.fault == 0)
        if (index+1)%100 == 0 {print("Native PID factories",index+1,"of6423")}
    }
    display.removeSurface(dst)
    precondition(list[3] == baseline && display.sourceAllocations == owners)
    runtime.advance(now:1016,delta:16,accumulated:16,held:0,pressed:0)
    precondition(runtime.fault == 0 && display.fault == 0)
    runtime.paletteResources!.shutdown()
    precondition(display.sourceAllocations.isEmpty && display.unresolved.isEmpty)
    print("PASS native PID factory6423 actual full-disc indexed assets → whole4bc520/4bf9c0(type4)/4bf310/real188-byte surface/descriptors/Lock/Unlock/key/list → every whole-original-captured pixel and source keyed/plainBltFast crop → removal/full graph cleanup; live image-controller/actor/menu election remains pending")
}
func verifyNativeMenuErrorBoundary() -> [[String:Any]] {
    var witnesses:[[String:Any]] = []
    for (latched,windowKind):(UInt32,UInt32) in [(0,0),(0,1),(0,2),(1,1),(7,2)] {
        let heap = ClawTokenHeap(),queue = ClawNativeWindowInputQueue()
        let window = queue.openWindow()
        let app:UInt32 = 0x61010000,receiver:UInt32 = 0x61011000,record:UInt32 = 0x61012000,vt:UInt32 = 0x61013000
        heap.store(token:app,words:3)[2] = receiver
        let bytes = heap.storeBytes(token:receiver,count:0x254)
        bytes.update(repeating:0xa5,count:0x254)
        let data = heap.lookup(receiver,words:0x254/4)!
        data[0] = vt;data[1] = windowKind == 0 ? 0:record;data[0x244/4] = 1;data[0x248/4] = latched
        let w = heap.store(token:record,words:4);w[1] = window;w[3] = windowKind == 2 ? 1:0
        heap.store(token:vt,words:8)[7] = 0x4b90b0
        func snapshot() -> [UInt8] {Array(UnsafeBufferPointer(start:bytes,count:0x254))}
        var posts:[[String:Any]] = []
        let owner = ClawNativeApplicationError(heap:heap,receiver:receiver,postClose:{ id in
            posts.append(["window":id,"state":snapshot()])
            try queue.postClose(window:id)
        })
        let host = ClawNativeCanonicalHost(heap:heap,dependency:{ h,q in owner.service(h,q) })
        var call = ClawCall();call.function = 0x429e10;call.receiver = app;call.argumentCount = 2
        call.arguments.0 = 0x8008;call.arguments.1 = 0x403
        let before = snapshot(),result = host.invoke(call)
        precondition(result.completed && host.fault == nil && owner.faultAddress == 0)
        let after = snapshot()
        precondition(queue.closeRequests.count == posts.count)
        if !posts.isEmpty {precondition(try! queue.takeCloseRequest(window:window))}
        precondition(!(try! queue.takeCloseRequest(window:window)))
        witnesses.append(["receiver":receiver,"application":app,"windowRecord":record,"vtable":vt,
                          "windowKind":windowKind,"window":window,"before":before,"after":after,"posts":posts])
        // The native first-error latch is stable across later reports.
        call.arguments.0 = 0x1234;call.arguments.1 = 0x5678
        precondition(host.invoke(call).completed && snapshot() == after)
        var typeCall = ClawCall();typeCall.function = 0x4c9bd0;typeCall.receiver = receiver
        precondition(host.invoke(typeCall).eax == 5)
        owner.close()
        precondition(!host.invoke(call).completed && host.fault?.address == 0x4b90b0)
        precondition(snapshot() == after)
    }
    // Withhold the error owner and the physical close service independently.
    for missingService in [false,true] {
        let heap = ClawTokenHeap(),app:UInt32 = 0x61010000,receiver:UInt32 = 0x61011000
        heap.store(token:app,words:3)[2] = receiver
        let data = heap.store(token:receiver,words:0x254/4)
        data[0] = 0x61013000;data[1] = 0x61012000;data[0x244/4] = 1
        heap.store(token:0x61013000,words:8)[7] = 0x4b90b0
        heap.store(token:0x61012000,words:4)[1] = 1
        let owner = ClawNativeApplicationError(heap:heap,receiver:receiver,postClose:nil)
        let host = ClawNativeCanonicalHost(heap:heap,dependency:missingService ? { h,q in owner.service(h,q) }:nil)
        var call = ClawCall();call.function = 0x429e10;call.receiver = app;call.argumentCount = 2
        call.arguments.0 = 0x8008;call.arguments.1 = 0x403
        precondition(!host.invoke(call).completed)
        precondition(host.fault?.address == (missingService ? 0x546d50:0x4b90b0))
        precondition(data[0x244/4] == 1 && data[0x24c/4] == 0 && data[0x250/4] == 0)
        precondition(data[0x248/4] == (missingService ? 1:0))
    }
    return witnesses
}

func verifyNativeMenuBase(root:URL,literals:[UInt32:Data]) throws {
    let errorBoundary = verifyNativeMenuErrorBoundary()
    let menu = try ClawNativeMenuBase(root:root,literals:literals)
    let heap = menu.heap,state = heap.lookup(menu.menuToken,words:178)!
    func snapshot(_ token:UInt32,_ bytes:UInt32)->[UInt8] {
        Array(UnsafeBufferPointer(start:heap.lookupBytes(token,count:bytes)!,count:Int(bytes)))
    }
    let constructorBytes = snapshot(menu.menuToken,UInt32(CLAW_STATE_FIVE_BYTES))
    let constructorAllocations = menu.constructorAllocations.map{["token":$0.token,"bytes":$0.bytes,"data":snapshot($0.token,$0.bytes)] as [String:Any]}
    // The actual factory mode-5 body composed with both recovered constructors.
    precondition(state[0] == 0x50c1e4 && state[0x154/4] == 0x50c23c)
    precondition(state[(0x154+60)/4] == 640 && state[(0x154+64)/4] == 480)
    precondition(state[(0x154+72)/4] == 0x513ed8 && state[0x2a8/4] == 1000)
    precondition(Array(UnsafeBufferPointer(start:state.advanced(by:0x27c/4),count:4)) == [480,0,640,0])
    precondition(state[(0x2ac+24)/4] == 10)
    let display = menu.palette!.display!
    let wrappers = [display.primaryToken,display.backToken,display.spareToken]
    precondition(Set(wrappers).count == 3 && !wrappers.contains(0))
    for (index,token) in wrappers.enumerated() {
        let wrapper = heap.lookup(token,words:12)!
        var call = ClawCall();call.function = index == 0 ? 0x4d5720:0x4d4280
        call.receiver = token;call.argumentCount = 3
        call.arguments.0 = wrapper[4];call.arguments.1 = wrapper[5];call.arguments.2 = wrapper[6]
        precondition(menu.menuVirtualService(call) == 1 && menu.fault == 0)
    }
    for token in wrappers {
        let image = heap.lookup(token,words:12)![11]
        let pixels = display.surfacePixels(image)!
        precondition(pixels.bytes.count == 640*480)
    }
    let fill = heap.allocate(bytes:100)
    let effects = heap.lookup(fill,words:25)!
    effects[0] = 100;effects[20] = 0x7b
    let fillTarget = heap.lookup(display.backToken,words:12)![11]
    precondition(display.surfaceOperation(0x4b9ce0,surface:fillTarget,args:[0,0,0,0x01000400,fill]) == 0)
    precondition(display.surfacePixels(fillTarget)!.bytes.allSatisfy{$0 == 0x7b})
    effects[0] = 99
    var invalidFill = ClawSurfaceBlitCall()
    invalidFill.function = ClawNativeDisplay.blt;invalidFill.argumentCount = 6
    invalidFill.arguments = (heap.lookup(fillTarget,words:3)![2],0,0,0,0x01000400,fill,0,0)
    precondition(display.surfaceService(invalidFill) == 0x80070057)
    precondition(display.surfacePixels(fillTarget)!.bytes.allSatisfy{$0 == 0x7b})
    effects[0] = 100;effects[20] = 0
    precondition(display.surfaceOperation(0x4b9ce0,surface:fillTarget,args:[0,0,0,0x01000400,fill]) == 0)
    heap.free(fill)
    // No palette or world is elected by native base setup.
    precondition(menu.palette!.wrapperToken == 0 && heap.lookup(menu.sceneToken,words:15)![9] == 0)
    let managerBefore = snapshot(menu.soundManager,52)
    let applicationBefore = snapshot(menu.applicationToken,UInt32(CLAW_ORIGINAL_APPLICATION_BYTES))
    let callStart = menu.calls.count
    precondition(heap.lookup(menu.applicationToken,words:33)![0x7c/4] == 640)
    precondition(heap.lookup(menu.applicationToken,words:33)![0x80/4] == 480)
    precondition(!menu.initializeBase(level:1,parameter:37))
    precondition(menu.applicationResult == 1)
    precondition(menu.fault != 0 && menu.boundary == 0x4b7cd0, "Unexpected menu boundary \(String(menu.boundary,radix:16)), fault \(menu.fault)")
    precondition(state[8] != 0 && menu.resourceDirectories[state[8]] == root.appendingPathComponent("STATES/MENU").path)
    precondition(menu.resourceDirectories.values.contains(root.appendingPathComponent("STATES/MENU/SOUNDS").path))
    precondition(!menu.calls.contains(0x42a060) && !menu.calls.contains(0x429e10))
    precondition(state[1] == menu.applicationToken && state[2] == menu.resourceRootToken && state[3] == menu.sceneToken)
    precondition(state[5] == 1 && state[6] == 37 && state[7] != 0 && state[0x34/4] == 1)
    precondition(state[0x44/4] == .max && state[0x48/4] == .max)
    precondition(heap.lookup(menu.sceneToken,words:15)![1] == display.holderToken)
    precondition(heap.lookup(0x537b58,words:1)![0] == menu.menuToken)
    precondition(!menu.calls.contains(0x4dcdf0))
    precondition(menu.soundManager != 0 && heap.lookup(menu.sceneToken,words:15)![10] == menu.soundManager)
    precondition(heap.lookup(menu.soundManager,words:13)![12] == 0)
    precondition(menu.soundLoadCount == UInt32(menu.soundResources.count) && menu.soundLoadCount > 0)
    precondition(menu.soundEntries.count == menu.soundResources.count)
    precondition(menu.audio!.playRequests == 0 && menu.audio!.activeVoiceCount == 0)
    precondition(menu.soundEntries.values.allSatisfy{menu.audio!.sceneSoundPCM($0)?.isEmpty == false})
    if let path = ProcessInfo.processInfo.environment["CLAW_NATIVE_MENU_WITNESS"] {
        let witness:[String:Any] = ["errorBoundary":errorBoundary,"menu":menu.menuToken,"application":menu.applicationToken,
            "scene":menu.sceneToken,"resourceRoot":menu.resourceRootToken,"resource":state[7],
            "directories":menu.resourceDirectories.map{["token":$0.key,"path":String($0.value.dropFirst(root.path.count+1))] as [String:Any]},
            "constructor":constructorBytes,"allocations":constructorAllocations,
            "soundManager":menu.soundManager,"managerBefore":managerBefore,
            "audioManager":menu.audio!.managerIdentity,
            "soundCount":menu.soundLoadCount,"soundEvents":menu.soundEvents,
            "resourceBlocks":menu.resourceBlocks.map{["token":$0.token,"data":snapshot($0.token,$0.bytes)] as [String:Any]},
            "soundResources":menu.soundResources.map{["token":$0.key,"path":String($0.value.dropFirst(root.path.count+1))] as [String:Any]},
            "soundEntries":menu.soundEntries.map{["name":$0.key,"owner":heap.lookup($0.value,words:5)![1],"pcm":menu.audio!.sceneSoundPCM($0.value)!] as [String:Any]},
            "applicationBytes":applicationBefore,
            "applicationAfter":snapshot(menu.applicationToken,UInt32(CLAW_ORIGINAL_APPLICATION_BYTES)),
            "applicationResult":menu.applicationResult!,"baseCalls":Array(menu.calls.dropFirst(callStart)).filter{[UInt32(0x6e130000),0x4a3920,0x4b7f20,0x42a000,0x4b68c0,0x4ca440,0x4b7cd0].contains($0)},
            "soundDirectory":menu.resourceDirectories.first{$0.value == root.appendingPathComponent("STATES/MENU/SOUNDS").path}.map{["token":$0.key,"data":snapshot($0.key,76)] as [String:Any]}!,
            "displayDimensions":wrappers.map{Array(UnsafeBufferPointer(start:heap.lookup($0,words:12)!.advanced(by:4),count:2))},
            "bound":snapshot(menu.menuToken,UInt32(CLAW_STATE_FIVE_BYTES)),"boundary":menu.boundary]
        try JSONSerialization.data(withJSONObject:witness,options:[.sortedKeys]).write(to:URL(fileURLWithPath:path))
    }
    // Real missing directories return the original failed-init result, not a
    // fabricated resource token or a successful menu.
    let missingResource = try ClawNativeMenuBase(root:root,literals:literals)
    precondition(!missingResource.initializeBase(level:999999))
    precondition(missingResource.fault == 0 && missingResource.boundary == 0)
    precondition(!missingResource.calls.contains(0x42a000))
    let missingBase = try ClawNativeMenuBase(root:root,literals:literals)
    precondition(!missingBase.initializeBase(level:1,composeBase:false))
    precondition(missingBase.fault != 0 && missingBase.boundary == 0x48f0d0)
    precondition(missingBase.heap.lookup(missingBase.menuToken,words:4)![1] == 0)
    do {
        _ = try ClawNativeMenuBase(root:root,literals:literals,missingOwner:0x4dcc40)
        preconditionFailure("A missing interface constructor must fail menu construction")
    } catch AssetError.invalid(let reason) {precondition(reason.contains("4dcc40"))}
    let missingApplication = try ClawNativeMenuBase(root:root,literals:literals,missingOwner:0x42a000)
    precondition(!missingApplication.initializeBase(level:1))
    precondition(missingApplication.fault != 0 && missingApplication.boundary == 0x42a000)
    precondition(missingApplication.applicationResult == nil)
    precondition(missingApplication.calls.filter{$0 == 0x4b7f20}.count == 1)
    // The admitted resize owner now runs inside menu_application. A real
    // dimension mismatch must reach its scene resize dependency.
    for offset in [0x7c/4,0x80/4] {
        let resize = try ClawNativeMenuBase(root:root,literals:literals)
        resize.heap.lookup(resize.applicationToken,words:33)![offset] -= 1
        precondition(!resize.initializeBase(level:1))
        precondition(resize.fault != 0 && resize.boundary == 0x4cf020,
                     "Unexpected resize boundary \(String(resize.boundary,radix:16)), fault \(resize.fault)")
        precondition(resize.applicationResult == nil && !resize.calls.contains(0x429e10))
        precondition(resize.calls.filter{$0 == 0x4b7f20}.count == 1)
        precondition(!resize.calls.contains(0x4dcdf0))
    }
    // Missing menu and sound directories return the source failure result and
    // never reach the missing sound manager. No assets are copied into controls.
    let temporary = FileManager.default.temporaryDirectory.appendingPathComponent("claw-menu-directories-\(UUID().uuidString)")
    defer {try? FileManager.default.removeItem(at:temporary)}
    try FileManager.default.createDirectory(at:temporary.appendingPathComponent("LEVEL1"),withIntermediateDirectories:true)
    for includeMenu in [false,true] {
        if includeMenu {try FileManager.default.createDirectory(at:temporary.appendingPathComponent("STATES/MENU"),withIntermediateDirectories:true)}
        let missing = try ClawNativeMenuBase(root:temporary,literals:literals)
        precondition(!missing.initializeBase(level:1) && missing.fault == 0 && missing.boundary == 0)
        precondition(!missing.calls.contains(0x4ca440) && !missing.calls.contains(0x4dcdf0))
        precondition(missing.calls.contains(0x4b68c0) == includeMenu)
        missing.shutdown()
        precondition(missing.resourceDirectories.isEmpty)
    }
    for owner:UInt32 in [0x4ca440,0x4ca3b0,0x4c8850,0x4f62a8,0x4f66cc] {
        let missing = try ClawNativeMenuBase(root:root,literals:literals,missingOwner:owner)
        precondition(!missing.initializeBase(level:1) && missing.fault != 0)
        precondition(missing.boundary == owner,"Missing owner masked: \(String(missing.boundary,radix:16)) vs \(String(owner,radix:16))")
        missing.shutdown()
    }
    let disabled = try ClawNativeMenuBase(root:root,literals:literals,audioAvailable:false)
    precondition(disabled.heap.lookup(disabled.soundManager,words:13)![12] == 1)
    precondition(!disabled.initializeBase(level:1) && disabled.boundary == 0x4b7cd0)
    precondition(disabled.soundLoadCount == 0 && disabled.soundEntries.isEmpty && !disabled.soundEvents.contains(0x4ca3b0))
    disabled.shutdown()
    // A rejected real WAV must exercise the entry's actual deleting destructor.
    let badDirectory = temporary.appendingPathComponent("STATES/MENU/SOUNDS")
    try FileManager.default.createDirectory(at:badDirectory,withIntermediateDirectories:true)
    var badWave = try Data(contentsOf:URL(fileURLWithPath:menu.soundResources.values.first!))
    badWave.replaceSubrange(0..<4,with:Data("NOPE".utf8))
    try badWave.write(to:badDirectory.appendingPathComponent("BROKEN.WAV"))
    let rejected = try ClawNativeMenuBase(root:temporary,literals:literals)
    precondition(!rejected.initializeBase(level:1) && rejected.boundary == 0x4b7cd0)
    precondition(rejected.soundLoadCount == 0 && rejected.soundEntries.isEmpty)
    precondition(rejected.soundEvents.contains(0x4c8850) && rejected.soundEvents.contains(0x4c88b0))
    precondition(rejected.audio!.loadedBufferCount == 0)
    rejected.shutdown()
    precondition(rejected.soundCleanupFault == 0 && rejected.soundCleanupRemaining == 0)
    let directoryIdentities = menu.resourceDirectories
    let entryIdentities = menu.soundEntries
    let audio = menu.audio!
    let soundManager = menu.soundManager
    precondition(!menu.initializeBase(level:1,parameter:37) && menu.boundary == 0x4b7cd0)
    precondition(menu.resourceDirectories == directoryIdentities)
    precondition(menu.soundLoadCount == 0 && menu.soundEntries == entryIdentities)
    let cleanupStart = menu.soundEvents.count
    menu.shutdown();menu.shutdown()
    precondition(menu.soundCleanupFault == 0 && menu.soundCleanupRemaining == 0)
    if let path = ProcessInfo.processInfo.environment["CLAW_NATIVE_MENU_WITNESS"] {
        let url = URL(fileURLWithPath:path)
        var witness = try JSONSerialization.jsonObject(with:Data(contentsOf:url)) as! [String:Any]
        witness["cleanupEvents"] = Array(menu.soundEvents.dropFirst(cleanupStart))
        try JSONSerialization.data(withJSONObject:witness,options:[.sortedKeys]).write(to:url)
    }
    precondition(menu.resourceDirectories.isEmpty && directoryIdentities.keys.allSatisfy{heap.lookup($0,words:1) == nil})
    precondition(state[7] == 0 && state[8] == 0)
    precondition(heap.lookup(soundManager,words:1) == nil && entryIdentities.values.allSatisfy{heap.lookup($0,words:1) == nil})
    precondition(audio.loadedBufferCount == 0 && audio.playRequests == 0)
    precondition(!menu.initializeBase(level:1) && menu.fault == 0)
    precondition(display.fault == 0 && display.unresolved.isEmpty && display.sourceAllocations.isEmpty)
    print("PASS native menu base: constructor -> 45ace0/48f0d0/42a000 -> real STATES_MENU/SOUNDS directories; missing menu/sounds and existing owner controls, stable directory identities and cleanup; actual WAV loading and sound cleanup; next exact boundary 4b7cd0 image directory, IFC parsing not reached")
}

func verifyNativeMenuDisplayBoundary() throws {
    let runtime = ClawNativeScene(player:try ClawNativePlayer(world:scene.world,assets:assets),clock:{1000})
    try runtime.loadRecoveredObjects(world:scene.world,root:root)
    let display = runtime.paletteResources!.display!,heap = runtime.heap
    let primary = heap.lookup(display.primaryToken,words:12)![11]
    let back = heap.lookup(display.backToken,words:13)![11]
    let spare = heap.lookup(display.spareToken,words:13)![11]
    let dd = heap.lookup(primary,words:47)![2]
    let method = heap.lookup(heap.lookup(dd,words:1)!.pointee,words:33)![24]
    precondition(method == ClawNativeDisplay.isLost)
    func request(_ f:UInt32,_ receiver:UInt32 = 0,_ arguments:[UInt32] = [])->ClawStateFiveCall {
        var q = ClawStateFiveCall();q.function = f;q.receiver = receiver;q.argumentCount = UInt32(arguments.count)
        withUnsafeMutableBytes(of:&q.arguments){dst in arguments.withUnsafeBytes{dst.copyBytes(from:$0)}}
        return q
    }
    precondition(display.menuDisplayService(request(method,0,[dd])) == 0)
    precondition(display.menuDisplayService(request(method,0,[0])) == 0x80070057)
    precondition(display.menuDisplayService(request(0x4dcdf0)) == nil)
    let child = heap.allocate(bytes:52)
    defer {heap.free(child)}
    var c = ClawStateFiveContext(),out:UInt32 = 0
    c.scene = runtime.actorHost;c.maximumOperations = 1000
    let callback:ClawStateFiveDependency = {c,q,u in
        guard let c,let q,let u else {return 0}
        let display = Unmanaged<ClawNativeDisplay>.fromOpaque(u).takeUnretainedValue()
        guard let result = display.menuDisplayService(q.pointee) else {c.pointee.fault = 1;return 0}
        c.pointee.fault = display.lastSurfaceFault;return result
    }
    func entry(_ f:UInt32,_ args:[UInt32])->UInt32 {
        let done = args.withUnsafeBufferPointer {
            claw_state_five_entry(f,child,$0.baseAddress,UInt32($0.count),&c,callback,Unmanaged.passUnretained(display).toOpaque(),&out)
        }
        precondition(done == 1 && c.fault == 0);return out
    }
    // Construct the recovered menu page base, then attach the existing native
    // back surface. This is a display-boundary fixture, not main-menu startup.
    _ = entry(0x45fde0,[runtime.sceneIdentity,99,0])
    let page = heap.lookup(child,words:13)!
    precondition(page[0] == 0x50e924 && page[1] == 99 && page[3] == runtime.sceneIdentity)
    page[11] = back
    let pixels = heap.lookup(spare,words:47)![12]
    let p = UnsafeMutableRawPointer(heap.lookup(pixels,words:640*480/4)!).assumingMemoryBound(to:UInt8.self)
    for i in 0..<640*480 {p[i] = UInt8(truncatingIfNeeded:i*7+19)}
    let expected = display.surfacePixels(spare)!.bytes
    let copies = display.calls[ClawNativeDisplay.bltFast] ?? 0
    _ = entry(0x45fee0,[display.spareToken])
    precondition(display.calls[ClawNativeDisplay.bltFast] == copies+1)
    precondition(display.surfacePixels(back)!.bytes == expected)
    precondition(display.menuDisplayService(request(0x4b98b0,primary,[0])) == 0)
    precondition(display.surfacePixels(primary)!.bytes == expected)
    precondition(display.lastSurfaceFault == 0 && display.fault == 0 && display.unresolved.isEmpty)
    // A missing platform owner must fail the same recovered copy, not become
    // a successful no-op. The framebuffer must remain unchanged.
    var missing = ClawStateFiveContext();missing.scene = runtime.actorHost
    let args = [display.spareToken]
    let done = args.withUnsafeBufferPointer {claw_state_five_entry(0x45fee0,child,$0.baseAddress,1,&missing,nil,nil,&out)}
    precondition(done == 0 && missing.fault != 0 && display.surfacePixels(back)!.bytes == expected)
    runtime.paletteResources!.shutdown()
    precondition(display.sourceAllocations.isEmpty && display.unresolved.isEmpty && display.fault == 0)
    precondition(display.menuDisplayService(request(method,0,[dd])) == 0x80070057 && display.lastSurfaceFault == 3)
    print("PASS native menu display boundary: recovered page constructor/copy -> native BltFast -> recovered Flip -> exact 640x480 pixels; native IsLost slot, unknown/missing owner and closed-display controls; full main-menu construction remains pending")
}
if CommandLine.arguments.contains("--menu-display-only") {try verifyNativeMenuDisplayBoundary();exit(0)}
if CommandLine.arguments.contains("--surface-only") {try verifyNativeSurfaceCopies();exit(0)}
if CommandLine.arguments.contains("--pid-factory-only") {try verifyNativeSurfaceCopies();try verifyNativePIDFactory();exit(0)}
func verifyNativeSurfaceFlip() throws {
    let player = try ClawNativePlayer(world:scene.world,assets:assets)
    let runtime = ClawNativeScene(player:player,clock:{1000})
    try runtime.loadRecoveredObjects(world:scene.world,root:root)
    let display = runtime.paletteResources!.display!,heap = runtime.heap
    let primary = heap.lookup(display.primaryToken,words:12)![11],back = heap.lookup(display.backToken,words:13)![11],spare = heap.lookup(display.spareToken,words:13)![11]
    let originalIndexed = runtime.rendering!.indexedToken
    for (source,pattern):(UInt32,UInt8) in [(back,31),(spare,79)] {
        let surface = heap.lookup(source,words:47)!,p = UnsafeMutableRawPointer(heap.lookup(surface[12],words:640*480/4)!).assumingMemoryBound(to:UInt8.self)
        for i in 0..<640*480 {p[i] = UInt8(truncatingIfNeeded:i)&+pattern}
        precondition(display.flipSurface(primary,source:source == back ? 0:source) == 0 && display.lastSurfaceFault == 0)
        precondition(display.surfacePixels(primary)!.bytes == display.surfacePixels(source)!.bytes)
        precondition(runtime.rendering!.indexedToken == originalIndexed && heap.lookup(back,words:47)![12] == originalIndexed)
    }
    let small = display.createSurface(width:8,height:6),before = display.surfacePixels(primary)!.bytes
    precondition(display.flipSurface(primary,source:small) == 0x80004001 && display.lastSurfaceFault == 0 && display.surfacePixels(primary)!.bytes == before)
    precondition(display.surfaceDiagnostics.last == [0x5324dc,0x29a,0x80004001])
    display.removeSurface(small);runtime.paletteResources!.shutdown()
    precondition(display.sourceAllocations.isEmpty && display.fault == 0 && display.unresolved.isEmpty)
    print("PASS native whole Flip wrapper → null attached-back/explicit spare full indexed memory presentation copy → retained indexed renderer allocation → rejected size/HRESULT/source diagnostic and unchanged front → whole cleanup; physical memory copy is explicit, hardware swap/live presentation election remain pending")
}
if CommandLine.arguments.contains("--surface-flip-only") {try verifyNativeSurfaceFlip();exit(0)}
func verifyNativeWarpFade() throws {
    let player = try ClawNativePlayer(world:scene.world,assets:assets)
    let runtime = ClawNativeScene(player:player,clock:{1000})
    try runtime.loadRecoveredObjects(world:scene.world,root:root)
    runtime.advance(now:1016,delta:16,accumulated:16,held:0,pressed:0)
    precondition(runtime.fault == 0)
    let pixels = runtime.rendering!.indexedSnapshot
    precondition(pixels.count == 640*480 && Set(pixels).count>1)
    let originalSeed = runtime.random.seedPointer!.pointee
    var physicalTick:UInt32 = 1000
    let warp = ClawNativeWarpFade(heap:runtime.heap,random:runtime.random,clock:{physicalTick &+= 16;return physicalTick})
    warp.setPixels(target:pixels,source:pixels)
    let beforeDraws = runtime.random.calls[0x4a3050,default:0]
    let clear = warp.create(clear:true)
    precondition(clear != 0 && warp.fault == 0 && warp.unresolved.isEmpty)
    precondition(runtime.random.calls[0x4a3050,default:0] == beforeDraws+2000)
    var expectedSeed = originalSeed
    for _ in 0..<2000 {expectedSeed = expectedSeed &* 214013 &+ 2531011}
    precondition(runtime.random.seedPointer!.pointee == expectedSeed)
    precondition(runtime.heap.lookup(clear,words:8023)![0] == 0x514228 && warp.entry(0x4ed5d0,receiver:clear) == 863)
    warp.entry(0x4ed1a0,receiver:clear,args:[400])
    precondition(warp.fault == 0 && warp.targetBytes != pixels && warp.targetBytes.contains(0) && warp.sourceBytes == pixels)
    warp.entry(0x4ec9c0,receiver:clear,args:[1450,0,0])
    precondition(warp.fault == 0 && warp.targetBytes.allSatisfy{$0 == 0} && warp.sourceBytes == pixels && warp.clockReads>0)
    warp.remove(clear)
    precondition(runtime.heap.lookup(clear,words:1) == nil && runtime.heap.lookup(warp.managerToken,words:10)![6] == 0)
    let copy = warp.create(clear:false)
    precondition(copy != 0 && warp.fault == 0)
    warp.entry(0x4ed1a0,receiver:copy,args:[400])
    precondition(warp.targetBytes != pixels && warp.targetBytes.contains(where:{$0 != 0}))
    warp.entry(0x4ec9c0,receiver:copy,args:[1450,0,0])
    precondition(warp.fault == 0 && warp.unresolved.isEmpty && warp.targetBytes == pixels && warp.sourceBytes == pixels)
    precondition(warp.locks[warp.targetSurface] == warp.unlocks[warp.targetSurface] && warp.locks[warp.sourceSurface] == warp.unlocks[warp.sourceSurface])
    warp.remove(copy);warp.shutdown()
    precondition(warp.fault == 0 && warp.sourceAllocations.isEmpty)
    precondition([copy,warp.managerToken,warp.targetSurface,warp.sourceSurface,warp.targetPixels,warp.sourcePixels].allSatisfy{runtime.heap.lookup($0,words:1) == nil})
    runtime.advance(now:1032,delta:16,accumulated:32,held:0,pressed:0)
    precondition(runtime.fault == 0 && runtime.random.fault == 0)
    print("PASS native warp fader actual indexed Level1 frame → type2 source factory/8023-word object/shared2000 CRT draws/gradient383,max863 → partial+source clock runner clear → source deletion → partial+runner copy byte-identical → source array cleanup → ordinary scene resumes; surface profile/spill row and16ms clock trajectory declared, WM805c/native presentation remain pending")
}
if CommandLine.arguments.contains("--warp-fade-only") { try verifyNativeWarpFade();exit(0) }
func verifyNativeElemental() throws {
    var totalRetained = 0
    for (power,callback,bit) in [(UInt32(0x26b8),UInt32(0x410100),UInt32(0x40000)),(0x26b9,0x4101c0,0x100000),(0x26ba,0x410280,0x80000)] {
        for duck in [false,true] {
            for facing:UInt32 in [0,1] {
                let player = try ClawNativePlayer(world:scene.world,assets:assets)
                var now:UInt32 = 1000
                let runtime = ClawNativeScene(player:player,clock:{now})
                try runtime.loadRecoveredObjects(world:scene.world,root:root)
                let component = runtime.projectiles!,down:UInt32 = duck ? 0x08000000 : 0
                func step(_ held:UInt32 = 0,_ pressed:UInt32 = 0) {
                    now &+= 16;runtime.advance(now:now,delta:16,accumulated:now-1000,held:held,pressed:pressed)
                    if runtime.fault != 0 { print("ELEMENTAL FAULT",power,duck,facing,runtime.fault,runtime.unresolvedDependencies,component.fault,component.unresolved,runtime.flares!.fault,runtime.flares!.failure as Any,player.unresolvedDependencies,player.failure as Any,runtime.rendering!.failure as Any) }
                    precondition(runtime.fault == 0 && component.fault == 0 && runtime.flares!.fault == 0 && player.unresolvedDependencies.isEmpty)
                }
                for _ in 0..<3 { step() }
                //Move within the real starting platform so the leftward95px
                //sword spawn clears its adjacent wall; no position injection.
                step(0x02000000,0x02000000)
                for _ in 0..<19 { step(0x02000000) }
                for _ in 0..<3 { step() }
                //Synthetic powerup fixture invokes the whole original41f990;
                //spawn, facing/pose/attack input and subsequent lifetimes are live.
                var powered = player.runtime
                _ = withUnsafeMutablePointer(to:&powered){player.dependency($0,entry:0x41f990,a:power,b:30000,c:0)}
                player.acceptRuntimeSnapshot(powered)
                precondition(player.runtime.powerup == power && runtime.playerPowerupGlobals!.pointee.powerup == power)
                let direction:UInt32 = facing == 0 ? 0x01000000 : 0x02000000
                step(direction,direction);step(direction);for _ in 0..<3 { step() }
                precondition(player.runtime.privateWords.0 == facing)
                if duck { step(down,down);for _ in 0..<4 { step(down) };precondition(player.runtime.logicState == 26) }
                step(down|2,2)
                for _ in 0..<100 where component.tokens.isEmpty { step(down) }
                print("ELEMENTAL LAUNCH",power,duck,facing,component.tokens.count,component.emitCounts,player.runtime.actor.19,player.runtime.actor.20)
                precondition(component.tokens.count == 1 && (component.emitCounts[0x41cc60] ?? 0) > 0)
                let token = component.tokens.first!
                print("ELEMENTAL BIRTH",runtime.snapshotActor(token)?.actor.19 as Any,runtime.snapshotActor(token)?.actor.20 as Any)
                step(down)
                let parent = runtime.snapshotActor(token)!,privateToken = parent.primary.6
                precondition(parent.primary.4 == callback && parent.primary.7 == 2001 && parent.actor.89 & bit != 0)
                precondition(component.initialized.contains(token) && runtime.heap.lookup(privateToken,words:86) != nil && runtime.heap.lookup(privateToken,words:87) == nil)
                let raw = runtime.heap.lookup(privateToken,words:86)!,flare = raw[0x150/4]
                precondition(raw[0x154/4] == 0 && flare != 0 && runtime.flares!.initialized.contains(flare))
                let flarePrivate = runtime.snapshotActor(flare)!.primary.6
                var frames = 0,retained = 0
                while runtime.snapshotActor(token) != nil && frames < 400 {
                    let raw = runtime.heap.lookup(privateToken,words:86)!
                    func real(_ offset:Int) -> Double { Double(bitPattern:UInt64(raw[offset/4])|UInt64(raw[offset/4+1])<<32) }
                    let x = UInt32(bitPattern:Int32((real(104)-(real(80)>0 ? -20 : 20)).rounded(.towardZero)))
                    let y = UInt32(bitPattern:Int32(real(112).rounded(.towardZero)))
                    step(down);frames += 1
                    if runtime.snapshotActor(token) != nil,let child = runtime.snapshotActor(flare) {
                        precondition(child.actor.19 == x && child.actor.20 == y);retained += 1
                    }
                }
                for _ in 0..<4 { step(down) }
                print("ELEMENTAL END",power,duck,facing,frames,retained,runtime.snapshotActor(token)?.primary.7 as Any,runtime.snapshotActor(token)?.actor.19 as Any,runtime.snapshotActor(token)?.actor.20 as Any,runtime.heap.lookup(privateToken,words:1) != nil)
                totalRetained += retained
                precondition(runtime.heap.lookup(token,words:1) == nil && runtime.heap.lookup(privateToken,words:1) == nil)
                if let child = runtime.snapshotActor(flare) {
                    precondition(child.actor.2 & 0x10000 != 0)
                    //The source child can leave the active viewport before its
                    //parent collides. Approach it through live camera/input so
                    //spatial residency elects the pending deletion normally.
                    step();for _ in 0..<6 { step() }
                    step(0x02000000,0x02000000)
                    for _ in 0..<180 where runtime.snapshotActor(flare) != nil { step(0x02000000) }
                }
                let pending = runtime.snapshotActor(flare)
                if let pending {
                    precondition(pending.actor.2 & 0x10000 != 0 && runtime.heap.lookup(flarePrivate,words:19) != nil)
                    print("ELEMENTAL PENDING CHILD",power,duck,facing,pending.actor.19,pending.actor.20,player.runtime.actor.19,player.runtime.actor.20)
                } else { precondition(runtime.heap.lookup(flarePrivate,words:1) == nil) }
                print("PASS native elemental",power,duck ? "duck" : "standing","facing",facing,"source41f990 fixture/input/actual ANI marker5 → whole41cc60/deferred family86-word constructor/FALLING → source directional20px Flare lead/flight or immediate tile collision → parent cleanup/child source deletion flag; retained frames",retained,"child released",pending == nil,"16ms clock, pending spatial cleanup/physical raster/target-hit scope separate")
            }
        }
    }
    precondition(totalRetained > 0)
}
if CommandLine.arguments.contains("--elemental-only") { try verifyNativeElemental();exit(0) }
func verifyNativeHUD() throws {
    let player = try ClawNativePlayer(world:scene.world,assets:assets)
    var now:UInt32 = 1000
    let runtime = ClawNativeScene(player:player,clock:{now})
    try runtime.loadRecoveredObjects(world:scene.world,root:root)
    let hud = runtime.hud!,heap = runtime.heap
    precondition(hud.token != 0 && runtime.actorTokens.contains(hud.token))
    func step() {
        now &+= 16;runtime.advance(now:now,delta:16,accumulated:now-1000,held:0,pressed:0)
        if runtime.fault != 0 || hud.fault != 0 { print("HUD FAULT",runtime.fault,hud.fault,hud.unresolved,runtime.unresolvedDependencies) }
        precondition(runtime.fault == 0 && hud.fault == 0 && hud.unresolved.isEmpty)
    }
    for _ in 0..<4 { step() }
    let frames = Dictionary(uniqueKeysWithValues:hud.children.compactMap { t -> (UInt32,UInt32)? in
        let a = heap.lookup(t,words:128)!,l = heap.lookup(a[27],words:93)!
        return ClawNativeHUD.frames.contains(l[4]) ? (l[4],t) : nil
    })
    precondition(frames.count == 5 && hud.children.count == 22)
    func actor(_ callback:UInt32) -> UnsafeMutablePointer<UInt32> { heap.lookup(frames[callback]!,words:128)! }
    func view(_ callback:UInt32) -> UnsafeMutablePointer<UInt32> {
        let a = actor(callback);return heap.lookup(heap.lookup(a[27],words:93)![6],words:24)!
    }
    func digitIDs(_ callback:UInt32) -> [UInt32] {
        let h = view(callback);return (0..<Int(h[12])).map { heap.lookup(h[13+$0],words:128)![91] }
    }
    precondition(digitIDs(0x4908b0) == [0,0,0,0,0,0,0,0])
    precondition(digitIDs(0x490c50) == [1,0,0] && digitIDs(0x4912a0) == [2])
    precondition(actor(0x491540)[16]&1 != 0)
    precondition(ClawNativeHUD.frames.filter{$0 != 0x491540}.allSatisfy{actor($0)[14] == 0})
    let drawCount = runtime.rendering!.actorDrawCalls
    // Synthetic score/private inputs exercise source-owned life thresholds,
    // numeric formatting, cap and persistent source-to-native write-back.
    var value = player.runtime
    value.actor.62 = 2_500_000;value.privateWords.31 = 3
    runtime.writePlayerRuntime(value)
    step();print("HUD SCORE LIFE",player.runtime.privateWords.31,view(0x4908b0)[11],actor(0x4908b0)[63]);precondition(player.runtime.privateWords.31 == 4)
    step();precondition(player.runtime.privateWords.31 == 5)
    step();precondition(player.runtime.privateWords.31 == 5)
    precondition(digitIDs(0x4908b0) == [0,2,5,0,0,0,0,0])
    value = player.runtime;value.actor.62 = 3_500_000;value.privateWords.31 = 10
    runtime.writePlayerRuntime(value);step();precondition(player.runtime.privateWords.31 == 10 && actor(0x4908b0)[63] == 4_000_000)
    for selector:UInt32 in 1...3 {
        value = player.runtime;value.privateWords.12 = selector
        value.privateWords.28 = 37;value.privateWords.29 = 48;value.privateWords.30 = 59
        runtime.writePlayerRuntime(value);step()
        precondition(digitIDs(0x490f80) == (selector == 1 ? [3,7] : selector == 2 ? [4,8] : [5,9]))
        let image = runtime.objectResources!.images(token:actor(0x490f80)[92])!.name
        precondition(image == (selector == 1 ? "GAME_INTERFACE_WEAPONS_PISTOL" : selector == 2 ? "GAME_INTERFACE_WEAPONS_MAGIC" : "GAME_INTERFACE_WEAPONS_DYNAMITE"))
    }
    runtime.playerPowerupGlobals!.pointee.remaining = 123456
    step();precondition(actor(0x491540)[16]&1 == 0 && digitIDs(0x491540) == [1,2,3])
    runtime.playerPowerupGlobals!.pointee.remaining = 0
    step();precondition(actor(0x491540)[16]&1 != 0)
    let timer = view(0x491540)
    for i in 0..<3 { precondition(heap.lookup(timer[13+i],words:128)![16]&1 != 0) }
    precondition(runtime.rendering!.actorDrawCalls > drawCount)
    let ownedChildren = hud.children
    heap.lookup(hud.token,words:128)![2] |= 0x10000
    step()
    precondition(!runtime.actorTokens.contains(hud.token) && heap.lookup(hud.token,words:1) == nil)
    precondition(ownedChildren.allSatisfy{heap.lookup($0,words:1) == nil})
    print("PASS native source HUD: actual MultiStats collection/five frames/17 digits → ordinary source updates/draws → all3 weapon ammo/images → score million thresholds/life cap/persistent write-back → powerup timer show/floor/hide → source scheduler/whole collection teardown; synthetic score/private/timer inputs, resource/graphics transports explicit")
}
if CommandLine.arguments.contains("--hud-only") { try verifyNativeHUD();exit(0) }
func verifyNativeSuperCheckpointSave() throws {
    let player = try ClawNativePlayer(world:scene.world,assets:assets)
    var now:UInt32 = 1000
    let runtime = ClawNativeScene(player:player,clock:{now})
    try runtime.loadRecoveredObjects(world:scene.world,root:root,saveDirectory:URL(fileURLWithPath:"work/native-super-save-check/"+UUID().uuidString,isDirectory:true))
    let checkpoints = runtime.checkpoints!,messages = runtime.statusMessages!,saves = runtime.saves!
    let records = checkpoints.originalRecords.values.filter{$0.primary.4 != 0x422ef0}.sorted{$0.token<$1.token}
    precondition(records.count == 2 && runtime.uninstantiatedObjectCount == 0)
    let initialFlags = player.runtime.actor.2
    func step() {
        now &+= 16;runtime.advance(now:now,delta:16,accumulated:now-1000,held:0,pressed:0)
        if runtime.fault != 0 { print("SUPER SAVE FAULT",runtime.fault,runtime.unresolvedDependencies,checkpoints.fault,checkpoints.missingSpans,checkpoints.unresolved,messages.fault,messages.unresolved,saves.fault,saves.unresolved,saves.failure ?? "",runtime.rendering!.fault,runtime.rendering!.failure as Any,runtime.rendering!.unknownServices,runtime.paletteResources!.fault,runtime.paletteResources!.unresolved) }
        precondition(runtime.fault == 0 && checkpoints.fault == 0 && messages.fault == 0 && saves.fault == 0)
    }
    for original in records {
        var visitor = player.sceneSnapshot(),physics = player.runtime.physics
        visitor.actor.19 = original.actor.19 &- 180;visitor.actor.20 = original.actor.20
        visitor.actor.52 = 0;visitor.actor.53 = 0;visitor.primary.7 = 24
        physics.velocity.0 = 0;physics.velocity.1 = 0
        player.acceptSceneSnapshot(visitor,physics:physics)
        runtime.camera!.entry(0x42d5f0,receiver:0x60003000,argument0:original.actor.19,argument1:original.actor.20)
        for _ in 0..<4 { step() }
        var target = player.sceneSnapshot();target.actor.19 = original.actor.19;target.actor.20 = original.actor.20 &- 60
        target.actor.52 = 2;target.actor.53 = 0;target.actor.2 = initialFlags;target.primary.7 = 24
        physics = player.runtime.physics;physics.velocity.0 = 0;physics.velocity.1 = 0
        player.acceptSceneSnapshot(target,physics:physics)
        let writes = saves.physicalWrites
        for _ in 0..<4 where !checkpoints.contacted.contains(original.token) { step() }
        print("SUPER SAVE CONTACT",original.token,original.primary.4,checkpoints.contacted.contains(original.token),messages.count,saves.physicalWrites,player.x,player.y,messages.textDraws.map{$0.text})
        precondition(checkpoints.contacted.contains(original.token) && saves.physicalWrites == writes+2)
        precondition(messages.count == 1 && messages.textDraws.last?.text == "Your game has been saved")
        precondition(messages.textDraws.last?.rect.minY == 110 && messages.textDraws.last?.rect.maxY == 174)
        let kind:UInt32 = original.primary.4 == 0x4232c0 ? 1 : 2
        let args:[UInt32] = [1,kind]
        var g = ClawCheckpointGlobals(),result:UInt32 = 0
        let record = saves.playerRecord
        withUnsafeMutablePointer(to:&g){p in
            var context = ClawCheckpointContext(scene:saves.sourceHost,globals:p,composeAnimation:0,composeContactBinding:0,composeSave:0,composeSaveCache:1,fault:0)
            precondition(args.withUnsafeBufferPointer{claw_checkpoint_entry(0x49ae60,record,$0.baseAddress,2,&context,nil,nil,&result)} == 1 && result != 0)
        }
        let packet = runtime.heap.lookup(result,words:44)!
        precondition(packet[0]&2 != 0 && packet[1] == UInt32(bitPattern:player.x) && packet[2] == UInt32(bitPattern:player.y))
        let plain = Data(bytes:runtime.heap.lookup(record+4,words:2449)!,count:0x2644)
        let h = ClawTokenHeap(),rng = ClawNativeRandom(heap:h),loaded = try ClawNativeSave(heap:h,random:rng,storageDirectory:saves.storageDirectory)
        precondition(Data(bytes:h.lookup(loaded.playerRecord+4,words:2449)!,count:0x2644) == plain)
        for _ in 0..<320 where messages.count != 0 { step() }
        precondition(messages.count == 0 && messages.timer == 0 && messages.getDCCount == messages.releaseDCCount)
    }
    precondition((checkpoints.serviceCounts[0x49bbc0] ?? 0) == 2 && (checkpoints.serviceCounts[0x42abf0] ?? 0) == 2)
    print("PASS both actual supercheckpoints: normal scanner → full44-word cache/calendar → physical source-format save/fresh source reload → source save-toast queue/draw/5000ms dequeue → shared source clock reset; visits/live flags/type/mask0 synthetic and native GDI/font raster transport explicit")
}
if CommandLine.arguments.contains("--super-save-only") { try verifyNativeSuperCheckpointSave();exit(0) }
func verifyNativeCheckpoints() throws {
    // Real contact election must publish the original checkpoint's respawn sensor,
    // animate RISE/WAVE and add the source bonus without inventing a reset serial.
    let checkpointPlayer = try ClawNativePlayer(world:scene.world,assets:assets)
    var checkpointNow:UInt32 = 1000
    let checkpointScene = ClawNativeScene(player:checkpointPlayer,clock:{checkpointNow})
    try checkpointScene.loadRecoveredObjects(world:scene.world,root:root)
    let checkpointRecords = checkpointScene.checkpoints!.originalRecords.values.filter{$0.primary.4 == 0x422ef0}.sorted{$0.token<$1.token}
    for original in checkpointRecords {
        let beforeBonus = checkpointScene.checkpoints!.globals.pointee.timerRemaining
        let beforeSerial = checkpointPlayer.runtime.privateWords.32
        var visitor = checkpointPlayer.sceneSnapshot(), physics = checkpointPlayer.runtime.physics
        visitor.actor.19 = original.actor.19;visitor.actor.20 = original.actor.20 &- 60;visitor.primary.7 = 24
        physics.velocity.0 = 0;physics.velocity.1 = 0
        var privateWords = checkpointPlayer.runtime.privateWords;privateWords.72 = 20000
        withUnsafeBytes(of:&privateWords) {
            checkpointPlayer.acceptSceneSnapshot(visitor,physics:physics,privateWords:$0.bindMemory(to:UInt32.self).baseAddress!)
        }
        checkpointScene.camera!.entry(0x42d5f0,receiver:0x60003000,argument0:visitor.actor.19,argument1:visitor.actor.20)
        for _ in 0..<15 where !checkpointScene.checkpoints!.contacted.contains(original.token) {
            checkpointNow &+= 16;checkpointScene.advance(now:checkpointNow,delta:16,accumulated:checkpointNow-1000,held:0,pressed:0)
        }
        let current = checkpointScene.snapshotActor(original.token)!
        let owner = checkpointScene.heap.lookup(checkpointScene.ownerIdentity,words:478)!
        if !checkpointScene.checkpoints!.contacted.contains(original.token) || checkpointScene.fault != 0 { print("CHECKPOINT DIAGNOSTIC",original.token,original.actor.19,original.actor.20,checkpointPlayer.x,checkpointPlayer.y,current.primary.7,current.contact.4,checkpointScene.fault,checkpointScene.checkpoints!.fault,checkpointScene.checkpoints!.unresolved) }
        precondition(checkpointScene.checkpoints!.initialized.contains(original.token) && checkpointScene.checkpoints!.contacted.contains(original.token))
        precondition(owner[0x44/4] == original.actor.19 && owner[0x48/4] == original.actor.20 &- 32)
        precondition(checkpointScene.checkpoints!.globals.pointee.timerRemaining == beforeBonus &+ 25000)
        precondition(checkpointPlayer.runtime.privateWords.32 == beforeSerial)
        precondition(current.actor.30 != 0 && current.contact.4 == 0x422ff0 && current.primary.7 == 6)
        for _ in 0..<240 where checkpointScene.snapshotActor(original.token)!.primary.7 == 6 && checkpointScene.fault == 0 {
            checkpointNow &+= 16;checkpointScene.advance(now:checkpointNow,delta:16,accumulated:checkpointNow-1000,held:0,pressed:0)
        }
        if checkpointScene.snapshotActor(original.token)!.primary.7 != 1 || checkpointScene.fault != 0 { print("CHECKPOINT ANIMATION DIAGNOSTIC",original.token,checkpointScene.snapshotActor(original.token)!.primary.7,checkpointPlayer.x,checkpointPlayer.y,checkpointScene.fault,checkpointScene.checkpoints!.fault,checkpointScene.checkpoints!.missingSpans,checkpointScene.rendering!.fault,checkpointScene.rendering!.unknownServices,checkpointScene.camera!.fault,checkpointScene.unresolvedDependencies) }
        precondition(checkpointScene.snapshotActor(original.token)!.primary.7 == 1)
    }
    precondition(checkpointRecords.count == 7 && checkpointScene.checkpoints!.fault == 0 && checkpointScene.checkpoints!.unresolved.isEmpty)
    precondition(checkpointScene.fault == 0 && checkpointScene.unresolvedDependencies.isEmpty && checkpointPlayer.failure == nil)
    print("PASS all7 ordinary WWD checkpoints: real contact scanner → respawn sensor/25000 bonus → RISE/WAVE; private reset serial unchanged and initial visits synthetic")
    // Source initialization must read the live owner's checkpoint fields, then
    // apply the original ground query. This synthetic lethal attacker exercises
    // the real queued command/retained-world respawn, not a host teleport.
    let checkpointOwner = checkpointScene.heap.lookup(checkpointScene.ownerIdentity,words:478)!
    let checkpointX = checkpointOwner[0x44/4], checkpointY = checkpointOwner[0x48/4]
    let beforeCheckpointWorld = checkpointScene.worldIdentity
    var lethal = ClawWorldObjectRuntime();lethal.actor.52 = 4;lethal.actor.65 = 200
    lethal.actor.19 = UInt32(bitPattern:checkpointPlayer.x-30);lethal.actor.20 = UInt32(bitPattern:checkpointPlayer.y);lethal.actor.78 = 0x80000000
    checkpointPlayer.receiveHit(from:&lethal,token:0x10010000);checkpointScene.write(checkpointPlayer.sceneSnapshot())
    for _ in 0..<300 where checkpointPlayer.pendingCommands.isEmpty {
        checkpointNow &+= 16;checkpointScene.advance(now:checkpointNow,delta:16,accumulated:checkpointNow-1000,held:0,pressed:0)
    }
    precondition(checkpointPlayer.pendingCommands == [0x803a])
    precondition(checkpointScene.processPlayerCommands())
    print("CHECKPOINT RESPAWN DIAGNOSTIC",checkpointX,checkpointY,checkpointPlayer.x,checkpointPlayer.y,checkpointPlayer.runtime.logicState,checkpointScene.fault,checkpointScene.respawn!.unresolvedServices)
    precondition(UInt32(bitPattern:checkpointPlayer.x) == checkpointX && checkpointPlayer.x != 689)
    precondition(checkpointPlayer.runtime.logicState == 24 && checkpointPlayer.runtime.privateWords.18 == 100)
    precondition(checkpointScene.worldIdentity == beforeCheckpointWorld && checkpointScene.fault == 0 && checkpointScene.respawn!.unresolvedServices.isEmpty)
    print("PASS elected checkpoint → live owner position read → lethal source hit/queued803a → original grounded respawn at checkpoint and retained world")

}

func verifyNativeAmbientAudio() throws {
    let ambientPlayer = try ClawNativePlayer(world:scene.world,assets:assets)
    var ambientNow:UInt32 = 1000
    let ambientScene = ClawNativeScene(player:ambientPlayer,clock:{ambientNow})
    try ambientScene.loadRecoveredObjects(world:scene.world,root:root)
    let triggers = ambientScene.soundTriggers!, ambient = ambientScene.ambientAudio!
    let records = triggers.originalRecords.values.filter{ClawNativeSoundTriggers.ambientCallbacks.contains($0.primary.4)}.sorted{$0.token<$1.token}
    precondition(records.count == 15)
    // Placement is synthetic. Each initialization is elected by ordinary source
    // frames, using all fifteen actual records and the real retained audio heap.
    for original in records {
        var visitor = ambientPlayer.sceneSnapshot(), physics = ambientPlayer.runtime.physics
        visitor.actor.19 = original.actor.19;visitor.actor.20 = original.actor.20;visitor.primary.7 = 24
        physics.velocity.0 = 0;physics.velocity.1 = 0
        var words = ambientPlayer.runtime.privateWords;words.72 = 20000
        withUnsafeBytes(of:&words){ambientPlayer.acceptSceneSnapshot(visitor,physics:physics,privateWords:$0.bindMemory(to:UInt32.self).baseAddress!)}
        ambientScene.camera!.entry(0x42d5f0,receiver:0x60003000,argument0:visitor.actor.19,argument1:visitor.actor.20)
        for _ in 0..<8 where !triggers.initialized.contains(original.token) && ambientScene.fault == 0 {
            ambientNow &+= 16;ambientScene.advance(now:ambientNow,delta:16,accumulated:ambientNow-1000,held:0,pressed:0)
        }
        if !triggers.initialized.contains(original.token) || ambientScene.fault != 0 {
            print("AMBIENT INITIALIZATION DIAGNOSTIC",original.token,original.primary.4,ambientScene.fault,ambient.fault,ambient.unresolved,triggers.fault,triggers.unresolved,ambientPlayer.unresolvedDependencies)
        }
        precondition(triggers.initialized.contains(original.token) && ambientScene.fault == 0)
    }
    let manager = ambientScene.heap.lookup(ambient.managerToken,words:12)!
    let controller = ambientScene.heap.lookup(manager[0],words:13)!
    precondition(controller[11] == ambientPlayer.audio!.managerIdentity)
    var objects:[UInt32] = [], node = manager[3]
    while node != 0 {
        let entry = ambient.actorHost.lookup!(ambient.actorHost.context,node,3)!
        objects.append(entry[2]);node = entry[0];precondition(objects.count <= 15)
    }
    print("AMBIENT RETAINED DIAGNOSTIC",objects.count,manager[5],ambient.serviceCounts,ambient.physicalMethods)
    precondition(objects.count > 0 && UInt32(objects.count) == manager[5])
    // Original refresh, center trajectories, timed updates, stop and destructor;
    // no broad host stopAll substitutes for source list/fader ordering.
    _ = triggers.service(0x402570,receiver:ambient.managerToken,arguments:[])
    for original in records {
        ambientNow &+= 16;_ = ambient.frame(ambient.managerToken,x:original.actor.19,y:original.actor.20)
        ambientNow &+= 1200;_ = ambient.frame(ambient.managerToken,x:original.actor.19 &+ 2000,y:original.actor.20 &+ 2000)
    }
    _ = triggers.service(0x402520,receiver:ambient.managerToken,arguments:[])
    // Audio remains live after ambient stop and is the same owner on scene.heap.
    precondition(ambientScene.heap.lookup(ambientPlayer.audio!.managerIdentity,words:32) ==
        ambientPlayer.audio!.ambientMetadata(token:ambientPlayer.audio!.managerIdentity,words:32))
    precondition(ambientPlayer.audio!.ambientMetadata(token:ambientPlayer.audio!.managerIdentity,words:32)![3] == 0)
    for object in objects { precondition(ambientScene.heap.lookup(object,words:6)![5] == 0) }
    let stopCount = ambient.physicalMethods[0x48,default:0]
    _ = triggers.service(0x402570,receiver:ambient.managerToken,arguments:[])
    _ = triggers.service(0x402270,receiver:ambient.managerToken,arguments:[])
    precondition(manager[0] == 0 && manager[3] == 0 && manager[4] == 0 && manager[5] == 0 && manager[6] == 0 && manager[7] == 0)
    for object in objects { precondition(ambientScene.heap.lookup(object,words:1) == nil) }
    precondition(stopCount > 0 && ambient.serviceCounts[0x4b3fe0,default:0] > 0 && ambient.serviceCounts[0x4b4b80,default:0] > 0)
    precondition(ambient.fault == 0 && ambient.unresolved.isEmpty && ambient.reports.isEmpty && triggers.fault == 0 && triggers.unresolved.isEmpty)
    print("PASS all15 actual ambient records: source frame activation, retained pooled objects, direct buffers/pan, timed fades, refresh/stop/destruction; physical mixer identity remains unproved")
}

func verifyNativeImpactParticles() throws {
    let hitPlayer = try ClawNativePlayer(world:scene.world,assets:assets)
    var hitNow:UInt32 = 1000
    let hitScene = ClawNativeScene(player:hitPlayer,clock:{hitNow})
    try hitScene.loadRecoveredObjects(world:scene.world,root:root)
    let effects = hitScene.effects!
    hitNow &+= 16;hitScene.advance(now:hitNow,delta:16,accumulated:hitNow-1000,held:0,pressed:0)
    var attacker = ClawWorldObjectRuntime();attacker.actor.52 = 4;attacker.actor.65 = 5
    attacker.actor.19 = UInt32(bitPattern:hitPlayer.x-30);attacker.actor.20 = UInt32(bitPattern:hitPlayer.y);attacker.actor.78 = 0x80000000
    hitPlayer.receiveHit(from:&attacker,token:0x10010000);hitScene.write(hitPlayer.sceneSnapshot())
    let bursts = effects.actors.values.filter{$0.snapshot()?.primary.4 == 0x461a90}
    print("IMPACT CREATE DIAGNOSTIC",bursts.count,hitPlayer.runtime.actor.14,hitPlayer.runtime.actor.67,effects.failure ?? "",effects.unresolved,hitPlayer.unresolvedDependencies)
    precondition(bursts.count == 1 && effects.fault == 0 && hitPlayer.unresolvedDependencies.isEmpty)
    let token = bursts[0].token, snapshot = hitScene.snapshotActor(token)!
    precondition(snapshot.actor.32 == 0x10002000 && snapshot.primary.7 == 5 && snapshot.actor.92 != 0 && snapshot.actor.100 != 0)
    precondition(effects.allocations.filter{$0.bytes == 0x1b4}.count == 1)
    let offsetX = snapshot.actor.86,offsetY = snapshot.actor.87
    var followed = false
    for _ in 0..<180 where hitScene.heap.lookup(token,words:1) != nil && hitScene.fault == 0 {
        hitNow &+= 16;hitScene.advance(now:hitNow,delta:16,accumulated:hitNow-1000,held:0,pressed:0)
        if let live = hitScene.snapshotActor(token),live.actor.2 & 0x10000 == 0 {
            let player = hitScene.snapshotActor(0x10002000)!
            precondition(live.actor.19 == player.actor.19 &+ offsetX && live.actor.20 == player.actor.20 &+ offsetY)
            followed = true
        }
    }
    if effects.fault != 0 || hitScene.fault != 0 { print("IMPACT LIFETIME DIAGNOSTIC",effects.failure ?? "",effects.unresolved,hitScene.unresolvedDependencies) }
    precondition(followed && hitScene.heap.lookup(token,words:1) == nil && effects.actors[token] == nil)
    precondition(effects.fault == 0 && effects.unresolved.isEmpty && hitScene.fault == 0 && hitPlayer.failure == nil)
    // Enemy-style hit uses its distinct actual five-image manager. Source
    // invalidation must delete it through the ordinary scheduler.
    precondition(effects.impactEntry(0x461a00,arguments:[hitScene.sceneIdentity,UInt32(bitPattern:hitPlayer.x),UInt32(bitPattern:hitPlayer.y),9000,0,0x10002000]) == 1)
    let enemyBurst = effects.actors.values.first{$0.snapshot()?.primary.4 == 0x461a90}!
    let enemySnapshot = enemyBurst.snapshot()!
    precondition(enemySnapshot.actor.92 != snapshot.actor.92)
    var invalid = hitScene.snapshotActor(0x10002000)!;invalid.actor.14 = 0xffffffff;hitScene.write(invalid)
    _ = effects.callback(enemyBurst.token,function:0x461a90)
    precondition(hitScene.snapshotActor(enemyBurst.token)!.actor.2 & 0x10000 != 0)
    precondition(effects.fault == 0 && effects.unresolved.isEmpty)
    print("PASS source player hit → actual Claw HitBurst → retained animation/following → generic scheduler destruction; distinct enemy image manager and invalid-source deletion")
}

func verifyNativeCurseGate() throws {
    let cursePlayer = try ClawNativePlayer(world:scene.world,assets:assets)
    var curseNow:UInt32 = 1000
    let curseScene = ClawNativeScene(player:cursePlayer,clock:{curseNow})
    try curseScene.loadRecoveredObjects(world:scene.world,root:root)
    let curses = curseScene.curses!, records = curses.originalRecords.values.sorted{$0.token<$1.token}
    precondition(records.count == 8 && curseScene.uninstantiatedObjectCount == 0)
    for original in records {
        var visitor = cursePlayer.sceneSnapshot(), physics = cursePlayer.runtime.physics
        visitor.actor.19 = original.actor.19;visitor.actor.20 = original.actor.20;visitor.primary.7 = 24
        physics.velocity.0 = 0;physics.velocity.1 = 0
        var words = cursePlayer.runtime.privateWords;words.72 = 20000
        withUnsafeBytes(of:&words){cursePlayer.acceptSceneSnapshot(visitor,physics:physics,privateWords:$0.bindMemory(to:UInt32.self).baseAddress!)}
        curseScene.camera!.entry(0x42d5f0,receiver:0x60003000,argument0:visitor.actor.19,argument1:visitor.actor.20)
        for _ in 0..<8 where !curses.initialized.contains(original.token) && curseScene.fault == 0 {
            curseNow &+= 16;curseScene.advance(now:curseNow,delta:16,accumulated:curseNow-1000,held:0,pressed:0)
        }
        if !curses.initialized.contains(original.token) || curseScene.fault != 0 { print("CURSE DIAGNOSTIC",original.token,curseScene.fault,curses.fault,curses.unresolved) }
        precondition(curses.initialized.contains(original.token) && curses.fault == 0)
        // The mode3 source path sets Delete and returns0. Ordinary scheduling
        // owns actual actor/common-logic teardown on the following pass.
        for _ in 0..<4 where curseScene.heap.lookup(original.token,words:1) != nil {
            curseNow &+= 16;curseScene.advance(now:curseNow,delta:16,accumulated:curseNow-1000,held:0,pressed:0)
        }
        precondition(curseScene.heap.lookup(original.token,words:1) == nil)
    }
    precondition(curses.fault == 0 && curses.unresolved.isEmpty && curseScene.fault == 0 && curseScene.unresolvedDependencies.isEmpty)
    print("PASS all8 actual CursePowerup records: source singleplayer mode3 rejection → ordinary Delete/list/common-logic destruction; no multiplayer effects fabricated")
}

func verifyNativeCrateCombat() throws {
    let cratePlayer = try ClawNativePlayer(world:scene.world,assets:assets)
    var crateNow:UInt32 = 1000
    let crateScene = ClawNativeScene(player:cratePlayer,clock:{crateNow})
    try crateScene.loadRecoveredObjects(world:scene.world,root:root)
    let crates = crateScene.singleCrates!, records = crates.originalRecords.values.sorted{$0.token<$1.token}
    var projectileInputs = 0
    for original in records {
        // One source projectile can elect more than one overlapping crate in
        // its cached scanner pass. Preserve that ordering; a prior hit may have
        // already completed a neighboring record's natural lifetime.
        if crateScene.heap.lookup(original.token,words:1) == nil {
            precondition(crates.initialized.contains(original.token));continue
        }
        func stepCrate() {
            // Keep the synthetic spectator near this record. Free fall can
            // move source residency away from an airborne crate mid-animation.
            var visitor = cratePlayer.sceneSnapshot(), physics = cratePlayer.runtime.physics
            visitor.actor.19 = original.actor.19 &- 180;visitor.actor.20 = original.actor.20;visitor.primary.7 = 24
            physics.velocity.0 = 0;physics.velocity.1 = 0
            var words = cratePlayer.runtime.privateWords;words.72 = 20000
            withUnsafeBytes(of:&words){cratePlayer.acceptSceneSnapshot(visitor,physics:physics,privateWords:$0.bindMemory(to:UInt32.self).baseAddress!)}
            crateScene.camera!.entry(0x42d5f0,receiver:0x60003000,argument0:original.actor.19,argument1:original.actor.20)
            crateNow &+= 16;crateScene.advance(now:crateNow,delta:16,accumulated:crateNow-1000,held:0,pressed:0)
        }
        for _ in 0..<4 { stepCrate() }
        let initial = crateScene.snapshotActor(original.token)!
        precondition([UInt32(5),31].contains(initial.primary.7) && initial.actor.67 <= 2)
        for _ in 0..<initial.actor.67 {
            let current = crateScene.snapshotActor(original.token)!, before = current.actor.67
            // Synthetic projectile, real source overlap/mask election and
            // CrateHit callback. No forced crate damage/state or loot is used.
            var projectile = ClawInteractionActor();projectile.token = crateScene.heap.allocate(bytes:512)
            projectile.actor.0 = 0x5137f0;projectile.actor.2 = current.actor.2 & 0x40000
            projectile.actor.3 = crateScene.sceneIdentity;projectile.actor.19 = current.actor.19;projectile.actor.20 = current.actor.20
            projectile.actor.25 = 9000;projectile.actor.27 = crateScene.heap.allocate(bytes:372)
            projectile.primary.0 = 0x513740;projectile.primary.3 = projectile.token;projectile.primary.4 = 0x4bb030;projectile.primary.7 = 5
            projectile.actor.52 = 0x20;projectile.actor.65 = 1
            projectile.actor.78 = UInt32(bitPattern:-40);projectile.actor.79 = UInt32(bitPattern:-40);projectile.actor.80 = 40;projectile.actor.81 = 40
            crateScene.adopt(projectile)
            stepCrate()
            if crates.fault != 0 || crateScene.fault != 0 { print("CRATE COMBAT DIAGNOSTIC",original.token,crates.fault,crates.unresolved,crateScene.fault,crateScene.unresolvedDependencies) }
            precondition(crateScene.snapshotActor(original.token)!.actor.67 == before &- 1)
            projectileInputs += 1
            precondition(crateScene.snapshotActor(projectile.token)!.actor.2 & 0x10000 != 0)
            for _ in 0..<35 { stepCrate() }
        }
        for _ in 0..<180 where crateScene.heap.lookup(original.token,words:1) != nil && crateScene.fault == 0 {
            stepCrate()
        }
        if let remaining = crateScene.snapshotActor(original.token) { print("CRATE TERMINAL DIAGNOSTIC",original.token,remaining.primary.7,remaining.primary.25,remaining.actor.67,remaining.actor.2,remaining.actor.103,remaining.actor.105,cratePlayer.x,cratePlayer.y,crates.fault,crates.unresolved,crateScene.fault) }
        precondition(crateScene.heap.lookup(original.token,words:1) == nil)
    }
    precondition(records.allSatisfy{crates.initialized.contains($0.token) && crateScene.heap.lookup($0.token,words:1) == nil})
    precondition(records.count == 34 && crates.fault == 0 && crates.unresolved.isEmpty && crateScene.fault == 0 && crateScene.unresolvedDependencies.isEmpty)
    print("PASS all34 actual single crates: synthetic projectiles → real overlap/CrateHit election → cooldown/damage/break ANI/loot → scheduler deletion; projectile inputs",projectileInputs)
}

func verifyNativeKegs() throws {
    let kegPlayer = try ClawNativePlayer(world:scene.world,assets:assets)
    var kegNow:UInt32 = 1000
    let kegScene = ClawNativeScene(player:kegPlayer,clock:{kegNow})
    try kegScene.loadRecoveredObjects(world:scene.world,root:root)
    let component = kegScene.breakables!,records = component.originalRecords.values.filter{$0.primary.4 == 0x46f1e0}.sorted{$0.token<$1.token}
    precondition(records.count == 58 && kegScene.uninstantiatedObjectCount == 0)
    for original in records {
        var visitor = kegPlayer.sceneSnapshot(),physics = kegPlayer.runtime.physics
        visitor.actor.19 = original.actor.19 &- 180;visitor.actor.20 = original.actor.20;visitor.primary.7 = 24
        physics.velocity.0 = 0;physics.velocity.1 = 0
        var words = kegPlayer.runtime.privateWords;words.72 = 20000
        withUnsafeBytes(of:&words){kegPlayer.acceptSceneSnapshot(visitor,physics:physics,privateWords:$0.bindMemory(to:UInt32.self).baseAddress!)}
        kegScene.camera!.entry(0x42d5f0,receiver:0x60003000,argument0:original.actor.19,argument1:original.actor.20)
        for _ in 0..<5 {
            kegNow &+= 16;kegScene.advance(now:kegNow,delta:16,accumulated:kegNow-1000,held:0,pressed:0)
            if component.fault != 0 || kegScene.fault != 0 { print("KEG DIAGNOSTIC",original.token,component.fault,component.unresolved,kegScene.fault,kegScene.unresolvedDependencies,component.bodies.map{($0.key,$0.value.failure ?? "",$0.value.unresolved)}) }
            precondition(component.fault == 0 && kegScene.fault == 0)
        }
        let snapshot = kegScene.snapshotActor(original.token)!,body = component.bodies[original.token]!
        let raw = kegScene.heap.lookup(snapshot.primary.6,words:260)!
        precondition(component.initialized.contains(original.token) && raw[0] == 0x50edd4 && raw[0x12c/4] == original.token)
        precondition(snapshot.primary.7 == body.states.ids["LS_IDLE"] && snapshot.actor.52 == 4 && snapshot.actor.53 == 0x1000020)
        precondition(snapshot.actor.89 & 1 != 0 && body.failure == nil && body.unresolved.isEmpty)
    }
    precondition(component.fault == 0 && component.unresolved.isEmpty && kegScene.fault == 0 && kegScene.unresolvedDependencies.isEmpty)
    print("PASS all58 actual PowderKeg records: source grid activation → whole generic/subtype constructors → actual vtable/bounds/grounding → retained source FSM; player/camera visits synthetic")
}

func verifyNativeKegCarry() throws {
    let carryPlayer = try ClawNativePlayer(world:scene.world,assets:assets)
    var now:UInt32 = 1000
    let carryScene = ClawNativeScene(player:carryPlayer,clock:{now})
    try carryScene.loadRecoveredObjects(world:scene.world,root:root)
    let record = carryScene.breakables!.originalRecords.values.filter{$0.primary.4 == 0x46f1e0}.sorted{$0.token<$1.token}.first!
    var observedKegStates:Set<UInt32> = []
    var visitor = carryPlayer.sceneSnapshot(),physics = carryPlayer.runtime.physics
    visitor.actor.19 = record.actor.19 &- 180;visitor.actor.20 = record.actor.20;visitor.primary.7 = 24
    physics.velocity.0 = 0;physics.velocity.1 = 0
    carryPlayer.acceptSceneSnapshot(visitor,physics:physics)
    carryScene.camera!.entry(0x42d5f0,receiver:0x60003000,argument0:record.actor.19,argument1:record.actor.20)
    func step(held:UInt32 = 0,pressed:UInt32 = 0) {
        now &+= 16;carryScene.advance(now:now,delta:16,accumulated:now-1000,held:held,pressed:pressed)
        if carryScene.fault != 0 || carryPlayer.failure != nil || !carryPlayer.unresolvedDependencies.isEmpty {
            print("CARRY DIAGNOSTIC",carryPlayer.runtime.logicState,carryPlayer.failure ?? "",carryPlayer.unresolvedDependencies,carryScene.fault,carryScene.carry!.fault,carryScene.carry!.unresolved,carryScene.breakables!.fault,carryScene.breakables!.unresolved)
        }
        for body in carryScene.breakables!.bodies.values { observedKegStates.insert(body.state.pointee.primary.7) }
        precondition(carryScene.fault == 0 && carryPlayer.failure == nil && carryPlayer.unresolvedDependencies.isEmpty)
    }
    for _ in 0..<5 { step() }
    let keg = carryScene.snapshotActor(record.token)!
    visitor = carryPlayer.sceneSnapshot();visitor.actor.19 = keg.actor.19 &- 30;visitor.actor.20 = keg.actor.20 &+ keg.actor.73 &- visitor.actor.73;visitor.primary.7 = 24;visitor.actor.51 = 1
    // Controlled fixture: prevent unrelated scene attackers interrupting throw.
    // This is a synthetic source hit-mask field, not an invulnerability timer.
    visitor.actor.53 = 0
    physics = carryPlayer.runtime.physics;physics.velocity.0 = 0;physics.velocity.1 = 0
    var words = carryPlayer.runtime.privateWords;words.0 = 1;words.1 = 0;words.72 = 20000
    withUnsafeBytes(of:&words){carryPlayer.acceptSceneSnapshot(visitor,physics:physics,privateWords:$0.bindMemory(to:UInt32.self).baseAddress!)}
    step(held:0x20,pressed:0x20)
    print("CARRY ELECT",record.token,carryPlayer.runtime.logicState,carryPlayer.runtime.privateWords.75,carryScene.carry!.entries)
    let elected = carryPlayer.runtime.privateWords.75
    precondition(carryPlayer.runtime.logicState == 5000 && carryScene.breakables!.originalRecords[elected] != nil)
    for _ in 0..<120 where carryPlayer.runtime.privateWords.2 == 0 { step() }
    precondition(carryPlayer.runtime.logicState == 5000 && carryPlayer.runtime.privateWords.2 == 1)
    step(held:0x20,pressed:0x20)
    precondition(carryPlayer.runtime.logicState == 5001)
    for _ in 0..<15 { step(held:0x20) }
    for _ in 0..<120 where carryPlayer.runtime.logicState == 5001 { step() }
    print("CARRY RELEASE",carryPlayer.runtime.privateWords.75,carryPlayer.runtime.logicState,observedKegStates)
    precondition(carryPlayer.runtime.privateWords.75 == 0 && observedKegStates.contains(carryScene.breakables!.bodies[elected]!.states.ids["LS_THROWN"]!))
    precondition(carryScene.carry!.entries[0x41dc50] == 1 && (carryScene.carry!.entries[5000] ?? 0)>0 && (carryScene.carry!.entries[5001] ?? 0)>0)
    let released = carryScene.snapshotActor(elected)!
    print("PASS native keg: actual selector → source lift → ordinary5000 carry → ordinary5001 charge/throw → released subtype; retained keg state",released.primary.7,"synthetic visitor and defender mask0")
}
if CommandLine.arguments.contains("--keg-carry-only") { try verifyNativeKegCarry(); exit(0) }
func verifyNativeStacks() throws {
    let stackPlayer = try ClawNativePlayer(world:scene.world,assets:assets)
    var now:UInt32 = 1000
    let stackScene = ClawNativeScene(player:stackPlayer,clock:{now})
    try stackScene.loadRecoveredObjects(world:scene.world,root:root)
    let component = stackScene.breakables!,records = component.originalRecords.values.filter{[UInt32(0x48d560),0x48d620].contains($0.primary.4)}.sorted{$0.token<$1.token}
    precondition(records.count == 22 && stackScene.uninstantiatedObjectCount == 0)
    var expectedChildren = 0
    for original in records {
        let inventory = withUnsafeBytes(of:original.primary){Array($0.bindMemory(to:UInt32.self))}
        var items = [original.actor.64 != 0 ? original.actor.64 : inventory[60]]
        if original.actor.64 != 0 { items.append(inventory[60]) };items.append(contentsOf:inventory[61...67])
        expectedChildren += items.filter{$0 != 0}.count
        var visitor = stackPlayer.sceneSnapshot(),physics = stackPlayer.runtime.physics
        visitor.actor.19 = original.actor.19 &- 180;visitor.actor.20 = original.actor.20;visitor.primary.7 = 24;visitor.actor.53 = 0
        physics.velocity.0 = 0;physics.velocity.1 = 0
        stackPlayer.acceptSceneSnapshot(visitor,physics:physics)
        stackScene.camera!.entry(0x42d5f0,receiver:0x60003000,argument0:original.actor.19,argument1:original.actor.20)
        for _ in 0..<5 {
            now &+= 16;stackScene.advance(now:now,delta:16,accumulated:now-1000,held:0,pressed:0)
            if component.fault != 0 || stackScene.fault != 0 { print("STACK DIAGNOSTIC",original.token,component.fault,component.unresolved,stackScene.fault,stackScene.unresolvedDependencies,component.bodies.map{($0.key,$0.value.failure ?? "",$0.value.unresolved)}) }
            precondition(component.fault == 0 && stackScene.fault == 0)
        }
        precondition(component.initialized.contains(original.token) && component.deletedStackParents.contains(original.token) && stackScene.heap.lookup(original.token,words:1) == nil)
    }
    precondition(component.childCrates.count == expectedChildren && component.deletedStackParents.count == 22)
    precondition(component.bodies.values.filter{$0.privateWords == 262}.count == expectedChildren)
    precondition(component.fault == 0 && component.unresolved.isEmpty && stackScene.fault == 0 && stackScene.unresolvedDependencies.isEmpty)
    print("PASS all22 native stack parents → original child creation/linking/grounding/FSM → scheduled19-word parent deletion; child crates",expectedChildren,"synthetic visitor and defender mask0")
}
if CommandLine.arguments.contains("--stack-only") { try verifyNativeStacks(); exit(0) }
func verifyNativeSpecials(award:Bool = false) throws {
    let specialPlayer = try ClawNativePlayer(world:scene.world,assets:assets)
    var now:UInt32 = 1000
    let specialScene = ClawNativeScene(player:specialPlayer,clock:{now})
    try specialScene.loadRecoveredObjects(world:scene.world,root:root)
    let component = specialScene.specialPowerups!,records = component.originalRecords.values.sorted{$0.token<$1.token}
    precondition(records.count == 10 && specialScene.uninstantiatedObjectCount == 0)
    let originalHitMask = specialPlayer.runtime.actor.53,originalFlags = specialPlayer.runtime.actor.2
    var waitNow:UInt32 = 1000
    component.waitClock = { waitNow &+= 250;return waitNow } // Explicit progressing clock fixture; no real-time delay claim.
    for original in records {
        var visitor = specialPlayer.sceneSnapshot(),physics = specialPlayer.runtime.physics
        visitor.actor.19 = original.actor.19 &- 180;visitor.actor.20 = original.actor.20;visitor.primary.7 = 24;visitor.actor.53 = 0
        physics.velocity.0 = 0;physics.velocity.1 = 0
        specialPlayer.acceptSceneSnapshot(visitor,physics:physics)
        specialScene.camera!.entry(0x42d5f0,receiver:0x60003000,argument0:original.actor.19,argument1:original.actor.20)
        for _ in 0..<4 {
            now &+= 16;specialScene.advance(now:now,delta:16,accumulated:now-1000,held:0,pressed:0)
            if specialScene.fault != 0 { print("SPECIAL DIAGNOSTIC",original.token,component.fault,component.unresolved,specialScene.fault,specialScene.unresolvedDependencies,specialScene.effects!.failure ?? "",specialScene.effects!.unresolved) }
            precondition(specialScene.fault == 0 && component.fault == 0)
        }
        let current = specialScene.snapshotActor(original.token)!
        print("SPECIAL INITIALIZED",original.token,current.primary.7,current.actor.52,current.actor.63,current.actor.50,current.actor.89,current.actor.82,current.actor.83)
        precondition(component.initialized.contains(original.token) && current.primary.7 == 5 && current.actor.52 == 0x100)
        precondition(current.actor.100 != 0 && current.actor.78 != 0x80000000)
        if award {
            var target = specialPlayer.sceneSnapshot(),physics = specialPlayer.runtime.physics
            // A synthetic visitor can enter retail hazard tiles. Restore the
            // original live-player flags before exercising the source scanner.
            target.actor.19 = current.actor.19;target.actor.20 = current.actor.20;target.actor.53 = originalHitMask;target.actor.2 = originalFlags;target.primary.7 = 24;target.actor.51 = 1
            physics.velocity.0 = 0;physics.velocity.1 = 0
            specialPlayer.acceptSceneSnapshot(target,physics:physics)
            let priorCommands = specialPlayer.pendingCommands.count,priorLives = specialPlayer.runtime.privateWords.31
            for _ in 0..<4 where !component.awarded.contains(original.token) {
                now &+= 16;specialScene.advance(now:now,delta:16,accumulated:now-1000,held:0,pressed:0)
                if specialScene.fault != 0 { print("SPECIAL HIT DIAGNOSTIC",original.token,current.actor.63,component.fault,component.unresolved,specialScene.fault,specialScene.unresolvedDependencies,specialPlayer.unresolvedDependencies) }
                precondition(specialScene.fault == 0 && component.fault == 0)
            }
            print("SPECIAL AWARD",original.token,current.actor.63,component.awarded.contains(original.token),specialPlayer.pendingCommands,component.warpTarget,specialPlayer.runtime.privateWords.31)
            precondition(component.awarded.contains(original.token))
            if current.actor.63 == 0x26ae {
                precondition(component.warpTarget.0 == current.actor.82 && component.warpTarget.1 == current.actor.83)
                precondition(specialPlayer.pendingCommands.count == priorCommands+1 && specialPlayer.pendingCommands.last == 0x805c)
            } else if current.actor.63 == 0x26ad {
                precondition(specialPlayer.pendingCommands.count == priorCommands+1 && specialPlayer.pendingCommands.last == 0x800e)
                precondition((component.serviceCounts[0x4b8960] ?? 0)>0)
            }
            else if current.actor.63 == 0x26be { precondition(specialPlayer.runtime.privateWords.31 == min(priorLives+1,10)) }
        }
    }
    precondition(component.fault == 0 && component.unresolved.isEmpty && specialScene.fault == 0 && specialScene.unresolvedDependencies.isEmpty)
    if award { precondition(specialPlayer.pendingCommands == Array(repeating:UInt32(0x805c),count:8)+[0x800e]) }
    if award { print("PASS all10 actual SpecialPowerup source scanner elections: all8 warp target/WM_COMMAND publications, map-piece command/sound/wait and extra-life award; placement/live-player flags/progressing wait clock are synthetic; command execution still pending") }
    print("PASS all10 actual SpecialPowerup records: source grid activation → original resources/metadata/type/bounds/glitter gate → retained ANI; visitor and defender mask0 synthetic")
}
if CommandLine.arguments.contains("--special-award-only") { try verifyNativeSpecials(award:true);exit(0) }
if CommandLine.arguments.contains("--special-only") { try verifyNativeSpecials(); exit(0) }
if CommandLine.arguments.contains("--keg-only") { try verifyNativeKegs(); exit(0) }
if CommandLine.arguments.contains("--crate-combat-only") { try verifyNativeCrateCombat(); exit(0) }
if CommandLine.arguments.contains("--curse-only") { try verifyNativeCurseGate(); exit(0) }
if CommandLine.arguments.contains("--impact-only") { try verifyNativeImpactParticles(); exit(0) }
if CommandLine.arguments.contains("--ambient-only") { try verifyNativeAmbientAudio(); exit(0) }
if CommandLine.arguments.contains("--checkpoint-only") { try verifyNativeCheckpoints(); exit(0) }

let player = try ClawNativePlayer(world: scene.world, assets: assets)
precondition(player.x == 689 && player.y == 4730 && player.runtime.logicState == 24)
precondition(assets.images[player.imageID] != nil)
var startup = player.runtime
precondition(claw_player_actor_word(&startup, 4) == 1 && claw_player_actor_word(&startup, 8) & 0x40002 == 0x40002)
precondition(claw_player_actor_word(&startup, 0xe8) == 320 && claw_player_actor_word(&startup, 0xec) == 350 && claw_player_actor_word(&startup, 0xf0) == 100)
precondition(claw_player_actor_word(&startup, 0xdc) == 10 && claw_player_actor_word(&startup, 0xe0) == 10)
precondition(claw_player_actor_word(&startup, 0x10c) == 100 && claw_player_actor_word(&startup, 0x70) != 0)
for (index, value) in [(UInt32(12),UInt32(1)),(18,100),(28,10),(29,5),(30,3),(31,3)] {
    precondition(claw_player_private_word(&startup, index) == value)
}
for (index, adjustment) in [4,8,12,16,40,54,58].enumerated() {
    if let sprite = assets.sprites[383 + index] {
        precondition(player.imageOffsetY[383 + index] == Int32(sprite.offsetY + adjustment))
    }
}
for _ in 0..<10 { player.advance(direction: 1, stageDelta: 16, animationDelta: 16) }
precondition(player.x > 689 && !player.mirrored && player.runtime.logicState == 8)
let rightX = player.x
for _ in 0..<10 { player.advance(direction: -1, stageDelta: 16, animationDelta: 16) }
precondition(player.x < rightX && player.mirrored && player.runtime.logicState == 9)
player.advance(direction: 0, stageDelta: 16, animationDelta: 16)
precondition(player.runtime.logicState == 24 && player.sequence == "STAND")
let startY = player.y
player.advance(direction: 0, jumpHeld: true, jumpPressed: true, stageDelta: 16, animationDelta: 16)
var states: Set<UInt32> = [player.runtime.logicState]
var minimumY = player.y
for index in 0..<120 {
    player.advance(direction: 0, jumpHeld: index < 10, stageDelta: 16, animationDelta: 16)
    states.insert(player.runtime.logicState); minimumY = min(minimumY, player.y)
}
precondition(minimumY < startY && states.contains(4) && states.contains(25) && states.contains(24))
precondition(player.y == startY)
player.advance(direction: 0, vertical: 1, stageDelta: 16, animationDelta: 16)
precondition(player.runtime.logicState == 26 && player.sequence == "DUCK")
for _ in 0..<5 { player.advance(direction: 0, vertical: 1, stageDelta: 16, animationDelta: 16) }
player.advance(direction: 0, stageDelta: 16, animationDelta: 16)
precondition(player.runtime.logicState == 24)
for _ in 0..<45 { player.advance(direction: 0, vertical: -1, stageDelta: 16, animationDelta: 16) }
precondition(player.runtime.logicState == 5003 && player.sequence == "LOOKUP")
player.advance(direction: 0, stageDelta: 16, animationDelta: 16)
precondition(player.runtime.logicState == 24)
// These exercise native animation tokens and reentrant dependency wiring, in
// addition to the worker's independent whole-buffer original comparisons.
for (held,expectedAttack) in [(UInt32(2),["SWIPE","KICK","PUNCH","UPPERCUT"]),
    (UInt32(0x08000002),["DUCKSWIPE"])] {
    if held & 0x08000000 != 0 {
        player.advance(held: 0x08000000, pressed: 0x08000000, stageDelta: 16, animationDelta: 16)
    }
    player.advance(held: held, pressed: 2, stageDelta: 16, animationDelta: 16)
    var attackState = player.runtime
    precondition(claw_player_private_word(&attackState, 1) == 1)
    precondition(expectedAttack.contains(player.sequence))
    for _ in 0..<120 { player.advance(held: held & ~2, pressed: 0, stageDelta: 16, animationDelta: 16) }
    attackState = player.runtime
    precondition(claw_player_private_word(&attackState, 1) == 0)
    player.advance(held: 0, pressed: 0, stageDelta: 16, animationDelta: 16)
}
let draw = player.drawCommand(camera: .zero, viewport: CGSize(width: 960, height: 6000))
precondition(draw != nil && draw!.rect.width > 0)
precondition(player.failure == nil && player.unresolvedDependencies.isEmpty)
precondition((player.audio?.playRequests ?? 0) > 0 && player.audio?.reports.isEmpty == true)
// Synthetic callback inputs verify native wiring only. The original generic
// hit scanner, effects, audio and respawn command handler are separate work.
let victim = try ClawNativePlayer(world: scene.world, assets: assets)
var attacker = ClawWorldObjectRuntime()
func setAttacker(_ offset: Int, _ value: UInt32) {
    withUnsafeMutableBytes(of: &attacker.actor) { $0.storeBytes(of: value, toByteOffset: offset, as: UInt32.self) }
}
setAttacker(0xd0, 4); setAttacker(0x104, 5)
setAttacker(0x4c, UInt32(bitPattern: victim.x - 30)); setAttacker(0x50, UInt32(bitPattern: victim.y))
setAttacker(0x138, 0x80000000)
victim.receiveHit(from: &attacker, token: 0x10010000)
var hurt = victim.runtime
precondition(claw_player_actor_word(&hurt, 0x10c) == 95 && hurt.logicState == 31)
precondition(["DAMAGE1", "DAMAGE2"].contains(victim.sequence))
for _ in 0..<200 { victim.advance(held: 0, pressed: 0, stageDelta: 16, animationDelta: 16) }
precondition(victim.runtime.logicState == 24 && victim.failure == nil)
setAttacker(0x104, 200)
victim.receiveHit(from: &attacker, token: 0x10010000)
precondition(victim.runtime.logicState == 5004 && victim.sequence == "FALLDEATH")
for _ in 0..<250 { victim.advance(held: 0, pressed: 0, stageDelta: 16, animationDelta: 16) }
precondition(victim.pendingCommands == [0x803a])
precondition(victim.runtime.logicState == 5004 && victim.failure == nil)
print("PASS native Swift adapter: Level 1 spawn, walking/facing/collision, jump → fall → stand, duck and look-up release, original sprite geometry and loaded image tokens")
print("PASS native hurt animation recovery and lethal fall: original respawn command queued once; command interpretation remains pending")
// Scene scheduling composes with the real native player and retained heap.
var sceneClock: UInt32 = 1000
let scheduledPlayer = try ClawNativePlayer(world: scene.world, assets: assets)
let scheduled = ClawNativeScene(player: scheduledPlayer, clock: { sceneClock })
precondition(scheduled.actorTokens == [0x10002000])
for delta: UInt32 in [0, 18, 19, 37, 99, 100] {
    sceneClock &+= delta
    scheduled.advance(now: sceneClock, delta: delta, accumulated: sceneClock - 1000,
        held: 0x02000000, pressed: delta == 0 ? 0x02000000 : 0)
    precondition(scheduled.lastPassCount == (delta > 18 && delta < 100 ? (delta + 17) / 18 : 1))
    precondition(scheduled.fault == 0 && scheduled.unresolvedDependencies.isEmpty && scheduledPlayer.failure == nil)
}
precondition(scheduledPlayer.x > 689)
let scheduledGround = scheduledPlayer.y
sceneClock &+= 16
scheduled.advance(now: sceneClock, delta: 16, accumulated: sceneClock - 1000, held: 1, pressed: 1)
var scheduledJumpStates: Set<UInt32> = [scheduledPlayer.runtime.logicState]
var scheduledMinimumY = scheduledPlayer.y
for index in 0..<120 {
    sceneClock &+= 16
    scheduled.advance(now: sceneClock, delta: 16, accumulated: sceneClock - 1000,
        held: index < 10 ? 1 : 0, pressed: 0)
    scheduledJumpStates.insert(scheduledPlayer.runtime.logicState)
    scheduledMinimumY = min(scheduledMinimumY, scheduledPlayer.y)
}
precondition(scheduledMinimumY < scheduledGround && scheduledPlayer.y == scheduledGround)
precondition(scheduledJumpStates.contains(4) && scheduledJumpStates.contains(25) && scheduledJumpStates.contains(24))
// Synthetic scanner attacker: this checks composition and callback write-back,
// not recovered enemy gameplay or the uninstantiated WWD object population.
var synthetic = ClawInteractionActor(); synthetic.token = 0x10010000
func setSynthetic(_ offset: Int, _ value: UInt32) {
    withUnsafeMutableBytes(of: &synthetic.actor) { $0.storeBytes(of: value, toByteOffset: offset, as: UInt32.self) }
}
setSynthetic(8, 0x40000); setSynthetic(0x4c, UInt32(bitPattern: scheduledPlayer.x))
setSynthetic(0x50, UInt32(bitPattern: scheduledPlayer.y)); setSynthetic(0x64, 2000)
setSynthetic(0x6c, 0x10011000); setSynthetic(0xd0, 4); setSynthetic(0x104, 5)
setSynthetic(0x138, UInt32(bitPattern: -10)); setSynthetic(0x13c, UInt32(bitPattern: -10))
setSynthetic(0x140, 10); setSynthetic(0x144, 10); synthetic.primary.4 = 0x4bb030
scheduled.adopt(synthetic)
precondition(scheduled.actorTokens == [0x10010000, 0x10002000])
sceneClock &+= 16
scheduled.advance(now: sceneClock, delta: 16, accumulated: sceneClock - 1000, held: 0, pressed: 0)
var scheduledHurt = scheduledPlayer.runtime
precondition(claw_player_actor_word(&scheduledHurt, 0x10c) == 95 && scheduledHurt.logicState == 31)
precondition(scheduled.snapshotActor(0x10002000)!.actor.67 == 95)
precondition(scheduled.fault == 0 && scheduled.unresolvedDependencies.isEmpty)
print("PASS native scene heap/list and player scheduling: 0/18/19/37/99/100ms choices; ordered actual hit scanner → player hit → heap write-back")
let rawPlayer = try ClawNativePlayer(world: scene.world, assets: assets)
var rawClock: UInt32 = 1000
let rawScene = ClawNativeScene(player: rawPlayer, clock: { rawClock })
try rawScene.loadRecoveredObjects(world: scene.world, root: root)
let nativeCamera = rawScene.camera!
let playerHeaderSnapshot = rawScene.snapshotActor(0x10002000)!
precondition(playerHeaderSnapshot.actor.93 != playerHeaderSnapshot.actor.91 &+ 1)
let playerHeader = rawScene.heap.lookup(playerHeaderSnapshot.actor.93, words: 16)!
precondition(playerHeader[0] == 0x513a70 && playerHeader[4] > 0 && playerHeader[5] > 0)
precondition(playerHeader[10] == 0x11 && playerHeader[12] != 0)

for (index, plane) in scene.world.planes.enumerated() {
    let runtimePlane = rawScene.heap.lookup(nativeCamera.planeTokens[index], words: 86)!
    precondition(runtimePlane[0] == 0x513d40 && runtimePlane[1] == UInt32(index) && runtimePlane[2] == plane.flags)
    precondition(runtimePlane[10] == UInt32(plane.width) && runtimePlane[11] == UInt32(plane.height))
    precondition(runtimePlane[28] == 640 && runtimePlane[29] == 480)
    let copiedTiles = rawScene.heap.lookup(runtimePlane[8], words: UInt32(plane.tiles.count))!
    precondition(Array(UnsafeBufferPointer(start: copiedTiles, count: plane.tiles.count)) == plane.tiles.map { UInt32(bitPattern: Int32($0)) })
    let rows = rawScene.heap.lookup(runtimePlane[9], words: UInt32(plane.height))!
    precondition(Array(UnsafeBufferPointer(start: rows, count: plane.height)) == (0..<plane.height).map { UInt32($0 * plane.width) })
}
precondition(nativeCamera.loaderFailure == nil)
print("PASS all Level1 original plane constructors/loaders, owned raw tiles/row offsets and640x480 startup projection")
let cameraBefore = rawScene.snapshotActor(rawScene.cameraActorToken)!
precondition(cameraBefore.actor.0 == 0x5137b0 && cameraBefore.actor.25 == 9999)
precondition(cameraBefore.primary.4 == 0x486240 && cameraBefore.primary.5 == 0 && cameraBefore.primary.7 == 0)
// Keep the actual keyboard poll boundary: a held transition creates one edge;
// the next poll consumes it, and a released low-bit-only tap is not a held key.
nativeCamera.setInput(held: 0x02000000, pressed: 0x02000000)
nativeCamera.entry(0x430ec0, receiver: nativeCamera.inputToken)
precondition(nativeCamera.held == 0x02000000 && nativeCamera.pressed == 0x02000000)
nativeCamera.entry(0x430ec0, receiver: nativeCamera.inputToken)
precondition(nativeCamera.held == 0x02000000 && nativeCamera.pressed == 0)
nativeCamera.setInput(held: 0, pressed: 1)
nativeCamera.entry(0x430ec0, receiver: nativeCamera.inputToken)
precondition(nativeCamera.held == 0 && nativeCamera.pressed == 0)
let rawStartX = rawPlayer.x
precondition(nativeCamera.nativeWorld!.flags == 3 && nativeCamera.nativeWorld!.descriptionTokens.count == 938)
precondition(nativeCamera.nativeWorld!.gridBatches.reduce(0) { $0 + Int($1.count) } == 1479)
precondition(nativeCamera.nativeWorld!.codecCalls == 1 && nativeCamera.nativeWorld!.unresolvedServices.isEmpty)
for index in 0..<10 {
    rawClock &+= 16
    rawScene.advance(now: rawClock, delta: 16, accumulated: rawClock - 1000, held: 0x02000000,
        pressed: index == 0 ? 0x02000000 : 0)
}
if !(rawPlayer.x > rawStartX && rawPlayer.sequence == "WALK") {
    FileHandle.standardError.write(Data("RAW WALK x=\(rawPlayer.x) y=\(rawPlayer.y) state=\(rawPlayer.runtime.logicState) sequence=\(rawPlayer.sequence) fault=\(rawScene.fault) unresolved=\(rawScene.unresolvedDependencies) failure=\(String(describing: rawPlayer.failure))\n".utf8))
}
precondition(rawPlayer.x > rawStartX && rawPlayer.sequence == "WALK")
rawScene.rendering!.render(world: 0x60003000, actors: rawScene.containerToken)
precondition(rawScene.rendering!.fault == 0 && rawScene.rendering!.unknownServices.isEmpty)
precondition(rawScene.rendering!.commands.count > 50 && rawScene.rendering!.graphicsCalls > 50 && rawScene.rendering!.actorDrawCalls > 0)
precondition(rawScene.unresolvedDependencies.isEmpty)
precondition(rawScene.frameRuntime!.frameCount == 10 && rawScene.frameRuntime!.presentationCount == 10)
precondition(Array(rawScene.frameRuntime!.events.suffix(5)) == [0x4cb9b0, ClawNativeFrame.presentFunction, 0x46c2c0, 0x4b98b0, 0x4d2000])
precondition(rawScene.rendering!.frameCount == 11 && rawScene.frameRuntime!.fault == 0)
print("PASS original singleplayer outer frame → three-plane world/image renderer → native presentation → message timers → final residency, with cached draw commands")

let cameraAfter = rawScene.snapshotActor(rawScene.cameraActorToken)!
precondition(cameraAfter.primary.5 != 0 && cameraAfter.primary.7 == 24)
let cameraPosition = rawScene.heap.lookup(cameraAfter.primary.5, words: 5)!
let mainProjection = nativeCamera.mainProjection!
precondition(mainProjection.cameraX &+ 320 == cameraPosition[0])
precondition(mainProjection.cameraY &+ 240 == cameraPosition[1])
precondition(mainProjection.extentX > 640 && mainProjection.extentY > 480)
precondition(nativeCamera.platformCalls > 0 && nativeCamera.fault == 0 && nativeCamera.unknownPlatformSlots.isEmpty)
precondition(rawScene.heap.lookup(0x10005000, words: 78)![68] == rawPlayer.runtime.privateWords.68)
print("PASS native original camera creation, retained follow, fixed640x480 projection and held/pressed keyboard poll edges")
for _ in 0..<40 {
    rawClock &+= 16
    rawScene.advance(now: rawClock, delta: 16, accumulated: rawClock - 1000, held: 0, pressed: 0)
}
precondition(rawPlayer.runtime.logicState == 24)
rawClock &+= 16
rawScene.advance(now: rawClock, delta: 16, accumulated: rawClock - 1000, held: 1, pressed: 1)
precondition(rawPlayer.runtime.logicState == 4 && rawPlayer.sequence == "JUMP")
var rawStates: Set<UInt32> = [4]
for _ in 0..<120 {
    rawClock &+= 16
    rawScene.advance(now: rawClock, delta: 16, accumulated: rawClock - 1000, held: 0, pressed: 0)
    rawStates.insert(rawPlayer.runtime.logicState)
}
precondition(rawStates.contains(25) && rawPlayer.runtime.logicState == 24)
precondition(rawScene.fault == 0 && rawScene.unresolvedDependencies.isEmpty && rawPlayer.failure == nil)
precondition(rawPlayer.runtime.actor.100 != 0 && rawPlayer.runtime.actor.101 != 0)
print("PASS raw scene animation caller → player WALK/JUMP/FALL/STAND chain with original grid activation and12 dormant Rat records")
// Retain the real player private delay and camera actor across look-down and
// release. This catches host write-back or stage ordering errors invisible in
// independent camera bodies.
for index in 0..<110 {
    rawClock &+= 16
    rawScene.advance(now: rawClock, delta: 16, accumulated: rawClock - 1000,
        held: 0x08000000, pressed: index == 0 ? 0x08000000 : 0)
}
let duckCamera = rawScene.snapshotActor(rawScene.cameraActorToken)!
precondition(rawPlayer.runtime.logicState == 26 && rawPlayer.runtime.privateWords.68 == 0)
precondition(duckCamera.primary.7 == 26)
let duckPosition = rawScene.heap.lookup(duckCamera.primary.5, words: 5)!
precondition(duckPosition[3] == UInt32(bitPattern: rawPlayer.y) &+ 200)
for _ in 0..<90 {
    rawClock &+= 16
    rawScene.advance(now: rawClock, delta: 16, accumulated: rawClock - 1000, held: 0, pressed: 0)
}
precondition(rawPlayer.runtime.logicState == 24 && rawScene.snapshotActor(rawScene.cameraActorToken)!.primary.7 == 24)
precondition(rawScene.fault == 0 && nativeCamera.fault == 0 && rawPlayer.failure == nil)
print("PASS retained player delay → camera look-down state → release and ordinary follow")

let enemyPlayer = try ClawNativePlayer(world: scene.world, assets: assets)
var enemyClock: UInt32 = 1000
let enemyScene = ClawNativeScene(player: enemyPlayer, clock: { enemyClock })
try enemyScene.loadRecoveredObjects(world: scene.world, root: root)
print("POPULATION enemies=\(enemyScene.enemies.count) humanoids=\(enemyScene.humanoids.count) pickups=\(enemyScene.loot?.pickups.count ?? -1) scenery=\(enemyScene.sceneryTokens.count) platforms=\(enemyScene.platforms!.tokens.count) pegs=\(enemyScene.pegs!.tokens.count) excluded=\(enemyScene.uninstantiatedObjectCount) active=\(enemyScene.actorTokens.count)")
precondition(enemyScene.enemies.count == 12 && enemyScene.humanoids.count == 42)
let initialPickups = enemyScene.loot!.pickups.count
precondition(initialPickups == 458 && enemyScene.sceneryTokens.count == 594 && enemyScene.platforms!.tokens.count == 31 && enemyScene.pegs!.tokens.count == 120 && enemyScene.soundTriggers!.tokens.count == 81 && enemyScene.singleCrates!.tokens.count == 34 && enemyScene.checkpoints!.tokens.count == 9 && enemyScene.uninstantiatedObjectCount == 0)
let initialPopulation = 54 + initialPickups + enemyScene.sceneryTokens.count + enemyScene.platforms!.tokens.count + enemyScene.pegs!.tokens.count + enemyScene.soundTriggers!.tokens.count + enemyScene.singleCrates!.tokens.count + enemyScene.checkpoints!.tokens.count + enemyScene.curses!.originalRecords.count + enemyScene.breakables!.originalRecords.count + enemyScene.specialPowerups!.originalRecords.count
precondition(enemyScene.uninstantiatedObjectCount + initialPopulation == 1479)
let actionPlaneToken = enemyScene.camera!.planeTokens[scene.world.planes.firstIndex(where: { $0.flags & 1 != 0 })!]
let gridToken = enemyScene.heap.lookup(actionPlaneToken, words: 45)![44]
let spatialGrid = enemyScene.heap.lookup(gridToken, words: 28)!
let spatialLayers = (1...3).map { enemyScene.heap.lookup(spatialGrid[$0], words: 17)! }
precondition(spatialLayers.map { $0[7] } == [4608,576,18432])
// Source WWD sound records are inserted directly into the actor list; other
// populations occupy the three source spatial layers. Five engine actors are
// player/camera/MultiStats/two speech controllers, outside the WWD partition.
precondition(spatialLayers.reduce(UInt32(0), { $0 + $1[2] }) + UInt32(enemyScene.actorTokens.count - 5) == UInt32(initialPopulation))
precondition(enemyScene.actorTokens.contains(0x10002000) && enemyScene.actorTokens.contains(enemyScene.cameraActorToken))
precondition(enemyScene.enemies.values.allSatisfy { !enemyScene.actorTokens.contains($0.token) })
for enemy in enemyScene.enemies.values {
    precondition(enemy.generic.pointee.enemyToken == 0 && enemyScene.snapshotActor(enemy.token)!.primary.7 == 0)
    precondition(enemyScene.heap.lookup(enemy.token, words: 128)![37] != 0)
}

let skullImages = try enemyScene.objectResources!.images(name: "LEVEL_SKULL")!
precondition(Set(skullImages.identities.keys) == [0])
let missingCande = try enemyScene.objectResources!.images(name: "LEVEL_CANDELABRASINGLE")
let missingManical = try enemyScene.objectResources!.sequence(name: "LEVEL_MANICALS_MANICAL")
let missingManicalShort = try enemyScene.objectResources!.sequence(name: "LEVEL_MANICALS_M")
let originalManicles = try enemyScene.objectResources!.sequence(name: "LEVEL_MANICLES_MANICAL")
precondition(missingCande == nil && missingManical == nil && missingManicalShort == nil && originalManicles != nil)
let ratImages = try enemyScene.objectResources!.images(name: "LEVEL_RAT")!
let bombImages = try enemyScene.objectResources!.images(name: "LEVEL_RATBOMB")!
for id in Set(ratImages.identities.keys).intersection(bombImages.identities.keys) {
    precondition(ratImages.identities[id] != bombImages.identities[id])
}
for index in 0..<180 {
    enemyClock &+= 16
    enemyScene.advance(now: enemyClock, delta: 16, accumulated: UInt32((index + 1) * 16), held: 0, pressed: 0)
}
precondition(enemyScene.actorTokens.contains(0x10002000) && enemyScene.actorTokens.contains(enemyScene.cameraActorToken))
precondition(enemyScene.enemies.values.allSatisfy { !enemyScene.actorTokens.contains($0.token) })
let originalRats = enemyScene.enemies.values.sorted { $0.token < $1.token }
for enemy in originalRats {
    // Visit each real Rat using synthetic player/camera placement. The original
    // grid body selects/inserts it; its gameplay initialization remains dormant
    // until actual scene scheduling dispatches its callback.
    let before = enemyScene.snapshotActor(enemy.token)!
    var visitor = enemyPlayer.sceneSnapshot()
    visitor.actor.19 = before.actor.19 &+ 90; visitor.actor.20 = before.actor.20
    var groundedVisitor = ClawCollisionActor(snapshot: visitor)
    _ = enemyPlayer.collision.placeOnGround(actor: &groundedVisitor)
    visitor.actor.19 = groundedVisitor.x; visitor.actor.20 = groundedVisitor.y
    enemyPlayer.acceptSceneSnapshot(visitor)
    enemyScene.camera!.entry(0x42d5f0, receiver: 0x60003000, argument0: visitor.actor.19, argument1: visitor.actor.20)
    for _ in 0..<6 {
        enemyClock &+= 16
        enemyScene.advance(now: enemyClock, delta: 16, accumulated: enemyClock - 1000, held: 0, pressed: 0)
    }
    precondition(enemyScene.actorTokens.contains(enemy.token))
    precondition(enemy.generic.pointee.enemyToken != 0 && enemy.failure == nil && enemy.unresolved.isEmpty)
    precondition(enemy.state.pointee.actor.67 == 1 && enemy.state.pointee.actor.65 == 5)
    precondition(enemy.state.pointee.actor.28 != 0 && enemy.state.pointee.actor.30 != 0)
    // Exercise a synthetic distant residency query directly, in addition to
    // the ordinary outer frame's now-connected final residency call.
    enemyScene.spatial(0x4d4d10, receiver: gridToken, arguments: [689, 4730])
    precondition(!enemyScene.actorTokens.contains(enemy.token))
    precondition(enemyScene.heap.lookup(enemy.token, words: 128)![37] != 0)
    precondition(enemyScene.fault == 0 && enemyScene.unresolvedDependencies.isEmpty)
}
precondition(originalRats.allSatisfy { !enemyScene.actorTokens.contains($0.token) })
precondition(spatialLayers.reduce(UInt32(0), { $0 + $1[2] }) >= 12)
precondition((enemyScene.spatialCalls[0x4d1fd0] ?? 0) > 180 && (enemyScene.spatialCalls[0x4d4d10] ?? 0) == 12)
print("PASS all12 actual Rat records: native grid/cells → camera-range activation → original constructor/binders/controllers → dormant reinsertion; player visits are synthetic")

let throwingRat = enemyScene.enemies.values.sorted { $0.token < $1.token }.first { enemy in
    var visitor = enemyPlayer.sceneSnapshot()
    visitor.actor.19 = enemy.state.pointee.actor.19 &+ 90; visitor.actor.20 = enemy.state.pointee.actor.20
    var grounded = ClawCollisionActor(snapshot: visitor)
    _ = enemyPlayer.collision.placeOnGround(actor: &grounded)
    return abs(Int(Int32(bitPattern: grounded.y)) - Int(Int32(bitPattern: enemy.state.pointee.actor.20))) < 10
}!
var placement = enemyPlayer.sceneSnapshot()
placement.actor.19 = throwingRat.state.pointee.actor.19 + 90
placement.actor.20 = throwingRat.state.pointee.actor.20
var grounded = ClawCollisionActor(snapshot: placement)
_ = enemyPlayer.collision.placeOnGround(actor: &grounded)
placement.actor.19 = grounded.x; placement.actor.20 = grounded.y
enemyPlayer.acceptSceneSnapshot(placement)
enemyScene.camera!.entry(0x42d5f0, receiver: 0x60003000, argument0: placement.actor.19, argument1: placement.actor.20)
enemyScene.spatial(0x4d1fd0, receiver: actionPlaneToken)
let camera = CGPoint(x: Int(throwingRat.state.pointee.actor.19) - 200, y: Int(throwingRat.state.pointee.actor.20) - 200)
precondition(throwingRat.drawCommand(camera: camera, viewport: CGSize(width: 640, height: 480)) != nil)
for index in 0..<160 where enemyScene.enemies.count == 12 {
    // This focused throw fixture retains the synthetic player placement. The
    // WWD support/platform actors around some Rats are still excluded; freely
    // falling through that partial world would leave the original throw range.
    var target = enemyPlayer.sceneSnapshot()
    target.actor.19 = placement.actor.19; target.actor.20 = placement.actor.20
    var heldPhysics = enemyPlayer.runtime.physics
    heldPhysics.velocity.1 = 0
    enemyPlayer.acceptSceneSnapshot(target, physics: heldPhysics)
    enemyClock &+= 16
    enemyScene.advance(now: enemyClock, delta: 16, accumulated: 2880 + UInt32((index + 1) * 16), held: 0, pressed: 0)
}
let bombs = enemyScene.enemies.values.filter { $0.kind == .bomb }
if !(bombs.count > 0 && throwingRat.failure == nil && throwingRat.unresolved.isEmpty) {
    throwingRat.refresh()
    FileHandle.standardError.write(Data("THROW DIAGNOSTIC bombs=\(bombs.count) enemies=\(enemyScene.enemies.count) RatState=\(throwingRat.state.pointee.primary.7) RatFlags=\(String(throwingRat.state.pointee.actor.2,radix:16)) draw=\(throwingRat.state.pointee.actor.14) xy=\(throwingRat.state.pointee.actor.19)/\(throwingRat.state.pointee.actor.20) player=\(enemyPlayer.x)/\(enemyPlayer.y) state=\(enemyPlayer.runtime.logicState) fault=\(enemyScene.fault) unresolved=\(enemyScene.unresolvedDependencies) enemyFailure=\(String(describing: throwingRat.failure)) enemyUnresolved=\(throwingRat.unresolved)\n".utf8))
}
precondition(bombs.count > 0 && throwingRat.failure == nil && throwingRat.unresolved.isEmpty)
for bomb in bombs {
    if !(bomb.failure == nil && bomb.unresolved.isEmpty && bomb.generic.pointee.enemyToken != 0 && bomb.state.pointee.primary.7 == 2001) {
        FileHandle.standardError.write(Data("BOMB DIAGNOSTIC state=\(bomb.state.pointee.primary.7) private=\(bomb.generic.pointee.enemyToken) failure=\(String(describing: bomb.failure)) unresolved=\(bomb.unresolved) sceneFault=\(enemyScene.fault) frameFault=\(enemyScene.frameRuntime!.fault) imageFault=\(enemyScene.rendering!.fault)\n".utf8))
    }
    precondition(bomb.failure == nil && bomb.unresolved.isEmpty && bomb.generic.pointee.enemyToken != 0)
    precondition(bomb.state.pointee.primary.7 == 2001)
}
print("PASS rendered actual Level1 Rat → original throw election/ANI marker → scene creator → RatBomb constructor and activation; player repositioning is a synthetic test setup")
let firstBomb = bombs.first!, firstBombToken = firstBomb.token
var observedBombStates: Set<UInt32> = [firstBomb.state.pointee.primary.7]
for index in 0..<240 where enemyScene.enemies[firstBombToken] != nil {
    // Follow this projectile with a synthetic player/camera target, so its
    // original offscreen residency deletion does not mask the collision and
    // explosion lifecycle this fixture is specifically exercising.
    if let live = enemyScene.snapshotActor(firstBombToken) {
        var observer = enemyPlayer.sceneSnapshot(), physics = enemyPlayer.runtime.physics
        observer.actor.19 = live.actor.19 &+ 200; observer.actor.20 = live.actor.20
        physics.velocity.1 = 0
        enemyPlayer.acceptSceneSnapshot(observer, physics: physics)
    }
    enemyClock &+= 16
    enemyScene.advance(now: enemyClock, delta: 16, accumulated: enemyScene.gameTime + 16, held: 0, pressed: 0)
    if let bomb = enemyScene.enemies[firstBombToken] {
        observedBombStates.insert(bomb.state.pointee.primary.7)
        _ = bomb.drawCommand(camera: camera, viewport: CGSize(width: 640, height: 480))
        precondition(bomb.failure == nil && bomb.unresolved.isEmpty)
    }
    if enemyScene.fault != 0 || !enemyScene.unresolvedDependencies.isEmpty {
        FileHandle.standardError.write(Data("FLIGHT DIAGNOSTIC index=\(index) sceneFault=\(enemyScene.fault) frameFault=\(enemyScene.frameRuntime!.fault) imageFault=\(enemyScene.rendering!.fault) unresolved=\(enemyScene.unresolvedDependencies) breakableFault=\(enemyScene.breakables!.fault) breakableUnresolved=\(enemyScene.breakables!.unresolved) bodies=\(enemyScene.breakables!.bodies.map{($0.key,$0.value.failure ?? "",$0.value.unresolved)})\n".utf8))
    }
    precondition(enemyScene.fault == 0 && enemyScene.unresolvedDependencies.isEmpty)
    _ = index
}
if !(observedBombStates.contains(2002) && enemyScene.enemies[firstBombToken] == nil) {
    FileHandle.standardError.write(Data("FLIGHT FINAL states=\(observedBombStates) alive=\(enemyScene.enemies[firstBombToken] != nil) raw=\(String(describing: enemyScene.snapshotActor(firstBombToken)?.actor.2))\n".utf8))
}
precondition(observedBombStates.contains(2002) && enemyScene.enemies[firstBombToken] == nil)
precondition(enemyScene.heap.lookup(firstBombToken, words: 1) == nil)
print("PASS retained actual RatBomb flight → real tile collision → explosion → deferred actor/logic/private destruction")
// Original residency rereads the destroyed actor's flags through a cached raw
// pointer. Exercise real native deletion, rather than a fixture that keeps every
// token alive, and require logical ownership to end before the call returns.
var transient = ClawInteractionActor()
transient.token = enemyScene.heap.allocate(bytes: 0x1b4)
transient.actor.0 = 0x5137f0; transient.actor.2 = 0x40; transient.actor.3 = 0x10001000
transient.actor.25 = 5000; transient.actor.27 = enemyScene.heap.allocate(bytes: 0x174)
transient.primary.0 = 0x513740; transient.primary.4 = 0x4bb030
let transientPrimary = transient.actor.27
enemyScene.adopt(transient)
enemyScene.spatial(0x4d4d10, receiver: gridToken, arguments: [spatialGrid[24] &+ 321, 4730])
precondition(!enemyScene.actorTokens.contains(transient.token))
precondition(enemyScene.heap.lookup(transient.token, words: 1) == nil && enemyScene.heap.lookup(transientPrimary, words: 1) == nil)
precondition(enemyScene.fault == 0 && enemyScene.unresolvedDependencies.isEmpty)
print("PASS native spatial destruction with cached post-free field reread and immediate logical token release")

//Exercise the controller owned by the actual native scene, rather than the
//separate worker fixture that constructs another application/state profile.
let resetPlayer = try ClawNativePlayer(world: scene.world, assets: assets)
var resetNow: UInt32 = 1000
let resetScene = ClawNativeScene(player: resetPlayer, clock: { resetNow })
try resetScene.loadRecoveredObjects(world: scene.world, root: root)
let resetWorld = resetScene.worldIdentity
let resetOwner = resetScene.heap.lookup(resetScene.ownerIdentity, words: 478)!
let resetApplication = resetOwner[1]
precondition(resetScene.heap.lookup(resetApplication, words: 77)![0] == 0x50bee4)
precondition(resetOwner[0] == 0x50c264 && resetOwner[0x250/4] == 0x52e1c4)
var lethal = ClawWorldObjectRuntime()
lethal.actor.52 = 4; lethal.actor.65 = 200
lethal.actor.19 = UInt32(bitPattern: resetPlayer.x - 30); lethal.actor.20 = UInt32(bitPattern: resetPlayer.y)
lethal.actor.78 = 0x80000000
resetPlayer.receiveHit(from: &lethal, token: 0x10010000)
resetScene.write(resetPlayer.sceneSnapshot())
for _ in 0..<300 where resetPlayer.pendingCommands.isEmpty {
    resetNow &+= 16
    resetScene.advance(now: resetNow, delta: 16, accumulated: resetNow - 1000, held: 0, pressed: 0)
}
precondition(resetPlayer.pendingCommands == [0x803a])
let beforeResetTime = resetScene.gameTime
let beforeResetRendering = resetScene.rendering!.frameCount
precondition(resetScene.processPlayerCommands())
if resetScene.fault != 0 {
    FileHandle.standardError.write(Data("RESPAWN DIAGNOSTIC fault=\(resetScene.fault) unresolved=\(resetScene.respawn!.unresolvedServices) player=\(resetPlayer.unresolvedDependencies) state=\(resetPlayer.runtime.logicState)\n".utf8))
}
precondition(resetScene.fault == 0 && resetScene.respawn!.unresolvedServices.isEmpty)
precondition(resetPlayer.runtime.logicState == 24 && resetPlayer.x == 689 && resetPlayer.y == 4730)
precondition(resetPlayer.runtime.privateWords.18 == 100 && resetPlayer.runtime.privateWords.31 == 2 && resetPlayer.runtime.privateWords.32 == 1)
precondition(resetPlayer.runtime.privateWords.72 == 20000 && resetScene.worldIdentity == resetWorld)
precondition(resetScene.gameTime == beforeResetTime && resetScene.currentClockSnapshot.deltaMilliseconds == 0)
precondition(resetScene.rendering!.frameCount == beforeResetRendering + 1 && resetScene.fadeRequests.count == 2)
precondition(resetPlayer.pendingCommands.isEmpty && resetScene.respawn!.consumedCommands == [0x803a])
precondition(resetPlayer.unresolvedDependencies.isEmpty)
resetNow &+= 16
resetScene.advance(now: resetNow, delta: 16, accumulated: beforeResetTime + 16, held: 0x02000000, pressed: 0x02000000)
precondition(resetPlayer.runtime.logicState == 8 && resetScene.fault == 0)
print("PASS scene-owned queued803a → source46be40/state23 → two refresh passes → render/present → clock publication and walking continuation; fades are explicit transport requests")

// All actual humanoids are elected by the original spatial grid and scheduled
// by the ordinary outer frame. Player/camera visits are synthetic test setup;
// unrecovered speech/particle calls are measured separately, never hidden.
let populationPlayer = try ClawNativePlayer(world: scene.world, assets: assets)
var populationNow: UInt32 = 1000
let populationScene = ClawNativeScene(player: populationPlayer, clock: { populationNow })
try populationScene.loadRecoveredObjects(world: scene.world, root: root)
let actualHumanoids = populationScene.humanoids.values.sorted { $0.token < $1.token }
var humanoidServices: Set<UInt32> = []
for body in actualHumanoids {
    let original = populationScene.snapshotActor(body.token)!
    var visitor = populationPlayer.sceneSnapshot(), physics = populationPlayer.runtime.physics
    visitor.actor.19 = original.actor.19 &+ 120; visitor.actor.20 = original.actor.20
    // Keep the source record position for this activation fixture. Grounding a
    // visitor through the still-excluded platform population can relocate it
    // outside the target cell before the camera ever elects that target.
    physics.velocity.1 = 0
    var privateWords = populationPlayer.runtime.privateWords; privateWords.72 = 20000
    withUnsafeBytes(of: &privateWords) {
        populationPlayer.acceptSceneSnapshot(visitor, physics: physics, privateWords: $0.bindMemory(to: UInt32.self).baseAddress!)
    }
    populationScene.camera!.entry(0x42d5f0, receiver: 0x60003000, argument0: visitor.actor.19, argument1: visitor.actor.20)
    for _ in 0..<12 {
        populationNow &+= 16
        populationScene.advance(now: populationNow, delta: 16, accumulated: populationNow - 1000, held: 0, pressed: 0)
    }
    body.refresh()
    if body.failure != nil || populationScene.fault != 0 || body.generic.pointee.enemyToken == 0 || body.state.pointee.primary.7 == 0 {
        print("HUMANOID DIAGNOSTIC token=\(body.token) kind=\(body.kind) failure=\(String(describing:body.failure)) state=\(body.state.pointee.primary.7) sceneFault=\(populationScene.fault) services=\(body.unresolved) original=\(original.actor.19)/\(original.actor.20) visitor=\(populationPlayer.x)/\(populationPlayer.y) active=\(populationScene.actorTokens.contains(body.token))")
    }
    if populationScene.fault != 0 { print("SCENE SOURCE FAULT",populationScene.checkpoints!.fault,populationScene.checkpoints!.missingSpans,populationScene.singleCrates!.fault,populationScene.singleCrates!.unresolved,populationScene.rendering!.fault,populationScene.rendering!.unknownServices,populationScene.frameRuntime!.fault,populationScene.camera!.fault,populationScene.unresolvedDependencies) }
    precondition(body.failure == nil && populationScene.fault == 0)
    precondition(body.generic.pointee.enemyToken != 0 && body.state.pointee.primary.7 != 0)
    humanoidServices.formUnion(body.unresolved)
}
print("PASS all42 actual Officer/Soldier records: source grid election → ordinary outer frame → retained native constructors/controllers; visits and idle-timer seeding are synthetic")
print("HUMANOID remaining services", humanoidServices.sorted().map { String($0, radix: 16) })
let sharedSpeech = populationScene.speech!
print("SPEECH native NPCqueues", sharedSpeech.serviceCounts[0x48ce40] ?? 0, "plays", sharedSpeech.playRequests.count, "controllers", sharedSpeech.actorTokens.count, "fault", sharedSpeech.fault, "services", sharedSpeech.unresolved)
precondition(humanoidServices.isEmpty && sharedSpeech.actorTokens.count == 2)
precondition(sharedSpeech.globals.pointee.clawActorToken != 0 && sharedSpeech.globals.pointee.enemyActorToken != 0)
precondition((sharedSpeech.serviceCounts[0x48ce40] ?? 0) > 0 && !sharedSpeech.playRequests.isEmpty)
precondition(sharedSpeech.fault == 0 && sharedSpeech.unresolved.isEmpty)
// This explicit forced name request exercises the player profile over the same
// shared heap; ordinary source frames perform actual play/follow/expiry. It is
// not an in-level sound-trigger or a fabricated native voice lifetime.
let beforeClawSpeech = sharedSpeech.playRequests.count
precondition(sharedSpeech.service(0x48c8a0, arguments: [0x524e04, 1]) == 1)
for _ in 0..<2 {
    populationNow &+= 16
    populationScene.advance(now: populationNow, delta: 16, accumulated: populationNow - 1000, held: 0, pressed: 0)
}
let clawDialog = populationScene.snapshotActor(sharedSpeech.globals.pointee.clawActorToken)!
let speechSound = populationPlayer.audio!.resolve(name: "CLAW_1001")!
let expectedVoiceDuration = populationPlayer.audio!.duration(resource: speechSound.resourceToken)
precondition(clawDialog.primary.7 == 15 && clawDialog.primary.76 <= expectedVoiceDuration && clawDialog.primary.76 > 0)
precondition(sharedSpeech.playRequests.count > beforeClawSpeech)
precondition(sharedSpeech.playRequests.contains { $0.pool == speechSound.voicePoolToken })
print("PASS actual42 NPC HOME speech queues → raw sound/pool duration → scheduled enemy dialog/play/follow; explicit Claw name queue reaches separate player profile and shared audio transport")

// Select an existing uncollected WWD treasure, then use the real camera/grid
// and interaction scanner. Only the visit position is synthetic: no direct
// award call or hand-elected contact is used in this fixture.
let actualTreasure = populationScene.loot!.pickups.values.sorted { $0.token < $1.token }.first {
    guard let snapshot = $0.snapshot() else { return false }
    return snapshot.primary.4 == 0x46fd10 && snapshot.actor.2 & 0x10000 == 0 && snapshot.actor.89 & 0x200 == 0
}!
let treasureOriginal = actualTreasure.snapshot()!
var treasureVisitor = populationPlayer.sceneSnapshot(), treasurePhysics = populationPlayer.runtime.physics
// Player feet at the treasure's center retain a body rectangle that overlaps
// the original initialized treasure attack rectangle.
treasureVisitor.actor.19 = treasureOriginal.actor.19; treasureVisitor.actor.20 = treasureOriginal.actor.20
// The fixture places a living player in Stand; ordinary source scheduling
// and pickup41ce80 still perform the contact and private/full-runtime commit.
treasureVisitor.primary.7 = 24; treasurePhysics.velocity.1 = 0
populationPlayer.acceptSceneSnapshot(treasureVisitor, physics: treasurePhysics)
populationScene.camera!.entry(0x42d5f0, receiver: 0x60003000, argument0: treasureVisitor.actor.19, argument1: treasureVisitor.actor.20)
let scoreBeforeTreasure = populationPlayer.runtime.actor.62
let effectsBeforeTreasure = populationScene.effects!.events.count
var awardedPointTokens: [UInt32] = []
populationScene.effects!.onCreated = { effect in
    if effect.snapshot()?.primary.4 == 0x473a70 { awardedPointTokens.append(effect.token) }
}
for _ in 0..<40 where actualTreasure.snapshot().map({ $0.actor.89 & 0x200 == 0 }) == true {
    populationNow &+= 16
    populationScene.advance(now: populationNow, delta: 16, accumulated: populationNow - 1000, held: 0, pressed: 0)
}
print("TREASURE DIAGNOSTIC score=\(scoreBeforeTreasure)→\(populationPlayer.runtime.actor.62) raw=\(String(describing:actualTreasure.snapshot()?.actor.89)) value=\(String(describing:actualTreasure.snapshot()?.actor.63)) failure=\(String(describing:actualTreasure.failure)) services=\(actualTreasure.unresolved) effects=\(populationScene.effects!.events.count-effectsBeforeTreasure) fxServices=\(populationScene.effects!.unresolved)")
precondition(actualTreasure.failure == nil && actualTreasure.unresolved.isEmpty)
precondition(actualTreasure.snapshot()!.actor.89 & 0x200 != 0 && populationPlayer.runtime.actor.62 > scoreBeforeTreasure)
for _ in 0..<40 {
    populationNow &+= 16
    populationScene.advance(now: populationNow, delta: 16, accumulated: populationNow - 1000, held: 0, pressed: 0)
}
precondition(populationScene.effects!.events.dropFirst(effectsBeforeTreasure).contains { $0.function == 0x4f6286 && $0.name == "PointsIcon" })
precondition(!awardedPointTokens.isEmpty)
print("POINTS native created", awardedPointTokens.count, "remaining", awardedPointTokens.filter { populationScene.heap.lookup($0, words: 1) != nil }.count)
precondition(populationScene.effects!.unresolved.isEmpty && populationScene.loot!.unresolved.isEmpty)
print("PASS actual WWD treasure → ordinary interaction election → full player score commit → source PointsIcon creator/retained FX; visit is synthetic")
precondition(populationScene.loot!.failure == nil && populationScene.effects!.failure == nil)
precondition(populationScene.unresolvedDependencies.isEmpty && populationPlayer.failure == nil)

// The original Level1 main plane has a real ladder at x1408..1471 and
// y4352..4735. This fixture starts at the real spawn and uses only held/pressed
// inputs and ordinary frames; it does not reposition or force a climb state.
let progressionPlayer = try ClawNativePlayer(world: scene.world, assets: assets)
var progressionNow: UInt32 = 1000
let progressionScene = ClawNativeScene(player: progressionPlayer, clock: { progressionNow })
try progressionScene.loadRecoveredObjects(world: scene.world, root: root)
for index in 0..<400 where progressionPlayer.x < 1438 {
    progressionNow &+= 16
    progressionScene.advance(now: progressionNow, delta: 16, accumulated: progressionNow - 1000,
        held: 0x02000000, pressed: index == 0 ? 0x02000000 : 0)
}
let ladderApproachY = progressionPlayer.y
var progressionStates: Set<UInt32> = []
var minimumProgressionY = progressionPlayer.y
for index in 0..<150 {
    progressionNow &+= 16
    progressionScene.advance(now: progressionNow, delta: 16, accumulated: progressionNow - 1000,
        held: index < 70 ? 0x04000001 : 0x04000000, pressed: index == 0 ? 1 : 0)
    progressionStates.insert(progressionPlayer.runtime.logicState)
    minimumProgressionY = min(minimumProgressionY, progressionPlayer.y)
}
print("LADDER DIAGNOSTIC x=\(progressionPlayer.x) y=\(progressionPlayer.y) approachY=\(ladderApproachY) minimumY=\(minimumProgressionY) states=\(progressionStates.sorted()) player=\(String(describing:progressionPlayer.failure)) services=\(progressionPlayer.unresolvedDependencies) scene=\(progressionScene.fault)")
precondition(progressionStates.contains(27) && minimumProgressionY < ladderApproachY - 200)
precondition(progressionPlayer.failure == nil && progressionPlayer.unresolvedDependencies.isEmpty)
precondition(progressionScene.fault == 0 && progressionScene.unresolvedDependencies.isEmpty)
print("PASS real spawn → ordinary walk inputs → jump/up into actual Level1 ladder → retained source climb; no synthetic placement/state or direct climb call")

// All594 real scenery records retain the source WWD/image/ANI load and cell
// membership. These camera visits are synthetic; ordinary source frames elect
// and execute each callback, including absent resource groups without aliases.
let originalScenery = progressionScene.sceneryTokens.sorted()
var visitedScenery = 0
for token in originalScenery {
    let original = progressionScene.snapshotActor(token)!
    var visitor = progressionPlayer.sceneSnapshot(), physics = progressionPlayer.runtime.physics
    visitor.actor.19 = original.actor.19; visitor.actor.20 = original.actor.20; visitor.primary.7 = 24
    physics.velocity.0 = 0; physics.velocity.1 = 0
    var privateWords = progressionPlayer.runtime.privateWords; privateWords.72 = 20000
    withUnsafeBytes(of: &privateWords) {
        progressionPlayer.acceptSceneSnapshot(visitor, physics: physics, privateWords: $0.bindMemory(to: UInt32.self).baseAddress!)
    }
    progressionScene.camera!.entry(0x42d5f0, receiver: 0x60003000, argument0: visitor.actor.19, argument1: visitor.actor.20)
    for _ in 0..<3 {
        progressionNow &+= 16
        progressionScene.advance(now: progressionNow, delta: 16, accumulated: progressionNow - 1000, held: 0, pressed: 0)
    }
    let current = progressionScene.snapshotActor(token)!
    if progressionScene.fault != 0 || current.actor.2 & 1 == 0 { print("SCENERY DIAGNOSTIC", token, String(current.primary.4,radix:16), current.primary.7, current.actor.2, progressionScene.fault, progressionScene.unresolvedDependencies) }
    precondition(progressionScene.fault == 0 && current.actor.2 & 1 != 0)
    precondition(current.primary.4 == 0x461730 || current.primary.7 != 0)
    visitedScenery += 1
}
precondition(visitedScenery == 594 && progressionScene.unresolvedDependencies.isEmpty)
print("PASS all594 actual scenery records: WWD/source resource binding → grid election → ordinary native callback/retained animation; camera/player visits are synthetic")

// Visit every original platform without electing support by hand. The source
// spatial grid and ordinary callback initialize the retained WWD controller.
let actualPlatforms = progressionScene.platforms!.tokens.sorted()
var movingPlatformVisits = 0
for token in actualPlatforms {
    let original = progressionScene.snapshotActor(token)!
    var visitor = progressionPlayer.sceneSnapshot(), physics = progressionPlayer.runtime.physics
    visitor.actor.19 = original.actor.19 &+ 100; visitor.actor.20 = original.actor.20 &- 80
    visitor.primary.7 = 24; visitor.actor.2 &= ~0x10; visitor.actor.32 = 0
    physics.velocity.0 = 0; physics.velocity.1 = 0
    var privateWords = progressionPlayer.runtime.privateWords; privateWords.72 = 20000
    withUnsafeBytes(of: &privateWords) {
        progressionPlayer.acceptSceneSnapshot(visitor, physics: physics, privateWords: $0.bindMemory(to: UInt32.self).baseAddress!)
    }
    progressionScene.camera!.entry(0x42d5f0, receiver: 0x60003000, argument0: visitor.actor.19, argument1: visitor.actor.20)
    for _ in 0..<15 {
        progressionNow &+= 16
        progressionScene.advance(now: progressionNow, delta: 16, accumulated: progressionNow - 1000, held: 0, pressed: 0)
    }
    let current = progressionScene.snapshotActor(token)!
    if current.primary.7 == 0 || progressionScene.fault != 0 { print("PLATFORM DIAGNOSTIC", token, String(current.primary.4, radix:16), current.primary.7, progressionScene.fault, progressionScene.platforms!.unresolved) }
    precondition(current.primary.7 != 0 && current.actor.2 & 1 != 0 && current.actor.52 == 0x80)
    precondition([current.actor.74,current.actor.75,current.actor.76,current.actor.77].map { Int32(bitPattern:$0) } == [-32,-8,36,64])
    if current.actor.19 != original.actor.19 || current.actor.20 != original.actor.20 { movingPlatformVisits += 1 }
}
precondition(actualPlatforms.count == 31 && movingPlatformVisits > 0)
precondition(progressionScene.platforms!.fault == 0 && progressionScene.platforms!.unresolved.isEmpty)
precondition(progressionScene.fault == 0 && progressionScene.unresolvedDependencies.isEmpty)
print("PASS all31 actual Elevator/Trigger/Start records: source grid activation → ordinary controller → Level1 hit rectangle and clock-driven movement; visits are synthetic")

// All120 original pegs are visited through cell election and ordinary source
// scheduling. Crumble rider/reset and complete toggle phases are independently
// compared; this assertion measures the actual native population/initialization.
let actualPegs = progressionScene.pegs!.tokens.sorted()
for token in actualPegs {
    let original = progressionScene.snapshotActor(token)!
    var visitor = progressionPlayer.sceneSnapshot(), physics = progressionPlayer.runtime.physics
    visitor.actor.19 = original.actor.19 &+ 80; visitor.actor.20 = original.actor.20 &- 100
    visitor.primary.7 = 24; visitor.actor.2 &= ~0x10; visitor.actor.32 = 0
    physics.velocity.0 = 0; physics.velocity.1 = 0
    var privateWords = progressionPlayer.runtime.privateWords; privateWords.72 = 20000
    withUnsafeBytes(of:&privateWords) {
        progressionPlayer.acceptSceneSnapshot(visitor,physics:physics,privateWords:$0.bindMemory(to:UInt32.self).baseAddress!)
    }
    progressionScene.camera!.entry(0x42d5f0,receiver:0x60003000,argument0:visitor.actor.19,argument1:visitor.actor.20)
    for _ in 0..<3 {
        progressionNow &+= 16
        progressionScene.advance(now:progressionNow,delta:16,accumulated:progressionNow-1000,held:0,pressed:0)
    }
    let current = progressionScene.snapshotActor(token)!
    if progressionScene.fault != 0 || current.primary.7 == 0 { print("PEG DIAGNOSTIC", token, String(current.primary.4,radix:16),current.primary.7,progressionScene.fault,progressionScene.pegs!.fault,progressionScene.pegs!.unresolved) }
    precondition(current.actor.2 & 1 != 0 && current.primary.7 != 0)
    let sourceTop:Int32 = current.primary.4 == 0x49d860 || current.primary.4 == 0x49d620 ? -46 : -8
    precondition([current.actor.74,current.actor.75,current.actor.76,current.actor.77].map{Int32(bitPattern:$0)} == [-24,sourceTop,24,64])
}
precondition(actualPegs.count == 120 && progressionScene.pegs!.fault == 0 && progressionScene.pegs!.unresolved.isEmpty)
precondition(progressionScene.fault == 0 && progressionScene.unresolvedDependencies.isEmpty)
print("PASS all120 actual crumble/toggle peg records: source grid activation → ordinary callbacks → source Level1 rectangles; visits are synthetic")

// A synthetic initial placement above an actual moving Elevator allows the
// ordinary source collision/player pipeline to acquire its support token.
let riderPlayer = try ClawNativePlayer(world:scene.world,assets:assets)
var riderNow:UInt32 = 1000
let riderScene = ClawNativeScene(player:riderPlayer,clock:{riderNow})
try riderScene.loadRecoveredObjects(world:scene.world,root:root)
// Activate the actual record, then let its source constructor establish bounds.
let riderToken = riderScene.platforms!.tokens.sorted().first {
    riderScene.snapshotActor($0)!.primary.4 == 0x49e2a0
}!
var riderVisit = riderPlayer.sceneSnapshot()
let dormantRiderPlatform = riderScene.snapshotActor(riderToken)!
riderVisit.actor.19 = dormantRiderPlatform.actor.19; riderVisit.actor.20 = dormantRiderPlatform.actor.20 &- 160
riderPlayer.acceptSceneSnapshot(riderVisit)
riderScene.camera!.entry(0x42d5f0,receiver:0x60003000,argument0:riderVisit.actor.19,argument1:riderVisit.actor.20)
for _ in 0..<3 {
    riderNow &+= 16; riderScene.advance(now:riderNow,delta:16,accumulated:riderNow-1000,held:0,pressed:0)
}
let riderPlatform = riderScene.snapshotActor(riderToken)!
var rider = riderPlayer.sceneSnapshot(), riderPhysics = riderPlayer.runtime.physics
rider.actor.19 = riderPlatform.actor.19
rider.actor.20 = riderPlatform.actor.20 &+ riderPlatform.actor.75 &- rider.actor.73 &- 20
rider.primary.7 = 24; rider.actor.2 &= ~0x10; rider.actor.32 = 0
riderPhysics.velocity.0 = 0; riderPhysics.velocity.1 = 0
var riderPrivate = riderPlayer.runtime.privateWords; riderPrivate.72 = 20000
withUnsafeBytes(of:&riderPrivate) {
    riderPlayer.acceptSceneSnapshot(rider,physics:riderPhysics,privateWords:$0.bindMemory(to:UInt32.self).baseAddress!)
}
riderScene.camera!.entry(0x42d5f0, receiver:0x60003000, argument0:rider.actor.19, argument1:rider.actor.20)
var acquiredRider = false, retainedRiderFrames = 0
for index in 0..<120 {
    riderNow &+= 16
    riderScene.advance(now:riderNow, delta:16, accumulated:riderNow - 1000, held:0, pressed:0)
    let currentPlayer = riderPlayer.sceneSnapshot()
    if currentPlayer.actor.2 & 0x10 != 0 && currentPlayer.actor.32 == riderToken {
        acquiredRider = true; retainedRiderFrames += 1
    }
    if index % 20 == 0 || index == 119 {
        let platform = riderScene.snapshotActor(riderToken)!
        print("RIDER DIAGNOSTIC",index,riderToken, acquiredRider, retainedRiderFrames,riderPlayer.x,riderPlayer.y,currentPlayer.actor.2,currentPlayer.actor.32,platform.actor.19,platform.actor.20,currentPlayer.actor.73,platform.actor.75,riderPlayer.failure as Any,riderPlayer.unresolvedDependencies)
    }
}
precondition(acquiredRider && retainedRiderFrames > 20)
precondition(riderPlayer.failure == nil && riderPlayer.unresolvedDependencies.isEmpty && riderScene.fault == 0)
print("PASS actual moving Elevator → source collision support election → retained ordinary player rider frames; only initial placement/idle-timer seeding is synthetic")

// Exercise the always-scheduled WWD triggers at every original sensor position.
// Position/idle-timer seeding are synthetic; callbacks and speech/play election are
// the original retained graph, including one-shot deletion and busy rejection.
let triggerPlayer = try ClawNativePlayer(world:scene.world,assets:assets)
var triggerNow:UInt32 = 1000
let triggerScene = ClawNativeScene(player:triggerPlayer,clock:{triggerNow})
try triggerScene.loadRecoveredObjects(world:scene.world,root:root)
let triggerRecords = triggerScene.soundTriggers!.originalRecords.values.filter{ClawNativeSoundTriggers.nonAmbientCallbacks.contains($0.primary.4)}.sorted { $0.token < $1.token }
let triggerAudioBefore = triggerPlayer.audio!.playRequests
for original in triggerRecords {
    var visitor = triggerPlayer.sceneSnapshot(), physics = triggerPlayer.runtime.physics
    visitor.actor.19 = original.actor.19;visitor.actor.20 = original.actor.20;visitor.primary.7 = 24
    physics.velocity.0 = 0;physics.velocity.1 = 0
    var privateWords = triggerPlayer.runtime.privateWords;privateWords.72 = 20000
    withUnsafeBytes(of:&privateWords) {
        triggerPlayer.acceptSceneSnapshot(visitor,physics:physics,privateWords:$0.bindMemory(to:UInt32.self).baseAddress!)
    }
    triggerScene.camera!.entry(0x42d5f0,receiver:0x60003000,argument0:visitor.actor.19,argument1:visitor.actor.20)
    for _ in 0..<4 {
        triggerNow &+= 16;triggerScene.advance(now:triggerNow,delta:16,accumulated:triggerNow-1000,held:0,pressed:0)
    }
    precondition(triggerScene.soundTriggers!.initialized.contains(original.token))
    precondition((triggerScene.soundTriggers!.callbackCounts[original.token] ?? 0) >= 2)
    if let current = triggerScene.snapshotActor(original.token) {
        precondition(current.actor.52 == 0x4000000 && current.actor.16 & 1 != 0 && current.primary.7 != 0)
    }
}
print("TRIGGER DIAGNOSTIC",triggerRecords.count,triggerPlayer.audio!.playRequests-triggerAudioBefore,triggerScene.speech!.playRequests.count,triggerScene.soundTriggers!.fault,triggerScene.soundTriggers!.unresolved,triggerScene.fault,triggerPlayer.failure as Any,triggerPlayer.unresolvedDependencies)
precondition(triggerRecords.count == 66 && triggerPlayer.audio!.playRequests > triggerAudioBefore)
precondition(!triggerScene.soundTriggers!.directVoiceRequests.isEmpty)
precondition(triggerScene.soundTriggers!.fault == 0 && triggerScene.soundTriggers!.unresolved.isEmpty)
precondition(triggerScene.fault == 0 && triggerScene.unresolvedDependencies.isEmpty && triggerPlayer.failure == nil)
print("PASS all66 actual sound/dialog trigger records: source callbacks/charge gates → original playback or shared speech queue; sensor visits/idle-timer seeding are synthetic")

let crateRecords = progressionScene.singleCrates!.originalRecords.values.sorted { $0.token < $1.token }
for original in crateRecords {
    var visitor = progressionPlayer.sceneSnapshot(), physics = progressionPlayer.runtime.physics
    visitor.actor.19 = original.actor.19 &+ 100;visitor.actor.20 = original.actor.20 &- 80;visitor.primary.7 = 24
    physics.velocity.0 = 0;physics.velocity.1 = 0
    var privateWords = progressionPlayer.runtime.privateWords;privateWords.72 = 20000
    withUnsafeBytes(of:&privateWords) {
        progressionPlayer.acceptSceneSnapshot(visitor,physics:physics,privateWords:$0.bindMemory(to:UInt32.self).baseAddress!)
    }
    progressionScene.camera!.entry(0x42d5f0,receiver:0x60003000,argument0:visitor.actor.19,argument1:visitor.actor.20)
    for _ in 0..<4 {
        progressionNow &+= 16;progressionScene.advance(now:progressionNow,delta:16,accumulated:progressionNow-1000,held:0,pressed:0)
    }
    precondition(progressionScene.singleCrates!.initialized.contains(original.token))
    let current = progressionScene.snapshotActor(original.token)!
    if progressionScene.singleCrates!.fault != 0 { print("CRATE DIAGNOSTIC",original.token,current.primary.7,progressionScene.singleCrates!.fault,progressionScene.singleCrates!.unresolved) }
    precondition(current.primary.7 == 5 && current.actor.52 == 0x200)
    precondition(current.actor.28 != 0 && current.secondary.4 == 0x4717e0 && current.actor.67 > 0)
}
precondition(crateRecords.count == 34 && progressionScene.singleCrates!.fault == 0 && progressionScene.singleCrates!.unresolved.isEmpty)
precondition(progressionScene.fault == 0 && progressionScene.unresolvedDependencies.isEmpty)
print("PASS all34 actual single-crate records: source grid activation → ordinary constructor/controller → real CrateHit secondary binding; visits are synthetic")

try verifyNativeCheckpoints()
try verifyNativeAmbientAudio()
try verifyNativeImpactParticles()
try verifyNativeCurseGate()
try verifyNativeCrateCombat()
try verifyNativeKegs()
try verifyNativeStacks()
try verifyNativeKegCarry()
try verifyNativeSpecials(award:true)
try verifyNativeDiskSave()
try verifyNativeSaveSeedBoundary()
try verifyNativeSuperCheckpointStartup()
try verifyNativeSuperCheckpointSave()

print("Movement, PCM effects, original outer frame/render/residency, Rat/Bomb spawn and803a respawn are connected. Remaining WWD actors, wider combat/lift/throw acceptance, full startup/manager timing, music, broader effects, source fade loops and game-over UI remain incomplete")

try verifyNativeHUD()
try verifyNativePistolLaunch()
try verifyNativeMagicLaunch()
try verifyNativeDynamiteLaunch()
try verifyNativeDuckRanged()
try verifyNativeRangedRepeat()
try verifyNativePalette()
try verifyNativeDisplayAutomaticRelease()
try verifyNativeWarpFade()
try verifyNativeElemental()
try verifyNativeSurfaceCopies()
try verifyNativeSurfaceFlip()
try verifyNativePaletteFade()
