import Foundation

/// One interpreter per custom map. Lua sees monotonically allocated handles,
/// never heap tokens. Identity checks reject recycled or freed allocations.
final class ClawCustomLua {
    static let callback: UInt32 = 0x7e100001
    enum Failure: LocalizedError {
        case script(String)
        var errorDescription: String? { if case .script(let s) = self { return s }; return nil }
    }
    private struct Object {
        let token: UInt32
        let identity: ClawTokenHeap.AllocationIdentity
        var name: String
        let root: UInt32
        let scripted: Bool
    }
    private let heap: ClawTokenHeap
    private let resources: ClawNativeMenuResources
    private let scene: UInt32
    private let epoch = UInt32(Date().timeIntervalSince1970)
    private let mapBounds:(UInt32,UInt32)
    private let level: UInt32
    private let entries: [String:UInt32]
    var nativeService: ((String,Double) throws -> Double)?
    private var vm: OpaquePointer?
    private var objects: [UInt32:Object] = [:], byToken: [UInt32:UInt32] = [:]
    private var byID:[UInt32:UInt32] = [:]
    private var hudParents:[UInt32:UInt32] = [:]
    private var next: UInt32 = 1
    private var iterationSnapshot: [UInt32] = []
    private var names: [UInt32:String] = [:]
    private var nativeDepth = 0
    private var loaded = false, secondLoad = false
    private var savedLevelBytes: [UInt32:UInt8] = [:]
    private(set) var events: [[String:Any]] = []
    private(set) var error: String?
    private var dispatches = 0
    private var callbackContext = "map initialization"
    private var eventIndices:[String:Int] = [:]
    private var legacyBuffers:[String:[UInt8]] = [:]
    private var legacySettings:[String:Double] = [:]
    private var legacyRouting = false
    // Finite original operand storage, read by the admitted movement bodies.
    // These are guest data identities only; scripts never receive addresses.
    private static let speedOperands: [(UInt32,Int32)] = [
        (0x418432,225),(0x418439,300),(0x418452,285),
        (0x4187e2,-225),(0x4187e9,-300),(0x418802,-285),
        (0x418b9a,225),(0x418bd0,-225),(0x41b7e6,225),(0x41b818,-225)]
    private static let jumpOperands: [(UInt32,UInt32)] = [
        (0x41b750,0x50bb10),(0x41b714,0x50bb0c),
        (0x41b6de,0x50bb08),(0x41b6a4,0x50bb08)]
    private var savedPhysicsBytes: [UInt32:UInt8] = [:]
    static func installPhysicsOperands(_ heap:ClawTokenHeap) throws {
        let operands = speedOperands.map {($0.0,UInt32(bitPattern:$0.1))} + jumpOperands.map {($0.0,UInt32(250))}
        for (address,value) in operands {
            if heap.lookupBytes(address,count:4) == nil {
                let base = address & ~3
                guard !heap.overlaps(base,count:8) else {throw Failure.script("Physics operand storage overlaps")}
                _ = heap.storeBytes(token:base,count:8)
            }
            var value = value.littleEndian
            withUnsafeBytes(of:&value) {heap.lookupBytes(address,count:4)!.update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:4)}
        }
    }
    private func writePhysics<T>(_ address:UInt32,_ value:T) throws {
        let count = UInt32(MemoryLayout<T>.size)
        guard let bytes = heap.lookupBytes(address,count:count) else {throw Failure.script("Physics storage unavailable")}
        for i in 0..<count where savedPhysicsBytes[address+i] == nil {savedPhysicsBytes[address+i] = bytes[Int(i)]}
        var value = value
        withUnsafeBytes(of:&value) {bytes.update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:Int(count))}
    }
    private func restorePhysics() {
        for (address,value) in savedPhysicsBytes {heap.lookupBytes(address,count:1)?.pointee = value}
        savedPhysicsBytes.removeAll()
    }
    private var privateKinds:[UInt32:String] = [:]
    private var poisonCounters:[UInt32:UInt32] = [:]
    private static let legacyNames = ["DeathSound":"LEVEL_DEATHTILE","BulletImage":"GAME_BULLETS","BossName":"LEVEL_BOSSNAME","DefeatVoice":"LEVEL_DEFEAT","StageClaw":"LEVEL_STAGING_CLAW","StageBoss":"LEVEL_STAGING_ENEMY"]
    private var plasmaSword = false, plasmaRouting = false
    private var cameraSpeed:[UInt32] = [400,400]
    private var cameraRouting = false
    private lazy var background = ClawNativeBackgroundLogic(heap:heap,resources:resources,scene:scene)
    private var lastGameplay:UInt32?
    private var physicsEvidence:[String:Any] {
        func operand(_ address:UInt32)->Int32 {
            guard let p = heap.lookupBytes(address,count:4) else {return 0}
            return UnsafeRawPointer(p).loadUnaligned(as:Int32.self)
        }
        let cap = heap.lookupBytes(0x534e98,count:8).map {UnsafeRawPointer($0).loadUnaligned(as:Double.self)} ?? 0
        let player = word(0x537e88),logic = word(player+0x6c),pd = word(logic+0x14)
        let velocity = heap.lookupBytes(0x534de8,count:8).map {UnsafeRawPointer($0).loadUnaligned(as:Double.self)} ?? 0
        return ["speeds":Self.speedOperands.map{operand($0.0)},"jump_bases":Self.jumpOperands.map{operand($0.0)},"fall_cap":cap,"modified":!savedPhysicsBytes.isEmpty,
                "player":["x":Int32(bitPattern:word(player+0x4c)),"y":Int32(bitPattern:word(player+0x50)),"state":word(logic+0x1c),"speed_x":Int32(bitPattern:word(player+0x148)),"velocity_y":velocity,"frame_ms":word(0x5430c4),"jump_hold":word(pd+0x118),"jump_peak":Int32(bitPattern:word(pd+0x64)),"running_timer":word(pd+0x114),"powerup":word(0x534eac),"jordan":word(0x537220)]]
    }
    var evidence: [String:Any] { ["events":events,"dispatches":dispatches,"objects":objects.count,"error":error ?? "", "core_replacement_executed":false,"physics":physicsEvidence] }
    init(package:ClawCustomAssets, saveDirectory:URL?, world:ClawWorld, level:UInt32, scene:UInt32, heap:ClawTokenHeap, resources:ClawNativeMenuResources, entries:[String:UInt32]) throws {
        let main = world.planes.first(where:{$0.flags & 1 != 0})!
        mapBounds = (UInt32(main.width*main.tileWidth),UInt32(main.height*main.tileHeight))
        self.heap = heap;self.resources = resources;self.scene = scene;self.level = level;self.entries = entries
        for object in world.planes.flatMap(\.objects) where object.logic == "CustomLogic" {
            let id = UInt32(bitPattern:Int32(object.id))
            guard names[id] == nil else {throw Failure.script("Ambiguous CustomLogic object ID \(id)")}
            names[id] = object.name
        }
        vm = claw_lua_create(Unmanaged.passUnretained(self).toOpaque(),customLuaService)
        guard vm != nil else {throw Failure.script("Lua interpreter allocation or bootstrap failed")}
        guard let saveDirectory else {throw Failure.script("Map save directory unavailable")}
        try FileManager.default.createDirectory(at:saveDirectory,withIntermediateDirectories:true)
        guard claw_lua_save_root(vm,saveDirectory.path,package.worldURL.deletingPathExtension().lastPathComponent) == 1 else {throw Failure.script("Map save directory denied")}
        for path in package.files.keys.sorted() where path.hasSuffix(".TXT") {
            if let data = try package.data(path) {
                _ = data.withUnsafeBytes { bytes in path.withCString { name in
                    claw_lua_data_file(vm,name,bytes.bindMemory(to:CChar.self).baseAddress,data.count)
                }}
            }
        }
        for path in package.files.keys.sorted() where path.hasSuffix(".LUA") && (path.hasPrefix("LOGICS/") || path.hasPrefix("MODULES/")) {
            // The hidden empty logic is an editor artifact, not a dispatch name.
            if path == "LOGICS/.LUA" {continue}
            if let data = try package.data(path) {
                let ok = data.withUnsafeBytes { bytes in path.withCString { name in
                    claw_lua_file(vm,name,bytes.bindMemory(to:CChar.self).baseAddress,data.count)
                }}
                guard ok == 1 else {throw Failure.script("Lua source exceeds limit: \(path)")}
            }
        }
        for path in package.files.keys.sorted() where path.hasPrefix("MODULES/") && ["DLL","SO","DYLIB"].contains(URL(fileURLWithPath:path).pathExtension) {
            let name = String(path.dropFirst(8)).split(separator:".").dropLast().joined(separator:".").replacingOccurrences(of:"/",with:".")
            try evaluate("_nativeModule("+Self.literal(name)+","+Self.literal(path)+")")
        }
        // Advertise only actual registered built-ins, with their native callback.
        // The dialect version is not permission to ignore unsupported services.
        for name in entries.keys.sorted() where name.withCString({claw_logic_registry_find($0)}) != nil {
            try evaluate("_builtin("+Self.literal(name)+")")
        }
        try evaluate("function GetMapFolder() return "+Self.literal("Custom/"+package.worldURL.deletingPathExtension().lastPathComponent)+" end")
        try evaluate(ClawCustomPalette.lua)
    }
    deinit {restorePhysics();claw_lua_close(vm)}
    private static func literal(_ text:String)->String {"\""+text.replacingOccurrences(of:"\\",with:"\\\\").replacingOccurrences(of:"\"",with:"\\\"")+"\""}
    func evaluate(_ text:String) throws {guard text.withCString({claw_lua_eval(vm,$0)}) == 1 else {throw failure()}}
    func checkImplementedAPIs(_ names:[String]) throws {
        for name in names {try evaluate("_assertImplemented("+Self.literal(name)+")")}
    }
    private func failure()->ClawCustomCapabilities.Failure {ClawCustomCapabilities.runtime(String(cString:claw_lua_error(vm)),context:callbackContext)}
    private func record(_ value:[String:Any]) {
        let key = "\(value["hook"] ?? "")/\(value["callback"] ?? "")/\(value["builtin"] ?? "")/\(value["handle"] ?? "")/\(value["level_array"] ?? "")/\(value["service"] ?? "")"
        if let i = eventIndices[key] {events[i] = value}
        else if events.count < 200 {eventIndices[key] = events.count;events.append(value)}
    }
    func hook(_ name:String) throws {
        callbackContext = "hook \(name)"
        guard name.withCString({claw_lua_hook(vm,$0)}) == 1 else {throw failure()}
        record(["hook":name])
    }
    func mapLoaded() throws {
        if !loaded {
            guard claw_lua_start(vm) == 1 else {throw failure()}
            loaded = true;try hook("OnMapLoad")
        }
    }
    func end() {
        do {try hook("OnLevelEnd")} catch {self.error = error.localizedDescription}
        for h in objects.keys.sorted() {
            if let o = objects[h],heap.allocationIdentity(at:o.token,count:0x1b4) === o.identity {
                do {try dispatch(h,"destroy")} catch {self.error = error.localizedDescription}
            }
        }
        for (address,value) in savedLevelBytes {heap.lookupBytes(address,count:1)?.pointee = value}
        savedLevelBytes.removeAll();restorePhysics();objects.removeAll();byToken.removeAll()
    }
    private func word(_ token:UInt32)->UInt32 {heap.lookup(token,words:1)?.pointee ?? 0}
    private func handle(_ token:UInt32, name:String? = nil)->UInt32? {
        if let h = byToken[token], let o = objects[h], heap.allocationIdentity(at:token,count:0x1b4) === o.identity {return h}
        guard let identity = heap.allocationIdentity(at:token,count:0x1b4) else {return nil}
        let logic = word(token+0x6c), id = word(logic+4)
        guard let name = (name?.isEmpty == false ? name:nil) ?? names[id] ?? name else {return nil}
        let h = next;next += 1
        objects[h] = Object(token:token,identity:identity,name:name,root:word(logic+0x10),scripted:word(logic+0x10) == Self.callback);byToken[token] = h
        return h
    }
    private func dispatch(_ h:UInt32,_ event:String,other:UInt32 = 0) throws {
        guard let object = objects[h] else {throw Failure.script("StaleHandle: \(h)")}
        guard object.scripted else {return}
        callbackContext = "object \(object.name) (handle \(h)), callback \(event)"
        let ok = object.name.withCString { n in event.withCString { e in claw_lua_object(vm,h,n,e,other) }}
        guard ok == 1 else {throw failure()}
        dispatches += 1
        if event != "init" {
            let a = object.token
            record(["callback":event,"name":object.name,"handle":h,"x":word(a+0x4c),"y":word(a+0x50),
                    "move_rect":(0..<4).map{Int32(bitPattern:word(a+0x118+UInt32($0*4)))},
                    "state":Int32(bitPattern:word(word(a+0x6c)+0x1c)),"health":Int32(bitPattern:word(a+0x10c)),"frame":word(a+0x16c),
                    "hit_rect":(0..<4).map{Int32(bitPattern:word(a+0x128+UInt32($0*4)))}])
        }
    }
    /// Intercepts callback dispatch only. A built-in runs through the unchanged
    /// source owner with recursion suppressed, retaining the script callback.
    func service(_ f:UInt32,_ r:UInt32,_ args:[UInt32])->UInt32? {
        if let result = background.service(f,r,args) {return result}
        if f == 0x486940,!cameraRouting,args.count == 5,word(0x52be14) != .max {
            cameraRouting = true;defer {cameraRouting = false}
            return resources.invoke(f,r,Array(args.prefix(3))+cameraSpeed)
        }
        if !legacyRouting, [UInt32(0x4c7970),0x4c7900,0x4c79e0,0x4c7a40,0x48c8a0,0x4f6286].contains(f),let text = args.first {
            let bytes = (0..<64).compactMap {heap.lookupBytes(text+UInt32($0),count:1)?.pointee}.prefix(while:{$0 != 0})
            let name = String(decoding:bytes,as:UTF8.self)
            if f == 0x4c7970,name == "GAME_BULLETS",word(word(r+0x6c)+0x10) == 0x40ff80 {
                if let collision = legacySettings["BulletCollision"] ?? legacySettings["BulletHit"] {put(r+0xd0,UInt32(collision))}
                if let speed = legacySettings[word(r+0x148)&0x80000000 == 0 ? "BulletRight":"BulletLeft"] {put(r+0x148,UInt32(bitPattern:Int32(speed)))}
                record(["service":"PiercingBullet","speed":Int32(bitPattern:word(r+0x148)),"collision":word(r+0xd0)])
            }
            if let key = Self.legacyNames.first(where:{$0.value == name})?.key,let buffer = legacyBuffers[key] {
                let replacement = String(decoding:buffer.prefix(while:{$0 != 0}),as:UTF8.self)
                let token = resources.textToken(replacement);defer {resources.release(token)}
                legacyRouting = true;defer {legacyRouting = false}
                var replaced = args;replaced[0] = token
                record(["service":"LegacyResource","name":key,"value":replacement])
                return resources.invoke(f,r,replaced)
            }
        }
        if f == 0x429e30 || f == 0x429e70 {
            let size = Int32(bitPattern:word(word(0x5371fc)+0x68))
            let bound = legacySettings[f == 0x429e30 ? "ViewportDecreaseLimit":"ViewportIncreaseLimit"] ?? (f == 0x429e30 ? 1:10)
            if f == 0x429e30 ? Double(size) <= bound:Double(size) >= bound {record(["service":"ViewportBound","size":size,"bound":bound]);return 0}
        }
        if f == 0x4b54f0,legacySettings["PowerupMusic"] != nil,legacySettings["PowerupMusic"] != 0,let text = args.first {
            let bytes = (0..<8).compactMap {heap.lookupBytes(text+UInt32($0),count:1)?.pointee}.prefix(while:{$0 != 0})
            if String(decoding:bytes,as:UTF8.self) == "POWERUP" {record(["service":"PowerupMusicSuppressed"]);return 0}
        }
        // Plasma uses the existing fire projectile's movement, collision and
        // explosion lifetime. Resource names are session-scoped substitutions,
        // never writes to executable code or shared retail resource bytes.
        if plasmaSword && word(0x534eac) != 0x26b8 {plasmaSword = false}
        if plasmaSword && !plasmaRouting && [UInt32(0x4c7970),0x4c79e0,0x4c7a40].contains(f),let text = args.first {
            var bytes:[UInt8] = []
            for i in 0..<128 {guard let p = heap.lookupBytes(text+UInt32(i),count:1),p.pointee != 0 else {break};bytes.append(p.pointee)}
            let requested = String(decoding:bytes,as:UTF8.self)
            if requested.contains("FIRE") {record(["service":"PlasmaResource:"+requested,"actor":r])}
            let names = ["GAME_FIRESWORDEXPLOSION":"GAME_PLASSWORDEXPLOSION","GAME_EXPLOS_FIRE":"GAME_EXPLOS_PLASMA","GAME_PROJECTILES_FIRESWORD":"GAME_PROJECTILES_PLASMASWORD"]
            if let replacement = names[String(decoding:bytes,as:UTF8.self)] {
                let token = resources.textToken(replacement);defer {resources.release(token)}
                plasmaRouting = true;defer {plasmaRouting = false}
                var replaced = args;replaced[0] = token
                let result = resources.invoke(f,r,replaced)
                guard word(r+0x170) != 0,word(r+0x174) != 0 else {return resources.fail(f)}
                record(["service":replacement.contains("EXPLOS") ? "PlasmaExplosion":"PlasmaProjectile","resource":replacement,"actor":r,"image_group":word(r+0x170),"image_frame":word(r+0x174)])
                return result
            }
        }
        guard error == nil else {return (Self.callback...Self.callback+2).contains(f) ? 0:nil}
        guard nativeDepth == 0 else {return nil}
        do {
            if f == 0x46ace0 || f == 0x46ad70 {
                if !secondLoad {try mapLoaded();try hook("OnMapLoad2");secondLoad = true}
                let now = word(0x537210)
                if lastGameplay != now {try hook("OnGameplay");lastGameplay = now}
            }
            if f == 0x4c9be0, let h = byToken[r] {
                try dispatch(h,"destroy");try evaluate("_forget(\(h))");byToken.removeValue(forKey:r);objects.removeValue(forKey:h)
                return nil
            }
            guard args.count == 1, r == 0, let token = args.first else {return nil}
            let existing = byToken[token]
            let logic = word(token+0x6c)
            if let h = existing,objects[h]?.scripted == true {
                for (slot,event):(UInt32,String) in [(0x70,"hit"),(0x78,"attack")] {
                    let secondary = word(token+slot)
                    if secondary != 0,word(secondary+0x10) == f {
                        let peer = word(token+slot+4), other = byToken[peer] ?? handle(peer,name:"") ?? 0
                        try dispatch(h,event,other:other)
                        return f == Self.callback+1 || f == Self.callback+2 ? 0:nil
                    }
                }
            }
            guard f == Self.callback || (existing != nil && objects[existing!]?.scripted == true && objects[existing!]?.root == f) else {return nil}
            guard let h = handle(token) else {throw Failure.script("CustomLogic: missing object Name or live identity")}
            try dispatch(h,"main")
            for (slot,callback):(UInt32,UInt32) in [(0x70,Self.callback+1),(0x78,Self.callback+2)] where word(token+slot) == 0 {
                let secondary = resources.allocate(0x174)
                heap.lookupBytes(secondary,count:0x174)?.update(repeating:0,count:0x174)
                heap.lookup(secondary,words:1)?.pointee = 0x513740
                heap.lookup(secondary+4,words:1)?.pointee = word(logic+4)
                heap.lookup(secondary+0xc,words:1)?.pointee = scene
                heap.lookup(secondary+0x10,words:1)?.pointee = callback
                heap.lookup(token+slot,words:1)?.pointee = secondary
            }
            return 0
        } catch {
            self.error = error.localizedDescription;record(["error":self.error!]);return 0
        }
    }
    // HUD children use MultiStats' separate list, whose retail updater does
    // not reap Destroy flags. Retire them between callbacks through its list
    // service and the actor's actual deleting destructor.
    func retireHUDObjects() throws {
        for (h,parent) in hudParents.sorted(by:{$0.key<$1.key}) {
            guard let o = objects[h],heap.allocationIdentity(at:o.token,count:0x1b4) === o.identity else {hudParents.removeValue(forKey:h);continue}
            guard word(o.token+8)&0x10000 != 0 else {continue}
            let node = word(o.token+0x68)
            guard node != 0,word(node+8) == o.token else {throw Failure.script("HUD child list identity")}
            guard let nativeService else {throw Failure.script("HUD list service unavailable")}
            _ = try nativeService("Presentation:HUDRemove:\(parent):\(node)",0)
            _ = resources.invoke(word(word(o.token)+4),o.token,[1])
            guard resources.fault == 0 else {throw Failure.script("HUD child retirement")}
            hudParents.removeValue(forKey:h)
        }
    }
    private func put(_ address:UInt32,_ value:UInt32) {heap.lookup(address,words:1)?.pointee = value}
    private func integer(_ text:String) throws -> UInt32 {
        guard let n = Double(text),n.isFinite,n >= Double(Int32.min),n <= Double(UInt32.max) else {throw Failure.script("ValueRange: \(text)")}
        return UInt32(truncatingIfNeeded:Int64(n))
    }
    private func liveHandles() -> [UInt32] {
        // Include dormant serialized objects, not just objects that happened to
        // dispatch a script. The allocation identity rejects recycled tokens.
        for token in heap.debugAllocationBases.sorted() where heap.lookupBytes(token,count:0x1b4) != nil && word(token+0xc) == scene && [UInt32(0x513770),0x5137f0].contains(word(token)) {
            let id = word(token+4)
            _ = handle(token,name:names[id] ?? "")
        }
        return objects.keys.sorted().filter {h in
            guard let o = objects[h] else {return false}
            return heap.allocationIdentity(at:o.token,count:0x1b4) === o.identity && word(o.token+8)&0x10000 == 0
        }
    }
    func gameplaySnapshot() throws -> [[String:Any]] {
        try activeHandles().compactMap { h in
            guard let o = objects[h] else {return nil}
            let a = o.token,l = word(a+0x6c)
            return ["handle":h,"id":word(a+4),"name":o.name,"root":String(format:"0x%x",o.root),
                    "x":Int32(bitPattern:word(a+0x4c)),"y":Int32(bitPattern:word(a+0x50)),
                    "state":Int32(bitPattern:word(l+0x1c)),"health":Int32(bitPattern:word(a+0x10c)),
                    "frame":word(a+0x16c),"flags":word(a+8),"below":word(a+0x88),
                    "move_rect":(0..<4).map{Int32(bitPattern:word(a+0x118+UInt32($0*4)))},
                    "hit_rect":(0..<4).map{Int32(bitPattern:word(a+0x128+UInt32($0*4)))}]
        }
    }
    private func activeHandles() throws -> [UInt32] {
        // The scene's object container owns the active doubly linked list.
        // GetObject deliberately retains the separate all-allocation inventory.
        var node = word(word(scene+8)+20), seen = Set<UInt32>(), result:[UInt32] = []
        while node != 0 {
            guard seen.insert(node).inserted,heap.lookup(node,words:3) != nil else {throw Failure.script("ObjectList: invalid active node")}
            if let h = handle(word(node+8),name:"") {result.append(h)}
            node = word(node)
        }
        return result
    }
    private func cameraActor() throws -> UInt32 {
        // The scene-owned camera is a plain actor, not a WWD sprite. Do not
        // expose it through Lua's sprite handles or cache an allocation token.
        let actors = heap.debugAllocationBases.filter { token in
            heap.lookupBytes(token,count:0x70) != nil && word(token+0xc) == scene &&
            word(word(token+0x6c)+0x10) == 0x486240
        }
        guard actors.count == 1,let actor = actors.first,
              heap.lookupBytes(word(word(actor+0x6c)+0x14),count:20) != nil else {
            throw Failure.script("Scene camera unavailable or uninitialized")
        }
        return actor
    }
    private func gameService(_ key:String,_ value:Double) throws -> Double {
        let parts = key.split(separator:":").map(String.init)
        let player = word(0x537e88),logic = word(player+0x6c),pd = word(logic+0x14)
        switch parts[0] {
        case "MovementSpeed":
            guard value.isFinite else {throw Failure.script("ValueRange: MultClawSpeed")}
            let values = Self.speedOperands.map {floor(Double($0.1)*value+0.5)}
            guard values.allSatisfy({$0 >= Double(Int32.min) && $0 <= Double(Int32.max)}) else {throw Failure.script("ValueRange: MultClawSpeed")}
            for (operand,result) in zip(Self.speedOperands,values) {try writePhysics(operand.0,UInt32(bitPattern:Int32(result)))}
            record(["service":"MultClawSpeed","value":value]);return 0
        case "JumpHeight":
            guard parts.count == 2,let mode = Int(parts[1]),Self.jumpOperands.indices.contains(mode),value.isFinite,value >= 0 else {throw Failure.script("ValueRange: jump height")}
            let (address,factorAddress) = Self.jumpOperands[mode]
            guard let bytes = heap.lookupBytes(factorAddress,count:4) else {throw Failure.script("Jump multiplier unavailable")}
            let factor = Double(UnsafeRawPointer(bytes).loadUnaligned(as:Float.self))
            let base = floor(value/factor)
            guard factor.isFinite,factor > 0,base <= Double(Int32.max) else {throw Failure.script("ValueRange: jump height")}
            try writePhysics(address,UInt32(base))
            record(["service":"JumpHeight:"+String(mode),"height":value,"base":base]);return 0
        case "FallSpeedCap":
            guard value.isFinite,value >= 0 else {throw Failure.script("ValueRange: SetClawFallSpeedCap")}
            try writePhysics(0x534e98,value)
            record(["service":"SetClawFallSpeedCap","value":value]);return 0
        case "Plane":
            guard let nativeService else {throw Failure.script("Plane service unavailable")}
            return try nativeService(key,value)
        case "Palette":
            guard let nativeService else {throw Failure.script("Palette service unavailable")}
            var request = key
            let i = parts.count > 2 && parts[2] == "CLT" ? 4:3
            if parts.count > i,parts[i] == "Token" {throw Failure.script("Image tokens are private")}
            if parts.count > i,parts[i] == "Object" {
                guard i+1 < parts.count,let h = UInt32(parts[i+1]),let o = objects[h] else {throw Failure.script("Invalid image object handle")}
                guard heap.allocationIdentity(at:o.token,count:0x1b4) === o.identity else {throw Failure.script("StaleHandle: image")}
                request = parts.prefix(i).joined(separator:":")+":Token:"+String(word(o.token+0x170))
            }
            return try nativeService(request,value)
        case "Key","KeyEdge","Input","ActionKey","PointerX","PointerY","Resolution","ResolutionWidth","ResolutionHeight","Sound","Text":
            guard let nativeService else {throw Failure.script("NativeService unavailable: \(parts[0])")}
            return try nativeService(key,value)
        case "LoadBaseLevDefaults":
            guard value.rounded() == value,(1...14).contains(value) else {throw Failure.script("Level defaults outside 1...14")}
            var profile = ClawElevatorLevelProfile()
            guard claw_elevator_initialize_profile(UInt32(value),&profile,nil,nil) == 1 else {throw Failure.script("Level defaults unavailable")}
            func copy(_ address:UInt32,_ data:UnsafeRawBufferPointer) throws {
                guard let p = heap.lookupBytes(address,count:UInt32(data.count)) else {throw Failure.script("Level defaults storage unavailable")}
                for i in 0..<data.count where savedLevelBytes[address+UInt32(i)] == nil {savedLevelBytes[address+UInt32(i)] = p[i]}
                UnsafeMutableRawPointer(p).copyMemory(from:data.baseAddress!,byteCount:data.count)
            }
            try withUnsafeBytes(of:&profile.words) {try copy(0x5378a0,$0)}
            try withUnsafeBytes(of:&profile.selectedToken) {try copy(0x537960,$0)}
            try withUnsafeBytes(of:&profile.levelWord) {try copy(0x537964,$0)}
            try withUnsafeBytes(of:&profile.scaleWords) {try copy(0x5262b0,$0)}
            record(["service":"LoadBaseLevDefaults","level":value]);return 0
        case "RemoveSound","RestoreSound":
            guard parts.count == 2,let nativeService else {throw Failure.script("Sound registry unavailable")}
            return try nativeService("Audio:"+key,value)
        case "Voice":
            let name = String(key.dropFirst(6)),text = resources.textToken(name)
            defer {resources.release(text)}
            _ = resources.invoke(0x48c8a0,0,[text,0])
            guard resources.fault == 0 else {throw Failure.script("NativeService: ClawSound")}
            return 0
        case "CameraSpeed":
            guard parts.count == 2 else {throw Failure.script("Camera speed requires two values")}
            let x = try integer(parts[1]),y = try integer(String(value))
            guard x <= 100000,y <= 100000 else {throw Failure.script("Camera speed out of range")}
            cameraSpeed = [x,y];return 0
        case "CameraPoint","CameraSet","CameraX","CameraY":
            let l = word(try cameraActor()+0x6c),data = word(l+0x14)
            guard data != 0 else {throw Failure.script("Camera not initialized")}
            if parts[0] == "CameraX" || parts[0] == "CameraY" {return Double(Int32(bitPattern:word(data+(parts[0] == "CameraX" ? 0:4))))}
            guard parts.count == 2 else {throw Failure.script("Camera point requires two values")}
            let x = try integer(parts[1]),y = try integer(String(value))
            put(0x52be14,x);put(0x52be18,y)
            put(l+0x1c,parts[0] == "CameraSet" ? 9000:8888)
            if parts[0] == "CameraSet" {put(data,x);put(data+4,y);put(data+8,x);put(data+12,y)}
            record(["service":parts[0],"x":Int32(bitPattern:x),"y":Int32(bitPattern:y)])
            return 0
        case "Quake":
            let duration = try integer(String(value))
            guard duration <= 600000 else {throw Failure.script("Earthquake duration out of range")}
            put(0x53c260,word(0x5430c8) &+ duration);return 0
        case "CameraToClaw":
            put(0x52be14,.max);put(0x52be18,.max)
            // OnMapLoad may construct Abyss objects before the scene camera.
            // The cleared forced target above is consumed by its initializer.
            if let actor = try? cameraActor() {
                let logic = word(actor+0x6c),state = word(logic+0x1c)
                if state != 0 && state != 26 && state != 5003 {put(logic+0x1c,24)}
            }
            return 0
        case "Powerup":return Double(plasmaSword && word(0x534eac) == 0x26b8 ? 0x26bb:word(0x534eac))
        case "Boss":
            let boss = word(0x5349dc)
            return Double(boss == 0 ? 0:handle(boss,name:"") ?? 0)
        case "SetBoss":
            if value == 0 {put(0x5349dc,0);return 0}
            guard value.isFinite,value >= 1,value <= Double(UInt32.max),let object = objects[UInt32(value)],
                  heap.allocationIdentity(at:object.token,count:0x1b4) === object.identity else {throw Failure.script("StaleHandle: boss")}
            put(0x5349dc,object.token);return 0
        case "PowerupTime":return Double(word(0x534ea8))
        case "GivePowerup":
            guard parts.count == 2 else {throw Failure.script("ValueType: powerup kind")}
            let kind = try integer(parts[1])
            _ = resources.invoke(0x41f990,0,[player,logic,pd,kind == 0x26bb ? 0x26b8:kind,try integer(String(value))])
            guard resources.fault == 0 else {throw Failure.script("NativeService: ClawGivePowerup")}
            plasmaSword = kind == 0x26bb
            return 0
        case "Epoch":return Double(epoch)+Double(word(0x537210)/1000)
        case "Time":return Double(word(0x537210))
        case "ID":
            let id = try integer(String(value))
            if let h = byID[id],let o = objects[h],heap.allocationIdentity(at:o.token,count:0x1b4) === o.identity,word(o.token+4) == id,word(o.token+8)&0x10000 == 0 {return Double(h)}
            byID.removeValue(forKey:id)
            // Retail's scene order resolves the player/map ID collision (both
            // may be 1). Handle creation order is not scene lookup order.
            let found = try activeHandles().first(where:{word(objects[$0]!.token+4) == id}) ?? liveHandles().first(where:{word(objects[$0]!.token+4) == id}) ?? 0
            if found != 0 {byID[id] = found}
            return Double(found)
        case "Next":
            if value == 0 {iterationSnapshot = try activeHandles();return Double(iterationSnapshot.first ?? 0)}
            guard let i = iterationSnapshot.firstIndex(where:{Double($0) == value}),i+1 < iterationSnapshot.count else {return 0}
            return Double(iterationSnapshot[i+1])
        case "Alive":
            guard value.isFinite,value >= 1,value <= Double(UInt32.max),let o = objects[UInt32(value)] else {return 0}
            return heap.allocationIdentity(at:o.token,count:0x1b4) === o.identity && word(o.token+8)&0x10000 == 0 ? 1:0
        case "Treasure","RegisterTreasure":
            guard parts.count == 2,let i = UInt32(parts[1]),i < 9 else {throw Failure.script("ValueBounds: treasure type")}
            let address:UInt32 = 0x5381e0+i*4
            if parts[0] == "RegisterTreasure" {put(address,word(address) &+ (try integer(String(value))))}
            return Double(word(address))
        case "Goodie":
            guard parts.count == 4 else {throw Failure.script("ValueType: goodie position")}
            let args = try parts.dropFirst().map {try integer($0)}
            _ = resources.invoke(0x4735b0,0,[scene]+args+[try integer(String(value))])
            guard resources.fault == 0 else {throw Failure.script("NativeService: CreateGoodie")}
            record(["service":"CreateGoodie","x":args[0],"y":args[1],"powerup":value]);return 0
        case "Damage","Kill":
            guard value.isFinite,value >= 0 else {throw Failure.script("ValueRange: damage")}
            let damage = parts[0] == "Kill" ? word(player+0x10c):try integer(String(value))
            put(player+0x10c,word(player+0x10c)>damage ? word(player+0x10c)-damage:0)
            if word(player+0x10c) == 0 {_ = resources.invoke(0x417b00,0,[player,logic,pd,0])}
            return 0
        case "FirePistolCheck":
            guard ProcessInfo.processInfo.arguments.contains("--lua-runtime-check"),ProcessInfo.processInfo.arguments.contains("--mute") else {throw Failure.script("UnsupportedExecution: binding check requires muted diagnostic mode")}
            let result = resources.invoke(0x41c9f0,0,[player,logic,pd])
            guard resources.fault == 0 else {throw Failure.script("NativeService: FireBullet")}
            return Double(result)
        case "Teleport":
            guard parts.count == 2 else {throw Failure.script("Teleport coordinates unavailable")}
            let x = try integer(parts[1]),y = try integer(String(value))
            guard x < mapBounds.0,y < mapBounds.1 else {throw Failure.script("Teleport outside main plane")}
            put(player+0x4c,x);put(player+0x50,y)
            record(["service":"Teleport","x":x,"y":y]);return 0
        case "Jump":
            // SavePoint teleport asks for zero jump height to settle at the
            // restored point; normal jumping keeps its source callback.
            if value == 0 {put(player+0x14c,0);return 0}
            guard value == 1 else {throw Failure.script("NotImplemented: nondefault ClawJump strength")}
            _ = resources.invoke(0x417590,0,[player,logic,pd]);return 0
        default:throw Failure.script("NotImplemented: gameplay service \(key)")
        }
    }
    private func objectService(_ h:UInt32,_ object:Object,_ key:String,_ value:Double) throws -> Double {
        let token = object.token
        let parts = key.split(separator:":",maxSplits:1).map(String.init)
        var result:UInt32 = 0
        switch parts[0] {
        case "ImageName":
            guard parts.count == 2,let index = UInt32(parts[1]),index < 128,let nativeService else {throw Failure.script("ValueBounds: image name")}
            return try nativeService("Bindings:ImageName:"+String(word(token+0x170))+":"+String(index),0)
        case "GlitterAttach":
            guard let glitter = objects[try integer(String(value))],
                  let metadata = "PowerupGlitter".withCString({claw_logic_registry_find($0)?.pointee}),glitter.root == metadata.callback,
                  heap.allocationIdentity(at:glitter.token,count:0x1b4) === glitter.identity,
                  word(token+0xc8) == 0 else {throw Failure.script("Invalid glitter object handle")}
            put(token+0xc8,glitter.token)
        case "ObjectBelow","HitRef","AttRef","BumpRef","GlitterPointer":
            let offsets:[String:UInt32] = ["ObjectBelow":0x88,"HitRef":0x74,"AttRef":0x7c,"BumpRef":0x84,"GlitterPointer":0xc8]
            let peer = word(token+offsets[key]!)
            return Double(peer == 0 ? 0:handle(peer,name:"") ?? 0)
        case "SetImage","SetAnimation","SetSound":
            guard parts.count == 2 else {throw Failure.script("ValueType: resource name")}
            let text = resources.textToken(parts[1]);defer {resources.release(text)}
            let function:UInt32 = parts[0] == "SetImage" ? 0x4c7970:parts[0] == "SetSound" ? 0x4c7a40:0x4c79e0
            result = resources.invoke(function,token,parts[0] == "SetAnimation" ? [text,try integer(String(value))]:[text])
        case "SetFrame":
            // Indexed image binding uses the current registered group name.
            let group = word(token+0x170)
            guard group != 0 else {throw Failure.script("SetFrame: object has no image set")}
            let index = try integer(String(value))
            result = resources.invoke(0x40f680,group,[index])
            put(token+0x16c,index);put(token+0x174,result)
        case "AnimationStep":result = resources.invoke(0x4c82a0,token+0x188,[word(0x5430c4)])
        case "AlignToGround":result = resources.invoke(0x4cd800,word(scene+0x24),[token,0])
        case "Physics":
            guard parts.count == 2 else {throw Failure.script("ValueType: physics target")}
            let coordinates = try parts[1].split(separator:":").map {try integer(String($0))}
            guard coordinates.count == 2 else {throw Failure.script("ValueType: physics target")}
            result = resources.invoke(0x4cbb60,word(scene+0x24),[token]+coordinates+[try integer(String(value))])
        case "Logic":
            if object.scripted {try dispatch(h,"main")}
            else {result = resources.invoke(object.root,0,[token])}
        default:throw Failure.script("NotImplemented: object service \(key)")
        }
        guard resources.fault == 0 else {throw Failure.script("NativeService: \(key)")}
        record(["service":parts[0],"handle":h,"result":result,"x":word(token+0x4c),"y":word(token+0x50),"frame":word(token+0x16c)])
        return Double(result)
    }
    // WWD word-to-host stores are those of the common native object loader;
    // these are semantic properties, never release-specific Windows pointers.
    private static let actorFields:[String:UInt32] = ["X":0x4c,"Y":0x50,"Z":0x64,"Health":0x10c,"Flags":8,"DrawFlags":0x40,
        "SpecialFlags":0x164,"BumpFlags":0xd0,"HitFlags":0xd4,"AttackFlags":0xd8,"ObjectType":0xd0,"ObjectTypeFlags":0xd0,"HitType":0xd4,"HitTypeFlags":0xd4,"AttackType":0xd8,"AttackTypeFlags":0xd8,
        "SpeedX":0x148,"SpeedY":0x14c,"Direction":0x110,"FacingDir":0x114,"Score":0xf8,"Points":0xfc,"Powerup":0x100,"Damage":0x104,"Smarts":0x108,
        "MoveResX":0xdc,"MoveResY":0xe0,"I":0x16c,"AX":0x98,"AY":0x9c,"EditorX":0xe8,"EditorY":0xec,"EditorZ":0xf0,"PhysicsType":0xcc,"MoveClawX":0x158,"MoveClawY":0x15c,"OnScreenWidth":0x30,"OnScreenHeight":0x34,"OnScreen":0x38]
    private static let logicFields:[String:UInt32] = ["State":0x1c,"UserFlags":0x28,"XMin":0x2c,"XMax":0x30,"YMin":0x34,"YMax":0x38,
        "XTweak":0x44,"YTweak":0x48,"Counter":0xb8,"Speed":0xbc,"Width":0xc8,"Height":0xcc,"TimeDelay":0x20,"FrameDelay":0x24,"ID":4]
    private static let actorRects:[String:UInt32] = ["MoveRect":0x118,"HitRect":0x128,"AttackRect":0x138,"ClipRect":0x54]
    private static let logicRects:[String:UInt32] = ["UserRect1":0xf0,"UserRect2":0x100]
    private func hasPrivateKind(_ h:UInt32,_ object:Object,_ kind:String)->Bool {
        guard let metadata = kind.withCString({claw_logic_registry_find($0)?.pointee}),
              word(word(object.token+0x6c)+0x18) != 0 else {return false}
        return object.root == metadata.callback || privateKinds[h] == kind
    }
    private func legacyAccess(_ op:Int32,_ h:UInt32,_ key:String,_ value:Double) throws -> Double {
        let p = key.split(separator:":",omittingEmptySubsequences:false).map(String.init)
        let name = p[0]
        var object:Object?
        if h != 0 {
            guard let o = objects[h],heap.allocationIdentity(at:o.token,count:0x1b4) === o.identity else {throw Failure.script("StaleHandle: legacy view")}
            object = o
        }
        if op == 12 {
            if name == "Audio" || name == "MessageBox" || name == "ExitLevel" {
                guard let nativeService else {throw Failure.script("Audio service unavailable")}
                return try nativeService(key,value)
            }
            guard let o = object else {throw Failure.script("ValueType: legacy call requires object")}
            let logic = word(o.token+0x6c)
            let player = word(0x537e88)
            let result:UInt32
            switch name {
            case "CrabFall":
                guard hasPrivateKind(h,o,"HermitCrab") else {throw Failure.script("ValueType: HermitCrab private state")}
                result = resources.invoke(0x44b780,word(logic+0x18))
            case "CrabType":
                guard hasPrivateKind(h,o,"HermitCrab") else {throw Failure.script("ValueType: HermitCrab private state")}
                result = resources.invoke(0x44acd0,word(logic+0x18),[try integer(String(value))])
            case "Drown":
                guard o.token == player else {throw Failure.script("ValueType: Drown requires Claw")}
                result = resources.invoke(0x417c50,0,[player,word(player+0x6c),word(word(player+0x6c)+0x14)])
            case "ProjectileInit":result = resources.invoke(0x41d6f0,0,[o.token])
            case "ProjectileMove":put(o.token+0x164,word(o.token+0x164)|0x200);put(o.token+8,word(o.token+8)|1);result = 1
            default:throw Failure.script("NotImplemented: legacy call \(key)")
            }
            guard resources.fault == 0 else {throw Failure.script("NativeService: legacy \(key)")}
            record(["service":name,"handle":h,"result":result]);return Double(result)
        }
        guard p.count == 2,let i = UInt32(p[1]) else {throw Failure.script("ValueBounds: legacy \(key)")}
        if let original = Self.legacyNames[name] {
            guard i < 32 else {throw Failure.script("ValueBounds: legacy string \(name)[\(i)]")}
            var bytes = legacyBuffers[name] ?? Array(original.utf8)+Array(repeating:0,count:32-original.utf8.count)
            if op == 11 {
                guard value.isFinite,value >= 0,value <= 255,value.rounded() == value else {throw Failure.script("ValueRange: legacy byte")}
                bytes[Int(i)] = UInt8(value);legacyBuffers[name] = bytes
                record(["service":"LegacyBuffer:"+name,"value":String(decoding:bytes.prefix(while:{$0 != 0}),as:UTF8.self)])
            }
            return Double(bytes[Int(i)])
        }
        let address:UInt32
        switch name {
        case "PrivateInt":
            guard let o = object,i == 276,hasPrivateKind(h,o,"Aquatis") else {throw Failure.script("NotImplemented: legacy private int \(i)")}
            address = word(word(o.token+0x6c)+0x18)+0x4cc
        case "PrivateDouble":
            guard let o = object,(10...13).contains(i),hasPrivateKind(h,o,"HermitCrab") else {throw Failure.script("NotImplemented: legacy private double \(i)")}
            let a = word(word(o.token+0x6c)+0x18)+(i-10)*8+0x40
            guard let bytes = heap.lookupBytes(a,count:8) else {throw Failure.script("StaleHandle: private double")}
            if op == 11 {guard value.isFinite else {throw Failure.script("ValueRange: private double")};UnsafeMutableRawPointer(bytes).storeBytes(of:value,as:Double.self)}
            return UnsafeRawPointer(bytes).loadUnaligned(as:Double.self)
        case "LogicRef":
            guard let o = object,i == 4,op == 10 else {throw Failure.script("ValueBounds: logic reference")}
            // Return a historical logic identity, never the native function pointer.
            return o.root == 0x40fec0 ? 0x410510:o.root == 0x40ff80 ? 0x410680:Double(o.root)
        case "Scene":
            guard [UInt32(17),18,473].contains(i) else {throw Failure.script("NotImplemented: legacy scene word \(i)")}
            address = word(word(0x5371fc)+0x2c)+i*4
        case "Cheats":
            guard i == 74 else {throw Failure.script("NotImplemented: legacy cheat word \(i)")}
            address = word(word(0x5371fc)+0x48)+0x128
        case "Clock":guard i == 0,op == 10 else {throw Failure.script("ValueBounds: clock")};return Double(word(0x537210))
        case "SoundVolume":guard i == 0,op == 10 else {throw Failure.script("ValueBounds: volume")};return Double(word(0x532c10))
        case "BossFrame":guard i == 0 else {throw Failure.script("ValueBounds: boss frame")};address = 0x52c6f0
        case "PowerupMusic":
            guard i == 0 else {throw Failure.script("ValueBounds: powerup music")}
            if op == 11 {guard value.isFinite,value.rounded() == value,(0...2).contains(value) else {throw Failure.script("ValueRange: powerup music")};legacySettings[name] = value}
            return legacySettings[name] ?? 0
        case "Viewport":
            guard i < 4,op == 10 else {throw Failure.script("ValueBounds: viewport")}
            guard let nativeService else {throw Failure.script("Viewport service unavailable")}
            return try nativeService("Bindings:Viewport:"+String(i),0)
        case "Result":
            guard op == 10 else {throw Failure.script("ValueType: read-only application view")}
            if i == 5 {return Double(word(word(0x5371fc)+0x14))};if i == 6 {return 60}
            throw Failure.script("NotImplemented: legacy application word \(i)")
        case "BulletCollision","BulletHit","BulletRight","BulletLeft","ViewportDecreaseLimit","ViewportIncreaseLimit":
            guard i == 0 else {throw Failure.script("ValueBounds: gameplay setting")}
            if op == 11 {guard value.isFinite,value.rounded() == value,value >= Double(Int32.min),value <= Double(Int32.max) else {throw Failure.script("ValueRange: gameplay setting")};legacySettings[name] = value;record(["service":"LegacySetting:"+name,"value":value])}
            let defaults:[String:Double] = ["BulletCollision":32,"BulletHit":32,"BulletRight":700,"BulletLeft":-700,"ViewportDecreaseLimit":1,"ViewportIncreaseLimit":10]
            return legacySettings[name] ?? defaults[name]!
        default:throw Failure.script("NotImplemented: legacy operation \(key)")
        }
        guard let ptr = heap.lookup(address,words:1) else {throw Failure.script("NotImplemented: legacy native storage \(key)")}
        if op == 11 {
            let v = try integer(String(value))
            if h == 0 {for j in 0..<4 where savedLevelBytes[address+UInt32(j)] == nil {savedLevelBytes[address+UInt32(j)] = UInt8(truncatingIfNeeded:ptr.pointee >> (j*8))}}
            ptr.pointee = v;record(["service":"LegacyWrite:"+name,"handle":h,"index":i,"value":value])
        }
        return Double(Int32(bitPattern:ptr.pointee))
    }
    fileprivate func access(_ op:Int32,_ h:UInt32,_ key:String,_ value:Double)throws->Double {
        if op == 13 {
            guard h == 0,let metadata = key.withCString({claw_logic_registry_find($0)?.pointee}) else {throw Failure.script("LogicNotFound: \(key)")}
            return metadata.callback == 0x40fec0 ? 0x410510:metadata.callback == 0x40ff80 ? 0x410680:Double(metadata.callback)
        }
        if (10...12).contains(op) {return try legacyAccess(op,h,key,value)}
        if op == 5 && h == 0 {return 1}
        if h == 0 && (op == 0 || op == 1) {
            // v1.0's active 48-word level configuration and pointer aliases are
            // the same native storage used by the Elevator/SpringBoard owners.
            let base:UInt32 = 0x5378a0
            let fields:[String:UInt32] = ["LevelNb":0,"DeathTileType":68,"BreakPlankWidth":168,"field_AC":172,"SplashY":176,"MPSkinnerPosX":180,"MPSkinnerPosY":184]
            let rects:[String:UInt32] = ["SpringBoardDefRect":72,"TogglePegDefRect":88,"ElevatorDefRect":104,"CrumblingPegDefRect":120,"SteppingStoneDefRect":136,"BigElevatorDefRect":152]
            let parts = key.split(separator:":").map(String.init)
            let address:UInt32, count:UInt32
            if parts.count == 2,let i = UInt32(parts[1]),i < 32,["SpringBoardAnimationIdle","SpringBoardAnimationSpring"].contains(parts[0]) {
                address = base+(parts[0] == "SpringBoardAnimationIdle" ? 4:36)+i;count = 1
            } else if parts.count == 2,let i = UInt32(parts[1]),i < 4,let offset = rects[parts[0]] {
                address = base+offset+i*4;count = 4
            } else if parts.count == 1,let offset = fields[key] {address = base+offset;count = 4}
            else {throw Failure.script("NotImplemented: LevelBasedData.\(key)")}
            guard let p = heap.lookupBytes(address,count:count) else {throw Failure.script("LevelBasedData: missing native storage")}
            if op == 1 {
                guard value.isFinite,value >= (count == 1 ? 0:Double(Int32.min)),value <= (count == 1 ? 255:Double(UInt32.max)) else {throw Failure.script("ValueRange: level value")}
                for i in 0..<count where savedLevelBytes[address+i] == nil {savedLevelBytes[address+i] = p[Int(i)]}
                if count == 1 {p.pointee = UInt8(value)}
                else {UnsafeMutableRawPointer(p).storeBytes(of:UInt32(truncatingIfNeeded:Int64(value)),as:UInt32.self)}
                if count == 1,value == 0,let i = UInt32(parts[1]) {
                    let start = address-i
                    let bytes = (0..<32).map {heap.lookupBytes(start+UInt32($0),count:1)?.pointee ?? 0}.prefix(while:{$0 != 0})
                    record(["level_array":parts[0],"value":String(decoding:bytes,as:UTF8.self)])
                }
            }
            return count == 1 ? Double(p.pointee):Double(Int32(bitPattern:UnsafeRawPointer(p).loadUnaligned(as:UInt32.self)))
        }
        if op == 7 {
            guard let h = handle(word(0x537e88),name:"CaptainClaw") else {throw Failure.script("GetClaw: player unavailable")}
            return Double(h)
        }
        if op == 9 {return try gameService(key,value)}
        if op == 3 || op == 14 {
            let parts = key.split(separator:"|").map(String.init)
            let name = parts[0],entry = entries[name] ?? 0
            guard entry != 0 else {throw Failure.script("LogicNotFound: \(name)")}
            let values = try parts.dropFirst().map {try integer($0)}
            let args:[UInt32] = values.count == 5 ? [values[0],values[1],values[2],values[3],entry,values[4]]:[0,0,0,0,entry,0x40000]
            let token:UInt32
            var hudParent:UInt32?
            if op == 14 {
                let callback = entries["MultiStats"].map {word($0+16)} ?? 0x491ed0
                let parent = heap.debugAllocationBases.first(where:{heap.lookupBytes($0,count:0x1d0) != nil && word($0) == 0x513830 && word($0+0xc) == scene && word(word($0+0x6c)+0x10) == callback})
                guard let parent else {throw Failure.script("CreateHUDObject: MultiStats unavailable")}
                hudParent = parent
                token = resources.invoke(0x4d3ca0,parent,args)
            } else {token = resources.invoke(0x4c8be0,word(scene+8),args)}
            guard token != 0,let h = handle(token,name:name) else {throw Failure.script("CreateObject: native constructor failed")}
            if let hudParent {hudParents[h] = hudParent}
            record(["service":"CreateObject","name":name,"handle":h,"x":word(token+0x4c),"y":word(token+0x50)])
            return Double(h)
        }
        guard let object = objects[h], heap.allocationIdentity(at:object.token,count:0x1b4) === object.identity else {throw Failure.script("StaleHandle: \(h)")}
        if op == 5 {return 1}
        if op == 8 {return try objectService(h,object,key,value)}
        if op == 6 {objects[h]?.name = key;return 0}
        let token = object.token, logic = word(token+0x6c)
        if op == 4 {heap.lookup(token+8,words:1)?.pointee = 0x10000;return 0}
        if op == 2 {
            guard let metadata = key.withCString({claw_logic_registry_find($0)?.pointee}),metadata.callback != Self.callback else {throw Failure.script("LogicNotFound: \(key)")}
            nativeDepth += 1
            _ = resources.invoke(metadata.callback,0,[token])
            nativeDepth -= 1
            guard resources.fault == 0 else {throw Failure.script("NativeLogic: \(key)")}
            privateKinds[h] = key
            record(["builtin":key,"handle":h]);return 0
        }
        if key == "_field_F4" {
            if op == 1 {poisonCounters[h] = try integer(String(value))}
            return Double(poisonCounters[h] ?? 0)
        }
        let address:UInt32
        if let off = Self.actorFields[key] {address = token+off}
        else if let off = Self.logicFields[key] {address = logic+off}
        else {
            let parts = key.split(separator:":").map(String.init)
            if parts.count == 2,parts[0] == "PData" {
                var fields:[String:UInt32] = ["Dir":0,"Direction":0,"LoadedFromSavePoint":0x24,"ActiveSecondWeapon":0x30,"JumpHeight":0x5c,"JumpStartY":0x60,"JumpPeakY":0x64,"RunningSpeedTime":0x114,"JumpPressTime":0x118,"ConveyorBeltForce":0x84,"_unkn34":0x84,"_unkn35":0x88,"FallHeight":0x40,"SpawnScore":0x44,"SpawnHealth":0x48,"DynamiteAmmo":0x78,"SpawnPointX":0x4c,"SpawnPointY":0x50,"PistolAmmo":0x70,"MagicAmmo":0x74,"TNTAmmo":0x78,"Lives":0x7c,"AttemptNb":0x80,"Score":0x44,"Health":0x48]
                for (i,name) in ["Coin","Goldbar","Ring","Chalice","Cross","Scepter","Gecko","Crown","Skull"].enumerated() {fields["Collected"+name] = 0x88+UInt32(i*4);fields["GameCollected"+name] = 0xb0+UInt32(i*4)}
                guard token == word(0x537e88),let offset = fields[parts[1]],word(logic+0x14) != 0 else {throw Failure.script("NotImplemented: typed PData.\(parts[1])")}
                address = word(logic+0x14)+offset
            }
            else if parts.count == 2,parts[0] == "PDataArray",let i = Int32(parts[1]),(-1..<35).contains(i),token == word(0x537e88),word(logic+0x14) != 0 {address = word(logic+0x14)+UInt32(0x8c+i*4)}
            else if parts.count == 2,let off = Self.actorRects[parts[0]],let i = UInt32(parts[1]),i < 4 {address = token+off+i*4}
            else if parts.count == 2,let off = Self.logicRects[parts[0]],let i = UInt32(parts[1]),i < 4 {address = logic+off+i*4}
            else if parts.count == 2,parts[0] == "User",let i = UInt32(parts[1]),i < 8 {address = logic+0x64+i*4}
            else if key.hasPrefix("UserValue"),let i = UInt32(key.dropFirst(9)),(1...8).contains(i) {address = logic+0x64+(i-1)*4}
            else {throw Failure.script("NotImplemented: object value \(key)")}
        }
        guard let p = heap.lookup(address,words:1) else {throw Failure.script("StaleHandle: object value")}
        if op == 1 {
            // Custom dynamite disables its attack box with -math.huge. The
            // integer rectangle view uses the offscreen INT_MIN sentinel.
            if key == "AttackRect:0",value == -Double.infinity {p.pointee = 0x80000000}
            else {
                guard value.isFinite,value >= Double(Int32.min),value <= Double(UInt32.max) else {throw Failure.script("ValueRange: \(key)")}
                p.pointee = UInt32(truncatingIfNeeded:Int64(value))
            }
        }
        return Double(Int32(bitPattern:p.pointee))
    }
}
private let customLuaService:ClawLuaService = { user,op,handle,key,value,out,error,capacity in
    guard let user,let key else {return 0}
    do {
        out?.pointee = try Unmanaged<ClawCustomLua>.fromOpaque(user).takeUnretainedValue().access(op,handle,String(cString:key),value)
        return 1
    } catch let failure {
        if let error,capacity > 0 {
            let bytes = Array(failure.localizedDescription.utf8.prefix(Int(capacity)-1))+[0]
            for (i,b) in bytes.enumerated() {error[i] = CChar(bitPattern:b)}
        }
        return 0
    }
}
