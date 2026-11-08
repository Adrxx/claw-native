import Foundation
import CryptoKit

// Native MFC storage transports for the actual IFC and image-registry graph.
// Menu selection, archive parsing, image names and dimensions remain in game owners.
final class ClawNativeMenuInterface {
    var customCheckpointMessage = ""
    var customCheckpointEvents: [[String: Any]] = []
    private(set) var checkpointInitialPlacements: [[String:Any]] = []
    let base:ClawNativeMenuBase
    let resources:ClawNativeMenuResources
    let diagnostics:ClawNativeDiagnostics
    let movieServices:ClawNativeMovieStateServices
    /// The original's movie library (0x4f0000 and up, platform layer) is
    /// replaced by AVFoundation. Recovered 0x42b140 still decides which
    /// numeric movie plays; the app answers availability and the blocking play
    /// with the original's play result (0x11111111 finished, 1 key skip).
    var movieAvailable:((UInt32)->Bool)?
    var moviePlay:((UInt32,UInt32)->UInt32)?
    var movieBackgroundFile:((UInt32)->URL?)?
    /// Native startup's stand-in for 0x42cab0's movie path (+0x100, "%s\\%s"
    /// of the working directory and CLAW.FEC): the prepared movie directory.
    /// OpenFile(OF_EXIST) on it answers whether the movies were prepared.
    var movieContainer:String?
    func configureMovieContainer(_ path:String) {
        movieContainer = path
        put(base.applicationToken+0x100,cstring(path))
    }
    private var movieObjects:[UInt32:UInt32] = [:]
    private var movieQueues:[UInt32:[[UInt32]]] = [:]
    private var movieBackgrounds:[UInt32:ClawNativeMovieBackground] = [:]
    private var moviePalettes:[UInt32:UInt32] = [:]
    private func closeMovieBackground(_ r:UInt32) {
        movieBackgrounds.removeValue(forKey:r)
        if let token = moviePalettes.removeValue(forKey:r) {base.palette?.releaseMoviePalette(token)}
        put(r+32,0)
    }
    private(set) var movieEvents:[[String:Any]] = []
    private var maps:[UInt32:[String:UInt32]] = [:]
    private var mapKeys:[UInt32:[String]] = [:]
    private var strings:Set<UInt32> = []
    private lazy var archiveServices = ClawNativeArchiveServices(
        bytes:{[unowned self] in self.heap.lookupBytes($0,count:$1)},
        allocate:{[unowned self] in self.resources.allocate($0)},
        release:{[unowned self] in self.resources.release($0)},
        fileService:{[unowned self] in self.saveFiles?.service($0,$1,$2,heap:self.heap)},
        empty:empty,makeString:{[unowned self] data in
            let block = self.resources.allocate(UInt32(data.count)+13)
            guard let target = self.heap.lookupBytes(block+12,count:UInt32(data.count)+1) else {return 0}
            self.strings.insert(block);self.put(block,1);self.put(block+4,UInt32(data.count));self.put(block+8,UInt32(data.count))
            data.copyBytes(to:target,count:data.count);target[data.count] = 0;return block+12
        })
    private var lists:[UInt32:Set<UInt32>] = [:]
    // Native game-thread CRT state exists from owner startup, before any menu
    // or level call. It survives world teardown and New Game; no Windows TLS
    // lookup or translated CRT thread record is needed by this platform owner.
    private var randomState:UInt32 = 1
    private var randomCalls:UInt64 = 0
    var randomSnapshot:[String:Any] {["state":randomState,"calls":randomCalls]}
    // Opt-in regression probe, consumed only by --crt-rand-check frame marks.
    func probeRandom() -> [String:Any] {
        let before = randomState
        var q = ClawCall();q.function = 0x4a3050
        let result = resources.service(q)
        return ["before":before,"after":randomState,"result":result,"calls":randomCalls,
                "fault":resources.fault]
    }
    // Read-only route evidence; inactive speech controllers may have no sound.
    var speechSnapshot:[String:Any] {
        func w(_ token:UInt32)->UInt32 {
            guard let p = heap.lookupBytes(token,count:4) else {return 0}
            return UnsafeRawPointer(p).loadUnaligned(as:UInt32.self)
        }
        let actor = w(0x53c9ac),logic = w(actor+0x6c),sound = w(actor+0x184)
        return ["voice":w(base.applicationToken+0x118),"state":w(logic+0x1c),"remaining":w(logic+0x130),
            "duration":w(w(sound+0x10)+0x28),
            "flags":w(actor+0x40),"x":w(actor+0x4c),"y":w(actor+0x50)]
    }
    private var exitCallbacks:[UInt32] = []
    // The latest physical time the game read (timeGetTime/GetTickCount).
    private var lastClock:UInt32 = 0
    private var manager:UInt32 = 0
    private var music:ClawNativeMenuMusic?
    private var musicManager:UInt32 = 0
    private var startupDelay:UInt32?
    private var fullInitialization = false
    private var recordingInitialization = false
    private(set) var physicalEffects:[[String:Any]] = []
    var observeEvidence:(([String:Any])->Void)?
    private func record(_ event:[String:Any]) {
        guard recordingInitialization else {return}
        var value = event
        for (key,field) in event {if let data = field as? Data {
            value.removeValue(forKey:key)
            value[key+"_sha256"] = SHA256.hash(data:data).map{String(format:"%02x",$0)}.joined()
        }}
        physicalEffects.append(value);observeEvidence?(value)
    }
    private var nativeStartupBlocks:[UInt32] = []
    private var localTmBuffer:UInt32 = 0
    private var postedCommands:[(window:UInt32,wParam:UInt32,lParam:UInt32)] = []
    /// Called once the posted window commands of a pump turn have been delivered.
    private(set) var deliveringPostedCommand: UInt32?
    var skipIdleFrameOnce = false
    var postedCommandsDelivered:(()->Void)?
    var hasPostedCommands:Bool {!postedCommands.isEmpty}
    /// Runs `body` (a key the host delivers before this pump turn's frame, as the
    /// traces' deliver_key does) so that the commands it posts wait for the
    /// delivery after the frame, as the original's pump delivers them.
    func postingAfterFrame(_ body:() throws->Void) rethrows {
        let count = postedCommands.count
        defer {afterFrameCommands += postedCommands[count...];postedCommands.removeSubrange(count...)}
        try body()
    }
    private var afterFrameCommands:[(window:UInt32,wParam:UInt32,lParam:UInt32)] = []
    private(set) var postedHistory:[[String:UInt32]] = []
    /// The cursor handle SetCursor last selected (the game passes handles it loaded, or 0).
    private var cursorHandle:UInt32 = 0
    /// The main window's accelerator table (RT_ACCELERATOR "CLAW", prepared into
    /// GameData/MENU/accelerators.json): flags (1 virtual key, 4 Shift, 8 Control,
    /// 0x10 Alt), key and command. Empty when the file is absent.
    var accelerators:[(flags:UInt32,key:UInt32,command:UInt32)] = []
    /// Every accelerator the pump translated: key, character, command, delivered.
    private(set) var acceleratorHistory:[[String:UInt32]] = []
    /// Accelerator commands can synchronously fade before the next game frame.
    private(set) var deliveringAccelerator = false
    /// Requirement failures return through an original synchronous fade too.
    private(set) var restoringCustomMenu = false
    /// TranslateAcceleratorA for the main window (the pump 0x4b8d10 ignores its
    /// result, so the key message is still translated and dispatched). A virtual
    /// key entry matches WM_KEYDOWN when its Shift, Control and Alt bits equal the
    /// held modifiers; an ASCII entry ('-', '=') matches the WM_CHAR that
    /// TranslateMessage makes. The WM_COMMAND is sent at once: the window's
    /// command handler 0x4b8810 passes (HIWORD 1, LOWORD command, 0).
    private func translateAccelerator(key:UInt32,character:UInt32?,modifiers:UInt32) throws {
        let match:(flags:UInt32,key:UInt32,command:UInt32)?
        if let character {
            match = accelerators.first {$0.flags & 1 == 0 && $0.flags & 0x10 == 0 && $0.key == character}
        } else {
            match = accelerators.first {$0.flags & 1 != 0 && $0.key == key && $0.flags & 0x1c == modifiers & 0x1c}
        }
        guard let match else {return}
        let deliver = true
        acceleratorHistory.append(["key":key,"character":character ?? 0,"command":match.command,"delivered":deliver ? 1:0])
        record(["service":"TranslateAcceleratorA","key":key,"character":character ?? 0,"command":match.command,"delivered":deliver])
        guard deliver else {return}
        let wasDelivering = deliveringAccelerator
        deliveringAccelerator = true
        defer {deliveringAccelerator = wasDelivering}
        _ = resources.invoke(0x426e30,base.applicationToken,[1,match.command,0])
        guard resources.fault == 0 else {
            throw ClawNativeMenuResources.Failure.invalid("Accelerator command \(String(match.command,radix:16)) at \(String(resources.faultAddress,radix:16))")
        }
    }
    /// The WM_CHAR TranslateMessage makes for the keys an ASCII accelerator
    /// names: '-' (VK_OEM_MINUS, VK_SUBTRACT) and '=' (VK_OEM_PLUS unshifted).
    /// Control makes no printable character for either; Alt makes WM_SYSCHAR.
    private static func character(key:UInt32,modifiers:UInt32)->UInt32? {
        guard modifiers & 0x18 == 0 else {return nil}
        switch key {
        case 0x6d: return 0x2d
        case 0xbd: return modifiers & 4 == 0 ? 0x2d:nil
        case 0xbb: return modifiers & 4 == 0 ? 0x3d:nil
        default: return nil
        }
    }
    /// Outcome of the last 0x428b60 call (debug logging only).
    private(set) var lastFrameCheck:[String:Any] = [:]
    /// Original data and BSS spans the Level 1 load and play touch, elected
    /// from the native Level 1 join; installed before the static initializers.
    var levelOneData:[UInt32:Data]?
    /// Native folder for the original's CLAW.USR (set before initialize()).
    var saveDirectory:URL?
    /// Native folder for the original's registry settings (set before
    /// initialize()); nil keeps none, so every launch is a fresh install.
    var settingsDirectory:URL?
    /// Original relative CLAWnnnn.BMP files live in Documents/Screen Dumps on
    /// both native platforms; check launches can select an isolated directory.
    var screenDumpDirectory:URL?
    private(set) var screenDumps:[[String:Any]] = []
    private(set) var settings:ClawNativeSettingsStore?
    /// The original configuration object (application +0x38, 540 bytes).
    private var configuration:UInt32 = 0
    private var startupSettings:[UInt32:UInt32] = [:]
    private(set) var settingsWritten = false
    private(set) var saveFiles:ClawNativeSaveFiles?
    private var inputController:UInt32 = 0,profileManagerToken:UInt32 = 0
    // Owner-approved native replacement for CONFIGCONTROLS. Only the dialog
    // command (8090, selector 0) is consumed; all other popup selectors stay original.
    var showControls:(()->Void)?
    var controlsActive = false
    var showPlayers:(()->Void)?
    var playersActive = false
    var showCustomLevels:(()->Void)?
    var customLevelsActive = false
    private var customLua:ClawCustomLua?
    private var customLogicEntry:UInt32 = 0
    private var customWorld:ClawCustomWorld?
    private var customCheckpointWorldURL:URL?
    private var customAssets:ClawCustomAssets?
    private var customPalettes:ClawCustomPalette?
    private var customPaletteState:UInt32 = 0
    private var customPaletteFirst = Data(),customPalettePending = Data(),customPaletteLoaded = Data()
    private var customPaletteTables:[String:UInt32] = [:]
    private var customPaletteAllocations:[UInt32] = []
    private var customPaletteImages:[UInt32:[UInt32]] = [:]
    private var customPaletteImageIdentities:[UInt32:ClawTokenHeap.AllocationIdentity] = [:]
    private var customAssetsMapped = false
    private var customImageKeys = Set<String>()
    private var customAnimationKeys = Set<String>()
    private var customSounds:[String:(original:UInt32, replacement:UInt32)] = [:]
    private var removedScriptSounds:[String:UInt32] = [:]
    private var customSoundAliases:[String:(original:UInt32,replacement:UInt32)] = [:]
    private var customMusic:[String:(original:UInt32, replacement:UInt32)] = [:]
    private var customMusicVolume:(percent:UInt32,raw:UInt32)?
    var customMessageBox:((String,String) throws -> Void)?
    private var customMusicMapped = false
    private var customAudioReady = false,customAudioRetiring = false
    private var customLoadingScreen = false
    private var customFileOffsets:[UInt32:Int] = [:]
    private var customVirtualPath = ""
    private var customLevelRecord:[String:Any] = [:]
    var customLevelEvidence:[String:Any] {
        get {var value = customLevelRecord;if let customLua {value["lua"] = customLua.evidence};return value}
        set {customLevelRecord = newValue}
    }

    var customPresentationActive:Bool {customLua != nil}
    private(set) var resizingPresentation = false
    private var presentationResolution:[UInt32]?
    private var normalResolution:[UInt32]?
    private var presentationHeld:Set<UInt32> = [],presentationEdges:Set<UInt32> = []
    private var crazySaves:ClawCrazyHookSaves?
    private var crazySaveURL:URL?
    private var crazyScriptOwned = false
    private var crazyPendingSlot:Int?
    private var crazyLastSave:UInt32 = 0
    private var crazyRestore:[UInt32]?
    private var crazyCompleted = false
    private func crazyURL(_ url:URL) -> URL? {
        let name = url.deletingPathExtension().lastPathComponent.lowercased()
        let key = SHA256.hash(data:Data(name.utf8)).map{String(format:"%02x",$0)}.joined()
        return saveDirectory?.appendingPathComponent("CustomSaves").appendingPathComponent(key+".plist")
    }
    func customRestartSlots(_ url:URL) throws -> [Int] {
        let package = try ClawCustomAssets(worldURL:url)
        if ClawCrazyHookSaves.scriptOwned(package) {return []}
        guard let path = crazyURL(url),FileManager.default.fileExists(atPath:path.path) else {return []}
        let map = SHA256.hash(data:try Data(contentsOf:url)).map{String(format:"%02x",$0)}.joined()
        return try ClawCrazyHookSaves.read(path,map:map).slots.keys.sorted()
    }
    func checkCapabilityAPIs(_ names:[String],worldURL:URL) throws -> [String:String] {
        let candidate = try ClawCustomWorld(url:worldURL)
        let package = try ClawCustomAssets(worldURL:worldURL)
        let map = w(base.sceneToken+20)+16
        let entries = (maps[map] ?? [:]).mapValues {w($0)}
        let lua = try ClawCustomLua(package:package,saveDirectory:saveDirectory?.appendingPathComponent("CapabilityProbe"),world:candidate.world,level:candidate.level,scene:base.sceneToken,heap:heap,resources:resources,entries:entries)
        var result:[String:String] = [:]
        for name in names {
            do {try lua.checkImplementedAPIs([name]);result[name] = "implemented"}
            catch {result[name] = error.localizedDescription}
        }
        return result
    }
    private(set) var customRequirementFailure:String?
    func takeCustomRequirementFailure() -> String? {
        defer {customRequirementFailure = nil}
        return customRequirementFailure
    }
    private func retireCustomSession() {
        guard customAssets != nil else {return}
        customLua?.end()
        customLevelEvidence["lua"] = customLua?.evidence
        customLua = nil
        presentationResolution = normalResolution;normalResolution = nil
        presentationHeld = [];presentationEdges = []
        unmapCustomAssets();resources.unmountPackage();customAssets = nil;customAssetsMapped = false
        crazySaves = nil;crazySaveURL = nil;crazyPendingSlot = nil;crazyRestore = nil;crazyScriptOwned = false
        put(0x536f00,0)
        customWorld = nil;customCheckpointWorldURL = nil;resources.configureWorldBuffers(nil);customVirtualPath = "";customFileOffsets.removeAll()
        customLevelEvidence["unloaded"] = true
    }
    private func retireFailedCustomLevel(_ message:String) throws {
        // At a frame/load boundary, after the bounded callback has unwound.
        // Do not clear native faults: real host failures still stop the app.
        guard resources.fault == 0 else {throw ClawCustomLua.Failure.script(message)}
        customRequirementFailure = message
        customLevelEvidence["requirement_failure"] = message
        retireCustomSession()
        // Use the same original return-to-menu command as Lua ExitLevel.
        // 0x42abb0 shuts down the application instead of replacing its state.
        restoringCustomMenu = true
        defer {restoringCustomMenu = false}
        _ = resources.invoke(0x426e30,base.applicationToken,[0,0x8023,0])
        guard resources.fault == 0,menuLive,customWorld == nil else {
            throw ClawNativeMenuResources.Failure.invalid("Custom-level failure cleanup at \(String(resources.faultAddress,radix:16)), fault \(resources.fault), state \(String(w(w(base.applicationToken+0x2c)),radix:16)): \(message)")
        }
        customLevelEvidence["failure_cleanup"] = "menu restored; package, Lua, audio and palette retired"
    }
    func startCustomLevel(_ url:URL, checkpoint:Int = 0) throws {
        var phase = "validate"
        defer {
            if ProcessInfo.processInfo.arguments.contains("--lua-runtime-check"),
               let folder = ProcessInfo.processInfo.environment["CLAW_REAL_SPEED_LOG"] {
                let result:[String:Any] = ["file":url.lastPathComponent,"phase":phase,"fault":resources.fault,"address":String(resources.faultAddress,radix:16),"evidence":customLevelEvidence,"lua":customLua?.evidence ?? [:]]
                try? JSONSerialization.data(withJSONObject:result,options:[.sortedKeys]).write(to:URL(fileURLWithPath:folder).appendingPathComponent("lua-load.json"),options:.atomic)
            }
        }
        customRequirementFailure = nil
        let capabilityReport = try ClawCustomCapabilities.preflight(url)
        let candidate = try ClawCustomWorld(url:url)

        let logics = maps[w(base.sceneToken+20)+16] ?? [:]
        let directory = resources.directory("LEVEL\(candidate.level)_WORLDS")
        let retailResource = resources.resource(directory:directory,name:"WORLD",type:0x575744)
        guard let retailData = resources.load(retailResource) else {throw ClawCustomWorld.Rejection.invalid("Base level is unavailable.")}
        _ = retailData
        let package = try ClawCustomAssets(worldURL:url)
        var checkpointWarning = ""
        let palettes = try ClawCustomPalette(package)
        let digest = SHA256.hash(data:candidate.data).map{String(format:"%02x",$0)}.joined()
        crazyScriptOwned = ClawCrazyHookSaves.scriptOwned(package)
        crazySaveURL = crazyURL(url);crazySaves = ClawCrazyHookSaves(mapSHA256:digest)
        crazyPendingSlot = nil;crazyLastSave = 0;crazyRestore = nil;crazyCompleted = false
        if !crazyScriptOwned,let path = crazySaveURL,FileManager.default.fileExists(atPath:path.path) {
            do {crazySaves = try ClawCrazyHookSaves.read(path,map:digest)}
            catch {if checkpoint != 0 {throw error};checkpointWarning = error.localizedDescription}
        }
        if checkpoint != 0 {
            guard !crazyScriptOwned,let saved = crazySaves?.slots[checkpoint] else {throw ClawCrazyHookSaves.Failure.invalid}
            crazyRestore = saved
        }
        for plane in candidate.world.planes {
            for object in plane.objects where !object.logic.isEmpty {
                guard object.logic == "CustomLogic" || logics[object.logic] != nil else {
                    throw ClawCustomCapabilities.Failure(kind:.pending,detail:"logic \(object.logic), object \(object.id) '\(object.name)', plane \(plane.name)")
                }
            }
        }
        // Validate package and retail image namespaces before retiring the menu.
        var imageSets = Set<String>()
        for plane in candidate.world.planes {
            for object in plane.objects where !object.sound.isEmpty {
                guard ["LEVEL_","GAME_","CLAW_"].contains(where:{object.sound.hasPrefix($0)}) ||
                    (object.sound.hasPrefix("CUSTOM_") && package.files.keys.contains(where:{$0.hasPrefix("ANIS/") && $0.hasSuffix(".ANI") && "CUSTOM_"+$0.dropFirst(5).dropLast(4).replacingOccurrences(of:"/",with:"_") == object.sound.uppercased()})) ||
                    package.files.keys.contains(where:{ path in
                        guard path.hasSuffix(".WAV") else {return false}
                        if path.hasPrefix("SOUNDS/") {return "CUSTOM_"+path.dropFirst(7).dropLast(4).replacingOccurrences(of:"/",with:"_") == object.sound.uppercased()}
                        return path.hasPrefix("LEVEL/") && "CUSTOM_"+path.dropLast(4).replacingOccurrences(of:"/",with:"_") == object.sound.uppercased()
                    }) else {
                    throw ClawCustomCapabilities.Failure(kind:.missing,detail:"sound/animation \(object.sound), object \(object.id) '\(object.name)'; companion \(url.deletingPathExtension().path)/SOUNDS or ANIS")
                }
            }
            for name in plane.imageSets where !package.containsImages("TILES/"+name) {imageSets.insert("LEVEL\(candidate.level)_TILES_"+name)}
            for object in plane.objects where !object.imageSet.isEmpty {
                let name = object.imageSet.uppercased()
                if package.containsImages("TILES/"+name) {continue}
                if name.hasPrefix("CUSTOM_"),package.containsImages("IMAGES/"+name.dropFirst(7).replacingOccurrences(of:"_",with:"/")) {continue}
                if name.hasPrefix("LEVEL_"),package.containsImages("LEVEL/"+name.dropFirst(6).replacingOccurrences(of:"_",with:"/")) {continue}
                let path:String
                if name.hasPrefix("LEVEL_") {path = "LEVEL\(candidate.level)_IMAGES_"+name.dropFirst(6)}
                else if name.hasPrefix("GAME_") {path = "GAME_IMAGES_"+name.dropFirst(5)}
                else if name.hasPrefix("CLAW_") {path = "CLAW_IMAGES_"+name.dropFirst(5)}
                else if name == "CLAW" {path = "CLAW_IMAGES"}
                else {path = "LEVEL\(candidate.level)_TILES_"+name}
                imageSets.insert(path)
            }
        }
        func assetDirectory(_ path:String)->UInt32 {
            let parts = path.split(separator:"_",maxSplits:2).map(String.init)
            guard parts.count >= 2 else {return 0}
            let root = resources.directory(parts[0]+"_"+parts[1])
            func descend(_ directory:UInt32,_ name:String)->UInt32 {
                guard directory != 0 else {return 0}
                let token = resources.textToken(name)
                let direct = resources.invoke(0x4b68c0,directory,[token]);resources.release(token)
                if direct != 0 {return direct}
                // Registration joins directory names with '_', but an actual
                // directory may itself contain '_', e.g. ARROWSIGN_RIGHT.
                for index in name.indices where name[index] == "_" {
                    let part = resources.textToken(String(name[..<index]))
                    let child = resources.invoke(0x4b68c0,directory,[part]);resources.release(part)
                    if child != 0 {
                        let found = descend(child,String(name[name.index(after:index)...]))
                        if found != 0 {return found}
                    }
                }
                return 0
            }
            return parts.count == 2 ? root:descend(root,parts[2])
        }
        // A serialized image-set name is not necessarily a directory. Keep
        // unresolved directory candidates visible, and let the unchanged native
        // image registry/loader decide the actual reference and failure path.
        phase = "asset directories"
        let unresolvedImageDirectories = imageSets.sorted().filter {assetDirectory($0) == 0}
        phase = "lua registration"
        let lua:ClawCustomLua?
        if candidate.world.planes.flatMap(\.objects).contains(where:{$0.logic == "CustomLogic"}) || package.files["LOGICS/MAIN.LUA"] != nil {
            let map = w(base.sceneToken+20)+16
            if customLogicEntry == 0 {
                // The registry owns real 372-byte logic holders and calls
                // their virtual destructor on both failure and normal exit.
                customLogicEntry = resources.invoke(0x4d6340,w(base.sceneToken+20),[ClawCustomLua.callback,cstring("CustomLogic"),0])
                guard customLogicEntry != 0,resources.fault == 0 else {throw ClawCustomLua.Failure.script("CustomLogic registration failed")}
            }
            let entries = (maps[map] ?? [:]).mapValues {w($0)}
            let mapNameHash = SHA256.hash(data:Data(url.lastPathComponent.lowercased().utf8)).map{String(format:"%02x",$0)}.joined()
            let scriptSaveDirectory = saveDirectory?.appendingPathComponent("ScriptSaves/v1").appendingPathComponent(digest+"-"+mapNameHash)
            lua = try ClawCustomLua(package:package,saveDirectory:scriptSaveDirectory,world:candidate.world,level:candidate.level,scene:base.sceneToken,heap:heap,resources:resources,entries:entries)
        } else {lua = nil}
        phase = "package mount"
        try resources.mountPackage(package.archive())
        lua?.nativeService = {[weak self] key,value in
            guard let self else {throw ClawCustomLua.Failure.script("Native service session ended")}
            if key.hasPrefix("Presentation:HUDRemove:") {
                let p = key.split(separator:":")
                guard p.count == 4,let parent = UInt32(p[2]),let node = UInt32(p[3]),self.heap.lookup(node,words:3) != nil else {throw ClawCustomLua.Failure.script("HUD list service identity")}
                return Double(self.transport(0x4f5212,parent+0x1b4,[node]))
            }
            if key == "ExitLevel:" {
                self.afterFrameCommands.append((self.base.windowInput?.window ?? 0,0x8023,0))
                self.customLevelEvidence["script_exit_requested"] = true
                return 0
            }
            if key.hasPrefix("MessageBox:") {
                let parts = String(key.dropFirst(11)).split(separator:"\n",maxSplits:1,omittingEmptySubsequences:false).map(String.init)
                guard parts.count == 2,let show = self.customMessageBox else {throw ClawCustomLua.Failure.script("NotImplemented: MessageBox native sheet")}
                try show(parts[0],parts[1]);return 1
            }
            if key.hasPrefix("Audio:") {return try self.legacyAudioService(key,value)}
            if key.hasPrefix("Bindings:ImageName:") {
                let parts = key.split(separator:":")
                guard parts.count == 4,let group = UInt32(parts[2]),let index = Int(parts[3]),index >= 0,index < 128 else {throw ClawCustomLua.Failure.script("Image name request")}
                let controller = self.w(self.base.sceneToken+16)
                guard let name = self.maps[controller+16]?.first(where:{self.w($0.value) == group})?.key else {throw ClawCustomLua.Failure.script("Image name unavailable")}
                let bytes = Array(name.utf8);return index < bytes.count ? Double(bytes[index]):0
            }
            if key.hasPrefix("Bindings:Viewport:") {
                guard let i = UInt32(key.dropFirst(18)),i < 4 else {throw ClawCustomLua.Failure.script("Viewport index")}
                let buffer = self.resources.allocate(16);defer {self.resources.release(buffer)}
                let rectangle = self.resources.invoke(0x42a450,self.base.applicationToken,[buffer])
                guard self.heap.lookup(rectangle,words:4) != nil else {throw ClawCustomLua.Failure.script("Viewport unavailable")}
                return Double(Int32(bitPattern:self.w(rectangle+i*4)))
            }
            if key.hasPrefix("Plane:") {return try self.customPlaneService(key,value)}
            if key.hasPrefix("Palette:") {return try self.paletteService(key,value)}
            if key == "ResolutionWidth" {return Double(self.w(self.base.applicationToken+0x7c))}
            if key == "ResolutionHeight" {return Double(self.w(self.base.applicationToken+0x80))}
            if key.hasPrefix("Resolution:") {
                guard let width = UInt32(key.dropFirst(11)),value.isFinite,value.rounded() == value,(320...2048).contains(width),(240...2048).contains(value) else {throw ClawCustomLua.Failure.script("Resolution outside native surface limits")}
                if self.normalResolution == nil {self.normalResolution = [self.w(self.base.applicationToken+0x7c),self.w(self.base.applicationToken+0x80)]}
                self.presentationResolution = [width,UInt32(value)];return 0
            }
            if key == "Input" {return Double(self.w(self.inputController+8))}
            if key.hasPrefix("ActionKey:") {
                let names = ["Left","Right","Up","Down","Jump","Attack","Projectile","ToggleProjectile","Unused","Lift","Pistol","Magic","Dynamite","Special"]
                guard let i = names.firstIndex(of:String(key.dropFirst(10))) else {throw ClawCustomLua.Failure.script("Unknown input action")}
                return Double(self.w(self.inputController+0x38+UInt32(i*4)))
            }
            if key == "PointerX" {return Double(self.base.windowInput?.cursorPosition.x ?? 0)}
            if key == "PointerY" {return Double(self.base.windowInput?.cursorPosition.y ?? 0)}
            if key.hasPrefix("Key:") || key.hasPrefix("KeyEdge:") {
                guard let code = UInt32(key.split(separator:":").last ?? ""),code < 256 else {throw ClawCustomLua.Failure.script("KeyPressed: invalid key")}
                return (key.hasPrefix("KeyEdge:") ? self.presentationEdges.contains(code):self.presentationKeyHeld(code)) ? 1:0
            }
            if key.hasPrefix("Sound:") {
                let name = String(key.dropFirst(6))
                guard self.audioRegistry(self.w(self.base.sceneToken+40)+16,name.uppercased()) != 0 else {throw ClawCustomCapabilities.Failure(kind:.missing,detail:"sound \(name), companion SOUNDS/ or LEVEL/; requested by PlaySound")}
                let voice = self.playCustomSound(name)
                if ProcessInfo.processInfo.arguments.contains("--presentation-check"),ProcessInfo.processInfo.arguments.contains("--mute"),voice != 0,let audio = self.base.audio {
                    var left = [Float](repeating:0,count:4096),right = left
                    left.withUnsafeMutableBufferPointer {l in right.withUnsafeMutableBufferPointer {r in audio.render(left:l.baseAddress!,right:r.baseAddress!,frames:l.count,sampleRate:44100)}}
                    var notes = self.customLevelEvidence["presentation_audio"] as? [[String:Any]] ?? []
                    if notes.count < 100 {notes.append(["sound":name,"voice":voice,"frames":left.count,"nonzero_frames":zip(left,right).filter{$0 != 0 || $1 != 0}.count])}
                    self.customLevelEvidence["presentation_audio"] = notes
                }
                return Double(voice)
            }
            if key.hasPrefix("Text:") {
                let text = self.resources.textToken(String(key.dropFirst(5)));defer {self.resources.release(text)}
                return Double(self.resources.invoke(0x42af70,self.base.applicationToken,[text]))
            }
            throw ClawCustomLua.Failure.script("NotImplemented: native service \(key)")
        }
        customLua = lua
        customAudioReady = false;customAudioRetiring = false
        customAssets = package;customAssetsMapped = false
        customPalettes = palettes
        customWorld = candidate
        customCheckpointWorldURL = url
        resources.configureWorldBuffers(candidate.world)
        customLevelEvidence = ["file":url.lastPathComponent,"base_level":candidate.level,
            "package_files":package.files.count,"package_images":[],"unresolved_image_directories":unresolvedImageDirectories,"sha256":SHA256.hash(data:candidate.data).map{String(format:"%02x",$0)}.joined(),"reads":0]
        customLevelEvidence["capabilities"] = ["file":capabilityReport.file,"requirement_count":capabilityReport.requirements.count,"dynamic_requirements":capabilityReport.dynamicRequirements] as [String:Any]
        customLevelEvidence["checkpoint_owner"] = crazyScriptOwned ? "script SaveSystem":"automatic"
        customLevelEvidence["checkpoint_slots"] = crazySaves?.slots.keys.sorted() ?? []
        customLevelEvidence["checkpoint_warning"] = checkpointWarning
        // Native dialog confirmation replaces 437710: selected CString ->
        // application +c0, followed by the original New Game command 8005.
        // Keep the original loading-screen name, with a bounded ASCII alias
        // for filenames the original Windows CString cannot represent.
        let leaf = String(url.lastPathComponent.unicodeScalars.map { scalar -> Character in
            scalar.value >= 32 && scalar.value < 127 && !"/\\:".unicodeScalars.contains(scalar) ? Character(String(scalar)):"_"
        }.prefix(100))
        customVirtualPath = "C:\\CLAW\\Custom\\" + leaf
        _ = transport(0x4f650f,base.applicationToken+0xc0,[])
        put(base.applicationToken+0xc0,cstring(customVirtualPath))
        customLevelsActive = false
        phase = "native load"
        _ = resources.invoke(0x426e30,base.applicationToken,[0,0x8005,0])
        if let error = customLevelEvidence["lua_map_error"] as? String ?? customLua?.error {
            try retireFailedCustomLevel(error)
            throw ClawCustomLua.Failure.script(error)
        }
        guard resources.fault == 0 else {throw ClawNativeMenuResources.Failure.invalid("Custom level load at \(String(resources.faultAddress,radix:16))")}
        phase = "loaded"
    }

    private func crazyValues() -> [UInt32] {
        let actor = w(0x537e88),pd = w(w(actor+0x6c)+0x14)
        return [w(actor+0xf8),w(actor+0x10c),w(actor+0x4c),w(actor+0x50),
                w(pd+0x70),w(pd+0x74),w(pd+0x78),w(pd+0x7c)] +
            (0..<9).map{w(pd+0x88+UInt32($0*4))} + [w(0x537210)]
    }
    private func updateCrazyCheckpoint() throws {
        guard customWorld != nil,!crazyScriptOwned,let slot = crazyPendingSlot,
              w(0x537210) > crazyLastSave &+ 2000,let path = crazySaveURL else {return}
        crazyPendingSlot = nil
        let values = crazyValues()
        if crazySaves?.save(values,slot:slot) == true {
            try crazySaves?.write(path);crazyLastSave = w(0x537210)
            _ = resources.invoke(0x42af70,base.applicationToken,[0x5253a8])
            customLevelEvidence["checkpoint_saved"] = ["slot":slot,"values":values]
            customLevelEvidence["checkpoint_slots"] = crazySaves?.slots.keys.sorted() ?? []
        }
    }
    private func restoreCrazyCheckpoint(state:UInt32) {
        guard let v = crazyRestore else {return};crazyRestore = nil
        applySuperCheckpoint(v,state:state)
        customLevelEvidence["checkpoint_restored"] = v
    }
    private func applySuperCheckpoint(_ v:[UInt32],state:UInt32,retireLoadedFlag:Bool = true) {
        let actor = w(0x537e88),pd = w(w(actor+0x6c)+0x14)
        put(actor+0xf8,v[0]);put(actor+0x10c,v[1]);put(pd+0x44,v[0]);put(pd+0x48,v[1])
        put(actor+0x4c,v[2]);put(actor+0x50,v[3]);put(state+0x44,v[2]);put(state+0x48,v[3])
        // Original super-checkpoint startup seeds these defaults before
        // constructing the HUD. Keep legacy format-3 restores consistent too.
        put(0x534cc4,v[0]);put(0x534cc8,v[1])
        put(0x534ccc,v[2]);put(0x534cd0,v[3])
        let world = w(w(state+0xc)+0x24)
        _ = resources.invoke(0x42d5f0,world,[v[2],v[3]])
        for i in 0..<4 {put(pd+0x70+UInt32(i*4),v[4+i])}
        for i in 0..<9 {put(pd+0x88+UInt32(i*4),v[8+i]);put(pd+0xb0+UInt32(i*4),v[8+i])}
        put(pd+0xec,(v[0]/1000000+1)*1000000)
        put(pd+0x24,1);put(pd+0x4c,v[2]);put(pd+0x50,v[3]);put(0x534ca4,1)
        // This native load has already initialized a standing player. The
        // v1.0 death-respawn state 23 resets health to 100, unlike a custom
        // saved-game restore; retain the initialized pose and saved health.
        // The original checkpoint tick consumes this loaded-save marker,
        // retiring the loaded super checkpoint instead of saving it again.
        put(0x537210,v[17]);put(0x536f00,retireLoadedFlag ? 1:0)
    }
    private func completeCrazyLevel() throws {
        guard customWorld != nil,!crazyCompleted,let path = crazySaveURL else {return}
        crazyCompleted = true
        let v = crazyValues()
        let collected = v[8..<17].reduce(0,&+)
        let total = (0..<9).map{w(0x5381e0+UInt32($0*4))}.reduce(0,&+)
        let cheated = w(w(base.applicationToken+0x48)+0x128) != 0
        let recorded = crazySaves?.complete(collected:collected,total:total,cheated:cheated) == true
        if recorded {try crazySaves?.write(path)}
        customLevelEvidence["completion"] = ["collected":collected,"total":total,"perfect":collected == total,"cheated":cheated,"recorded":recorded]
    }
    // Diagnostic placement only; the real scanner contact still requires a
    // delivered key, and all saved stats come from the live player.
    func placeCrazyCheckpointCheck(_ slot:Int) throws {
        guard let world = customWorld,let object = world.world.planes.flatMap(\.objects).first(where:{$0.logic == (slot == 1 ? "FirstSuperCheckpoint":"SecondSuperCheckpoint")}) else {throw ClawCrazyHookSaves.Failure.invalid}
        let player = w(0x537e88)
        put(player+0x4c,UInt32(max(0,object.x-80)));put(player+0x50,UInt32(max(0,object.y-32)))
        let pd = w(w(player+0x6c)+0x14)
        // Non-default inventory makes the restore assertion distinguish a
        // checkpoint from an ordinary fresh start. This is a labelled fixture.
        put(player+0x10c,73);put(pd+0x48,73);put(player+0xf8,12345);put(pd+0x44,12345)
        for i in 0..<3 {put(pd+0x70+UInt32(i*4),UInt32(7+i))}
        for i in 0..<9 {put(pd+0x88+UInt32(i*4),UInt32(i+1));put(pd+0xb0+UInt32(i*4),UInt32(i+1))}
        customLevelEvidence["checkpoint_fixture"] = ["slot":slot,"object":[object.x,object.y],"inventory":"synthetic non-default fixture; real map and scanner"] as [String:Any]
    }

    // Native backing for the plane bindings. Resolve each operation against the
    // current world table, so a stale Lua index never becomes a host pointer.
    func customPlane(_ index:Int, world:UInt32) -> UInt32? {
        guard world != 0, index >= 0, index < Int(w(world+0x3c)), index < 16 else {return nil}
        let token = w(w(world+0x38)+UInt32(index*4))
        return token != 0 && heap.lookupBytes(token,count:0x158) != nil ? token:nil
    }
    func customPlane(named name:String, world:UInt32) -> Int? {
        for index in 0..<min(16,Int(w(world+0x3c))) {
            if let token = customPlane(index,world:world),resources.text(token+0xb4) == name {return index}
        }
        return nil
    }
    private func customPlaneService(_ key:String,_ value:Double) throws -> Double {
        let p = key.split(separator:":",omittingEmptySubsequences:false).map(String.init)
        let world = w(base.sceneToken+0x24)
        func invalid() -> ClawCustomLua.Failure {.script("ValueBounds: plane request " + key)}
        func image(_ name:String) throws -> UInt32 {
            guard !name.isEmpty,name.utf8.count < 128,!name.contains(":"),!name.utf8.contains(0) else {throw invalid()}
            let text = resources.textToken(name.uppercased());defer {resources.release(text)}
            let token = customRegistryValue(w(base.sceneToken+16),text)
            guard token != 0,heap.lookupBytes(token,count:0x6c) != nil else {throw ClawCustomLua.Failure.script("ImageNotFound: " + name)}
            return token
        }
        guard p.count >= 2,world != 0 else {throw invalid()}
        if p[1] == "CheckCollision",p.count == 4,ProcessInfo.processInfo.arguments.contains("--lua-runtime-check"),
           let x = UInt32(p[2]),let y = UInt32(p[3]),let source = customWorld?.world.planes.first(where:{$0.flags&1 != 0}),
           Int(x) < source.width*source.tileWidth,Int(y) < source.height*source.tileHeight {
            let actor = resources.allocate(0x128);defer {resources.release(actor)}
            put(actor+0x4c,x);put(actor+0x50,y);put(actor+0x124,0)
            let result = resources.invoke(0x4cd740,world,[actor,0])
            guard resources.fault == 0 else {throw invalid()}
            return Double(result)
        }
        if p[1] == "Image",p.count == 3 {_ = try image(p[2]);return 1}
        if p[1] == "Find",p.count == 3,p[2].utf8.count < 128,!p[2].utf8.contains(0) {return Double(customPlane(named:p[2],world:world).map {$0+1} ?? 0)}
        if p[1] == "Main",p.count == 2 {
            for i in (0..<min(16,Int(w(world+0x3c)))).reversed() {if let token = customPlane(i,world:world),w(token+8)&1 != 0 {return Double(i+1)}}
            throw invalid()
        }
        guard p.count >= 3,let h = Int(p[2]),h > 0,h <= 16,let plane = customPlane(h-1,world:world) else {throw invalid()}
        if p[1] == "Screen",p.count == 4,let i = UInt32(p[3]),i < 4 {return Double(Int32(bitPattern:w(plane+0x40+i*4)))}
        if p[1] == "Tileset",p.count == 5,let slot = UInt32(p[3]),slot < w(plane+0xa4) {
            let token = try image(p[4])
            put(w(plane+0xa0)+slot*4,token)
            customLevelEvidence["lua_tileset_"+String(h)+"_"+String(slot)] = p[4]
            return 0
        }
        guard p.count == 5,let x = Int(p[3]),let y = Int(p[4]),let old = customTile(h-1,x:x,y:y,world:world) else {throw invalid()}
        if p[1] == "Get" {return Double(old)}
        guard p[1] == "Place",value.isFinite,value.rounded() == value,value >= Double(Int32.min),value <= Double(UInt32.max) else {throw invalid()}
        guard customPlaceTile(h-1,x:x,y:y,tile:Int32(truncatingIfNeeded:Int64(value)),world:world) else {
            let tile = UInt32(truncatingIfNeeded:Int64(value)),slot = tile >> 16
            let count = w(plane+0xa4),set = slot < count ? w(w(plane+0xa0)+slot*4):0
            throw ClawCustomLua.Failure.script("ValueBounds: tile \(Int64(value)) in plane \(h), sets \(count), range \(w(set+0x64))...\(w(set+0x68)), frames \(w(set+0x18)), requested frame exists \(slot < count && (tile&0xffff) < w(set+0x18) && w(w(set+0x14)+(tile&0xffff)*4) != 0)")
        }
        customLevelEvidence["lua_tile_"+String(h)] = ["x":x,"y":y,"before":old,"after":Int64(value)]
        if value >= 0 {
            let tile = UInt32(value),set = w(w(plane+0xa0)+(tile >> 16)*4)
            let frame = w(w(set+0x14)+(tile&0xffff)*4)
            let graph = w(frame+0x30),surface = w(frame+0x2c)
            // A frame can use either native indexed representation. The tile
            // validator above checks its slot; the renderer validates storage.
            customLevelEvidence["lua_indexed_tile_"+String(h)] = ["tile":tile,"indexed_frame":graph != 0 || surface != 0,"compressed":graph != 0,"surface":surface != 0]
        }
        return 0
    }
    func customTile(_ index:Int, x:Int, y:Int, world:UInt32) -> Int32? {
        guard let plane = customPlane(index,world:world), x >= 0,y >= 0,
              x < Int(w(plane+0x28)),y < Int(w(plane+0x2c)) else {return nil}
        return Int32(bitPattern:w(w(plane+0x20)+UInt32((y*Int(w(plane+0x28))+x)*4)))
    }
    @discardableResult func customPlaceTile(_ index:Int, x:Int, y:Int, tile:Int32, world:UInt32) -> Bool {
        guard customTile(index,x:x,y:y,world:world) != nil,let plane = customPlane(index,world:world) else {return false}
        let word = UInt32(bitPattern:tile)
        if word != 0xffffffff && word != 0xeeeeeeee {
            let setIndex = word >> 16, id = word & 0xffff
            guard setIndex < w(plane+0xa4) else {return false}
            let images = w(w(plane+0xa0)+setIndex*4)
            guard images != 0,id >= w(images+0x64),id <= w(images+0x68),w(w(images+0x14)+id*4) != 0 else {return false}
            if w(plane+8) & 1 != 0 && id >= w(world+0x50) {return false}
        }
        // The original renderer and collision query both read this live table.
        put(w(plane+0x20)+UInt32((y*Int(w(plane+0x28))+x)*4),word)
        return true
    }
    struct CustomTileLayer {
        var plane:Int, x:Int, y:Int, width:Int, height:Int, content:[Int32]
    }
    func customTileLayer(_ index:Int,x:Int,y:Int,width:Int,height:Int,world:UInt32) -> CustomTileLayer? {
        guard customPlane(index,world:world) != nil,
              x >= Int(Int32.min),x <= Int(Int32.max),y >= Int(Int32.min),y <= Int(Int32.max),
              width > 0,height > 0,width <= 4096,height <= 4096,width*height <= Int(ClawNativeMenuResources.gridCellLimit) else {return nil}
        var content:[Int32] = [];content.reserveCapacity(width*height)
        for row in 0..<height {for column in 0..<width {
            content.append(customTile(index,x:x+column,y:y+row,world:world) ?? -2)
        }}
        return CustomTileLayer(plane:index,x:x,y:y,width:width,height:height,content:content)
    }
    @discardableResult func customPlaceLayer(_ layer:CustomTileLayer,world:UInt32) -> Int {
        guard layer.x >= Int(Int32.min),layer.x <= Int(Int32.max),layer.y >= Int(Int32.min),layer.y <= Int(Int32.max),
              layer.width > 0,layer.height > 0,layer.width <= 4096,layer.height <= 4096,
              layer.content.count == layer.width*layer.height else {return 0}
        var placed = 0
        for row in 0..<layer.height {for column in 0..<layer.width {
            let tile = layer.content[row*layer.width+column]
            if tile != -2,customPlaceTile(layer.plane,x:layer.x+column,y:layer.y+row,tile:tile,world:world) {placed += 1}
        }}
        return placed
    }

    // Elect the existing raw-mask transport for the native app. These bodies
    // already exist in RawTileDescription/WorldFileRuntime; the menu dispatch
    // previously had no route to them because retail maps use types 1 and 2.
    private func customMaskService(_ function:UInt32,_ token:UInt32,_ arguments:[UInt32]) -> UInt32? {
        let scans:Set<UInt32> = [0x4d5900,0x4d5960,0x4d59b0,0x4d5a20,0x4d5a80,0x4d5af0,0x4d5b50,0x4d5bd0]
        let expected:Int
        if scans.contains(function) {expected = 4}
        else if function == 0x4cdef0 {expected = 2}
        else if [UInt32(0x40af90),0x4cdf10,0x4cde90].contains(function) {expected = 0}
        else {return nil}
        guard w(token) == 0x513a10 else {return nil}
        guard arguments.count == expected else {return resources.fail(function)}
        let host = ClawSceneActorHost(context:Unmanaged.passUnretained(self).toOpaque(),lookup:{raw,at,words in
            guard let raw else {return nil}
            return Unmanaged<ClawNativeMenuInterface>.fromOpaque(raw).takeUnretainedValue().heap.lookup(at,words:words)
        },allocate:nil,free:{raw,at in
            guard let raw else {return}
            Unmanaged<ClawNativeMenuInterface>.fromOpaque(raw).takeUnretainedValue().resources.release(at)
        },call:nil,readClock:nil)
        var fault:UInt32 = 0,result:UInt32 = 0
        let done:UInt32
        if function == 0x4cde90 {
            var context = ClawWorldFileContext(),args = ClawWorldFileArguments()
            context.scene = host;args.count = 0
            done = claw_world_file_entry(function,token,args,&context,nil,nil,&result)
            fault = context.fault
        } else {
            var args = ClawRawTileArguments();args.count = UInt32(arguments.count)
            withUnsafeMutableBytes(of:&args.words) {bytes in
                for (index,word) in arguments.enumerated() {bytes.storeBytes(of:word,toByteOffset:index*4,as:UInt32.self)}
            }
            done = claw_raw_tile_entry(function,token,args,host,&fault,&result)
        }
        return done == 1 && fault == 0 ? result:resources.fail(function)
    }

    // Geometry-only probe: unchanged package input is parsed and validated;
    // original world loading uses a private copy with object population disabled.
    // Real gameplay acceptance is a separate real-input check, never this probe.
    func checkPlaneGeometry(_ request:URL,_ output:URL) throws {
        guard ProcessInfo.processInfo.arguments.contains("--mute"),
              let paths = try JSONSerialization.jsonObject(with:Data(contentsOf:request)) as? [String:String] else {throw AssetError.invalid("Plane check request")}
        var results:[String:Any] = [:]
        // The ordinary allocator remains capped; the explicit world-buffer
        // path and its snapshot image accept the measured maximum, and no more.
        do {
            let storage = ClawTokenHeap(),limit = ClawTokenHeap.worldBufferByteLimit
            guard storage.allocate(bytes:4_194_305) == 0,storage.allocateWorldBuffer(bytes:limit+1) == 0 else {throw AssetError.invalid("World allocation bound")}
            let token = storage.allocateWorldBuffer(bytes:limit)
            guard token != 0,storage.lookupBytes(token,count:limit) != nil else {throw AssetError.invalid("World allocation maximum")}
            try storage.checkpoint().image.validate()
            storage.free(token)
        }
        for name in paths.keys.sorted() {
            let url = URL(fileURLWithPath:paths[name]!)
            if name.hasPrefix("invalid_") {
                do {_ = try ClawCustomWorld(url:url)}
                catch {results[name] = ["rejected":true];continue}
                throw AssetError.invalid("Malformed geometry was accepted: \(name)")
            }
            let candidate = try ClawCustomWorld(url:url),source = candidate.world
            func register(_ path:String,_ prefix:String) {
                let key = resources.textToken(prefix),sep = resources.textToken("_")
                _ = resources.invoke(0x4cff40,w(base.sceneToken+16),[resources.directory(path),key,sep])
                resources.release(key);resources.release(sep)
            }
            register("LEVEL\(candidate.level)_TILES","")
            let package = try ClawCustomAssets(worldURL:url)
            try resources.mountPackage(package.archive());customAssets = package;customAssetsMapped = false
            mapCustomAssets(tilesOnly:true)
            guard resources.fault == 0 else {throw AssetError.invalid("Geometry tiles \(name) at \(String(resources.faultAddress,radix:16))")}
            var data = source.decodedBytes
            func setWord(_ offset:Int,_ value:UInt32) {var v = value.littleEndian;withUnsafeBytes(of:&v){data.replaceSubrange(offset..<offset+4,with:$0)}}
            setWord(8,1) // Private uncompressed geometry fixture.
            for plane in source.planes {setWord(plane.encodedHeaderOffset+128,0);setWord(plane.encodedHeaderOffset+140,0)}
            resources.configureWorldBuffers(source)
            let buffer = resources.allocate(UInt32(data.count)),world = resources.allocate(224)
            guard let bytes = heap.lookupBytes(buffer,count:UInt32(data.count)) else {throw AssetError.invalid("Geometry allocation")}
            data.copyBytes(to:bytes,count:data.count)
            _ = resources.invoke(0x4cace0,world,[base.sceneToken,0,0])
            _ = resources.invoke(0x4cb040,world,[640,480])
            let loaded = resources.invoke(0x4cb200,world,[buffer])
            guard loaded == 1,resources.fault == 0,w(world+0x3c) == source.planes.count else {
                throw AssetError.invalid("Geometry \(name) at \(String(resources.faultAddress,radix:16)): \(resources.failureTrace.suffix(8))")
            }
            var planes:[[String:Any]] = []
            for (index,plane) in source.planes.enumerated() {
                guard let token = customPlane(index,world:world),w(token+8) == plane.flags,
                      w(token+0x28) == plane.width,w(token+0x2c) == plane.height,
                      w(token+0x38) == plane.tileWidth,w(token+0x3c) == plane.tileHeight,
                      Int(Int32(bitPattern:w(token+0x80))) == plane.z,
                      Int(Int32(bitPattern:w(token+0x94))) == plane.movementPercentX,
                      Int(Int32(bitPattern:w(token+0x98))) == plane.movementPercentY else {throw AssetError.invalid("Plane metadata \(name)/\(index)")}
                for (cell,tile) in plane.tiles.enumerated() {
                    guard w(w(token+0x20)+UInt32(cell*4)) == UInt32(bitPattern:Int32(tile)) else {throw AssetError.invalid("Plane tile copy")}
                }
                // Metamorphic check against the recovered original clamp:
                // toggling each sampled high bit leaves its geometry unchanged.
                let projection = (0..<20).map{w(token+0x10+UInt32($0*4))}
                for bit in [UInt32(0x20),0x40,0x80] {
                    put(token+8,plane.flags ^ bit)
                    _ = resources.invoke(0x4d0a60,token)
                    guard (0..<20).map({w(token+0x10+UInt32($0*4))}) == projection else {throw AssetError.invalid("High-bit clamp behavior")}
                }
                put(token+8,plane.flags)
                planes.append(["high_bit_clamp_invariant":true,"name":plane.name,"flags":w(token+8),"z":Int(Int32(bitPattern:w(token+0x80))),"size":[plane.width,plane.height],"tile_size":[w(token+0x38),w(token+0x3c)],"objects":plane.objectCount])
            }
            var maskPixels = 0
            for (index,tile) in source.tileDescriptions.enumerated() where tile.type == 3 {
                let token = w(w(world+0x4c)+UInt32(index*4))
                for y in 0..<Int(tile.height) {for x in 0..<Int(tile.width) {
                    let actual = resources.invoke(0x4cdef0,token,[UInt32(x),UInt32(y)])
                    guard actual == tile.attribute(x:x,y:y) else {throw AssetError.invalid("Mask attribute mismatch")}
                    maskPixels += 1
                }}
            }
            var row:[String:Any] = ["planes":planes,"object_count":source.planes.reduce(0){$0+$1.objectCount},"mask_pixels":maskPixels,"all_tiles_copied":true,"decoded_bytes":source.decodedBytes.count]
            if name == "arcana_v13" {
                guard let action = customPlane(named:"Action",world:world),let token = customPlane(action,world:world),
                      let old = customTile(action,x:117,y:164,world:world),
                      let layer = customTileLayer(action,x:117,y:164,width:1,height:1,world:world) else {throw AssetError.invalid("Arcana ladder plane")}
                let actor = resources.allocate(0x128)
                put(actor+0x4c,117*64+32);put(actor+0x50,164*64+32);put(actor+0x124,0)
                guard customPlaceTile(action,x:117,y:164,tile:-1,world:world) else {throw AssetError.invalid("Clear ladder")}
                let clear = resources.invoke(0x4cd740,world,[actor,0])
                guard customPlaceTile(action,x:117,y:164,tile:203,world:world) else {throw AssetError.invalid("Place ladder")}
                let climb = resources.invoke(0x4cd740,world,[actor,0])
                guard clear == 0,climb == 3,w(w(token+0x20)+UInt32((164*Int(w(token+0x28))+117)*4)) == 203,
                      customPlaceLayer(layer,world:world) == 1,customTile(action,x:117,y:164,world:world) == old,
                      !customPlaceTile(action,x:-1,y:0,tile:203,world:world),!customPlaceTile(action,x:117,y:164,tile:65535,world:world) else {throw AssetError.invalid("Live ladder collision/layer restore")}
                row["ladder"] = ["cleared":clear,"placed":climb,"layer_restored":true,"bounds_rejected":true]
                resources.release(actor)
            }
            guard resources.fault == 0 else {throw AssetError.invalid("Geometry query fault")}
            results[name] = row
            _ = resources.invoke(0x4cdd10,world,[1]);resources.release(buffer)
            unmapCustomAssets()
            resources.unmountPackage();customAssets = nil;customAssetsMapped = false
            resources.configureWorldBuffers(nil)
            guard resources.fault == 0 else {throw AssetError.invalid("Geometry cleanup")}
        }
        try JSONSerialization.data(withJSONObject:["status":"pass","samples":results],options:[.prettyPrinted,.sortedKeys]).write(to:output,options:.atomic)
    }

    // Explicit regression fixture, enabled only by --lua-runtime-check.
    // This positions the player beside a real serialized object; the check
    // then delivers movement through the window, never a synthetic key.
    func placeCustomLuaCheck(_ encoded:String) throws {
        let name = encoded.replacingOccurrences(of:"%20",with:" ")
        guard let world = customWorld,let object = world.world.planes.flatMap(\.objects).first(where:{$0.logic == "CustomLogic" && $0.name == name}) else {throw AssetError.invalid("Lua check object not found: \(name)")}
        let player = w(0x537e88)
        put(player+0x4c,UInt32(max(0,object.x-100)));put(player+0x50,UInt32(max(0,object.y-32)))
        customLevelEvidence["lua_check_placement"] = ["name":name,"object":[object.x,object.y],"player":[max(0,object.x-100),max(0,object.y-32)]]
    }
    func checkCustomLuaValues() throws {
        guard let customLua else {throw AssetError.invalid("Lua session absent")}
        try customLua.evaluate("""
        local o=CreateObject{Logic='DoNothing',X=120,Y=140,Name='native-fixture'}
        assert(o.X==120 and o.Y==140)
        assert(GetClaw()._p.PistolAmmo==GetClaw().PData.PistolAmmo)
        o.User[0]=37;assert(o.UserValue1==37)
        o._v.State=9;assert(o.State==9)
        o.UserRect1={-1,-2,3,4};assert(o.UserRect1.Left==-1 and o.UserRect1.Bottom==4)
        o.Flags.AlwaysActive=true;assert(o.Flags.AlwaysActive)
        o:Destroy();assert(o.State==9)
        _nativeCheckObject=o
        """)
        customLevelEvidence["lua_native_values"] = "pending deferred destruction"
    }
    func checkCustomGameplayScript(_ encoded:String) throws {
        guard let customLua,let data = Data(base64Encoded:encoded),let script = String(data:data,encoding:.utf8) else {throw AssetError.invalid("Gameplay check encoding/session")}
        try customLua.evaluate(script)
        customLevelEvidence["gameplay_check"] = ["script":script,"status":"pass","objects":try customLua.gameplaySnapshot()]
    }
    func checkCustomGameplayValues() throws {
        guard let customLua else {throw AssetError.invalid("Lua session absent")}
        try customLua.evaluate("""
        local claw=GetClaw()
        local t=GetTime();assert(GetTicks()==t)
        local o=CreateObject{logic='DoNothing',id=2147483000,x=claw.X+200,y=claw.Y-100,z=1000,image='GAME_TREASURE_COINS'}
        assert(o.X==claw.X+200 and o.Y==claw.Y-100)
        assert(GetObject(2147483000)==o)
        o.tag={value=73};assert(GetObject(2147483000).tag.value==73)
        o:SetFrame(1);assert(o.I==1)
        o:SetAnimation('GAME_CYCLE100');o:AnimationStep()
        o.MoveRect={-4,-4,4,4};o.PhysicsType=8
        local x=o.X;local result=o:Physics(x+3,o.Y,8);assert(o.X==x+3 and type(result)=='number')
        local found=LoopThroughObjects(function(p) if p==o then return p end end);assert(found==o)
        local count=GetTreasuresNb('Coin');RegisterTreasure('Coin',2);assert(GetTreasuresNb(0)==count+2)
        RegisterTreasure(0,-2);assert(GetTreasuresNb(0)==count)
        CreateGoodie{x=claw.X+160,y=claw.Y-60,powerup=33}
        o:Destroy();assert(o.tag.value==73)
        _nativeCheckObject=o
        """)
        customLevelEvidence["gameplay_values"] = "pass: lowercase creation, ID lookup, custom fields, frame/animation, native physics, iteration, goodie and treasure totals"
    }
    func checkCustomLuaStale() throws {
        guard let customLua else {throw AssetError.invalid("Lua session absent")}
        try customLua.evaluate("""
        local ok,e=pcall(function() return _nativeCheckObject.State end)
        assert(not ok and e:find('StaleHandle'))
        _nativeCheckObject=nil
        """)
        customLevelEvidence["lua_native_values"] = "pass: native creation, scalar/rectangle/flags/array aliases, deferred destruction, stale handle"
    }

    private func customRegistryValue(_ controller:UInt32,_ key:UInt32)->UInt32 {
        let slot = resources.allocate(4);defer {resources.release(slot)}
        put(slot,0)
        _ = transport(0x4f6286,controller+16,[key,slot])
        return w(slot)
    }

    // Focused app check: real package bytes enter the same registries as play.
    // It deliberately does not certify plane composition or scripted gameplay.
    func checkAssetPackages(_ request:URL,_ output:URL) throws {
        guard ProcessInfo.processInfo.arguments.contains("--mute"),
              let paths = try JSONSerialization.jsonObject(with:Data(contentsOf:request)) as? [String:String] else {throw AssetError.invalid("Asset check request")}
        var results:[String:Any] = [:]
        func root(_ name:String,_ animations:Bool = false)->UInt32 {
            let key = resources.textToken(name);defer {resources.release(key)}
            return customRegistryValue(w(base.sceneToken+(animations ? 44:16)),key)
        }
        func register(_ directory:UInt32,_ prefix:String,_ animations:Bool = false) {
            guard directory != 0 else {return}
            let key = resources.textToken(prefix), sep = resources.textToken("_")
            _ = resources.invoke(animations ? 0x4ce0d0:0x4cff40,w(base.sceneToken+(animations ? 44:16)),[directory,key,sep])
            resources.release(key);resources.release(sep)
        }
        for name in paths.keys.sorted() {
            let url = URL(fileURLWithPath:paths[name]!),package = try ClawCustomAssets(worldURL:url)
            let raw = try Data(contentsOf:url)
            let title = String(decoding:raw[16..<80].prefix(while:{$0 != 0}),as:UTF8.self)
            let digits = title.drop(while:{!$0.isNumber}).prefix(while:{$0.isNumber})
            guard let level = Int(digits),(1...14).contains(level) else {throw AssetError.invalid("Probe base level")}
            register(resources.directory("LEVEL\(level)_TILES"),"")
            register(resources.directory("LEVEL\(level)_IMAGES"),"LEVEL")
            register(resources.directory("LEVEL\(level)_ANIS"),"LEVEL",true)
            guard resources.fault == 0 else {throw AssetError.invalid("Retail asset probe at \(String(resources.faultAddress,radix:16))") }
            let baseSplash = root("LEVEL_SPLASH"), fallback = baseSplash == 0 ? 0:w(w(baseSplash+20)+(name == "synthetic" ? 2:8)*4)
            try resources.mountPackage(package.archive())
            customAssets = package;customAssetsMapped = false
            mapCustomAssets()
            guard resources.fault == 0 else {throw AssetError.invalid("Package registry at \(String(resources.faultAddress,radix:16)): \(resources.failureTrace.suffix(6))")}
            var row:[String:Any] = ["files":package.files.count,"mapped":customLevelEvidence["package_images"] ?? []]
            if name == "cannonballin" {
                let images = root("CUSTOM_SEATREAT"), splash = root("LEVEL_SPLASH")
                guard images != 0,w(w(images+20)+4) != 0,splash != 0 else {throw AssetError.invalid("Cannon images not registered")}
                row["cannon_frame"] = w(w(images+20)+4)
                row["base_fallback"] = fallback == 0 || w(w(splash+20)+8*4) == fallback
                guard row["base_fallback"] as? Bool == true else {throw AssetError.invalid("Base frame fallback")}
            }
            if name == "synthetic" {
                let images = root("LEVEL_SPLASH")
                guard fallback != 0,images != 0,w(w(images+20)+2*4) == fallback else {throw AssetError.invalid("Synthetic base frame fallback")}
                row["base_fallback"] = "Retail frame 2 retained beside supplied frame 1"
            }
            if name == "heart_of_the_woods" {
                let tiles = root("BACK")
                guard tiles != 0,w(tiles+104) >= 100,w(w(tiles+20)+100*4) != 0 else {throw AssetError.invalid("Heart tiles missing")}
                row["tile_100"] = w(w(tiles+20)+100*4)
            }
            if name == "just_keep_calm" {
                let path = "LEVEL/WOLVINGTON/ADVANCE.ANI"
                guard let data = try package.data(path) else {throw AssetError.invalid("Missing sample ANI")}
                let expected = try ClawAnimation(data:data), seq = root("LEVEL_WOLVINGTON_ADVANCE",true)
                guard seq != 0,w(seq+16) == expected.frames.count else {throw AssetError.invalid("ANI frame count")}
                var timing:[[String:Any]] = []
                for (index,frame) in expected.frames.enumerated() {
                    let record = w(w(seq+12)+UInt32(index*4))
                    guard w(record+20) == frame.record.parameter,w(record+24) == frame.record.duration else {throw AssetError.invalid("ANI frame timing")}
                    timing.append(["image":frame.imageID,"milliseconds":frame.milliseconds,"event":frame.event ?? ""])
                }
                row["ani_timing"] = timing
            }
            if let loading = try package.data("SCREENS/LOADING.PCX") {
                let resource = resources.resource(directory:resources.packageDirectory("SCREENS"),name:"LOADING",type:0x504358)
                guard resources.load(resource) == loading else {throw AssetError.invalid("Loading PCX bytes")}
                let key = resources.textToken("PACKAGE_LOADING")
                _ = resources.invoke(0x4cfaa0,w(base.sceneToken+16),[resource,key,1,1]);resources.release(key)
                guard resources.fault == 0,root("PACKAGE_LOADING") != 0 else {throw AssetError.invalid("Loading screen decode")}
                customImageKeys.insert("PACKAGE_LOADING")
                row["loading_screen"] = "PCX registered through native decoder"
            }
            results[name] = row
            unmapCustomAssets()
        }
        if let cannon = paths["cannonballin"] {
            let source = URL(fileURLWithPath:cannon),folder = output.deletingLastPathComponent().appendingPathComponent("imported")
            let first = try ClawCustomAssets.importPackage(source.deletingLastPathComponent(),into:folder)
            let second = try ClawCustomAssets.importPackage(source.deletingLastPathComponent(),into:folder)
            guard let a = first.first,let b = second.first,a != b else {throw AssetError.invalid("Import collision")}
            let p = try ClawCustomAssets(worldURL:b)
            guard try p.data("images\\seatreat\\frame001.pid") == ClawCustomAssets(worldURL:source).data("IMAGES/SEATREAT/FRAME001.PID") else {throw AssetError.invalid("Companion import")}
            do {_ = try p.data("../FRAME001.PID");throw AssetError.invalid("Traversal accepted")}
            catch let error as AssetError {if String(describing:error).contains("Traversal accepted") {throw error}}
            results["import"] = ["folder_selection":"same Mac/iPad Files entry point","first":a.lastPathComponent,"renamed":b.lastPathComponent,"windows_paths":true,"traversal_rejected":true]
        }
        resources.unmountPackage();customAssets = nil;customAssetsMapped = false
        try JSONSerialization.data(withJSONObject:["status":"pass","samples":results],options:[.prettyPrinted,.sortedKeys]).write(to:output,options:.atomic)
    }

    private func unmapCustomAssets() {
        var restoredImages = 0
        for (graph,values) in customPaletteImages {
            if let identity = customPaletteImageIdentities[graph],heap.allocationIdentity(at:graph,count:32) === identity,
               let settings = heap.lookup(graph,words:8) {
                settings[5] = values[0];settings[6] = values[1];settings[7] = values[2];restoredImages += 1
            }
        }
        customLevelEvidence["palette_image_restore"] = ["resident_restored":restoredImages,"tracked":customPaletteImages.count]
        customPaletteImages.removeAll();customPaletteImageIdentities.removeAll()
        for token in customPaletteAllocations {resources.release(token)}
        customPaletteAllocations.removeAll();customPaletteTables.removeAll()
        customPalettes = nil;customPaletteState = 0
        customPaletteFirst = Data();customPalettePending = Data();customPaletteLoaded = Data()
        unmapCustomAudio()
        // The retail teardown knows retail prefixes. Explicitly retire CUSTOM
        // roots too, before destroying the archive their image records retain.
        for name in customImageKeys.sorted() {
            let key = resources.textToken(name)
            _ = resources.invoke(0x4cf230,w(base.sceneToken+16),[key]);resources.release(key)
        }
        for name in customAnimationKeys.sorted() {
            let key = resources.textToken(name),controller = w(base.sceneToken+44)
            let sequence = customRegistryValue(controller,key)
            if sequence != 0 {_ = resources.invoke(0x4ce250,sequence,[1]);_ = transport(0x4f5db6,controller+16,[key])}
            resources.release(key)
        }
        customImageKeys.removeAll();customAnimationKeys.removeAll()
    }

    private func mapCustomAssets(tilesOnly:Bool = false,refresh:Bool = false) {
        guard (!customAssetsMapped || refresh),customAssets != nil else {return}
        customAssetsMapped = true
        var registered:[[String:Any]] = []
        var supplied = Set<String>()
        let images = w(base.sceneToken+16), anis = w(base.sceneToken+44)
        func visit(_ directory:UInt32,_ prefix:String,_ animations:Bool) {
            guard directory != 0 else {return}
            var child = resources.invoke(0x4b68e0,directory)
            while child != 0,resources.fault == 0 {
                let name = string(w(child))
                visit(child,prefix.isEmpty ? name:prefix+"_"+name,animations)
                child = resources.invoke(0x4b6900,directory,[child])
            }
            let key = resources.textToken(prefix);defer {resources.release(key)}
            let controller = animations ? anis:images
            var type = resources.invoke(0x4b6920,directory)
            while type != 0,resources.fault == 0 {
                var file = resources.invoke(0x4b6960,directory,[type])
                while file != 0,resources.fault == 0 {
                    let tag = resources.invoke(0x4b61b0,file), name = string(w(file))
                    if animations,tag == 0x414e49 {
                        let full = resources.textToken(prefix.isEmpty ? name:prefix+"_"+name)
                        let old = customRegistryValue(controller,full)
                        if old != 0 {_ = resources.invoke(0x4ce250,old,[1])}
                        customLevelEvidence["loading_animation"] = prefix.isEmpty ? name:prefix+"_"+name
                        _ = resources.invoke(0x4cdff0,controller,[full,file])
                        resources.release(full)
                        customAnimationKeys.insert(prefix.isEmpty ? name:prefix+"_"+name)
                        registered.append(["name":prefix+"_"+name,"type":"ANI"])
                    } else if !animations,[UInt32(0x504944),0x504358].contains(tag),!prefix.isEmpty {
                        // The first numeric substring is the original frame id.
                        let digits = name.drop(while:{!$0.isASCII || !$0.isNumber}).prefix(while:{$0.isASCII && $0.isNumber})
                        let id = UInt32(digits) ?? 0
                        guard id < 100000 else {_ = resources.fail(0x4ce5e0);return}
                        let identity = prefix+"/"+String(id)
                        if !supplied.insert(identity).inserted {
                            file = resources.invoke(0x4b6980,directory,[file]);continue
                        }
                        let root = customRegistryValue(controller,key)
                        if root != 0,id < w(root+24) {
                            let at = w(root+20)+id*4,old = w(at)
                            if old != 0 {_ = resources.invoke(0x4ce8e0,old,[1]);put(at,0)}
                        }
                        _ = resources.invoke(0x4cfaa0,controller,[file,key,id,1])
                        customImageKeys.insert(prefix)
                        registered.append(["name":prefix,"frame":id,"resource":name,"type":tag == 0x504944 ? "PID":"PCX"])
                    }
                    file = resources.invoke(0x4b6980,directory,[file])
                }
                type = resources.invoke(0x4b6940,directory,[type])
            }
        }
        let folders = tilesOnly ? [("TILES","")]:[("TILES",""),("IMAGES","CUSTOM"),("LEVEL","LEVEL")]
        for (folder,prefix) in folders {
            supplied.removeAll();visit(resources.packageDirectory(folder),prefix,false)
        }
        if tilesOnly {customLevelEvidence["package_images"] = registered;return}
        visit(resources.packageDirectory("HELPERIMAGES"),"GAME",false)
        visit(resources.packageDirectory("HELPERANIS"),"GAME",true)
        visit(resources.packageDirectory("ANIS"),"CUSTOM",true)
        visit(resources.packageDirectory("LEVEL"),"LEVEL",true)
        supplied.removeAll()
        if resources.packageDirectory("IMAGES_SPLASH") != 0 {visit(resources.packageDirectory("IMAGES_SPLASH"),"LEVEL_SPLASH",false)}
        customLevelEvidence["package_images"] = registered
    }

    private func writeAudioRegistry(_ map:UInt32,_ name:String,_ value:UInt32) {
        let key = resources.textToken(name);defer {resources.release(key)}
        if value == 0 {_ = audioMapCall(0x4f5db6,map,[key])}
        else {put(audioMapCall(0x4f62a8,map,[key]),value)}
    }
    private func audioMapCall(_ function:UInt32,_ map:UInt32,_ arguments:[UInt32])->UInt32 {
        transport(function,map,arguments)
    }
    private func audioRegistry(_ map:UInt32,_ name:String)->UInt32 {
        let key = resources.textToken(name);defer {resources.release(key)}
        let out = resources.allocate(4);defer {resources.release(out)}
        put(out,0);_ = audioMapCall(0x4f6286,map,[key,out]);return w(out)
    }
    private func mapCustomSounds() {
        guard !customAudioRetiring,customAssetsMapped,let package = customAssets,customSounds.isEmpty else {return}
        let manager = w(base.sceneToken+40)
        var files:[String:UInt32] = [:]
        let helperFolder = resources.packageDirectory("HELPERSOUNDS")
        let helper = helperFolder == 0 ? 0:resources.resource(directory:helperFolder,name:"PLASMASWORD",type:0x574156)
        if helper != 0 {
            let name = "CLAW_PLASMASWORD",old = audioRegistry(manager+16,name),key = resources.textToken(name)
            let sound = base.loadPackageSound(name:key,resource:helper);resources.release(key)
            guard sound != 0,base.fault == 0 else {_ = resources.fail(base.boundary);return}
            customSounds[name] = (old,sound)
        }
        for path in package.files.keys.sorted() where path.hasSuffix(".WAV") && (path.hasPrefix("SOUNDS/") || path.hasPrefix("LEVEL/")) {
            let parts = path.dropLast(4).split(separator:"/").map(String.init)
            let name = ([parts[0] == "SOUNDS" ? "CUSTOM":"LEVEL"]+parts.dropFirst()).joined(separator:"_")
            // As in recursive folder mapping, the first package spelling of
            // an underscore-joined name wins; never orphan a loaded voice pool.
            if customSounds[name] != nil {continue}
            let folder = resources.packageDirectory(parts.dropLast().joined(separator:"/"))
            let file = resources.resource(directory:folder,name:parts.last!,type:0x574156)
            let old = audioRegistry(manager+16,name),key = resources.textToken(name)
            let sound = base.loadPackageSound(name:key,resource:file);resources.release(key)
            guard sound != 0,resources.fault == 0,base.fault == 0 else {_ = resources.fail(base.boundary == 0 ? 0x4ca3b0:base.boundary);return}
            customSounds[name] = (old,sound)
            files[name] = file
        }
        // Some older WWDs, including Las Almenas, explicitly retain the
        // package-root spelling CUSTOM_LEVEL_*. Each map key owns its own
        // entry; an explicit SOUNDS/LEVEL asset takes precedence.
        let requested = Set(customWorld?.world.planes.flatMap(\.objects).map{$0.sound.uppercased()} ?? [])
        for name in customSounds.keys.sorted() where name.hasPrefix("LEVEL_") {
            let alias = "CUSTOM_"+name
            if requested.contains(alias),customSounds[alias] == nil {
                let old = audioRegistry(manager+16,alias),key = resources.textToken(alias)
                let sound = base.loadPackageSound(name:key,resource:files[name]!)
                resources.release(key)
                guard sound != 0,base.fault == 0 else {_ = resources.fail(base.boundary);return}
                customSoundAliases[alias] = (old,sound)
            }
        }
        customLevelEvidence["package_sounds"] = (Array(customSounds.keys)+Array(customSoundAliases.keys)).sorted()
    }
    private func mapCustomMusic() {
        guard !customAudioRetiring,customAssetsMapped,!customMusicMapped,let package = customAssets else {return}
        customMusicMapped = true
        for path in package.files.keys.sorted() where path.hasPrefix("MUSIC/") && path.hasSuffix(".XMI") {
            let name = String(path.dropFirst(6).dropLast(4))
            guard !name.contains("/"),name.utf8.count < 64 else {_ = resources.fail(0x4b53f0);return}
            do {
                guard let data = try package.data(path),ClawXMIDISong(data) != nil else {throw AssetError.invalid("Invalid XMI: \(path)")}
                // LEVEL is also PLAY in CrazyHook's custom-world start path.
                for alias in name == "LEVEL" ? ["LEVEL","PLAY"]:[name] {
                    let old = audioRegistry(musicManager,alias),key = resources.textToken(alias)
                    let bytes = resources.allocate(UInt32(data.count))
                    data.copyBytes(to:heap.lookupBytes(bytes,count:UInt32(data.count))!,count:data.count)
                    let track = resources.invoke(0x4b53f0,musicManager,[bytes,UInt32(data.count),key])
                    resources.release(bytes);resources.release(key)
                    guard track != 0,resources.fault == 0 else {_ = resources.fail(0x4b53f0);return}
                    customMusic[alias] = (old,track)
                }
            } catch {_ = resources.fail(0x4b53f0);return}
        }
        customLevelEvidence["package_music"] = customMusic.keys.sorted()
    }
    private func unmapCustomAudio() {
        unmapCustomSounds();unmapCustomMusic()
    }
    private func unmapCustomSounds() {
        let manager = w(base.sceneToken+40)
        for (name,sound) in removedScriptSounds {writeAudioRegistry(manager+16,name,sound)}
        removedScriptSounds.removeAll()
        for alias in customSoundAliases.keys.sorted() {
            let entry = customSoundAliases[alias]!
            writeAudioRegistry(manager+16,alias,entry.original)
            base.unloadPackageSound(name:alias,sound:entry.replacement,original:entry.original)
        }
        customSoundAliases.removeAll()
        for name in customSounds.keys.sorted() {
            let entry = customSounds[name]!
            writeAudioRegistry(manager+16,name,entry.original)
            base.unloadPackageSound(name:name,sound:entry.replacement,original:entry.original)
        }
        customSounds.removeAll()
    }
    private func unmapCustomMusic() {
        if let volume = customMusicVolume {
            _ = resources.invoke(0x4b55e0,musicManager,[volume.percent]);customMusicVolume = nil
            customLevelEvidence["music_volume_restored"] = w(musicManager+0x28) == volume.raw
        }
        for name in customMusic.keys.sorted() {
            let entry = customMusic[name]!
            if w(musicManager+0x1c) == entry.replacement {_ = resources.invoke(0x4b5550,musicManager)}
            writeAudioRegistry(musicManager,name,entry.original)
            _ = resources.invoke(0x4b56b0,entry.replacement,[1])
        }
        customMusic.removeAll();customMusicMapped = false
    }
    // Native service surface for the bindings task. These use the very same
    // registry records and playback pools consumed by ANI/gameplay events.
    private func legacyAudioService(_ key:String,_ value:Double) throws -> Double {
        let p = key.split(separator:":",omittingEmptySubsequences:false).map(String.init)
        guard p.count >= 3 else {throw ClawCustomLua.Failure.script("ValueType: audio operation")}
        let action = p[1],name = p.last!.uppercased()
        if action == "GetVolume" {return Double(resources.invoke(0x4b5650,musicManager))}
        if action == "SetVolume" {
            guard value.isFinite,value.rounded() == value,(0...100).contains(value) else {throw ClawCustomLua.Failure.script("ValueRange: music volume")}
            if customMusicVolume == nil {
                // The manager stores a 0...127 MIDI volume. Its percentage
                // getter truncates, so feeding it back loses a volume step.
                // Recover the integer setter input that produced this value.
                let raw = w(musicManager+0x28)
                customMusicVolume = ((raw*100+126)/127,raw)
            }
            _ = resources.invoke(0x4b55e0,musicManager,[UInt32(value)])
            return Double(resources.invoke(0x4b5650,musicManager))
        }
        guard !name.isEmpty,!name.contains("/") else {throw ClawCustomLua.Failure.script("ValueType: audio name")}
        let sound = audioRegistry(w(base.sceneToken+40)+16,name)
        if action == "RemoveSound" {
            let null = audioRegistry(w(base.sceneToken+40)+16,"GAME_NULL")
            guard sound != 0,null != 0 else {return 0}
            if removedScriptSounds[name] == nil {removedScriptSounds[name] = sound}
            writeAudioRegistry(w(base.sceneToken+40)+16,name,null);return 1
        }
        if action == "RestoreSound" {
            guard let old = removedScriptSounds.removeValue(forKey:name) else {return 0}
            writeAudioRegistry(w(base.sceneToken+40)+16,name,old);return 1
        }
        if action == "FindSound" {return sound == 0 ? 0:1}
        if action == "StopSound" {return stopCustomSound(name) ? 1:0}
        if action == "PlaySound" {
            guard sound != 0 else {throw ClawCustomCapabilities.Failure(kind:.missing,detail:"PlaySound \(name), companion SOUNDS/ or LEVEL/")}
            guard p.count == 7,let volume = UInt32(p[2]),volume <= 100,let pan = Int32(p[3]),let pitch = UInt32(p[4]),let loop = UInt32(p[5]) else {throw ClawCustomLua.Failure.script("ValueRange: audio playback")}
            let voice = playCustomSound(name,volume:volume,pan:pan,pitch:pitch,loop:loop != 0)
            if ProcessInfo.processInfo.arguments.contains("--lua-runtime-check"),ProcessInfo.processInfo.arguments.contains("--mute"),voice != 0,let audio = base.audio {
                var left = [Float](repeating:0,count:44100),right = left
                left.withUnsafeMutableBufferPointer { l in right.withUnsafeMutableBufferPointer { r in
                    audio.render(left:l.baseAddress!,right:r.baseAddress!,frames:l.count,sampleRate:44100)
                }}
                let nonzero = zip(left,right).filter{$0 != 0 || $1 != 0}.count
                guard nonzero > 0 else {throw ClawCustomLua.Failure.script("Offline legacy audio is silent")}
                customLevelEvidence["legacy_audio_offline"] = ["sound":name,"frames":left.count,"nonzero_frames":nonzero,"sample_rate":44100]
            }
            return Double(voice)
        }
        mapCustomMusic()
        let track = audioRegistry(musicManager,name)
        if action == "SetMusic" {return Double(setCustomMusic(name))}
        if action == "FindMusic" {return track == 0 ? 0:1}
        if action == "MusicState" {return track == 0 ? 0:Double(resources.invoke(0x4b5bd0,track))}
        if action == "StopMusic" {return Double(stopCustomMusic(name))}
        throw ClawCustomLua.Failure.script("NotImplemented: audio operation \(action)")
    }
    func playCustomSound(_ name:String,volume:UInt32? = nil,pan:Int32 = 0,pitch:UInt32 = 0,loop:Bool = false)->UInt32 {
        let sound = audioRegistry(w(base.sceneToken+40)+16,name.uppercased())
        guard sound != 0 else {return 0}
        return resources.invoke(0x4208e0,sound,[volume ?? w(0x532c10),UInt32(bitPattern:pan),pitch,loop ? 1:0])
    }
    func stopCustomSound(_ name:String)->Bool {
        let sound = audioRegistry(w(base.sceneToken+40)+16,name.uppercased())
        return sound != 0 && base.audio?.stopSceneSound(sound) == true
    }
    func setCustomMusic(_ name:String)->UInt32 {
        mapCustomMusic()
        let key = resources.textToken(name.uppercased());defer {resources.release(key)}
        return resources.invoke(0x4b54f0,musicManager,[key,1])
    }
    func stopCustomMusic(_ name:String)->UInt32 {
        mapCustomMusic()
        let track = audioRegistry(musicManager,name.uppercased())
        return track == 0 ? 0:resources.invoke(0x4b5ad0,track)
    }

    func checkAudioPackages(_ request:URL,_ output:URL) throws {
        guard ProcessInfo.processInfo.arguments.contains("--mute"),
              let paths = try JSONSerialization.jsonObject(with:Data(contentsOf:request)) as? [String:String],
              let audio = base.audio else {throw AssetError.invalid("Audio probe requires mute")}
        var results:[String:Any] = [:]
        let directory = output.deletingLastPathComponent()
        for label in paths.keys.sorted() {
            let package = try ClawCustomAssets(worldURL:URL(fileURLWithPath:paths[label]!))
            if label == "las_almenas" {customWorld = try ClawCustomWorld(url:package.worldURL)}
            try resources.mountPackage(package.archive())
            customAssets = package;customAssetsMapped = true
            mapCustomSounds();mapCustomMusic()
            guard resources.fault == 0 else {throw AssetError.invalid("Audio map \(label) at \(String(resources.faultAddress,radix:16))")}
            var sounds:[[String:Any]] = [],tracks:[[String:Any]] = []
            if label == "las_almenas" {
                let alias = "CUSTOM_LEVEL_PEGCRUMBLE"
                guard customSoundAliases[alias] != nil,
                      audioRegistry(w(base.sceneToken+40)+16,alias) == customSoundAliases[alias]?.replacement,
                      audio.sceneSoundPCM(customSoundAliases[alias]!.replacement) == audio.sceneSoundPCM(customSounds["LEVEL_PEGCRUMBLE"]!.replacement),
                      playCustomSound(alias) != 0,stopCustomSound(alias) else {throw AssetError.invalid("WWD sound alias")}
                results["las_almenas-sound-alias"] = ["name":alias,"independent_lifetime":true,"equal_pcm":true,"played_stopped":true]
                let path = "LEVEL/SPRINGBOX/SPRING.ANI",name = "LEVEL_SPRINGBOX_SPRING"
                guard let data = try package.data(path) else {throw AssetError.invalid("Missing spring ANI")}
                let animation = try ClawAnimation(data:data),controller = w(base.sceneToken+44)
                let file = resources.resource(directory:resources.packageDirectory("LEVEL/SPRINGBOX"),name:"SPRING",type:0x414e49)
                let key = resources.textToken(name)
                _ = resources.invoke(0x4cdff0,controller,[key,file]);resources.release(key)
                customAnimationKeys.insert(name)
                let sequence = audioRegistry(controller+16,name)
                guard sequence != 0,w(sequence+16) == animation.frames.count else {throw AssetError.invalid("Spring ANI registration")}
                var milliseconds = 0,marks:[[String:Any]] = []
                for (index,frame) in animation.frames.enumerated() {
                    let record = w(w(sequence+12)+UInt32(index*4))
                    guard w(record+20) == frame.record.parameter,w(record+24) == frame.record.duration else {throw AssetError.invalid("Spring ANI timing")}
                    if let event = frame.event,!event.isEmpty {
                        guard audioRegistry(w(base.sceneToken+40)+16,event) != 0,playCustomSound(event) != 0 else {throw AssetError.invalid("ANI sound \(event)")}
                        marks.append(["milliseconds":milliseconds,"sound":event])
                    }
                    milliseconds += frame.milliseconds
                }
                guard !marks.isEmpty else {throw AssetError.invalid("Spring ANI event missing")}
                results["las_almenas-ani"] = ["events":marks,"duration_ms":milliseconds,"native_frames":w(sequence+16)]
            }
            for name in customSounds.keys.sorted() {
                let sound = customSounds[name]!.replacement
                guard let pcm = audio.sceneSoundPCM(sound),!pcm.isEmpty else {throw AssetError.invalid("No PCM: \(name)")}
                sounds.append(["name":name,"bytes":pcm.count,"pcm_sha256":SHA256.hash(data:Data(pcm)).map{String(format:"%02x",$0)}.joined()])
            }
            let probes = label == "arcana_v13" ? customSounds.keys.sorted().filter {$0.hasPrefix("CUSTOM_AMBIENT_SPACETAP")} : Array(customSounds.keys.sorted().prefix(1))
            if label == "arcana_v13",probes.count != 3 {throw AssetError.invalid("Arcana ADPCM sound inventory")}
            for name in probes {
                let stem = label == "arcana_v13" ? label+"-"+name:label
                audio.stopAll()
                let sound = customSounds[name]!.replacement
                guard playCustomSound(name,volume:80,pan:-25,pitch:125,loop:true) != 0 else {throw AssetError.invalid("Sound play: \(name)")}
                var left = [Float](repeating:0,count:88200),right = left
                left.withUnsafeMutableBufferPointer { l in right.withUnsafeMutableBufferPointer { r in
                    audio.render(left:l.baseAddress!,right:r.baseAddress!,frames:l.count,sampleRate:44100)
                }}
                let nonzero = zip(left,right).filter{$0 != 0 || $1 != 0}.count
                guard nonzero > 0,stopCustomSound(name),audio.poolInputEvidence(w(sound+16))["voices"] != nil else {throw AssetError.invalid("Offline sound/stop: \(name)")}
                var interleaved:[Float] = [];interleaved.reserveCapacity(left.count*2)
                for i in left.indices {interleaved.append(left[i]);interleaved.append(right[i])}
                try interleaved.withUnsafeBytes {try Data($0).write(to:directory.appendingPathComponent(stem+"-sound.f32"))}
                results[stem+"-sound"] = ["name":name,"nonzero_frames":nonzero,"frames":left.count,"sample_rate":44100,"format":"stereo float32 little endian","events":audio.lifetimeEvidence]
            }
            for name in customMusic.keys.sorted() {
                guard setCustomMusic(name) != 0,let entry = customMusic[name] else {throw AssetError.invalid("Music select: \(name)")}
                let path = "MUSIC/"+(name == "PLAY" ? "LEVEL":name)+".XMI"
                guard let data = try package.data(path),let song = ClawXMIDISong(data) else {throw AssetError.invalid("Missing song")}
                let stem = label+"-"+name
                try ClawMusicSynth.renderOffline(song:song,seconds:4,wav:directory.appendingPathComponent(stem+".wav"),log:directory.appendingPathComponent(stem+".json"),extra:["name":name,"sha256":SHA256.hash(data:data).map{String(format:"%02x",$0)}.joined()])
                guard resources.invoke(0x4b5bd0,entry.replacement) != 0,stopCustomMusic(name) != 0,
                      resources.invoke(0x4b5bd0,entry.replacement) == 0 else {throw AssetError.invalid("Music playback state")}
                tracks.append(["name":name,"ticks":song.ticks,"messages":song.messages.count,"selected_stopped":true,"render":stem+".json"])
            }
            let savedSounds = customSounds,savedMusic = customMusic
            unmapCustomAssets()
            guard savedSounds.allSatisfy({audioRegistry(w(base.sceneToken+40)+16,$0.key) == $0.value.original}),
                  savedMusic.allSatisfy({audioRegistry(musicManager,$0.key) == $0.value.original}),resources.fault == 0 else {throw AssetError.invalid("Audio restoration at \(String(resources.faultAddress,radix:16)), native \(String(base.boundary,radix:16))")}
            results[label] = ["sounds":sounds,"tracks":tracks,"restored":true]
            resources.unmountPackage();customAssets = nil;customAssetsMapped = false;customWorld = nil
        }
        try JSONSerialization.data(withJSONObject:["status":"pass","samples":results,"music_events":musicEvidence],options:[.prettyPrinted,.sortedKeys]).write(to:output,options:.atomic)
    }

    private func customFileService(_ f:UInt32,_ r:UInt32,_ a:[UInt32])->UInt32? {
        if f == 0x4f2360, a.count == 1 {
            // Original menu probes Custom then restores '..'. Never chdir the
            // process shared with other windows or expose arbitrary paths.
            let path = string(a[0])
            if path.lowercased() == "custom" || path == ".." {return 0}
        }
        if f == 0x4f7448,a.count == 3,!customVirtualPath.isEmpty,string(a[0]) == customVirtualPath {
            guard a[1] == 0,customWorld != nil else {return 0}
            customFileOffsets[r] = 0;put(r+4,r);put(r+8,1);return 1
        }
        guard let offset = customFileOffsets[r],let customWorld else {return nil}
        switch f {
        case 0x4f774d: return UInt32(customWorld.data.count)
        case 0x4f7570:
            // The title-only probe precedes retail image registration. The
            // subsequent payload read is the actual world load: install the
            // package overlay here, before planes resolve the registered sets.
            if a.count == 2,offset+Int(a[1]) > 1524,!customAssetsMapped {
                mapCustomAssets()
                guard resources.fault == 0 else {return 0}
                customLevelEvidence["asset_overlay_read_offset"] = offset
                customLevelEvidence["asset_overlay_read_bytes"] = a[1]
            }
            guard a.count == 2,let out = heap.lookupBytes(a[0],count:a[1]) else {return nil}
            let count = min(Int(a[1]),customWorld.data.count-offset)
            customWorld.data.withUnsafeBytes {raw in
                if count > 0 {UnsafeMutableRawPointer(out).copyMemory(from:raw.baseAddress!.advanced(by:offset),byteCount:count)}
            }
            customFileOffsets[r] = offset+count
            customLevelEvidence["reads"] = (customLevelEvidence["reads"] as? Int ?? 0)+1
            return UInt32(count)
        case 0x4f7369,0x4f766e:
            customFileOffsets.removeValue(forKey:r);put(r+4,.max);put(r+8,0);return 0
        default:return nil
        }
    }
    struct PlayerChoice:Identifiable {
        let id:UInt32
        let name:String
        let location:String
        let email:String
    }
    var selectedPlayer:UInt32 {w(base.applicationToken+0x64)}
    private var pendingCustomCheckpoint: ClawCustomCheckpoint?
    var checkpointFramePhase: (() -> UInt32?)?
    var restoreCheckpointFramePhase: ((UInt32) -> Void)?
    var playerChoices:[PlayerChoice] {
        var choices:[PlayerChoice] = [],node = w(profileManagerToken+4)
        while node != 0 {
            let record = w(node+8)
            choices.append(PlayerChoice(id:record,name:string(record+20),location:string(record+54),email:string(record+136)))
            node = w(node)
        }
        return choices
    }
    private func savePlayers() throws {
        // Normal USERNEW/USERREMOVECONFIRM request persistence but ignore its
        // return value (v1.3 49ff20/4882c0). A failed write does not undo actions.
        if saveFiles != nil {_ = resources.invoke(0x49bbc0,profileManagerToken)}
        guard resources.fault == 0 else {throw ClawNativeMenuResources.Failure.invalid("Player operation at \(String(resources.faultAddress,radix:16))")}
    }
    func finishPlayerDialog(cancelled:Bool) {

        // Shared normal-dialog result, using this host's v1.0 layout.
        let result = claw_v13_profile_close_result(cancelled ? 1:0)
        precondition(result != 0, "v1.3 profile close transport")
        put(0x52545c,result)
    }
    func selectPlayer(_ record:UInt32) throws {

        guard playerChoices.contains(where:{$0.id == record}) else {return}
        _ = resources.invoke(0x42bf90,base.applicationToken,[record])
        guard resources.fault == 0 else {throw ClawNativeMenuResources.Failure.invalid("Could not select player.")}
    }
    // USERNEW reads buffers of 16/64/64 bytes, including the terminator.
    static let playerTextLimits = [15,63,63]
    func createPlayer(name:String,location:String,email:String) throws -> UInt32 {
        let values = [name,location,email]
        guard !name.isEmpty else {throw ClawNativeMenuResources.Failure.invalid("Please enter your name.")}
        guard !location.isEmpty else {throw ClawNativeMenuResources.Failure.invalid("Please enter your location.")}
        guard zip(values,Self.playerTextLimits).allSatisfy({value,limit in
            !value.contains("\0") && value.utf8.count <= limit && value.unicodeScalars.allSatisfy{$0.value < 128}
        }) else {throw ClawNativeMenuResources.Failure.invalid("Use a name of up to 15 ASCII characters and location/comment of up to 63 ASCII characters.")}

        let tokens = values.map{resources.textToken($0)}
        defer {for token in tokens {resources.release(token)}}
        let record = resources.invoke(0x49bdb0,profileManagerToken,tokens+[0])
        if record != 0 {_ = resources.invoke(0x42bf90,base.applicationToken,[record])}
        try savePlayers()
        return selectedPlayer
    }
    func removePlayer(_ record:UInt32) throws {

        guard let choice = playerChoices.first(where:{$0.id == record}),choice.name.lowercased() != "player" else {return}
        // Same order as original 485160: switch away before destroying a selected record.
        if selectedPlayer == record {
            let fallback = resources.invoke(0x49bee0,profileManagerToken,[0x5255e8])
            _ = resources.invoke(0x42bf90,base.applicationToken,[fallback])
        }
        _ = resources.invoke(0x49bf30,profileManagerToken,[record])
        try savePlayers()
        // Original repairs a missing selection only AFTER requesting the save.
        // A newly created fallback is not persisted by a second save here.
        if selectedPlayer == 0 {
            let fallback = resources.invoke(0x49bee0,profileManagerToken,[0x5255e8])
            _ = resources.invoke(0x42bf90,base.applicationToken,[fallback])
            if selectedPlayer == 0 {
                let created = resources.invoke(0x49bdb0,profileManagerToken,[0x5255e8,0x534938,0x534938,0])
                _ = resources.invoke(0x42bf90,base.applicationToken,[created])
            }
        }
    }
    struct ControlAction {
        let name:String
        let slot:UInt32
        let key:UInt32
        let button:UInt32
    }
    // CONFIGCONTROLS IDs 413,415,417,419,41d,41f,421,423,425.
    // Slot 8 is unused; arrows are fixed by the original dialog.
    static let controlActions:[ControlAction] = [
        .init(name:"Jump",slot:4,key:0x20,button:1),
        .init(name:"Hand Attack",slot:5,key:0x11,button:2),
        .init(name:"Projectile Attack",slot:6,key:0x12,button:4),
        .init(name:"Projectile Toggle",slot:7,key:0x10,button:0x38),
        .init(name:"Throw",slot:9,key:0x5a,button:0),
        .init(name:"Pistol Attack",slot:10,key:0x31,button:0),
        .init(name:"Magic Attack",slot:11,key:0x32,button:0x40),
        .init(name:"Dynamite Attack",slot:12,key:0x33,button:0x80),
        .init(name:"Special Attack",slot:13,key:0x34,button:0)]
    var controlKeys:[UInt32] {Self.controlActions.map{w(inputController+0x38+$0.slot*4)}}
    var controlButtons:[UInt32] {Self.controlActions.map{w(inputController+($0.slot*4))}}
    private var controllerProfile:UInt32 = 0
    private func installControllerDefaults() {
        let player = w(base.applicationToken+0x64)
        guard player != 0, player != controllerProfile else {return}
        controllerProfile = player
        // Migrate only untouched original defaults. Saved custom mappings stay
        // owned by CLAW.USR and the original binding loader.
        if controlButtons == [1,2,4,8,16,32,64,128,0] {
            for action in Self.controlActions {
                put(player+0x2608+action.slot*4,action.button)
            }
            _ = resources.invoke(0x430ac0,inputController,[player])
        }
    }
    var joystickDisabled:Bool {w(0x53723c) != 0}
    private func initializeInputSource(_ source:UInt32) {
        _ = resources.invoke(0x4b3240,source,[joystickDisabled ? 1:3,0])
        // The application applies these after source initialization (4263fa),
        // including its Skip Joystick Menu Button setting, before bindings.
        for (index,key): (Int,UInt32) in [UInt32(0x20),0x11,0x12,0x10].enumerated() {
            put(source+0x1ec+UInt32(index*4),key)
        }
        put(source+0x1d8,1) // Native Menu/Start sends Escape, never synthetic Space.
    }
    var controllerEvidence:[String:Any] {
        let source = w(inputController)
        return ["connected":base.windowInput?.joystick != nil,"mode":w(source+0x1cc),
                "available":w(source+0x1d0),"raw":w(source+0x214),"edges":w(source+0x210),
                "binding_edges":w(inputController+4),"binding_current":w(inputController+8),
                "disabled":joystickDisabled]
    }
    func applyControls(keys:[UInt32],buttons:[UInt32],disableJoystick:Bool) throws {
        let player = w(base.applicationToken+0x64)
        guard keys.count == 9,buttons.count == 9,player != 0,inputController != 0 else {
            throw ClawNativeMenuResources.Failure.invalid("Controls require a selected player")
        }

        // Native dialog writes the same profile fields as original 430b70.
        // The recovered 430ac0 republishes them to the unchanged game poller.
        for (index,action) in Self.controlActions.enumerated() {
            put(player+0x25c4+action.slot*4,keys[index])
            put(player+0x2608+action.slot*4,buttons[index])
        }
        _ = resources.invoke(0x430ac0,inputController,[player])
        put(0x53723c,disableJoystick ? 1:0)
        _ = resources.invoke(0x4b3430,w(inputController),[disableJoystick ? 0:2])
        _ = resources.invoke(0x431300,inputController)
        if saveFiles != nil {
            guard resources.invoke(0x49bbc0,profileManagerToken) != 0 else {
                throw ClawNativeMenuResources.Failure.invalid("Could not save Controls to CLAW.USR")
            }
        }
        if configuration != 0 {_ = resources.invoke(0x4b5e50,configuration,[0x52582c,disableJoystick ? 1:0])}
        guard resources.fault == 0,settings?.writeFailure == nil else {
            throw ClawNativeMenuResources.Failure.invalid("Controls save failed at \(String(resources.faultAddress,radix:16))")
        }
    }
    var musicEvidence:[[String:Any]] {music?.events ?? []}
    private var startupManagers:[(offset:UInt32,token:UInt32,destructor:UInt32)] = []
    private var empty:UInt32 = 0
    private(set) var calls:[UInt32] = []
    private(set) var imageCount:UInt32 = 0
    private(set) var loaded = false
    private var closed = false
    private(set) var cleanupFault:UInt32 = 0
    private(set) var destroyedWorld = Data()
    /// Window events only; callbacks must not re-enter recovered frames.
    var yieldWindowEvents:(()->Void)?
    let clock:()->UInt32
    var observeClockRead:((UInt32,UInt32)->Void)?
    private let captureEvidence:Bool
    var heap:ClawTokenHeap {base.heap}
    init(base:ClawNativeMenuBase,archiveURL:URL,metadata:[UInt32:Data],captureEvidence:Bool = false,
         diagnostics:ClawNativeDiagnostics = .shared,
         clock:@escaping ()->UInt32 = {UInt32(truncatingIfNeeded:UInt64(ProcessInfo.processInfo.systemUptime*1000))}) throws {
        self.base = base
        self.diagnostics = diagnostics
        movieServices = ClawNativeMovieStateServices(heap:base.heap)
        self.clock = clock
        self.captureEvidence = captureEvidence
        var staticMetadata = metadata
        if let delay = staticMetadata.removeValue(forKey:0x528a60),delay.count == 4 {
            startupDelay = delay.withUnsafeBytes{$0.loadUnaligned(as:UInt32.self)}
        }
        if let volume = staticMetadata[0x541178],let audio = base.audio {
            guard audio.acceptsInitialVolumeMetadata(volume,in:base.heap) else {
                throw ClawNativeMenuResources.Failure.invalid("Audio volume metadata ownership")
            }
            staticMetadata.removeValue(forKey:0x541178)
        }
        resources = try ClawNativeMenuResources(heap:base.heap,archiveURL:archiveURL,metadata:staticMetadata)
        try ClawCustomLua.installPhysicsOperands(base.heap)
        let constructorString = base.heap.lookup(base.menuToken+0x154+72+20,words:1)!.pointee
        guard constructorString >= 12,base.constructorAllocations.contains(where:{$0.token == constructorString-12}) else {
            throw ClawNativeMenuResources.Failure.invalid("Interface constructor string ownership")
        }
        try base.transferInterfaceConstructorAllocations(to:resources)
        try base.transferStateAllocation(to:resources)
        strings.insert(constructorString-12)
        resources.completedInvocation = {[unowned self] function,result in
            // Reading the custom header can precede retail registration.
            // Reapply package images/animations after that registrar replaces
            // its groups, before the world binds tile and object image sets.
            if self.customWorld != nil,[UInt32(0x4cff40),0x4ce0d0].contains(function) {
                self.mapCustomAssets(refresh:true)
            }
            if function == 0x42aa50 || function == 0x46a6d0,let flags = self.heap.lookup(0x58010000,words:4) {
                flags.update(repeating:0,count:4)
            }
            // Display records outlive the menu resource owner. Keep canonical
            // resize allocations on the existing display destruction ledger.
            if result != 0,[UInt32(0x4bc890),0x4bcf80,0x4bc670].contains(function),
               self.resources.allocationData(result) != nil {
                guard let display = self.base.palette?.display,self.resources.transferAllocation(result,to:display) else {_ = self.resources.fail(function);return}
            }
        }
        resources.gameEntry = claw_native_menu_interface_entry
        resources.checkpointLogicEntries = {[weak self] in
            guard let self else {return [:]}
            return (self.maps[self.w(self.base.sceneToken+20)+16] ?? [:]).mapValues {self.w($0)}
        }
        resources.checkpointSequenceName = {[weak self] token in
            guard let self else {return nil}
            return self.maps[self.w(self.base.sceneToken+0x2c)+16]?.filter {self.w($0.value) == token}.map(\.key).sorted().first
        }
        resources.beforeMusicLookup = {[weak self] in self?.mapCustomMusic()}
        resources.levelLoaded = { [unowned self] state in
            self.mapCustomSounds()
            if self.customWorld != nil {
                do {try self.installCustomPalettes(state)} catch {
                    self.customLevelEvidence["palette_error"] = error.localizedDescription
                    _ = self.resources.fail(ClawCustomLua.callback);return
                }
            }
            guard self.resources.fault == 0 else {return}
            if self.customWorld != nil,!self.customAudioRetiring {self.customAudioReady = true}
            if self.customWorld != nil,ClawNativeMenuResources.countInvokes {
                let world = self.w(self.w(state+0xc)+0x24)
                self.customLevelEvidence["tile_frame_plane_count"] = self.w(world+0x3c)
                self.customLevelEvidence["unresolved_tile_frames"] = self.resources.missingTileFrames(world:world)
            }
            do {try self.customLua?.mapLoaded()} catch {
                self.customLevelEvidence["lua_map_error"] = error.localizedDescription
            }
            if let world = self.customWorld?.world {
                self.resources.capturePlacements(world:world,state:state)
            } else if let root = Bundle.main.resourceURL,
               let data = try? Data(contentsOf: root.appendingPathComponent("GameData/LEVEL\(self.w(state+0x14))/WORLDS/WORLD.WWD")),
               let world = try? ClawWorld(data: data) {
                self.resources.capturePlacements(world: world, state: state)
            }
            self.finishCustomCheckpointLoad(state: state)
            self.restoreCrazyCheckpoint(state:state)
        }
        resources.dependency = {[unowned self] q in self.service(q)}
        base.applicationErrors?.physicalAvailable = {[weak resources] in resources?.missingService != $0}
        base.applicationErrors?.observePostClose = {[weak self] in self?.record(["service":"PostMessageA","window":$0,"message":UInt32(0x10),"wparam":UInt32(0),"lparam":UInt32(0)])}
        if captureEvidence {
            resources.traceAllocations = true
            resources.observePhysical = {[weak self] in self?.record($0)}
            base.palette?.observePhysical = {[weak self] in self?.record($0)}
            base.palette?.display?.observePhysical = {[weak self] in self?.record($0)}
            base.audio?.observePhysical = {[weak self] in self?.record($0)}
            base.windowInput?.queue.observePhysical = {[weak self] in self?.record($0)}
        }
        resources.releaseExternalAllocation = {[unowned self] token in
            self.base.palette?.display?.releaseMenuImageAllocation(token) ?? false
        }
        resources.gameService = {[unowned self] f,r,a in
            self.calls.append(f)
            if f == 0x4c80c0,r == self.customLogicEntry,a.first.map({$0 & 1 != 0}) == true {
                self.customLogicEntry = 0
            }
            // Results/menu construction reuses the scene registries before
            // the old world's destructor. Retire package ownership before
            // any original bulk clear can delete the entries behind us.
            if f == 0x4ca300 && r == self.w(self.base.sceneToken+40) {
                if self.customAudioReady {self.customAudioRetiring = true}
                self.unmapCustomSounds()
            }
            if [UInt32(0x4b5340),0x4b5300].contains(f),r == self.musicManager {
                // Music selection also clears this registry during startup.
                // Bound WWD sound actors still own their sound descriptors.
                self.unmapCustomMusic()
            }
            if f == 0x428c40,self.customWorld != nil {
                self.customLevelEvidence["state_load_arguments"] = a
            }
            if f == 0x4231a0,self.customWorld != nil,a.count == 1 {
                // Keep the original scanner, RISE/WAVE animation and respawn
                // publication; replace only its retail persistence branch.
                let result = self.resources.invoke(0x422ff0,r,a)
                let callback = self.w(self.w(a[0]+0x6c)+0x10)
                if !self.crazyScriptOwned {
                    self.crazyPendingSlot = callback == 0x4232c0 ? 1:callback == 0x4232e0 ? 2:nil
                }
                self.customLevelEvidence["checkpoint_contact"] = callback == 0x4232c0 ? 1:2
                return result
            }
            if let value = self.customMaskService(f,r,a) {return value}
            if let value = self.customLua?.service(f,r,a) {return value}
            // Menu return can destroy the registry without going through the
            // retail level-end callback. Retire the custom session first.
            if (f == 0x45b3f0 || (f == 0x42abb0 && r == self.base.applicationToken)),self.customAssets != nil {
                self.retireCustomSession()
            }
            if f == 0x48f3e0,!self.customLoadingScreen,self.customAssets != nil,
               a.count == 5,self.string(a[0]).uppercased().contains("LOADING"),
               self.resources.packageDirectory("SCREENS") != 0 {
                let old = self.w(r+0x20)
                self.put(r+0x20,self.resources.invoke(0x4b7540,self.resources.packageArchive))
                self.customLoadingScreen = true
                let value = self.resources.invoke(f,r,a)
                self.customLoadingScreen = false;self.put(r+0x20,old)
                self.customLevelEvidence["loading_screen"] = value != 0
                return value
            }
            if claw_native_v13_enabled() != 0,f == 0x426e30,a.count == 3,(0x80ad...0x80b6).contains(a[1] & 0xffff) {
                return self.v13Cheat(a[1] & 0xffff,application:r)
            }
            if claw_native_v13_enabled() != 0,f == 0x426e30,a.count == 3,let result = self.v13ApplicationCommand(a[1],application:r) {return result}
            if let result = self.titleService(f,r,a) {return result}
            if f == 0x4bd260 || f == 0x4b4ed0 {
                do {
                    try self.resources.installMetadata(self.diagnostics.sharedMetadata())
                    for (address,display):(UInt32,Bool) in [(0x54130c,false),(0x54139c,true)] {
                        for (index,value) in self.diagnostics.flagWords(display:display).enumerated() {
                            let token = address+UInt32(index*4)
                            let pointer = self.heap.lookup(token,words:1) ?? self.heap.store(token:token,words:1)
                            pointer.pointee = value
                        }
                    }
                } catch {return self.resources.fail(f)}
            }
            if f == 0x4bc110,let frame = self.resources.diagnosticFrame {
                var q = ClawCall();q.function = f;q.receiver = r;q.argumentCount = UInt32(a.count)
                withUnsafeMutableBytes(of:&q.arguments){dst in a.withUnsafeBytes{dst.copyBytes(from:$0)}}
                return self.diagnosticService(q,frame:frame)
            }
            if f == 0x4b45f0 {
                guard a.count == 4,let audio = self.base.audio else {return self.resources.fail(f)}
                let result = audio.playVoicePool(r,request:ClawAudioRequest(volume:a[0],pan:a[1],pitchPercent:a[2],looping:a[3]))
                return audio.lifecycleFault == 0 ? result:self.resources.fail(f)
            }
            if [UInt32(0x4b9730),0x4c96d0,0x4bffa0,0x4c0450,0x4c0920,0x4c0cc0,0x4c1190,0x4c25b0,0x4c3800,0x4c4c20].contains(f) {
                var q = ClawCall();q.function = f;q.receiver = r;q.argumentCount = UInt32(a.count)
                q.stackPointer = self.resources.currentFrame
                withUnsafeMutableBytes(of:&q.arguments){dst in a.withUnsafeBytes{dst.copyBytes(from:$0)}}
                return self.base.palette?.display?.rawActorService(ClawNativeMenuRawDisplayHost(self.resources),q)
                    ?? self.resources.fail(f)
            }
            // Native application timing replaces the platform base helpers.
            // Game timing and all animation decisions still run in their owners.
            if f == 0x4b83d0 || f == 0x4b83a0 {
                guard r == self.base.applicationToken,a.count == (f == 0x4b83d0 ? 0:1) else {return self.resources.fail(f)}
                let now = self.transport(0x546df0,0,[])
                if f == 0x4b83d0 {
                    self.put(0x541328,now);self.put(0x54132c,0);self.put(0x541330,0)
                } else {
                    self.put(r+0x20,0);self.put(r+0x24,now)
                    if a[0] != 0 {self.put(r+0x18,.max)}
                }
                return f == 0x4b83d0 ? 0:a[0]
            }
            if f == 0x4cdd30 {
                guard a.isEmpty else {return self.resources.fail(f)}
                // Existing recovered world teardown uses its typed legacy ABI.
                // Only its platform array storage is adapted here.
                var context = ClawWorldFileContext(),out:UInt32 = 0
                let arguments = ClawWorldFileArguments()
                context.scene = self.base.actorHost
                context.scene.free = {u,t in
                    guard let u else {return}
                    Unmanaged<ClawNativeMenuBase>.fromOpaque(u).takeUnretainedValue().sharedMenuResources?.release(t)
                }
                let done = claw_world_file_entry(f,r,arguments,&context,{c,q,u in
                    guard let c,let q,let u else {return 0}
                    let owner = Unmanaged<ClawNativeMenuInterface>.fromOpaque(u).takeUnretainedValue(),e = q.pointee
                    let args = withUnsafeBytes(of:e.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(e.argumentCount)))}
                    let result = e.function >= 0x4f0000 ? owner.transport(e.function,e.receiver,args):owner.resources.invoke(e.function,e.receiver,args)
                    if owner.resources.fault != 0 {c.pointee.fault = 1};return result
                },Unmanaged.passUnretained(self).toOpaque(),&out)
                if done == 1,context.fault == 0,let bytes = self.heap.lookupBytes(r,count:0xe0) {
                    self.destroyedWorld = Data(bytes:bytes,count:0xe0)
                    return out
                }
                return self.resources.fail(f)
            }
            if self.base.sharedMenuResources === self.resources,
               let result = self.base.sharedInitializerService(f,r,a) {
                if f == 0x4ca440,self.base.fault == 0 {self.mapCustomSounds()}
                return self.base.fault == 0 ? result:self.resources.fail(self.base.boundary)
            }
            if f == 0x4d2410 {
                guard let result = self.base.palette?.display?.loadMenuResourceImage(r,args:a) else {
                    return self.resources.fail(f)
                }
                return result
            }
            if f == 0x4bebc0,a.count == 3,let display = self.base.palette?.display,
               a[0] == self.base.palette?.backendManagerToken {
                let result = display.decodePCX(surface:r,data:a[1],byteCount:a[2])
                return display.lastPCXFault == 0 ? result:self.resources.fail(f)
            }
            if f == 0x4bc5f0,a.count == 1,let palette = self.base.palette,
               palette.display?.sourceAllocations.contains(r) == true {
                let result = palette.graphicsEntry(f,receiver:r,args:a)
                return palette.fault == 0 ? result:self.resources.fail(f)
            }
            if f == 0x4bc4f0,a.count == 1,r == self.base.palette?.backendManagerToken,
               self.base.palette?.display?.sourceAllocations.contains(a[0]) == true {
                self.base.palette?.display?.removeSurface(a[0])
                if self.base.palette?.display?.fault != 0 {return self.resources.fail(f)}
                return 0
            }
            return nil
        }
        // The base constructor and every native CString transport share the
        // original immortal empty buffer, including its negative refcount.
        empty = 0x52e1c4
    }
    deinit {close()}
    // State switches destroy and recreate menus. The native startup token is
    // only the first allocation, never an identity for a later menu instance.
    var menuToken:UInt32 {
        guard !closed else {return 0}
        let state = w(base.applicationToken+0x2c)
        return state != 0 && resources.owns(state) && w(state) == 0x50c1e4 ? state:0
    }
    var menuLive:Bool {menuToken != 0}
    func close() {
        guard !closed else {return}
        writeSettings()
        let liveToken = menuToken,live = liveToken != 0;closed = true
        if live,fullInitialization {_ = resources.invoke(0x429530,liveToken)}
        else if live,loaded {_ = resources.invoke(0x4dccb0,liveToken+0x154)}
        // These two process callbacks destroy native CPtrArray storage; the
        // recovered scene owner registered them when its first frame ran.
        for callback in exitCallbacks.reversed() where resources.fault == 0 {
            _ = transport(0x4f58de,callback == 0x4c91c0 ? 0x5430f0:0x5430d8,[])
        }
        exitCallbacks.removeAll()
        if manager != 0,resources.fault == 0 {_ = resources.invoke(0x4cf160,manager,[1])}
        put(base.sceneToken+16,0)
        for item in startupManagers.reversed() {
            if resources.fault == 0 {_ = resources.invoke(item.destructor,item.token,[1])}
            put(base.sceneToken+item.offset,0)
        }
        if musicManager != 0,resources.fault == 0 {
            _ = resources.invoke(0x4b5300,musicManager)
            _ = transport(0x4f61f3,musicManager,[])
            resources.release(musicManager);put(base.applicationToken+0x50,0)
        }
        music?.close()
        if inputController != 0,resources.fault == 0 {_ = transport(0x4f5d00,inputController+0x74,[])}
        if profileManagerToken != 0,resources.fault == 0 {_ = transport(0x4f5172,profileManagerToken,[])}
        for block in nativeStartupBlocks {resources.release(block)};nativeStartupBlocks.removeAll()
        for block in strings {resources.release(block)};strings.removeAll()
        cleanupFault = resources.fault
        base.palette?.display?.menuSwapChain = false
        resources.completedInvocation = nil
        resources.levelLoaded = nil
        resources.gameService = nil;resources.dependency = nil;resources.gameEntry = nil
        resources.releaseExternalAllocation = nil
        base.audio?.releaseSharedAllocation = nil
        base.applicationErrors?.physicalAvailable = nil;base.applicationErrors?.observePostClose = nil
        base.sharedMenuResources = nil
        // A surviving menu state returns to its native constructor owner.
        if live,liveToken == base.menuToken {_ = resources.relinquish(liveToken)}
        resources.close();loaded = false
    }
    func w(_ token:UInt32)->UInt32 {
        guard let p = heap.lookupBytes(token,count:4) else {_ = resources.fail(token);return 0}
        return UnsafeRawPointer(p).loadUnaligned(as:UInt32.self)
    }
    func put(_ token:UInt32,_ value:UInt32) {
        guard let p = heap.lookupBytes(token,count:4) else {_ = resources.fail(token);return}
        var v = value;withUnsafeBytes(of:&v){p.update(from:$0.baseAddress!.assumingMemoryBound(to:UInt8.self),count:4)}
    }
    // Native v1.3 composition. The dispatcher/presentation families compare
    // the game decisions; these calls reuse the live v1.0 physical owners.
    private func v13Cheat(_ command:UInt32,application app:UInt32)->UInt32 {
        let state = w(app+0x2c)
        guard state != 0,resources.invoke(w(w(state)+0x10),state) == 3 else {return 0}
        func acknowledge(_ text:String,major:Bool = false) {
            let audio = w(w(app+0x30)+0x28)
            if w(audio+0x30) == 0 {
                let sound = resources.invoke(0x4061b0,audio,[major ? 0x525bf4:0x525b68])
                if sound != 0 {_ = resources.invoke(0x4208e0,sound,[w(0x532c10),0,0,0])}
            }
            _ = resources.invoke(0x42af70,app,[cstring(text)])
        }
        switch command {
        case 0x80b2,0x80b5,0x80b6,0x80b3:
            let offset:UInt32 = command == 0x80b2 ? 0:command == 0x80b5 ? 4:command == 0x80b6 ? 8:12
            let name = command == 0x80b2 ? "Long Range Attack Mode":command == 0x80b5 ? "Easy Mode":command == 0x80b6 ? "Twin Sequential Turbo Mode":"Bounce Counter"
            put(0x58010000+offset,w(0x58010000+offset)^1)
            if command == 0x80b3 {put(0x58010010,0)}
            acknowledge(name+(w(0x58010000+offset) != 0 ? " is ON":" is OFF"),major:command != 0x80b3)
        case 0x80b4:
            let actor = w(0x537e88)
            if actor != 0 {put(actor+0x40,w(actor+0x40)^4);acknowledge("Wild, wacky stuff...")}
        case 0x80ad:
            acknowledge("Just like my old TV!")
            base.palette?.toggleGrayscale()
        case 0x80ae:
            let manager = w(w(app+0x30)+0x28),map = manager+0x10
            var sounds:[UInt32] = []
            if w(manager+0x30) == 0 {
                if let keys = mapKeys[map] {sounds = keys.compactMap{maps[map]?[$0]}.map{w($0)}}
                else {
                    // The sound loader uses the native MFC storage owner.
                    // GetNextAssoc walks increasing buckets and then each
                    // published association chain; values live at node +12.
                    let table = w(map+4),buckets = w(map+8)
                    if table != 0,buckets <= 65536 {
                        var seen:Set<UInt32> = []
                        for bucket in 0..<buckets {
                            var node = w(table+bucket*4)
                            while node != 0,seen.insert(node).inserted {
                                sounds.append(w(node+12));node = w(node)
                            }
                        }
                    }
                }
            }
            var cursor = w(0x5801001c)
            if cursor == 0 {
                let advances = Int(transport(0x4a3050,0,[]))%101
                if !sounds.isEmpty {cursor = sounds[advances%sounds.count]}
            } else if let index = sounds.firstIndex(of:cursor),index+1 < sounds.count {cursor = sounds[index+1]}
            else {cursor = 0}
            if cursor == 0 {put(0x5801001c,sounds.first ?? 0);return 1}
            put(0x5801001c,cursor)
            _ = resources.invoke(0x4208e0,cursor,[w(0x532c10),0,0,0])
        case 0x80af,0x80b0,0x80b1:
            let manager = w(app+0x50)
            guard w(app+0x14) != 0,manager != 0 else {return 1}
            let sequence = w(manager+0x1c)
            guard sequence != 0,w(sequence+0x58) != 0 else {return 1}
            let speed:UInt32 = command == 0x80af ? 150:command == 0x80b0 ? 75:100
            let transition:UInt32 = command == 0x80b1 ? 1000:2500
            guard music?.acceptsTempo(w(sequence+0x58)) == true else {return 1}
            acknowledge(command == 0x80af ? "Time to speed things up!":command == 0x80b0 ? "Ready to slow things down?":"Back to normal...")
            _ = music?.requestTempo(w(sequence+0x58),speed:speed,milliseconds:transition)
            put(sequence+0x54,speed)
        default:return 0
        }
        return 1
    }
    private func v13ApplicationCommand(_ command:UInt32,application app:UInt32)->UInt32? {
        if command == 0x80ac {
            // Neither factory constructs state 15. Retain teardown, shutdown's
            // generic-state route and the v1.3 error resource; expose no screen.
            if resources.invoke(0x428c40,app,[15,1,0,0]) == 0 {
                _ = resources.invoke(0x429e10,app,[0x8005,0x44a])
            }
            return 1
        }
        guard command == 0x8006 || command == 0x800f,w(app+0x9c) != 0 else {return nil}
        let state = w(app+0x2c)
        let id = state == 0 ? 0:resources.invoke(w(w(state)+0x10),state)
        if command == 0x800f && (id == 3 || id == 4) {return nil}
        let counter = w(0x58010020)
        if counter != 0 {put(0x58010020,counter-1);return nil}
        // 0x4498f0 only computes a discarded private statistics buffer. There
        // is no persisted statistics result or additional native service.
        // The retained exit-message owner has the same 4000-ms clock/wrap
        // contract, using the native app's retained vtable slots.
        if state != 0,id == 3 {_ = resources.invoke(0x46bcf0,state)}
        _ = resources.invoke(0x42abb0,app)
        return 1
    }
    var v13CheatEvidence:[String:Any] {
        var result:[String:Any] = [:]
        for (i,name) in ["long_range","easy","turbo","bounce","bounce_total","bounce_current","bounce_max","noise_cursor","quit_counter"].enumerated() {
            result[name] = heap.lookup(0x58010000+UInt32(i*4),words:1)?.pointee ?? 0
        }
        let actor = heap.lookup(0x537e88,words:1)?.pointee ?? 0
        result["velocity_x"] = actor == 0 ? 0:Int(Int32(bitPattern:w(actor+0x148)))
        result["attack_bounds"] = actor == 0 ? []:(0..<4).map{Int(Int32(bitPattern:w(actor+0x138+UInt32($0*4))))}
        result["music_services"] = musicEvidence.suffix(12).map{$0}
        result["palette_gray"] = base.palette?.isGrayscale ?? false
        return result
    }
    private func cstring(_ value:String)->UInt32 {
        let bytes = Array(value.utf8)+[0],block = resources.allocate(UInt32(bytes.count)+12)
        strings.insert(block);put(block,1);put(block+4,UInt32(bytes.count-1));put(block+8,UInt32(bytes.count-1))
        if let p = heap.lookupBytes(block+12,count:UInt32(bytes.count)) {bytes.withUnsafeBufferPointer{p.update(from:$0.baseAddress!,count:$0.count)}}
        return block+12
    }
    private func string(_ t:UInt32,maximumBytes:UInt32 = 4096)->String {
        guard let value = resources.text(t,maximumBytes:maximumBytes) else {_ = resources.fail(t);return ""}
        return value
    }
    private func arraySize(_ t:UInt32,_ count:UInt32,_ growth:UInt32 = .max)->UInt32 {
        guard count <= 4096 else {return resources.fail(t)}
        let old = w(t+4),n = w(t+8),data = count == 0 ? 0:resources.allocate(count*4)
        if old != 0,data != 0,let from = heap.lookupBytes(old,count:min(n,count)*4),let to = heap.lookupBytes(data,count:count*4) {
            to.update(from:from,count:Int(min(n,count)*4))
        }
        if old != 0 {resources.release(old)}
        put(t+4,data);put(t+8,count);put(t+12,count)
        if growth != .max {put(t+16,growth)}
        return 0
    }
    private func constructImageManager() {
        // Native startup supplies the inline image-manager storage from 4cea10.
        // The admitted recursive registrar then owns every image/group decision.
        manager = resources.allocate(44)
        put(manager,0x513b88);put(manager+12,base.sceneToken)
        put(manager+16,0x5105c4);put(manager+24,17);put(manager+40,10)
        maps[manager+16] = [:];mapKeys[manager+16] = []
        put(base.sceneToken+16,manager)
        _ = resources.invoke(0x4cdf20,manager)
        // 4cea10 also initializes the image-effects manager (0x4cfa60): the
        // game's DDBLTFX at 0x543108, dwSize 100, whose dwDDFX (0x54310c) the
        // mirrored sprite blits set. Without it every mirrored Blt is refused.
        _ = resources.invoke(0x4cfa60,0)
    }
    func initialize() throws {

        guard !closed,!loaded,resources.archive == 0 else {throw ClawNativeMenuResources.Failure.invalid("Menu initialization lifetime")}
        guard let startupDelay else {throw ClawNativeMenuResources.Failure.invalid("Missing original menu timing metadata")}
        if heap.lookupBytes(0x5370c8,count:16) == nil {
            guard !heap.overlaps(0x5370c8,count:16) else {throw ClawNativeMenuResources.Failure.invalid("Viewport globals overlap")}
            heap.storeBytes(token:0x5370c8,count:16)
        }
        put(0x528a60,startupDelay)
        // The original static initializer table (0x522004..0x522244): every
        // game entry in table order, as the Level 1 join runs them; C runtime
        // and MFC entries stay native. 0x4251e0 is the application object's
        // own initializer, replaced by native startup. The table and the data
        // the initializers touch are original image spans elected by the join.
        if let data = levelOneData {try resources.installMetadata(data,onlyUnmapped:true);levelOneData = nil}
        guard w(0x522000) == 0,w(0x522244) == 0 else {
            throw ClawNativeMenuResources.Failure.invalid("Static initializer table sentinel")
        }
        for slot in stride(from:UInt32(0x522004),to:0x522244,by:4) {
            let entry = w(slot)
            guard entry != 0x4251e0,claw_level_game_range(entry) == 1 else {continue}
            _ = resources.invoke(entry,0)
            guard resources.fault == 0 else {
                throw ClawNativeMenuResources.Failure.invalid("Static initializer \(String(entry,radix:16)) at \(String(resources.faultAddress,radix:16))")
            }
        }
        try readStartupSettings()
        // Native window attachment supplies the base timing effects of 4b8280.
        put(base.applicationToken+0x1c,0)
        _ = resources.invoke(0x4b83a0,base.applicationToken,[1])
        _ = resources.invoke(0x4b83d0,base.applicationToken)
        put(0x541334,100);put(0x541338,100)
        // Share the audio owner's initialized lookup table with canonical fades.
        // The executable's data image contains the pre-startup zero table.
        for index:UInt32 in 0...100 {put(0x541178+index*4,UInt32(bitPattern:claw_audio_volume_table(index)))}
        try resources.open()
        base.sharedMenuResources = resources
        base.audio?.releaseSharedAllocation = {[weak resources] token in resources?.releaseIfOwned(token) ?? false}
        put(base.applicationToken+0x34,resources.archive)
        loadGameInterfaces()
        put(0x5371fc,base.applicationToken)
        constructImageManager()
        let world = resources.allocate(0xe0)
        _ = resources.invoke(0x4cace0,world,[base.sceneToken,0,0])
        put(base.sceneToken+0x24,world)
        // Native startup replaces 0x42ce90's display-mode setup. Its stores at
        // 0x42cfb4/0x42cfb7 reduce the constructor's 64-pixel collision steps
        // to 14 before gameplay; leaving 64 lets fast falls skip thin floors.
        put(world+0x64,14);put(world+0x68,14)
        startupManagers.append((0x24,world,0x4cdd10))
        if let display = base.palette?.display {
            _ = resources.invoke(0x4cb040,world,[w(display.primaryToken+16),w(display.primaryToken+20)])
        }
        let animations = resources.allocate(44)
        put(animations,0x513ad8);put(animations+12,base.sceneToken)
        _ = serviceMapConstructor(animations+16,10)
        put(base.sceneToken+44,animations)
        startupManagers.append((44,animations,0x4cf9d0))
        for (offset,table,destructor,list):(UInt32,UInt32,UInt32,Bool) in [
            (8,0x513c20,0x4cf8a0,true),(12,0x513be8,0x4cf280,true),(20,0x513b60,0x4cf940,false)] {
            let token = resources.allocate(44)
            _ = resources.invoke(0x45fde0,token,[base.sceneToken,0,0])
            _ = transport(list ? 0x4f5620:0x4f6118,token+16,[10])
            put(token,table);put(base.sceneToken+offset,token)
            startupManagers.append((offset,token,destructor))
        }
        // The complete unchanged game registration (0x401000), as native
        // startup and the Level 1 join run it: the menu's five logics plus
        // every class Level 1 creates ("CaptainClaw" and the rest).
        // Its per-class setup reads original data globals beyond the menu's
        // spans: the image spans the Level 1 join elects, installed unmapped-only.
        if let data = levelOneData {try resources.installMetadata(data,onlyUnmapped:true);levelOneData = nil}
        _ = resources.invoke(0x401000,0,[base.sceneToken])
        guard resources.fault == 0 else {
            throw ClawNativeMenuResources.Failure.invalid("Game logic registration at \(String(resources.faultAddress,radix:16))")
        }
        maps[base.menuToken+0x2ac] = [:];mapKeys[base.menuToken+0x2ac] = []
        if let palette = base.palette {
            for offset:UInt32 in [16,44,72] {maps[palette.managerToken+offset] = [:];mapKeys[palette.managerToken+offset] = []}
        }
        // Native startup storage corresponding to the inline constructors in
        // application startup. Recovered owners establish bindings and profiles.
        let input = resources.allocate(0x248),controller = resources.allocate(0x90)
        inputController = controller;nativeStartupBlocks += [input,controller]
        put(input,.max);_ = resources.invoke(0x4b3410,input)
        base.windowInput?.sampleJoystick()
        initializeInputSource(input)
        _ = transport(0x4f5cbd,controller+0x74,[10])
        put(0x537200,input);put(0x537204,controller)
        _ = resources.invoke(0x430590,controller,[input,0])
        let profileManager = resources.allocate(0x58)
        profileManagerToken = profileManager;nativeStartupBlocks.append(profileManager)
        _ = transport(0x4f5620,profileManager,[10]);put(profileManager+0x1c,empty)
        put(profileManager+0x44,0x4d505255);put(base.applicationToken+0x60,profileManager)
        // The original startup (0x425730) runs the saved-game manager's own
        // startup 0x49b840: path <current directory>\CLAW.USR, load the saved
        // games (0x49b9a0), select or create "Player". Its files are native
        // (ClawNativeSaveFiles); a launch without a folder keeps no saves.
        if let saveDirectory {
            saveFiles = ClawNativeSaveFiles(directory:saveDirectory)
            guard resources.invoke(0x49b840,profileManager,[0x525618]) == 1,resources.fault == 0 else { // 0x525618: "CLAW.USR"
                throw ClawNativeMenuResources.Failure.invalid("Saved-game startup at \(String(resources.faultAddress,radix:16))")
            }
            record(["service":"saved games","directory":saveDirectory.path,"reads":saveFiles!.reads])
        } else {
            _ = resources.invoke(0x49bdb0,profileManager,[0x5255e8,0x534938,0x534938,0])
        }
        if selectStoredPlayer(profileManager) == 0 {
            let selected = resources.invoke(0x49bee0,profileManager,[0x5255e8])
            if selected != 0 {nativeStartupBlocks.append(selected)}
            _ = resources.invoke(0x42bf90,base.applicationToken,[selected])
        }
        installControllerDefaults()
        music = ClawNativeMenuMusic(resources:resources)
        music?.now = {[unowned self] in self.lastClock}
        music?.observePhysical = {[weak self] in self?.record($0)}
        music?.output = base.audio
        musicManager = resources.allocate(44)
        _ = transport(0x4f6118,musicManager,[10])
        _ = resources.invoke(0x4b52a0,musicManager,[1,1,0])
        put(base.applicationToken+0x50,musicManager)
        // Original startup applies the stored volumes right after creating
        // their owners. Fresh install: Music Volume 50 through 0x4b55e0 at
        // 0x42625c (master volume 63 of 127), unless 0x537234 disabled music,
        // in which case startup clears the manager's enabled field instead.
        if w(0x537234) != 0 {put(musicManager+0x28,0)} else {_ = resources.invoke(0x4b55e0,musicManager,[startupSettings[0x5256c0] ?? 50])}
        // Sound Volume 80 through 0x42cdc0 at 0x426340: application +0x12c
        // and the animation-sound volume 0x532c10. The sound-events object is
        // created later by native startup, already with volume 80 (0x402240).
        _ = resources.invoke(0x42cdc0,base.applicationToken,[startupSettings[0x5256b0] ?? 80])
        applyStartupOptions()
        guard resources.fault == 0 else {
            throw ClawNativeMenuResources.Failure.invalid("Startup volumes at \(String(resources.faultAddress,radix:16))")
        }
        try installPaperServices()
        if w(base.applicationToken+0x44) != 0 {try installApplicationServices()}
        let arguments = ProcessInfo.processInfo.arguments
        if arguments.contains("--movie-flow-check") && arguments.contains("--movie-unlock-check") {
            // Isolated real-input check fixture: seed completion records before
            // the original builds/enables the Replay Movies controls.
            let player = w(base.applicationToken+0x64)
            for level:UInt32 in [2,4,6,8,10,12,13,14] {
                let entry = resources.invoke(0x49ae60,player,[level,3])
                guard player != 0,entry != 0,heap.lookup(entry,words:1) != nil else {
                    throw ClawNativeMenuResources.Failure.invalid("Movie completion check fixture")
                }
                put(entry,w(entry)|1)
            }
        }
        recordingInitialization = captureEvidence
        let result = resources.invoke(0x45ace0,base.menuToken,[base.applicationToken,1,0])
        recordingInitialization = false
        guard result == 1,resources.fault == 0,base.fault == 0 else {
            throw ClawNativeMenuResources.Failure.invalid("Full menu initialization at \(String(resources.faultAddress,radix:16))")
        }
        loaded = true
        fullInitialization = true
    }
    /// Original startup's settings (0x4257f9..0x425ae1): its configuration
    /// object (application +0x38) opened by 0x4b5c50 on HKEY_LOCAL_MACHINE,
    /// then every value read through 0x4b5f30/0x4b5e90 in the original order,
    /// with the original default, into the original destination. A fresh
    /// store answers every read with its default: Status Layout +0x68 10 (the
    /// full 640x480 view), Num Runs +0x70 0 (then counted), Num Movies +0x74 0,
    /// Sound Volume +0x12c 80. Values startup consumes later (sound flags,
    /// volumes, front layer, the last user) wait for their original point.
    private func readStartupSettings() throws {
        let app = base.applicationToken
        let store = ClawNativeSettingsStore(directory:settingsDirectory)
        settings = store
        let config = resources.allocate(540)
        put(config,0);put(app+0x38,config);configuration = config
        guard resources.invoke(0x4b5c50,config,[0x5258b8,0x524eec,0x5258d0,0,0x80000002,0]) != 0,resources.fault == 0 else {
            throw ClawNativeMenuResources.Failure.invalid("Settings key at \(String(resources.faultAddress,radix:16))")
        }
        func read(_ key:UInt32,_ fallback:UInt32)->UInt32 {resources.invoke(0x4b5f30,config,[key,fallback])}
        put(app+0x68,read(0x5258a8,10))
        put(app+0x70,read(0x52589c,0))
        put(app+0x74,read(0x525890,0))
        // Variable Jump .. Skip Joystick Menu Button, then the tuning values
        // whose defaults are the globals' own image values.
        for (key,global,fallback):(UInt32,UInt32,UInt32) in [(0x525880,0x525510,1),(0x525874,0x525514,1),(0x525860,0x525518,1),
            (0x525850,0x537234,0),(0x525840,0x537238,0),(0x52582c,0x53723c,0),(0x525818,0x537240,0),(0x5257fc,0x537244,0),
            (0x5257ec,0x537248,0),(0x5257dc,0x53724c,0),(0x5257c8,0x537250,0),(0x5257b4,0x537254,0),(0x525798,0x537258,0)] {
            put(global,read(key,fallback))
        }
        for (key,global):(UInt32,UInt32) in [(0x525784,0x52c6e4),(0x525770,0x52c6e8),(0x525758,0x52c6ec),
            (0x525744,0x527134),(0x525730,0x527130),(0x52571c,0x527138)] {
            put(global,read(key,w(global)))
        }
        // "User": the last player, a 32-byte buffer with capacity 30.
        let user = resources.allocate(32),length = resources.allocate(4)
        nativeStartupBlocks += [user,length]
        put(user,0);put(length,30)
        _ = resources.invoke(0x4b5e90,config,[0x525714,user,length,0])
        startupSettings[0x525714] = user
        for (key,field):(UInt32,UInt32) in [(0x52570c,0x14),(0x525704,0x10),(0x5256fc,0x118),(0x5256f4,0x11c),
            (0x5256e8,0x120),(0x5256dc,0x124),(0x5256d0,0x128)] {
            startupSettings[key] = read(key,w(app+field))
        }
        startupSettings[0x5256c0] = read(0x5256c0,50)
        let soundVolume = read(0x5256b0,80)
        startupSettings[0x5256b0] = soundVolume
        put(app+0x12c,soundVolume)
        put(app+0x70,w(app+0x70)&+1)
        if w(0x537244) != 0 {put(0x537238,1);put(0x537254,1)}
        guard resources.fault == 0 else {
            throw ClawNativeMenuResources.Failure.invalid("Startup settings at \(String(resources.faultAddress,radix:16))")
        }
    }
    /// Original startup's player choice after the saved games load
    /// (0x4265ce..0x4266db): the stored last "User" if it names a player;
    /// otherwise v1.3 installation metadata (User Name, Location, Comment) selects or
    /// creates its player and is then deleted. Returns 0 when neither chose a
    /// player, and native startup selects "Player" as before. A store without
    /// the metadata answers all three reads empty, so they are not repeated.
    private func selectStoredPlayer(_ profiles:UInt32)->UInt32 {
        let app = base.applicationToken,config = configuration
        guard config != 0,let store = settings else {return 0}
        if let user = startupSettings[0x525714],let p = heap.lookupBytes(user,count:1),p.pointee != 0 {
            let player = resources.invoke(0x49bee0,profiles,[user])
            if player != 0 {nativeStartupBlocks.append(player);_ = resources.invoke(0x42bf90,app,[player]);return player}
        }
        let metadataField = ProcessInfo.processInfo.environment["CLAW_GAME_VERSION"] == "1.0" ? "User Email":"User Comment"
        guard ["User Name","User Location",metadataField].contains(where:{store.text($0) != nil}) else {return 0}
        let commentKey = resources.textToken(metadataField)
        defer {resources.release(commentKey)}
        let name = resources.allocate(0x50),location = resources.allocate(0x50),comment = resources.allocate(0x50),length = resources.allocate(4)
        nativeStartupBlocks += [name,location,comment,length]
        for (key,buffer):(UInt32,UInt32) in [(0x52560c,name),(0x5255fc,location),(commentKey,comment)] {
            put(buffer,0);put(length,0x50)
            _ = resources.invoke(0x4b5e90,config,[key,buffer,length,0])
        }
        var player:UInt32 = 0
        if let p = heap.lookupBytes(name,count:1),p.pointee != 0 {
            player = resources.invoke(0x49bee0,profiles,[name])
            if player == 0 {player = resources.invoke(0x49bdb0,profiles,[name,location,comment,0])}
            _ = resources.invoke(0x42bf90,app,[player])
        }
        for key:UInt32 in [0x52560c,0x5255fc,commentKey] {_ = resources.invoke(0x4b5f80,config,[key])}
        return w(app+0x64) != 0 ? player:0
    }
    /// Original startup's stored sound and display options (0x4266ee..0x42673b),
    /// after the volumes: Music +0x14, Sound +0x10 and 0x532c0c, Voice +0x118,
    /// Ambient +0x11c, High Detail +0x124, Interlaced +0x120, and the front
    /// layer through 0x42ce20. A value equal to the field it defaulted from
    /// leaves the field as the constructor made it.
    private func applyStartupOptions() {
        let app = base.applicationToken
        for (key,field):(UInt32,UInt32) in [(0x52570c,0x14),(0x525704,0x10),(0x5256fc,0x118),(0x5256f4,0x11c),(0x5256dc,0x124),(0x5256e8,0x120)] {
            if let value = startupSettings[key],value != w(app+field) {put(app+field,value)}
        }
        if let sound = startupSettings[0x525704],sound != w(0x532c0c) {put(0x532c0c,sound)}
        if let front = startupSettings[0x5256d0],front != w(app+0x128) {_ = resources.invoke(0x42ce20,app,[front])}
    }
    /// Original teardown's settings (0x426984..0x426ad6), before anything is
    /// destroyed: Num Runs, Num Movies, the sound and display options, Display
    /// Rankings, Disable Joystick, the selected player as "User" (then
    /// application +0x64 cleared), Music Volume from the music manager
    /// (0x4b5650), Sound Volume (0x532c10) while the sound manager lives, and
    /// the colour depth flags. Then 0x4b5d70 closes the keys. It runs once.
    func writeSettings() {
        guard !settingsWritten,!closed,configuration != 0,resources.fault == 0 else {return}
        settingsWritten = true
        let app = base.applicationToken,config = configuration
        func write(_ key:UInt32,_ value:UInt32) {_ = resources.invoke(0x4b5e50,config,[key,value])}
        write(0x52589c,w(app+0x70));write(0x525890,w(app+0x74))
        write(0x525704,w(app+0x10));write(0x5256fc,w(app+0x118));write(0x5256f4,w(app+0x11c))
        write(0x52570c,w(app+0x14));write(0x5256e8,w(app+0x120));write(0x5256dc,w(app+0x124))
        write(0x5256d0,w(app+0x128));write(0x525860,w(0x525518));write(0x52582c,w(0x53723c))
        if w(app+0x60) != 0,w(app+0x64) != 0 {
            _ = resources.invoke(0x4b5df0,config,[0x525714,w(app+0x64)+0x14])
            put(app+0x64,0)
        }
        if w(app+0x50) != 0 {write(0x5256c0,resources.invoke(0x4b5650,w(app+0x50)))}
        if w(app+0x30) != 0,w(w(app+0x30)+0x28) != 0 {write(0x5256b0,w(0x532c10))}
        write(0x5257dc,w(app+0x78) == 0x10 ? 1:0)
        write(0x5257c8,0)
        _ = resources.invoke(0x4b5d70,config)
        put(app+0x38,0);resources.release(config);configuration = 0
    }
    /// The original startup's GAME interfaces after the archive opens: the
    /// in-game menu (application +0xf0, read by 0x44f880) and the game-over
    /// screen (+0xf4), each looked up as IFC and kept locked.
    private func loadGameInterfaces() {
        let game = resources.directory("GAME")
        let detail = w(base.applicationToken+0x9c) != 0
        for (offset,name) in [(UInt32(0xf0),detail ? "NANIINGAME":"INGAME"),(0xf4,detail ? "NANIGAMEOVER":"GAMEOVER")] {
            let resource = game == 0 ? 0:resources.resource(directory:game,name:name,type:0x494643)
            put(base.applicationToken+offset,resource)
            if resource != 0 {_ = resources.invoke(0x4b61c0,resource)}
        }
    }
    func load() throws {
        try resources.open()
        put(base.applicationToken+0x34,resources.archive)
        loadGameInterfaces()
        guard resources.invoke(0x48f0d0,base.menuToken,[base.applicationToken,1,0]) == 1 else {
            throw ClawNativeMenuResources.Failure.invalid("Menu base binding at \(String(resources.faultAddress,radix:16))")
        }
        constructImageManager()
        let images = resources.directory("STATES_MENU_IMAGES")
        let prefix = resources.textToken("MENU"),separator = resources.textToken("_")
        imageCount = resources.invoke(0x4cff40,manager,[images,prefix,separator])
        resources.release(prefix);resources.release(separator)
        guard imageCount > 0,resources.fault == 0 else {throw ClawNativeMenuResources.Failure.invalid("Image registration at \(String(resources.faultAddress,radix:16))")}
        put(0x537b58,base.menuToken);put(0x5371fc,base.applicationToken)
        let menu = resources.directory("STATES_MENU")
        let resource = resources.resource(directory:menu,name:"CLAW",type:0x494643)
        guard resource != 0 else {throw ClawNativeMenuResources.Failure.invalid("Missing CLAW.IFC")}
        let data = resources.invoke(0x4b61c0,resource)
        let result = resources.invoke(0x4dcdf0,base.menuToken+0x154,
            [base.palette!.backendManagerToken,data,w(resource+20),0x45f940,0,0,0])
        _ = resources.invoke(0x4b6230,resource)
        guard result == 1,resources.fault == 0 else {throw ClawNativeMenuResources.Failure.invalid("IFC loader at \(String(resources.faultAddress,radix:16))")}
        loaded = true
    }
    // The single-player native host has no network services.
    // Use the original IFC disabled flag: activation still reaches 45c240 with
    // enabled=0, which plays the unavailable sound and leaves the page intact.
    // Page entry can re-enable Upload Scores / Game Lobby, so reapply after
    // original menu work as well as before input (including queued clicks).
    private(set) var unavailableMenuFlags:[String:UInt32] = [:]
    // Read-only IFC observations for the real-input audit, including Escape's
    // separate tree. Do not change menuToken's main-menu lifetime semantics.
    var activeInterfaceToken:UInt32 {
        let state = w(base.applicationToken+0x2c)
        return state != 0 && resources.owns(state) && [UInt32(0x50c1e4),0x50c044].contains(w(state)) ? state:0
    }
    var menuAudit:[[String:Any]] {
        guard activeInterfaceToken != 0 else {return []}
        var rows:[[String:Any]] = []
        func visit(_ node:UInt32,_ parent:UInt32) {
            let id = w(node+0x50),widget = node+0x3c,flags = w(widget+0x44)
            let images = w(widget+4)
            let disabledImage = images == 0 ? 0:w(images + (flags & 4 == 0 ? 0x14:flags & 0x10 == 0 ? 0x18:0x1c))
            rows.append(["id":id,"parent":parent,"title":resources.text(w(node+0x14)) ?? "",
                "disabled":flags & 0x20 != 0,"flags":flags,"image":w(widget+0x40),"disabled_image":disabledImage,
                "rect":[w(widget+0x54),w(widget+0x58),w(widget+0x5c),w(widget+0x60)]])
            for i in 0..<min(w(node+0x20),256) {visit(w(w(node+0x1c)+i*4),id)}
        }
        visit(activeInterfaceToken+0x154+0x48,0)
        return rows
    }
    private func disableUnavailableMenuItems() {
        let interface = activeInterfaceToken
        guard interface != 0,resources.fault == 0 else {return}
        // The retail Save Game page contains only Back; native checkpoints
        // live in the in-game save overlay instead of this empty service.
        var unavailable:[UInt32] = [11004,11005,12001,12002,12003,12201]
        // Native dialog callbacks are optional host services. Missing one must
        // use IFC's disabled artwork, never fall into the Windows dialog path.
        if showControls == nil {unavailable += [13003,23001]}
        if showPlayers == nil {unavailable += [13001]}
        if showCustomLevels == nil {unavailable += [11003]}
        for id in unavailable {
            let node = resources.invoke(0x4dd020,interface+0x154,[id])
            if node != 0,w(node+0x80) & 0x20 == 0 {
                _ = resources.invoke(0x4dceb0,interface+0x154,[id,0])
            }
            if node != 0 {unavailableMenuFlags[String(id)] = w(node+0x80)}
        }

    }
    func enter(previous:UInt32 = 0) throws {

        guard loaded,fullInitialization,!closed else {throw ClawNativeMenuResources.Failure.invalid("Menu entry lifetime")}
        recordingInitialization = captureEvidence
        defer {recordingInitialization = false}
        base.palette?.display?.menuSwapChain = true
        put(base.applicationToken+0x2c,base.menuToken)
        _ = resources.invoke(0x45b3f0,base.menuToken,[previous])
        disableUnavailableMenuItems()
        guard resources.fault == 0 else {throw ClawNativeMenuResources.Failure.invalid("Menu entry at \(String(resources.faultAddress,radix:16))")}
        // Complete the factory's successful entry continuation (429356..429393).
        // In particular, reset frame/animation baselines after the paper wait.
        put(w(base.applicationToken+8)+0x244,1)
        _ = resources.invoke(0x431300,inputController)
        put(inputController+0xc,.max)
        let input = w(0x537200)
        _ = resources.invoke(0x4b3ab0,input)
        put(input+0x20c,.max)
        _ = resources.invoke(0x42abf0,base.applicationToken)
        guard resources.fault == 0 else {
            throw ClawNativeMenuResources.Failure.invalid("Menu entry continuation at \(String(resources.faultAddress,radix:16))")
        }
    }
    func invokeBranch(_ function:UInt32,_ receiver:UInt32,_ arguments:[UInt32])->UInt32 {

        recordingInitialization = captureEvidence
        defer {recordingInitialization = false}
        return resources.invoke(function,receiver,arguments)
    }
    // Native attract/title lifecycle. This is a host implementation, not an
    // admission of startup_state_two. Resource, paper, sound and display work
    // stays with the existing owners; the application still dispatches 8027
    // and 8023 and owns creation/destruction of the state.
    private func titleService(_ function:UInt32,_ state:UInt32,_ args:[UInt32])->UInt32? {
        guard [UInt32(0x408b30),0x408bf0,0x408c20,0x408d30,0x408e20,0x408f50,
               0x408fa0,0x409000,0x409050,0x4293f0,0x429410].contains(function) else {return nil}
        guard heap.lookupBytes(state,count:0x158) != nil,w(state) == 0x50c2d4 else {
            return resources.fail(function)
        }
        func call(_ f:UInt32,_ r:UInt32,_ a:[UInt32] = [])->UInt32 {resources.invoke(f,r,a)}
        func titleSound()->UInt32 {
            let slot = resources.allocate(4)
            defer {resources.release(slot)}
            _ = transport(0x4f6286,w(w(state+0xc)+0x28)+0x10,[0x52374c,slot])
            return w(slot)
        }
        func backToMenu() {
            if w(w(state+4)+0x9c) != 0 {_ = call(0x42b990,w(state+4),[1])}
            else if let input = base.windowInput {_ = transport(0x546d50,0,[input.window,0x111,0x8023,0])}
        }
        switch function {
        case 0x408b30:
            guard args.count == 3 else {return resources.fail(function)}
            guard call(0x48f0d0,state,args) != 0 else {return 0}
            _ = transport(0x546d54,0,[0])
            _ = call(0x42a000,args[0],[0])
            put(state+0x20,call(0x4b7f20,w(state+8),[0x52373c]))
            put(state+0x24,call(0x4b7f20,w(state+8),[0x523734]))
            guard w(state+0x20) != 0,w(state+0x24) != 0 else {return 0}
            let sounds = call(0x4b68c0,w(state+0x20),[0x52372c])
            guard sounds != 0 else {return 0}
            _ = call(0x4ca440,w(w(state+0xc)+0x28),[sounds,0x534938,0x523728])
            return resources.fault == 0 ? 1:0
        case 0x408c20:
            guard args.count == 1 else {return resources.fail(function)}
            _ = transport(0x546d54,0,[0])
            let roll = [UInt32(2),5,8,9].contains(args[0])
            if roll {_ = call(0x48f500,state,[700])}
            if w(state+0x10) != 0 {
                _ = call(0x48f740,state,[0x52374c,0,roll ? 0:500,roll ? 0:500,700])
            } else {_ = call(0x48f3e0,state,[0x52374c,0,0,1,0])}
            let display = w(w(state+0xc)+4)
            _ = call(0x4ca9e0,display,[w(display+0x14)])
            put(state+0x154,3000)
            if w(w(state+4)+0x9c) == 0 {
                let sound = titleSound()
                if sound != 0 {
                    let voice = w(sound+0x10)
                    if w(0x532c0c) != 0 {_ = call(0x4b3dc0,voice,[100,0,0,0])}
                    put(state+0x154,w(voice+0x28))
                }
            }
            return 1
        case 0x408e20:
            guard args.isEmpty else {return resources.fail(function)}
            let audio = w(w(w(state+0xc)+0x28)+0x2c)
            if audio != 0 {_ = call(0x4b4b80,audio)}
            let remaining = w(state+0x154),delta = w(0x53720c)
            put(state+0x154,remaining > delta ? remaining-delta:0)
            if w(w(state+4)+0x9c) == 0 {
                let sound = titleSound()
                if sound != 0,call(0x4b3e70,w(sound+0x10)) == 0 {put(state+0x154,0)}
            }
            _ = call(0x4b3490,w(0x537200))
            if w(w(0x537200)+0x210) & 0xffffff != 0 || w(state+0x154) == 0 {
                backToMenu()
                put(w(w(state+4)+8)+0x244,0)
            }
            return 1
        case 0x409000,0x409050:
            guard args.count == (function == 0x409000 ? 2:3) else {return resources.fail(function)}
            if function == 0x409050 || [UInt32(13),27,32].contains(args[0]) {backToMenu()}
            return 1
        case 0x408f50:
            let display = w(w(state+0xc)+4)
            if call(0x4ca930,display) != 0 {_ = call(0x48f3e0,state,[0x52374c,0,0,1,0])}
            return 1
        case 0x408fa0:
            guard w(state+0x34) != 0,w(state+0x2c) != 0 else {return 0}
            let display = w(w(state+0xc)+4)
            _ = call(0x4b98b0,w(w(display+0x10)+0x2c),[0])
            _ = call(0x4ca9e0,display,[w(display+0x14)])
            return 1
        case 0x408d30:
            let sound = titleSound()
            if sound != 0 {_ = call(0x4b3fe0,w(sound+0x10),[0,0,1])}
            return 1
        default:
            let manager = w(w(state+0xc)+0x28),audio = w(manager+0x2c)
            if audio != 0 {_ = call(0x4b4b40,audio)}
            _ = call(0x4ca300,manager)
            _ = call(0x48f180,state)
            if function == 0x4293f0,args.first.map({$0 & 1 != 0}) == true {resources.release(state)}
            return function == 0x4293f0 ? state:0
        }
    }
    private func presentationKeyHeld(_ code:UInt32)->Bool {
        guard let input = base.windowInput else {return false}
        if input.asyncKeyState(code)&0x8000 != 0 {return true}
        guard !joystickDisabled,let pad = input.joystick else {return false}
        if code == 37 && pad.x < 16384 || code == 39 && pad.x > 49151 || code == 38 && pad.y < 16384 || code == 40 && pad.y > 49151 {return true}
        return Self.controlActions.contains {w(inputController+0x38+$0.slot*4) == code && pad.buttons&w(inputController+$0.slot*4) != 0}
    }
    private func updatePresentation() throws {
        try customLua?.retireHUDObjects()
        if let size = presentationResolution {
            presentationResolution = nil
            if w(base.applicationToken+0x7c) != size[0] || w(base.applicationToken+0x80) != size[1] {
                resizingPresentation = true;defer {resizingPresentation = false}
                guard resources.invoke(0x42a060,base.applicationToken,size) == 1,resources.fault == 0 else {throw ClawCustomLua.Failure.script("Native logical resolution change failed")}
            }
            customLevelEvidence["logical_resolution"] = size
        }
        if customLua != nil {
            let held = Set((UInt32(0)..<256).filter {presentationKeyHeld($0)})
            presentationEdges = held.subtracting(presentationHeld);presentationHeld = held
        }
    }
    func frame() throws {

        guard loaded,fullInitialization,!closed else {throw ClawNativeMenuResources.Failure.invalid("Menu frame lifetime")}
        if let input = base.windowInput {
            let connected = input.joystick != nil
            input.sampleJoystick()
            if connected != (input.joystick != nil) {
                // Reattach the physical port without resetting player bindings.
                // On removal stop polling before WinMM's retained buffer could
                // repeat the last held button indefinitely.
                let source = w(inputController)
                initializeInputSource(source)
                _ = resources.invoke(0x4b3430,source,[joystickDisabled ? 0:2])
                _ = resources.invoke(0x431300,inputController)
            }
        }
        try updatePresentation()
        installControllerDefaults()
        if controlsActive || playersActive || customLevelsActive {return}
        recordingInitialization = captureEvidence
        defer {recordingInitialization = false}
        if let input = base.windowInput {
            // PostMessage queues a window command for the next pump turn. The
            // admitted application dispatcher elects its meaning and state.
            // The pump delivers until the queue is empty, so a command posted
            // while another is delivered runs in the same turn, before the
            // frame (the original's PeekMessage loop; the traces' bounded drain).
            var delivered = 0
            while !postedCommands.isEmpty {
                guard delivered < 128 else {throw ClawNativeMenuResources.Failure.invalid("Posted command queue did not drain")}
                let command = postedCommands.removeFirst()
                delivered += 1
                guard command.window == input.window else {
                    throw ClawNativeMenuResources.Failure.invalid("Posted command window lifetime")
                }
                // Queued accelerators use the same capability boundary as
                // IFC activation. Unsupported Windows dialogs cannot dispatch.
                if command.wParam == 0x8090,
                   (command.lParam == 0 && showControls == nil ||
                    command.lParam == 2 && showCustomLevels == nil ||
                    command.lParam == 4 && showPlayers == nil ||
                    ![UInt32(0),2,4].contains(command.lParam)) {continue}
                if command.wParam == 0x8090,command.lParam == 0,let showControls {
                    input.releaseMenuKeys()
                    // No queued key or click may leak through the modal boundary.
                    while try input.queue.next(window:input.window) != nil {}
                    controlsActive = true
                    showControls()
                    return
                }
                if command.wParam == 0x8090,command.lParam == 2,let showCustomLevels {
                    input.releaseMenuKeys()
                    while try input.queue.next(window:input.window) != nil {}
                    customLevelsActive = true;showCustomLevels();return
                }
                if command.wParam == 0x8090,command.lParam == 4,let showPlayers {
                    // Normal EDITPLAYERS. v1.3 CONFIG_PLAYERS requires the
                    // separate developer gate (535978), initialized off at
                    // 4267e0; it is not a new normal menu option.
                    input.releaseMenuKeys()
                    while try input.queue.next(window:input.window) != nil {}
                    playersActive = true;showPlayers();return
                }
                if command.wParam == 0x800e {try completeCrazyLevel()}
                deliveringPostedCommand = command.wParam
                _ = resources.invoke(0x426e30,base.applicationToken,[0,command.wParam,command.lParam])
                deliveringPostedCommand = nil
                guard resources.fault == 0 else {
                    if let error = customLua?.error {throw ClawCustomLua.Failure.script(error)}
                    throw ClawNativeMenuResources.Failure.invalid("Menu command at \(String(resources.faultAddress,radix:16))")
                }
            }
            if delivered > 0 {postedCommandsDelivered?()}
            if skipIdleFrameOnce {
                skipIdleFrameOnce = false
                lastFrameCheck = ["skipped":true,"presentations":0,"frame_ms":0]
                return
            }
            postedCommands += afterFrameCommands
            afterFrameCommands.removeAll()
            while let event = try input.queue.next(window: input.window) {
                disableUnavailableMenuItems()
                switch event.message {
                case .keyDown:
                    try translateAccelerator(key: event.wParam, character: nil, modifiers: event.modifiers)
                    _ = resources.invoke(0x429d60, base.applicationToken, [event.wParam, event.lParam])
                    if resources.fault == 0, let character = Self.character(key: event.wParam, modifiers: event.modifiers) {
                        // The WM_CHAR follows in the same pump turn; every state's
                        // character handler is inert (0x40af40).
                        try translateAccelerator(key: event.wParam, character: character, modifiers: event.modifiers)
                    }
                case .primaryDown, .primaryUp, .mouseMove:
                    let target: UInt32 = event.message == .primaryDown ? 0x429d80 :
                        event.message == .primaryUp ? 0x429db0 : 0x429de0
                    _ = resources.invoke(target, base.applicationToken,
                        [event.wParam, event.lParam & 0xffff, event.lParam >> 16])
                case .keyUp: break // The original window has no WM_KEYUP handler.
                }
                guard resources.fault == 0 else {
                    throw ClawNativeMenuResources.Failure.invalid("Menu input at \(String(resources.faultAddress, radix: 16))")
                }
            }
        }
        disableUnavailableMenuItems()
        // Window idle 0x4b9070 only calls the application frame while +0x244
        // is enabled. Native window activity (+0x240) is checked by the app's
        // activation guard. Keep pumping messages above so Pause can resume.
        guard w(w(base.applicationToken+8)+0x244) != 0 else {
            lastFrameCheck = ["skipped":true,"presentations":0,"frame_ms":0]
            return
        }
        let before = base.palette?.display?.presentations
        let movieEventStart = movieEvents.count
        let result = resources.invoke(0x428b60,base.applicationToken)
        if let error = customLua?.error,resources.fault == 0 {
            try retireFailedCustomLevel(error)
            return
        }
        lastFrameCheck = ["result":result,"fault":resources.fault,"fault_address":String(resources.faultAddress,radix:16),
            "presentations":(base.palette?.display?.presentations ?? -1) - (before ?? 0),
            "frame_ms":heap.lookupBytes(0x53720c,count:4) == nil ? -1:Int(w(0x53720c))]
        // The original frame presents once, or not at all on the first results
        // frame after level-complete command 0x800e (end-of-level trace, frame cycle 117).
        // In-game Options > Display: Front Layer (0x5b05 in 0x451230) and the Game Play
        // Area slider repaint through 0x450380 -> 0x46dd90, which presents once more
        // inside the same frame before the menu frame's own present.
        // Replay Movies fades/clears twice in 0x45e0e0, then redraws and
        // presents again in 0x45e1b0 before this frame returns. Those physical
        // presentations are valid; the ordinary frame's two-flip bound is not.
        let playedMovie = movieEvents.dropFirst(movieEventStart).contains { $0["call"] as? String == "play" }
        lastFrameCheck["played_movie"] = playedMovie
        guard result == 1,resources.fault == 0,let before,let after = base.palette?.display?.presentations,
              after >= before,playedMovie || after <= before+2 else {
            if let error = customLua?.error {throw ClawCustomLua.Failure.script(error)}
            throw ClawNativeMenuResources.Failure.invalid("Menu frame at \(String(resources.faultAddress,radix:16))")
        }
        try updateCrazyCheckpoint()
        if !applicationServicesInstalled {try installApplicationServices()}
        disableUnavailableMenuItems()
    }
    /// Original startup builds the screen fader (0x426075 constructs it with
    /// 0x4ebf80, 0x426090 initializes it with 0x4ec010(0,0,0), application
    /// +0x44) and the light palette manager (0x426474: 0x4c61d0, 0x4c6260,
    /// application +0x58) before the first state. Menu initialization snapshots
    /// +0x44 into menu +0x10; without both, every paper roll (0x45dc90's
    /// unroll, 0x48f500 roll-up, 0x48f740 unroll) takes its early return.
    /// --no-paper-startup leaves them out: the startup profile of the menu and
    /// Level 1 reference traces, which do not construct them.
    private func installPaperServices() throws {
        guard !ProcessInfo.processInfo.arguments.contains("--no-paper-startup") else {return}
        let app = base.applicationToken
        let fader = resources.allocate(0x28)
        _ = resources.invoke(0x4ebf80,fader)
        guard resources.invoke(0x4ec010,fader,[0,0,0]) == 1,resources.fault == 0 else {
            throw ClawNativeMenuResources.Failure.invalid("Screen fader initialization at \(String(resources.faultAddress,radix:16))")
        }
        put(app+0x44,fader)
        let tables = resources.allocate(0x18)
        _ = resources.invoke(0x4c61d0,tables)
        put(app+0x58,tables)
        guard resources.invoke(0x4c6260,tables) != 0,resources.fault == 0 else {
            throw ClawNativeMenuResources.Failure.invalid("Palette-table initialization at \(String(resources.faultAddress,radix:16))")
        }
    }
    private var applicationServicesInstalled = false
    // Native application startup also owns four objects the original builds
    // inline in its startup body; the Level 1 state reads them through the
    // application. Paper startup installs them before menu entry so applying
    // the stored volume cannot cancel the menu's newly created audio fade.
    // The older no-paper comparison profile installs them after frame one.
    private func installApplicationServices() throws {
        applicationServicesInstalled = true
        let app = base.applicationToken
        func check(_ what:String) throws {
            guard resources.fault == 0 else {throw ClawNativeMenuResources.Failure.invalid("\(what) at \(String(resources.faultAddress,radix:16))")}
        }
        if w(app+0x58) == 0 {
            let tables = resources.allocate(0x18)
            _ = resources.invoke(0x4c61d0,tables)
            put(app+0x58,tables)
            guard resources.invoke(0x4c6260,tables) != 0 else {throw ClawNativeMenuResources.Failure.invalid("Palette-table initialization")}
            try check("Palette-table initialization")
        }
        // Inline 0x4262c4..0x4262d7: CObList at +8, fields +0 and +4.
        let sounds = resources.allocate(0x30)
        _ = transport(0x4f5133,sounds+8,[10]);put(sounds,0);put(sounds+4,0x64)
        put(app+0x5c,sounds)
        // 0x4262e7: the stored Sound Volume (default 80, read at 0x425acc).
        let soundVolume = startupSettings[0x5256b0] ?? 80
        guard resources.invoke(0x402240,sounds,[w(w(app+0x30)+0x28),soundVolume]) != 0 else {throw ClawNativeMenuResources.Failure.invalid("Sound-events initialization")}
        try check("Sound-events initialization")
        // 0x426314..0x42633b: the stored Ambient (read at 0x425a5e) switches the
        // group's enabled word: on and off -> set it and 0x402570; off and on ->
        // clear it and 0x402520. Then 0x426340 applies the volume through
        // 0x42cdc0, which now also reaches the group (0x4024e0).
        let ambient = startupSettings[0x5256f4] ?? w(app+0x11c)
        if ambient != 0 {
            if w(sounds+0x24) == 0 {put(sounds+0x24,1);_ = resources.invoke(0x402570,sounds)}
        } else if w(sounds+0x24) != 0 {
            put(sounds+0x24,0);_ = resources.invoke(0x402520,sounds)
        }
        _ = resources.invoke(0x42cdc0,app,[soundVolume])
        try check("Startup ambient switch")
        // Inline 0x4260d3..0x4260f5: string map at +4, cleared header fields.
        let commands = resources.allocate(0x12c)
        _ = transport(0x4f5cbd,commands+4,[10]);put(commands,0)
        if let p = heap.lookupBytes(commands+0x20,count:1) {p.pointee = 0}
        for offset:UInt32 in [0x120,0x124,0x128] {put(commands+offset,0)}
        put(app+0x48,commands)
        _ = resources.invoke(0x422890,commands,[w(w(app+0x04)+0x04)])
        // The ten added v1.3 registration tuples, including the original
        // presentation-only versus game-cheating flags.
        for (name,id,flag):(String,UInt32,UInt32) in [
            ("MPLONGRANGE",0x80b2,0),("MPEASYMODE",0x80b5,0),("MPTWINTURBO",0x80b6,0),
            ("MPGLOOMY",0x80ad,1),("MPNOISE",0x80ae,1),("MPMAESTRO",0x80af,1),
            ("MPLANGSAM",0x80b0,1),("MPNORMALMUSIC",0x80b1,1),
            ("MPBOUNCECOUNT",0x80b3,1),("MPWILDWACKY",0x80b4,1)] {
            let key = String(bytes:name.utf8.map{$0+0x11},encoding:.utf8)!
            _ = resources.invoke(0x422980,commands,[cstring(key),id,flag])
        }
        _ = heap.store(token:0x58010000,words:9)
        _ = heap.storeBytes(token:0x58010100,count:128)
        put(0x58010020,9999)
        try check("Command-manager initialization")
        // Inline 0x42614c..0x42616b: CStringList, CString at +0x1c.
        let overlay = resources.allocate(0x38)
        _ = transport(0x4f5249,overlay,[10]);_ = transport(0x4f6439,overlay+0x1c,[])
        put(overlay+0x30,0);put(overlay+0x34,0)
        put(app+0x4c,overlay)
        guard resources.invoke(0x4222a0,overlay,[5000,2000]) != 0 else {throw ClawNativeMenuResources.Failure.invalid("Message-overlay initialization")}
        try check("Message-overlay initialization")
    }
    // 0x4f0000 initialize(window, display interface, mode descriptor words),
    // 0x4f02e0 open(container, movie number, ...), 0x4f0380 play(flags 1 = any
    // WM_KEYDOWN skips, play count, input), 0x4f0120 cleanup.
    private func movieLibrary(_ function:UInt32,_ r:UInt32,_ a:[UInt32])->UInt32? {
        switch function {
        case 0x4f0000:
            guard a.count == 31 else {return nil}
            movieObjects[r] = 0;movieQueues[r] = []
            movieEvents.append(["call":"initialize","object":r,"descriptor":Array(a[3..<30])]);return 1
        case 0x4f02e0:
            guard a.count == 6,movieObjects[r] != nil else {return nil}
            let available = movieAvailable?(a[1]) == true
            movieEvents.append(["call":"open","movie":a[1],"container":string(a[0]),"available":available])
            guard available else {return 0}
            if a[1] == 11 || a[1] == 12 {
                closeMovieBackground(r)
                guard let file = movieBackgroundFile?(a[1]),let palette = base.palette else {return resources.fail(function)}
                do {movieBackgrounds[r] = try ClawNativeMovieBackground(file:file)}
                catch {return resources.fail(function)}
                let token = palette.makeMoviePalette(ClawNativeMovieBackground.entries)
                guard token != 0 else {return resources.fail(function)}
                moviePalettes[r] = token;put(r+32,token)
            }
            movieObjects[r] = a[1];return 1
        case 0x4f0610:
            guard a.count == 2,a[1] == .max,let decoder = movieBackgrounds[r],let display = base.palette?.display else {return nil}
            do {
                let playing = try display.movieFrame(decoder,surface:a[0],clock:lastClock)
                movieEvents.append(["call":"background-frame","movie":movieObjects[r] ?? 0,"clock":lastClock,"playing":playing,"frame":decoder.frames])
                return playing ? 1:0
            } catch {return resources.fail(function)}
        case 0x4f06e0:
            guard a.isEmpty,movieObjects[r] != nil else {return nil}
            closeMovieBackground(r)
            movieEvents.append(["call":"background-close","object":r]);return 0
        case 0x4f0380:
            guard a.count == 3,let movie = movieObjects[r],movie != 0 else {return nil}
            let result = moviePlay?(movie,a[0]) ?? 0
            movieEvents.append(["call":"play","movie":movie,"flags":a[0],"count":a[1],"result":result]);return result
        case 0x4f10d0:
            guard a.count == 9,movieObjects[r] != nil else {return nil}
            movieQueues[r,default:[]].append(a)
            movieEvents.append(["call":"enqueue","movie":a[1],"flags":a[6],"count":a[7]])
            return 1
        case 0x4f1500:
            guard a.count == 1,movieObjects[r] != nil,a[0] == 1 else {return nil}
            // 0x4f15bc/0x4f165e: any result other than natural completion
            // ends the entire queue, including key (1) and mouse (0x100).
            for entry in movieQueues[r] ?? [] {
                guard movieAvailable?(entry[1]) == true else {return 0}
                movieObjects[r] = entry[1]
                let result = moviePlay?(entry[1],entry[6]) ?? 0
                movieEvents.append(["call":"play","movie":entry[1],"flags":entry[6],"count":entry[7],"result":result])
                if result != 0x11111111 {return result}
            }
            return 0x11111111
        case 0x4f1490:
            guard a.isEmpty else {return nil}
            movieQueues.removeValue(forKey:r)
            movieEvents.append(["call":"clear-queue","object":r]);return 0
        // MFC CFile and CArray lifetimes of the movie helper (0x42b4b0 and the
        // 0x42b140 epilogue). The native player never opens the container.
        case 0x4f72c9:
            guard a.isEmpty,heap.lookup(r,words:4) != nil else {return nil}
            put(r,0x510844);put(r+4,.max);put(r+8,0);put(r+12,0x52e1c4);return r
        case 0x4f7369:
            guard a.isEmpty,w(r) == 0x510844,w(r+4) == .max,w(r+12) == 0x52e1c4 else {return nil}
            put(r,0x510844);return 0
        case 0x4f57f8:
            guard a.isEmpty,w(r) == 0x5108d4 else {return nil}
            _ = arraySize(r,0);put(r,0x50becc);return 0
        case 0x4a3b10: // CRT time
            guard a.count == 1 else {return nil}
            let now = customCalendarTime()
            if a[0] != 0 {guard let slot = heap.lookup(a[0],words:1) else {return nil};slot.pointee = now}
            return now
        case 0x546a30:
            guard let movieContainer,a.count == 3,a[2] == 0x4000,string(a[0]) == movieContainer else {return nil}
            movieEvents.append(["call":"exists","container":movieContainer])
            return movieAvailable == nil ? .max:1
        case 0x4f0120:
            guard a.isEmpty else {return nil}
            if moviePalettes[r] != nil {closeMovieBackground(r)}
            movieQueues.removeValue(forKey:r)
            if movieObjects.removeValue(forKey:r) != nil {movieEvents.append(["call":"cleanup","object":r])}
            return 0
        default:return nil
        }
    }
    /// Original startup's movie point (between its settings and the first
    /// state): unless the detail build or the frozen 0x42a680 hook says
    /// otherwise, a first run (intro count +0x74 < 1 or run count +0x70 < 2)
    /// plays the logo (0x42b900) and the intro (0x42b140 with 0), and counts
    /// a played intro. A repeat launch plays the logo alone unless the stored
    /// "Skip Logo Movies" is set; the counters come from the settings store.
    func playStartupMovies() throws {
        let app = base.applicationToken
        guard w(app+0x9c) == 0 else {return}
        if let movieContainer,string(w(app+0x100)).isEmpty {put(app+0x100,cstring(movieContainer))}
        movieEvents.append(["call":"startup","intro_count":w(app+0x74),"runs":w(app+0x70),"container":string(w(app+0x100))])
        if Int32(bitPattern:w(app+0x74)) > 0,Int32(bitPattern:w(app+0x70)) > 1 {
            // A repeat launch after a played intro: the logo alone, unless
            // the stored "Skip Logo Movies" is set (0x42675e..0x426777).
            let skip = configuration != 0 ? resources.invoke(0x4b5f30,configuration,[0x5255d4,0]):0
            movieEvents.append(["call":"repeat-launch","skip_logo":skip])
            if skip == 0 {
                _ = resources.invoke(0x42b900,app)
                guard resources.fault == 0 else {throw ClawNativeMenuResources.Failure.invalid("Startup logo movie at \(String(resources.faultAddress,radix:16))")}
            }
            movieEvents.append(["call":"startup-done","intro_result":0])
            return
        }
        _ = resources.invoke(0x42b900,app)
        guard resources.fault == 0 else {throw ClawNativeMenuResources.Failure.invalid("Startup logo movie at \(String(resources.faultAddress,radix:16))")}
        let movie = resources.invoke(0x42b140,app,[0])
        guard resources.fault == 0 else {throw ClawNativeMenuResources.Failure.invalid("Startup intro movie at \(String(resources.faultAddress,radix:16))")}
        put(0x53ec58,movie)
        if movie != 0 {put(app+0x74,w(app+0x74)&+1)}
        movieEvents.append(["call":"startup-done","intro_result":movie])
    }
    private func service(_ q:ClawCall)->UInt32? {
        guard resources.fault == 0 else {return nil}
        calls.append(q.function)
        let a = withUnsafeBytes(of:q.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(q.argumentCount)))}
        let r = q.receiver
        // Original 0x42aa90 returns zero before reading its slot/profile data
        // unless the state's actual virtual type query returns 4. Single-player
        // has no type-4 state. Keep an unexpected type-4 route a visible fault.
        if q.function == 0x42aa90 {
            guard a.count == 1 else {return nil}
            let state = w(r+0x2c)
            if state == 0 {return 0}
            let kind = resources.invoke(w(w(state)+0x10),state)
            guard resources.fault == 0,kind != 4 else {return nil}
            return 0
        }
        if q.function == 0x4b9e10 {
            guard a.count == 3,a[1] == 1,let directory = screenDumpDirectory,
                  let display = base.palette?.display,let surface = display.surfacePixels(r),
                  a[2] != 0,let entries = heap.lookupBytes(w(a[2]+0x0c),count:1024) else {return 0}
            let name = string(a[0])
            guard name.hasPrefix("CLAW"),name.hasSuffix(".BMP"),!name.contains("/"),!name.contains("\\") else {return 0}
            let rgb = Data((0..<256).flatMap {i in [entries[i*4],entries[i*4+1],entries[i*4+2]]})
            let data = ClawNativeScreenDump.bitmap(pixels:surface.bytes,width:surface.width,height:surface.height,stride:surface.stride,rgb:rgb)
            var event:[String:Any] = ["name":name,"width":Int(surface.width),"height":Int(surface.height),
                "pixels_sha256":SHA256.hash(data:surface.bytes).map{String(format:"%02x",$0)}.joined(),
                "rgb_sha256":SHA256.hash(data:rgb).map{String(format:"%02x",$0)}.joined(),"success":false]
            do {
                guard let data else {return 0}
                try FileManager.default.createDirectory(at:directory,withIntermediateDirectories:true)
                try data.write(to:directory.appendingPathComponent(name),options:.atomic)
                event["success"] = true
                screenDumps.append(event)
                return 1
            } catch {
                event["error"] = String(describing:error)
                screenDumps.append(event)
                return 0
            }
        }
        if let frame = resources.diagnosticFrame,let result = diagnosticService(q,frame:frame) {return result}
        if let result = customFileService(q.function,r,a) {return result}
        if let result = movieLibrary(q.function,r,a) {return result}
        if [UInt32(0x546834),0x54682c,0x546824,0x546820,0x546830].contains(q.function) {
            return settings?.service(q.function,a,heap:heap)
        }
        if let result = archiveServices.service(q.function,r,a) {return result}
        if let files = saveFiles,let result = files.service(q.function,r,a,heap:heap) {return result}
        if q.function == 0x4f766e || (q.function == 0x4f5915 && movieServices.ownsArray(r)) {
            do {return try movieServices.service(q.function,receiver:r,arguments:a)}
            catch {return resources.fail(q.function)}
        }
        // MFC CTime (platform layer, replaced natively): 0x4f504f GetCurrentTime
        // writes time(NULL) to its hidden return slot; 0x4f5062 GetLocalTm(ptm)
        // converts the receiver's time_t with localtime into ptm or a static tm.
        if q.function == 0x4f504f {
            guard a.count == 1,let slot = heap.lookup(a[0],words:1) else {return nil}
            slot.pointee = customCalendarTime();return a[0]
        }
        if q.function == 0x4f5062 {
            guard a.count == 1,let source = heap.lookup(r,words:1) else {return nil}
            if localTmBuffer == 0 {localTmBuffer = resources.allocate(0x24)}
            let target = a[0] != 0 ? a[0]:localTmBuffer
            guard let out = heap.lookup(target,words:9) else {return nil}
            var t = time_t(Int32(bitPattern:source.pointee)),value = tm()
            guard localtime_r(&t,&value) != nil else {return 0}
            let fields = [value.tm_sec,value.tm_min,value.tm_hour,value.tm_mday,value.tm_mon,value.tm_year,value.tm_wday,value.tm_yday,value.tm_isdst]
            for (i,f) in fields.enumerated() {out[i] = UInt32(bitPattern:f)}
            return target
        }
        if q.function == 0x71020014,let audio = base.audio {
            guard r == 0,a.count == 3,let output = heap.lookup(a[2],words:1) else {return nil}
            return audio.deviceDuplicate(device:a[0],source:a[1],out:output)
        }
        if q.function & 0xffff0000 == 0x71010000,let audio = base.audio {
            let method = q.function & 0xffff
            guard r == 0,a.count <= 4,!a.isEmpty else {return nil}
            var event = ClawAmbientAudioBackendCall()
            event.function = q.function;event.bufferMethod = method;event.argumentCount = q.argumentCount
            withUnsafeMutableBytes(of:&event.arguments){dst in a.withUnsafeBytes{dst.copyBytes(from:$0)}}
            if [UInt32(0x18),0x1c,0x20,0x24].contains(method) {
                guard a.count == 2,let output = heap.lookup(a[1],words:1) else {return nil}
                event.outputWord = output
            }
            return audio.ambientPhysical(event)
        }
        if let result = base.sharedSoundStorageService(q) {return base.fault == 0 ? result:resources.fail(base.boundary)}
        if let result = music?.service(q.function,r,a) {return result}
        if let display = base.palette?.display,let result = display.menuListService(q) {
            return display.fault == 0 ? result:resources.fail(q.function)
        }
        if let palette = base.palette,let result = palette.menuPhysicalService(q) {
            return palette.fault == 0 ? result:resources.fail(q.function)
        }
        if let display = base.palette?.display,let result = display.menuPhysicalService(q) {
            return display.fault == 0 && display.lastSurfaceFault == 0 ? result:resources.fail(q.function)
        }
        if base.sharedMenuResources === resources,let result = base.sharedInitializerService(q.function,r,a) {
            return base.fault == 0 ? result:resources.fail(base.boundary)
        }
        if q.function == 0x546d58 {
            return base.palette?.display?.rawActorService(ClawNativeMenuRawDisplayHost(resources),q)
        }
        switch q.function {
        case 0x546d50: // Native asynchronous window command delivery.
            guard a.count == 4,let input = base.windowInput,a[0] == input.window else {return nil}
            if a[1] == 0x10,a[2] == 0,a[3] == 0 {
                do { try input.queue.postClose(window:input.window) }
                catch { return resources.fail(q.function) }
                record(["service":"PostMessageA","window":a[0],"message":a[1],"wparam":a[2],"lparam":a[3]])
                return 1
            }
            guard a[1] == 0x111 else {return nil}
            postedCommands.append((a[0],a[2],a[3]))
            postedHistory.append(["wparam":a[2],"lparam":a[3]])
            record(["service":"PostMessageA","window":a[0],"message":a[1],"wparam":a[2],"lparam":a[3]])
            return 1
        case 0x546918: // CreateFontA: the message overlay's one logical font.
            guard a.count == 14,Array(a.prefix(13)) == [12,8,0,0,100,0,0,0,1,0,0,0,0] else {return nil}
            let handle = resources.allocate(16)
            nativeStartupBlocks.append(handle);base.palette?.display?.registerFont(handle)
            record(["service":"CreateFontA","font":handle,"height":12,"width":8,"face":a[13] == 0 ? "":string(a[13])])
            return handle
        case 0x4a35f0:
            // Bounded physical exit registration of game callbacks, as the
            // Level 1 join accepts them from every game static initializer.
            guard a.count == 1,claw_level_game_range(a[0]) == 1,exitCallbacks.count < 1024 else {return nil}
            record(["service":"CRT atexit","callback":"0x"+String(a[0],radix:16)])
            exitCallbacks.append(a[0]);return 0
        case 0x546ce4:
            guard a.count == 1,a[0] < 256,let input = base.windowInput else {return nil}
            let result = input.asyncKeyState(a[0])
            record(["service":"GetAsyncKeyState","key":a[0],"result":result])
            return result
        case 0x546df8: // One discoverable native extended-gamepad port.
            guard a.isEmpty,let input = base.windowInput else {return nil}
            return input.joystick == nil ? 0:1
        case 0x546df4: // JOYCAPSA, exact 404-byte layout.
            guard a.count == 3,a[0] == 0,a[2] == 404,let input = base.windowInput,
                  heap.lookupBytes(a[1],count:404) != nil else {return nil}
            guard let sample = input.joystick else {return 165}
            for (index,value) in sample.capabilities.enumerated() {put(a[1]+UInt32(index*4),value)}
            return 0
        case 0x546de8: // JOYINFOEX; retain caller's size and requested flags.
            guard a.count == 2,a[0] == 0,let input = base.windowInput,
                  heap.lookupBytes(a[1],count:52) != nil,w(a[1]) == 52 else {return nil}
            guard let physical = input.joystick else {return 165}
            let state = w(base.applicationToken+0x2c)
            // Native menus receive controller key messages. The original menu
            // also polls WinMM; neutralize that second path to avoid double
            // steps and a selection leaking into the page it just opened.
            let sample = state != 0 && w(state) == 0x50c264 && !controlsActive && !playersActive && !customLevelsActive
                ? physical:ClawNativeJoystickSample(buttonCount:physical.buttonCount)
            for (index,value) in sample.position(size:w(a[1]),flags:w(a[1]+4)).enumerated() {put(a[1]+UInt32(index*4),value)}
            return 0
        case 0x546cd0:
            guard a.count == 1,let input = base.windowInput,heap.lookupBytes(a[0],count:8) != nil else {return nil}
            record(["service":"GetCursorPos","position":[input.cursorPosition.x,input.cursorPosition.y]])
            let position = [input.cursorPosition.x,input.cursorPosition.y]
            guard position.count == 2 else { return resources.fail(q.function) }
            put(a[0],position[0]);put(a[0]+4,position[1]);return 1
        case 0x546cd4: // PtInRect: signed coordinates, exclusive right/bottom.
            guard a.count == 3, heap.lookupBytes(a[0], count: 16) != nil else { return nil }
            let x = Int32(bitPattern: a[1]), y = Int32(bitPattern: a[2])
            return x >= Int32(bitPattern: w(a[0])) && x < Int32(bitPattern: w(a[0]+8)) &&
                y >= Int32(bitPattern: w(a[0]+4)) && y < Int32(bitPattern: w(a[0]+12)) ? 1 : 0
        case 0x546d9c:
            guard a.count == 2,let input = base.windowInput else {return nil}
            record(["service":"SetCursorPos","position":a])
            input.cursorPosition = (a[0],a[1]);return 1
        case 0x546cd8: // SetCursor: the window's cursor handle; returns the previous one.
            guard a.count == 1 else {return nil}
            let previous = cursorHandle;cursorHandle = a[0]
            record(["service":"SetCursor","cursor":a[0],"previous":previous]);return previous
        case 0x546d54:
            guard a.count == 1,let input = base.windowInput else {return nil}
            let count = input.showCursor(a[0] != 0)
            record(["service":"ShowCursor","show":a[0] != 0,"count":Int32(bitPattern:count)]);return count
        case 0x546c44:
            guard a.count == 1,a[0] < 2,let display = base.palette?.display else {return nil}
            record(["service":"GetSystemMetrics","index":a[0],"result":w(display.primaryToken+16+a[0]*4)])
            return w(display.primaryToken+16+a[0]*4)
        case 0x546d5c,0x546cdc:
            guard a.count == (q.function == 0x546d5c ? 5:1),heap.lookupBytes(a[0],count:16) != nil else {return nil}
            for index in 0..<4 {put(a[0]+UInt32(index*4),q.function == 0x546d5c ? a[index+1]:0)}
            return 1
        case 0x546d24,0x546b7c: // InflateRect / OffsetRect(lprc, dx, dy): wrapping signed 32-bit edges.
            guard a.count == 3,heap.lookupBytes(a[0],count:16) != nil else {return nil}
            let inflate = q.function == 0x546d24
            put(a[0],w(a[0]) &+ (inflate ? 0 &- a[1]:a[1]));put(a[0]+4,w(a[0]+4) &+ (inflate ? 0 &- a[2]:a[2]))
            put(a[0]+8,w(a[0]+8) &+ a[1]);put(a[0]+12,w(a[0]+12) &+ a[2])
            return 1
        case 0x546d4c,0x546ce0,0x546d94: // IsRectEmpty / IntersectRect / UnionRect, Win32 semantics.
            let sources = q.function == 0x546d4c ? [a.first ?? 0]:Array(a.dropFirst())
            guard a.count == (q.function == 0x546d4c ? 1:3),
                  ([a[0]] + sources).allSatisfy({heap.lookupBytes($0,count:16) != nil}) else {return nil}
            func edges(_ p:UInt32) -> [Int32] {(0..<4).map {Int32(bitPattern:w(p+UInt32($0*4)))}}
            func empty(_ e:[Int32]) -> Bool {e[2] <= e[0] || e[3] <= e[1]}
            if q.function == 0x546d4c {return empty(edges(a[0])) ? 1:0}
            let x = edges(a[1]),y = edges(a[2])
            var out:[Int32]
            if q.function == 0x546ce0 {
                out = [max(x[0],y[0]),max(x[1],y[1]),min(x[2],y[2]),min(x[3],y[3])]
            } else if empty(x) {out = y} else if empty(y) {out = x} else {
                out = [min(x[0],y[0]),min(x[1],y[1]),max(x[2],y[2]),max(x[3],y[3])]
            }
            if empty(out) {out = [0,0,0,0]}
            for index in 0..<4 {put(a[0]+UInt32(index*4),UInt32(bitPattern:out[index]))}
            return empty(out) ? 0:1
        case 0x4a3050:
            guard a.isEmpty else {return nil}
            let value = claw_level_rand(&randomState)
            randomCalls &+= 1
            record(["service":"CRT rand","state":randomState,"result":value])
            return value
        case 0x4a4630: // CRT div: truncating signed quotient; canonical callers derive EDX themselves.
            guard a.count == 2,a[1] != 0,!(a[0] == 0x80000000 && a[1] == 0xffffffff) else {return nil}
            return UInt32(bitPattern:Int32(bitPattern:a[0]) / Int32(bitPattern:a[1]))
        case 0x4a3040: // CRT srand: reseeds the same native sequence.
            guard a.count == 1 else {return nil}
            randomState = a[0];record(["service":"CRT srand","seed":a[0]]);return 0
        case 0x546ccc: // UpdateWindow on the presented native window: empty update region, no paint.
            guard a.count == 1,let input = base.windowInput,a[0] == input.window,
                  (base.palette?.display?.presentations ?? 0) > 0 else {return nil}
            yieldWindowEvents?()
            record(["service":"UpdateWindow","window":a[0],"update_region":"empty"]);return 1
        case 0x4f5288: // CStringList RemoveAll (platform layer, replaced natively).
            guard a.isEmpty,let nodes = lists[r],w(r) == 0x510224,nodes.count == w(r+12) else {return nil}
            if nodes.isEmpty {
                guard [UInt32(4),8,12,16,20].allSatisfy({w(r+$0) == 0}) else {return nil}
            }
            for node in nodes {
                let text = w(node+8)
                if text >= 12,strings.remove(text-12) != nil {resources.release(text-12)}
                resources.release(node)
            }
            for offset:UInt32 in [4,8,12,16,20] {put(r+offset,0)}
            lists[r] = []
            record(["service":"CStringList RemoveAll","receiver":r,"count":nodes.count]);return 0
        case 0x4f53b7,0x4f5382: // CStringList AddTail / AddHead(const char *), natively.
            guard a.count == 1,let nodes = lists[r],w(r) == 0x510224,nodes.count == w(r+12) else {return nil}
            let head = q.function == 0x4f5382,node = resources.allocate(12)
            let next = head ? w(r+4):0,previous = head ? 0:w(r+8)
            put(node,next);put(node+4,previous);put(node+8,a[0] == 0 ? empty:cstring(string(a[0])))
            put(previous == 0 ? r+4:previous,node);put(next == 0 ? r+8:next+4,node)
            put(r+12,w(r+12)+1);lists[r]!.insert(node);return node
        case 0x4f53eb: // CStringList RemoveHead into the caller's CString slot, natively.
            guard a.count == 1,let nodes = lists[r],w(r) == 0x510224,nodes.count == w(r+12),
                  let node = Optional(w(r+4)),nodes.contains(node) else {return nil}
            let next = w(node)
            put(r+4,next);put(next == 0 ? r+8:next+4,0)
            put(a[0],w(node+8))
            put(r+12,w(r+12)-1);lists[r]!.remove(node);resources.release(node);return a[0]
        case 0x4f650f: // CString Empty.
            guard a.isEmpty,r != 0 else {return nil}
            let pointer = w(r)
            guard pointer >= 12 else {return nil}
            let length = w(pointer-8),capacity = w(pointer-4)
            guard length <= capacity,capacity <= 0x100000 else {return nil}
            if length != 0 {
                if strings.remove(pointer-12) != nil {resources.release(pointer-12)}
                put(r,empty)
            }
            return 0
        case 0x4ffa56: // CRect::InflateRect(l, t, r, b).
            guard a.count == 4,r != 0,let p = heap.lookup(r,words:4) else {return nil}
            var rect = (0..<4).map{p[$0]}
            rect.withUnsafeMutableBufferPointer{claw_level_inflate_rect($0.baseAddress!,a[0],a[1],a[2],a[3])}
            for index in 0..<4 {p[index] = rect[index]}
            return 0
        case 0x4a5290: // CRT memmove.
            guard a.count == 3,a[2] <= 0x800000 else {return nil}
            if a[2] == 0 {return a[0]}
            guard a[0] != 0,a[1] != 0,let to = heap.lookupBytes(a[0],count:a[2]),let from = heap.lookupBytes(a[1],count:a[2]) else {return nil}
            memmove(to,from,Int(a[2]));return a[0]
        case 0x4b0d30,0x4b0d60,0x4b0d90:
            var value:UInt32 = 0
            guard a.count == 1,claw_level_ctype(q.function,a[0],&value) == 1 else {return nil}
            return value
        case 0x4f5133,0x4f5620,0x4f5249:
            guard a.count == 1,lists[r] == nil,let p = heap.lookupBytes(r,count:28) else {return nil}
            p.update(repeating:0,count:28)
            put(r,q.function == 0x4f5133 ? 0x51000c:q.function == 0x4f5249 ? 0x510224:0x5107bc)
            put(r+24,a[0]);lists[r] = [];return r
        case 0x4f51c5,0x4f572a:
            guard a.count == (q.function == 0x4f51c5 ? 1:2),let nodes = lists[r] else {return nil}
            let next = q.function == 0x4f51c5 ? 0:(a[0] == 0 ? w(r+4):a[0])
            guard (next == 0 || nodes.contains(next)),nodes.count == w(r+12) else {return nil}
            let previous = next == 0 ? w(r+8):w(next+4),node = resources.allocate(12)
            put(node,next);put(node+4,previous);put(node+8,a.last!)
            put(previous == 0 ? r+4:previous,node);put(next == 0 ? r+8:next+4,node)
            put(r+12,w(r+12)+1);lists[r]!.insert(node);return node
        case 0x4f5212:
            guard a.count == 1,lists[r]?.remove(a[0]) != nil else {return nil}
            let next = w(a[0]),previous = w(a[0]+4)
            put(previous == 0 ? r+4:previous,next);put(next == 0 ? r+8:next+4,previous)
            put(r+12,w(r+12)-1);resources.release(a[0]);return 0
        case 0x4f5172,0x4f565f,0x4f5192:
            guard a.isEmpty,let nodes = lists[r],nodes.count == w(r+12) else {return nil}
            for node in nodes {resources.release(node)}
            for offset:UInt32 in [4,8,12,16,20] {put(r+offset,0)}
            if q.function == 0x4f565f || q.function == 0x4f5192 {lists.removeValue(forKey:r);put(r,0x50becc)}
            else {lists[r] = []};return 0
        case 0x4a4a20:
            guard a.count == 3,let p = heap.lookupBytes(a[0],count:a[2]) else {return nil}
            p.update(repeating:UInt8(truncatingIfNeeded:a[1]),count:Int(a[2]));return a[0]
        case 0x4a4a80:
            guard a.count == 3,let p = heap.lookupBytes(a[0],count:a[2]),let s = heap.lookupBytes(a[1],count:a[2]) else {return nil}
            memmove(p,s,Int(a[2]));return a[0]
        case 0x4a3810:
            guard a.count == 2 else {return nil}
            let left = string(a[0]),right = string(a[1]);return left == right ? 0:left < right ? .max:1
        case 0x4f5e89:
            guard a.count == 1,maps[r] == nil else {return nil}
            _ = serviceMapConstructor(r,a[0])
            put(r,0x510264)
            return r
        case 0x4fcf35:
            guard a.isEmpty,let p = heap.lookupBytes(r,count:16) else {return nil}
            p.update(repeating:0,count:16)
            put(r,0x510444)
            return r
        case 0x4f5cbd,0x4f6118:
            guard a.count == 1,maps[r] == nil else {return nil}
            return serviceMapConstructor(r,a[0],pointerKeys:q.function == 0x4f6118)
        case 0x546a24,0x546df0:
            guard a.isEmpty,r == 0 else {return nil}
            yieldWindowEvents?()
            let value = clock()
            lastClock = value;observeClockRead?(resources.clockCaller,value)
            record(["service":q.function == 0x546a24 ? "GetTickCount":"timeGetTime","result":value]);return value
        case 0x4b0a70:
            guard a.count == 3,a[2] <= 65536,let output = heap.lookupBytes(a[0],count:a[2]) else {return nil}
            let bytes = Array(string(a[1]).utf8.prefix(Int(a[2])))
            output.update(repeating:0,count:Int(a[2]))
            bytes.withUnsafeBufferPointer{if let p = $0.baseAddress {output.update(from:p,count:$0.count)}}
            return a[0]
        case 0x4f6439:put(r,empty);return r
        case 0x4f6433:return 0x52e1cc
        case 0x4f65f2,0x4f66cc:
            // The original credits TXT is larger than the menu-name limit.
            guard a.count == 1 else {return nil};put(r,a[0] == 0 ? empty:cstring(string(a[0],maximumBytes:65537)));return r
        case 0x4f6449,0x4f667d:
            guard a.count == 1 else {return nil};put(r,cstring(string(w(a[0]))));return r
        case 0x4f684d:
            guard r == 0,a.count == 3 else {return nil}
            let left = a[1] == 0 ? "":string(a[1])
            put(a[0],cstring(left+string(w(a[2]))))
            return a[0]
        case 0x4f6920: // CString::operator+=(LPCTSTR), thiscall; returns this.
            guard a.count == 1 else {return nil}
            put(r,cstring(string(w(r))+(a[0] == 0 ? "":string(a[0]))));return r
        case 0x4f695c: // CString::operator+=(const CString&), thiscall; returns this.
            guard a.count == 1 else {return nil}
            put(r,cstring(string(w(r))+string(w(a[0]))));return r
        case 0x4f6974:
            guard a.count == 1,a[0] <= 0x100000 else {return nil}
            let current = w(r)
            guard current >= 12,w(current-8) <= w(current-4),w(current-4) <= 0x100000 else {return nil}
            let references = w(current-12)
            // An unshared buffer large enough is returned in place, as MFC does.
            if a[0] <= w(current-4),!(references > 1 && references < 0x80000000) {return current}
            let bytes = Array(string(current).utf8)
            let capacity = max(a[0],UInt32(bytes.count))
            guard capacity <= 0x100000 else {return nil}
            let block = resources.allocate(12+capacity+1)
            guard let p = heap.lookupBytes(block+12,count:capacity+1) else {return nil}
            strings.insert(block)
            put(block,1);put(block+4,UInt32(bytes.count));put(block+8,capacity)
            p.update(repeating:0,count:Int(capacity+1))
            bytes.withUnsafeBufferPointer{if let data = $0.baseAddress {p.update(from:data,count:$0.count)}}
            put(r,block+12)
            return block+12
        case 0x4f69c3:
            guard a.count == 1 else {return nil}
            let buffer = w(r)
            guard buffer >= 12 else {return nil}
            let length = a[0] == .max ? UInt32(string(buffer).utf8.count):a[0]
            guard length <= w(buffer-4),let end = heap.lookupBytes(buffer+length,count:1) else {return nil}
            put(buffer-8,length);end.pointee = 0
            return 0
        case 0x4f6584:put(r,empty);return 0
        case 0x4f6a1d:put(r,cstring(string(w(r)).lowercased()));return 0
        case 0x4f4c93:
            guard a.count == 1 else {return nil}
            let text = string(w(r)),needle = string(a[0])
            return text.range(of:needle).map{UInt32(text.distance(from:text.startIndex,to:$0.lowerBound))} ?? .max
        case 0x4f58ab,0x4f54ea,0x4f57c5:
            guard a.isEmpty,let p = heap.lookupBytes(r,count:20) else {return nil}
            p.update(repeating:0,count:20);put(r,q.function == 0x4f58ab ? 0x5108fc:q.function == 0x4f54ea ? 0x51079c:0x5108d4);return r
        case 0x4f58de,0x4f551d:
            _ = arraySize(r,0);put(r,0x50becc);return 0
        case 0x4f5915:
            guard a.count == 2 else {return nil};return arraySize(r,a[0],a[1])
        case 0x4f582f:
            guard a.count == 2,a[0] < 4096 else {return nil}
            if a[0] >= w(r+8) {_ = arraySize(r,a[0]+1)}
            put(w(r+4)+a[0]*4,a[1]);return 0
        case 0x4f55e9:
            // CPtrArray::RemoveAt(index,count): shift the tail down, shrink the size.
            guard a.count == 2 else {return nil}
            let size = w(r+8),data = w(r+4)
            guard a[0] <= size,a[1] <= size-a[0] else {return nil}
            let move = size-a[0]-a[1]
            for i in 0..<move {put(data+(a[0]+i)*4,w(data+(a[0]+a[1]+i)*4))}
            put(r+8,size-a[1]);return 0
        case 0x4f6286:
            guard a.count == 2,let map = maps[r] else {
                return nil
            }
            guard let cell = map[string(a[0])] else {return 0};put(a[1],w(cell));return 1
        case 0x4f62a8:
            guard a.count == 1,maps[r] != nil else {return nil}
            let key = string(a[0]);if let cell = maps[r]?[key] {return cell}
            let cell = resources.allocate(4);maps[r]![key] = cell;mapKeys[r,default:[]].append(key);put(r+12,UInt32(maps[r]!.count));return cell
        case 0x4f5db6:
            guard a.count == 1,maps[r] != nil else {return nil}
            let key = string(a[0]);guard let cell = maps[r]!.removeValue(forKey:key) else {return 0}
            resources.release(cell);mapKeys[r]?.removeAll{$0 == key};put(r+12,UInt32(maps[r]!.count));return 1
        case 0x4f5e1e:
            guard a.count == 3,let map = maps[r],let keys = mapKeys[r],!keys.isEmpty else {return nil}
            let index:Int
            if w(a[0]) == .max {index = 0}
            else {guard let position = keys.firstIndex(where:{map[$0] == w(a[0])}) else {return nil};index = position}
            let key = keys[index]
            put(a[0],index+1 < keys.count ? map[keys[index+1]]!:0)
            put(a[1],cstring(key));put(a[2],w(map[key]!));return 0
        case 0x4f61a1,0x4f61f3,0x4f5d00:
            guard let map = maps[r] else {return nil}
            for cell in map.values {resources.release(cell)}
            maps[r] = [:];mapKeys[r] = []
            for offset:UInt32 in [4,12,16,20] {put(r+offset,0)}
            if q.function != 0x4f61a1 {maps.removeValue(forKey:r);mapKeys.removeValue(forKey:r);put(r,0x50becc)}
            return 0
        case 0x4f2190: // CRT _access(path, mode): the paper fader's optional light-table file
            // (fader initializer, descriptor +0x24). The game names no such file on
            // the paper paths it uses (an empty CString); an empty path does not exist.
            guard a.count == 2,string(a[0]).isEmpty else {return nil}
            return .max
        case 0x4a3ce0:
            guard a.count == 1 else {return nil}
            let text = string(a[0]).trimmingCharacters(in:.whitespaces)
            let digits = text.prefix(while:{$0.isNumber || $0 == "-" || $0 == "+"})
            return UInt32(bitPattern:Int32(digits) ?? 0)
        case 0x4a3920,0x4f4f58:
            guard a.count >= 2 else {return nil}
            var values = Array(a.dropFirst(2))
            // Variadic calls declare only their fixed arguments (buffer or
            // CString, format); the rest are read from the caller's stack.
            if a.count == 2,formatArgumentCount(a[1]) != 0 {
                guard let count = formatArgumentCount(a[1]),count <= 8,q.stackPointer != 0 else {return nil}
                values = (0..<count).map{w(q.stackPointer+12+UInt32($0)*4)}
            }
            guard let text = format(a[1],values) else {return nil}
            if q.function == 0x4f4f58 {put(a[0],cstring(text));return 0}
            let bytes = Array(text.utf8)+[0]
            guard let p = heap.lookupBytes(a[0],count:UInt32(bytes.count)) else {return nil}
            bytes.withUnsafeBufferPointer{p.update(from:$0.baseAddress!,count:$0.count)};return UInt32(bytes.count-1)
        default:return nil
        }
    }
    private func serviceMapConstructor(_ receiver:UInt32,_ growth:UInt32,pointerKeys:Bool = false)->UInt32 {
        guard let p = heap.lookupBytes(receiver,count:28) else {return resources.fail(receiver)}
        p.update(repeating:0,count:28)
        put(receiver,pointerKeys ? 0x5105c4:0x510054);put(receiver+8,17);put(receiver+24,growth)
        maps[receiver] = [:];mapKeys[receiver] = []
        return receiver
    }
    private func diagnosticService(_ q:ClawCall,frame:UInt32)->UInt32? {
        guard let result = diagnostics.sharedService(q,frame:frame,bytes:{[unowned self] in self.heap.lookupBytes($0,count:$1)}) else {return nil}
        return diagnostics.fault == 0 ? result:resources.fail(diagnostics.faultAddress)
    }
    private func transport(_ function:UInt32,_ receiver:UInt32,_ arguments:[UInt32])->UInt32 {
        var q = ClawCall();q.function = function;q.receiver = receiver;q.argumentCount = UInt32(arguments.count)
        withUnsafeMutableBytes(of:&q.arguments){dst in arguments.withUnsafeBytes{dst.copyBytes(from:$0)}}
        return service(q) ?? resources.fail(function)
    }
    private func formatArgumentCount(_ token:UInt32)->Int? {
        let bytes = Array(string(token).utf8);var index = 0,count = 0
        while index < bytes.count {
            if bytes[index] != 37 {index += 1;continue}
            index += 1;guard index < bytes.count else {return nil}
            if bytes[index] == 37 {index += 1;continue}
            while index < bytes.count,bytes[index] >= 48,bytes[index] <= 57 {index += 1}
            guard index < bytes.count,[UInt8(115),100,105,117,120,88].contains(bytes[index]) else {return nil}
            count += 1;index += 1
        }
        return count
    }
    private func format(_ token:UInt32,_ arguments:[UInt32])->String? {
        let bytes = Array(string(token).utf8);var index = 0,argument = 0,output = ""
        while index < bytes.count {
            if bytes[index] != 37 {output.append(Character(UnicodeScalar(bytes[index])));index += 1;continue}
            index += 1;guard index < bytes.count else {return nil}
            if bytes[index] == 37 {output += "%";index += 1;continue}
            let begin = index
            while index < bytes.count,bytes[index] >= 48,bytes[index] <= 57 {index += 1}
            guard index < bytes.count,argument < arguments.count,index-begin <= 3 else {return nil}
            let value = arguments[argument];argument += 1
            switch bytes[index] {
            case 115:
                guard begin == index else {return nil};output += string(value)
            case 100,105,117,120,88:
                let spec = "%"+String(decoding:bytes[begin...index],as:UTF8.self)
                output += String(format:spec,value)
            default:return nil
            }
            index += 1;guard output.utf8.count <= 4096 else {return nil}
        }
        return argument == arguments.count ? output:nil
    }
}

// Native platform services for the original saved-game manager (0x49b840
// startup load, 0x49bbc0 write at a super checkpoint) on the app path: the
// Win32 directory queries and MFC CFile (Open, GetLength, Read, Write, Close,
// destructor), which are platform layer and replaced natively. The original
// keeps CLAW.USR in its current directory; here the game sees the fixed
// current directory C:\CLAW and every file C:\CLAW\<name> lives in a native
// folder (the app's data folder, or one a launch names). The game's own code
// builds the path, formats, ciphers and checks the records; this moves bytes.
final class ClawNativeSaveFiles {
    var directory:URL
    private(set) var reads = 0,writes = 0,opens:[[String:Any]] = []
    private var handles:[UInt32:FileHandle] = [:],nextHandle:UInt32 = 0x6b000000
    static let currentDirectory = Array("C:\\CLAW".utf8)
    init(directory:URL) {self.directory = directory}
    deinit {for handle in handles.values {try? handle.close()}}
    static let functions:Set<UInt32> = [0x546a28,0x546a2c,0x546a10,0x4f7448,0x4f774d,0x4f75f5,0x4f7570,0x4f75aa,0x4f766e,0x4f7369]

    /// nil: not this owner's call (another owner may serve it) or malformed (the caller faults).
    func service(_ function:UInt32,_ r:UInt32,_ a:[UInt32],heap:ClawTokenHeap)->UInt32? {
        guard Self.functions.contains(function) else {return nil}
        func bytes(_ token:UInt32,_ count:UInt32)->UnsafeMutablePointer<UInt8>? {heap.lookupBytes(token,count:count)}
        func text(_ token:UInt32)->[UInt8]? {
            var value:[UInt8] = []
            for offset:UInt32 in 0..<1024 {
                guard let byte = heap.lookupBytes(token &+ offset,count:1)?.pointee else {return nil}
                if byte == 0 {return value};value.append(byte)
            }
            return nil
        }
        func put(_ value:[UInt8],_ token:UInt32,capacity:UInt32)->UInt32? {
            // Directory queries: length without the terminator, or the size needed.
            guard UInt32(value.count) < capacity else {return UInt32(value.count+1)}
            guard let out = bytes(token,UInt32(value.count+1)) else {return nil}
            for (i,b) in (value+[0]).enumerated() {out[i] = b};return UInt32(value.count)
        }
        // CFile: +0 vtable 0x510844, +4 m_hFile (-1 when closed), +8 m_bCloseOnDelete, +12 m_strFileName.
        let file = heap.lookup(r,words:4)
        func open()->FileHandle? {file.flatMap {$0[0] == 0x510844 ? handles[$0[1]]:nil}}
        func close() throws {
            guard let file,let handle = handles.removeValue(forKey:file[1]) else {return}
            file[1] = .max;file[2] = 0;try handle.close()
        }
        do {
            switch function {
            case 0x546a28:guard a.count == 2 else {return nil};return put(Self.currentDirectory,a[1],capacity:a[0])
            case 0x546a10:guard a.count == 2 else {return nil};return put(Array("C:\\WINDOWS".utf8),a[0],capacity:a[1])
            case 0x546a2c:guard a.count == 1 else {return nil};return 3 // DRIVE_FIXED: saves stay in C:\CLAW.
            case 0x4f7448:
                // Open(name, flags, CFileException*): FALSE when the file cannot be opened.
                guard a.count == 3,let file,file[0] == 0x510844,file[1] == .max,let raw = text(a[0]) else {return nil}
                let flags = a[1],name = String(decoding:raw,as:UTF8.self).uppercased(),prefix = "C:\\CLAW\\"
                guard flags & ~UInt32(0x3073) == 0,flags & 3 != 3 else {return nil} // access, share, create, no-truncate
                let leaf = String(name.dropFirst(prefix.count))
                guard name.hasPrefix(prefix),!leaf.isEmpty,!leaf.contains("\\"),!leaf.contains("/"),leaf != ".",leaf != ".." else {return 0}
                let url = directory.appendingPathComponent(leaf),exists = FileManager.default.fileExists(atPath:url.path)
                if flags & 0x1000 != 0 {
                    try FileManager.default.createDirectory(at:directory,withIntermediateDirectories:true)
                    if flags & 0x2000 == 0 || !exists {try Data().write(to:url)}
                } else if !exists {return 0}
                let access = flags & 3
                let handle = access == 2 ? try FileHandle(forUpdating:url):access == 1 ? try FileHandle(forWritingTo:url):try FileHandle(forReadingFrom:url)
                nextHandle &+= 1;handles[nextHandle] = handle;file[1] = nextHandle;file[2] = 1
                opens.append(["file":leaf,"flags":flags]);return 1
            case 0x4f774d:
                guard a.isEmpty,let handle = open() else {return nil}
                let position = try handle.offset(),end = try handle.seekToEnd();try handle.seek(toOffset:position)
                guard end < UInt64(Int32.max) else {return nil};return UInt32(end)
            case 0x4f75f5: // CFile::Seek(offset, origin), signed low-word distance.
                guard a.count == 2,a[1] <= 2,let handle = open() else {return nil}
                let previous = try handle.offset()
                let base:UInt64
                if a[1] == 2 {
                    base = try handle.seekToEnd();try handle.seek(toOffset:previous)
                } else {base = a[1] == 0 ? 0:previous}
                guard base <= UInt64(Int64.max)-UInt64(Int32.max) else {return nil}
                let position = Int64(base)+Int64(Int32(bitPattern:a[0]))
                guard position >= 0,position < Int64(UInt32.max) else {return nil}
                try handle.seek(toOffset:UInt64(position));return UInt32(position)
            case 0x4f7570,0x4f75aa:
                guard a.count == 2,let handle = open() else {return nil}
                if a[1] == 0 {return 0}
                guard a[1] < 0x1000000,let span = bytes(a[0],a[1]) else {return nil}
                if function == 0x4f75aa {
                    try handle.write(contentsOf:Data(bytes:span,count:Int(a[1])));writes += 1;return 0
                }
                let data = try handle.read(upToCount:Int(a[1])) ?? Data()
                data.withUnsafeBytes {if let base = $0.baseAddress {UnsafeMutableRawPointer(span).copyMemory(from:base,byteCount:$0.count)}}
                reads += 1;return UInt32(data.count)
            case 0x4f766e:
                guard a.isEmpty,open() != nil else {return nil};try close();return 0
            case 0x4f7369:
                // Destructor: closes a file still open (m_bCloseOnDelete), as MFC does.
                guard a.isEmpty,let file,open() != nil,file[2] == 1,file[3] == 0x52e1c4 else {return nil}
                try close();return 0
            default:return nil
            }
        } catch {
            // A failed physical read or write is the CFileException the game never handles: fault.
            return nil
        }
    }
}

/// Native storage for the original's registry settings: the values startup
/// reads (0x425827..0x425ad9, 0x4265ff..0x4267a6) and teardown writes
/// (0x42698f..0x426ad6) under HKEY_LOCAL_MACHINE\Software\Monolith
/// Productions\Claw\1.0, plus the in-game layout write (0x46bbc0). Values keep
/// the original names, types (REG_DWORD 4, REG_SZ 1) and bytes; the admitted
/// configuration bodies keep every default, type check and decision. A store
/// without a file keeps nothing, so a launch without a settings folder is
/// always the original's fresh install.
final class ClawNativeSettingsStore {
    struct Value {let type:UInt32;let bytes:[UInt8]}
    var file:URL?
    private(set) var keys:[String:[String:Value]] = [:]
    private var handles:[UInt32:String] = [:]
    private var nextHandle:UInt32 = 0x7a000000
    private(set) var events:[[String:Any]] = []
    private(set) var writeFailure:String?
    init(directory:URL?) {
        file = directory?.appendingPathComponent("registry.json")
        guard let file,let data = try? Data(contentsOf:file),
              let root = try? JSONSerialization.jsonObject(with:data) as? [String:[String:[String:Any]]] else {return}
        for (path,values) in root {
            var key:[String:Value] = [:]
            for (name,value) in values {
                guard let type = value["type"] as? Int,let hex = value["hex"] as? String,hex.count % 2 == 0 else {continue}
                var bytes:[UInt8] = [];var index = hex.startIndex
                while index < hex.endIndex {
                    let end = hex.index(index,offsetBy:2)
                    guard let byte = UInt8(hex[index..<end],radix:16) else {bytes = [];break}
                    bytes.append(byte);index = end
                }
                key[name] = Value(type:UInt32(type),bytes:bytes)
            }
            keys[path] = key
        }
    }
    static let root = "HKEY_LOCAL_MACHINE\\Software\\Monolith Productions\\Claw\\1.0"
    /// The game's value under the main key (for evidence only).
    func dword(_ name:String)->UInt32? {
        guard let value = keys[Self.root]?[name],value.type == 4,value.bytes.count == 4 else {return nil}
        return value.bytes.withUnsafeBytes{$0.loadUnaligned(as:UInt32.self)}
    }
    func text(_ name:String)->String? {
        guard let value = keys[Self.root]?[name],value.type == 1 else {return nil}
        return String(decoding:value.bytes.prefix{$0 != 0},as:UTF8.self)
    }
    private func save() {
        guard let file else {return}
        var root:[String:[String:[String:Any]]] = [:]
        for (path,values) in keys {
            root[path] = values.mapValues {["type":Int($0.type),"hex":$0.bytes.map{String(format:"%02x",$0)}.joined()]}
        }
        do {
            try FileManager.default.createDirectory(at:file.deletingLastPathComponent(),withIntermediateDirectories:true)
            try JSONSerialization.data(withJSONObject:root,options:[.prettyPrinted,.sortedKeys]).write(to:file,options:.atomic)
        } catch {writeFailure = String(describing:error)}
    }
    /// ADVAPI32 registry services the configuration bodies import: RegCreateKeyExA
    /// 0x546834, RegQueryValueExA 0x54682c, RegSetValueExA 0x546824,
    /// RegDeleteValueA 0x546820 and RegCloseKey 0x546830. Statuses are the
    /// Win32 ones: 0 success, 2 not found, 6 invalid handle, 234 more data.
    func service(_ function:UInt32,_ a:[UInt32],heap:ClawTokenHeap)->UInt32? {
        func text(_ token:UInt32)->String? {
            var bytes:[UInt8] = []
            for offset:UInt32 in 0..<1024 {
                guard let p = heap.lookupBytes(token+offset,count:1) else {return nil}
                if p.pointee == 0 {return String(decoding:bytes,as:UTF8.self)}
                bytes.append(p.pointee)
            }
            return nil
        }
        func put(_ token:UInt32,_ value:UInt32)->Bool {
            guard let p = heap.lookupBytes(token,count:4) else {return false}
            var v = value;withUnsafeBytes(of:&v){p.update(from:$0.baseAddress!.assumingMemoryBound(to:UInt8.self),count:4)}
            return true
        }
        func path(_ handle:UInt32)->String? {handle == 0x80000002 ? "HKEY_LOCAL_MACHINE":handles[handle]}
        switch function {
        case 0x546834:
            guard a.count == 9,let parent = path(a[0]),let name = text(a[1]) else {return nil}
            let full = name.isEmpty ? parent:parent+"\\"+name
            let existing = keys[full] != nil || keys.keys.contains{$0.hasPrefix(full+"\\")}
            if keys[full] == nil {keys[full] = [:]}
            let handle = nextHandle;nextHandle &+= 4;handles[handle] = full
            guard put(a[7],handle) else {return nil}
            if a[8] != 0,!put(a[8],existing ? 2:1) {return nil}
            events.append(["call":"RegCreateKeyExA","key":full,"disposition":existing ? 2:1])
            return 0
        case 0x54682c:
            guard a.count == 6,let key = handles[a[0]],let name = text(a[1]) else {return a.count == 6 ? 6:nil}
            guard let value = keys[key]?[name] else {
                events.append(["call":"RegQueryValueExA","name":name,"result":2]);return 2
            }
            if a[3] != 0,!put(a[3],value.type) {return nil}
            var status:UInt32 = 0
            if a[5] != 0 {
                guard let length = heap.lookupBytes(a[5],count:4) else {return nil}
                let capacity = UnsafeRawPointer(length).loadUnaligned(as:UInt32.self)
                if a[4] != 0 {
                    if value.bytes.count > Int(capacity) {status = 234}
                    else if !value.bytes.isEmpty {
                        guard let data = heap.lookupBytes(a[4],count:UInt32(value.bytes.count)) else {return nil}
                        value.bytes.withUnsafeBufferPointer{data.update(from:$0.baseAddress!,count:$0.count)}
                    }
                }
                guard put(a[5],UInt32(value.bytes.count)) else {return nil}
            }
            events.append(["call":"RegQueryValueExA","name":name,"type":value.type,"bytes":value.bytes.count,"result":status])
            return status
        case 0x546824:
            guard a.count == 6,let key = handles[a[0]],let name = text(a[1]) else {return a.count == 6 ? 6:nil}
            var bytes:[UInt8] = []
            if a[5] != 0 {
                guard let data = heap.lookupBytes(a[4],count:a[5]) else {return nil}
                bytes = Array(UnsafeBufferPointer(start:data,count:Int(a[5])))
            }
            keys[key,default:[:]][name] = Value(type:a[3],bytes:bytes)
            events.append(["call":"RegSetValueExA","name":name,"type":a[3],"value":a[3] == 4 && bytes.count == 4 ? Int(bytes.withUnsafeBytes{$0.loadUnaligned(as:UInt32.self)}):String(decoding:bytes.prefix{$0 != 0},as:UTF8.self)])
            save();return 0
        case 0x546820:
            guard a.count == 2,let key = handles[a[0]],let name = text(a[1]) else {return a.count == 2 ? 6:nil}
            let removed = keys[key]?.removeValue(forKey:name) != nil
            events.append(["call":"RegDeleteValueA","name":name,"result":removed ? 0:2])
            if removed {save()}
            return removed ? 0:2
        case 0x546830:
            guard a.count == 1 else {return nil}
            return handles.removeValue(forKey:a[0]) != nil ? 0:6
        default:return nil
        }
    }
}

// Custom checkpoints never write the original profile/checkpoint records.
extension ClawNativeMenuInterface {
    private func customCalendarTime() -> UInt32 { UInt32(truncatingIfNeeded:Int(Date().timeIntervalSince1970)) }
    var customCheckpointURL: URL? {
        guard let directory = saveDirectory else {return nil}
        let folder = directory.appendingPathComponent("ManualSuperCheckpoints")
        var state = w(base.applicationToken+0x2c)
        if w(state) == 0x50c044 {state = resources.invoke(0x42bfd0,base.applicationToken)}
        if w(state) == 0x50c264 {
            let key = customWorld.map { SHA256.hash(data:$0.data).map{String(format:"%02x",$0)}.joined() }
                ?? "retail-\(w(state+0x14))"
            return folder.appendingPathComponent(key+".clawcheckpoint")
        }
        // The menu resumes the most recently saved level after relaunch.
        let files = (try? FileManager.default.contentsOfDirectory(at:folder,includingPropertiesForKeys:[.contentModificationDateKey])) ?? []
        return files.filter{$0.pathExtension == "clawcheckpoint"}.max {
            ((try? $0.resourceValues(forKeys:[.contentModificationDateKey]).contentModificationDate) ?? .distantPast) <
            ((try? $1.resourceValues(forKeys:[.contentModificationDateKey]).contentModificationDate) ?? .distantPast)
        } ?? directory.appendingPathComponent("custom-checkpoint.clawcheckpoint")
    }
    private var customCheckpointSource: URL? {
        guard let url = customCheckpointURL else {return nil}
        return FileManager.default.fileExists(atPath:url.path) ? url :
            saveDirectory?.appendingPathComponent("custom-checkpoint.clawcheckpoint")
    }
    var customCheckpointDates: [Date] {
        guard let url = customCheckpointSource else {return []}
        return (try? ClawCustomCheckpoint.slotDates(url)) ?? []
    }
    var hasCustomCheckpoint: Bool {customCheckpointSource.map{FileManager.default.fileExists(atPath:$0.path)} ?? false}
    var canSaveCustomCheckpoint: Bool {
        let state = w(base.applicationToken+0x2c), actor = w(0x537e88)
        return loaded && !closed && state != 0 && w(state) == 0x50c264 && actor != 0
            && w(state+0x38) == 0 && w(actor+0x10c) > 0
            && !controlsActive && !playersActive && !customLevelsActive && resources.fault == 0 && customCheckpointURL != nil
    }
    private var scoreHUD: UInt32? {
        let scene = w(w(0x537e88)+0xc)
        return heap.debugAllocationBases.first { token in
            heap.containingAllocationIdentity(at:token,count:0x1b4) != nil &&
            [UInt32(0x513770),0x5137f0].contains(w(token)) && w(token+0xc) == scene &&
            w(w(token+0x6c)+0x10) == 0x4908b0
        }
    }
    func checkpointStats() -> [String:Any] {
        let actor = w(0x537e88), inventory = w(w(actor+0x6c)+0x14)
        let plane = w(w(w(actor+0xc)+0x24)+0x5c)
        return ["level":w(w(base.applicationToken+0x2c)+0x14),"x":w(actor+0x4c),"y":w(actor+0x50),
            "facing":w(actor+0x40)&2,"health":w(actor+0x10c),"score":w(actor+0xf8),
            "lives":w(inventory+0x7c),"lives_lost":w(inventory+0x80),"weapon":w(inventory+0x30),
            "ammo":[w(inventory+0x70),w(inventory+0x74),w(inventory+0x78)],
            "treasure":(0..<10).map {w(inventory+0x88+UInt32($0*4))},
            "power_kind":w(0x534eac),"power_ms":w(0x534ea8),"elapsed_ms":w(0x537210),
            "extra_life_threshold":w(inventory+0xec),"hud_extra_life_threshold":scoreHUD.map{w($0+0xfc)} ?? 0,
            "removed_count":resources.removedPlacements.count,
            "clock_words":[UInt32(0x537208),0x53720c,0x537210,0x5430c4,0x5430c8].map {w($0)},
            "camera_rect":(0..<4).map{w(plane+0x40+UInt32($0*4))}]
    }
    func placeCheckpointEnemyCheck(_ id: UInt32 = 1490) throws {
        guard let row = resources.checkpointPlacementEvidence.first(where:{$0["id"] as? UInt32 == id && $0["live"] as? Bool == true}),
              let x = row["x"] as? UInt32,let y = row["y"] as? UInt32 else {throw ClawCustomCheckpoint.Failure.unavailable}
        let actor = w(0x537e88), inventory = w(w(actor+0x6c)+0x14)
        put(actor+0x4c,x-70);put(actor+0x50,y-10)
        _ = resources.invoke(0x418120,0,[actor,w(actor+0x6c),inventory])
    }
    func placeCheckpointMechanismCheck(_ id: UInt32) throws {
        guard ProcessInfo.processInfo.arguments.contains("--custom-checkpoint-check"),
              let row = resources.checkpointPlacementEvidence.first(where:{$0["id"] as? UInt32 == id && $0["live"] as? Bool == true}),
              let x = row["x"] as? UInt32,let y = row["y"] as? UInt32 else {throw ClawCustomCheckpoint.Failure.unavailable}
        let player = w(0x537e88)
        if row["logic"] as? String == "BossStager" {
            put(player+0x4c,x > 24 ? x-24 : 0);put(player+0x50,y > 40 ? y-40 : 0)
            put(player+0x14c,0)
            if let velocity = heap.lookupBytes(0x534de8,count:8) {velocity.update(repeating:0,count:8)}
            _ = resources.invoke(0x418120,0,[player,w(player+0x6c),w(w(player+0x6c)+0x14)])
            customLevelEvidence["mechanism_position_fixture"] = ["id":id,"label":"position fixture before real boss staging contact; requires delivered movement"]
            return
        }
        // Claw's movement rectangle reaches 60 pixels below its origin;
        // starting only 64 pixels above a platform overlaps its top edge.
        put(player+0x4c,x);put(player+0x50,y > 120 ? y-120 : 0)
        put(player+0x14c,0)
        if let velocity = heap.lookupBytes(0x534de8,count:8) {velocity.update(repeating:0,count:8)}
        customLevelEvidence["mechanism_position_fixture"] = ["id":id,"x":x,"y":y,
            "label":"position fixture; activation still requires delivered movement"]
    }
    func placeCheckpointDropCheck() throws {
        guard let loot = resources.checkpointLoot.first else {throw ClawCustomCheckpoint.Failure.unavailable}
        let player = w(0x537e88)
        put(player+0x4c,loot.actor[1] > 32 ? loot.actor[1]-32 : 0)
        put(player+0x50,loot.actor[2] > 45 ? loot.actor[2]-45 : 0)
        customLevelEvidence["drop_position_fixture"] = "position fixture beside remaining native drop; collection requires delivered movement"
    }
    func placeCheckpointLootCheck() throws {
        let actor = w(0x537e88), x = Int(w(actor+0x4c)), y = Int(w(actor+0x50))
        let world: ClawWorld
        if let customWorld {world = customWorld.world}
        else {
            guard let root = Bundle.main.resourceURL else {throw ClawCustomCheckpoint.Failure.unavailable}
            world = try ClawWorld(data:Data(contentsOf:root.appendingPathComponent("GameData/LEVEL\(w(w(base.applicationToken+0x2c)+0x14))/WORLDS/WORLD.WWD")))
        }
        let removed = Set(resources.removedPlacements.map(\.id))
        guard let object = world.planes.flatMap(\.objects)
            .filter({$0.logic == "TreasurePowerup" && !removed.contains(UInt32(bitPattern:Int32($0.id)))})
            .min(by:{abs($0.x-x)+abs($0.y-y) < abs($1.x-x)+abs($1.y-y)}) else {throw ClawCustomCheckpoint.Failure.unavailable}
        put(actor+0x4c,UInt32(max(0,object.x-16)));put(actor+0x50,UInt32(max(0,object.y)))
        customLevelEvidence["manual_checkpoint_loot_fixture"] = ["id":object.id,"x":object.x,"y":object.y,
            "fixture":"position only; original pickup requires a real frame and collision"]
    }
    func prepareCheckpointScoreCheck() {
        let actor = w(0x537e88), inventory = w(w(actor+0x6c)+0x14)
        let threshold = scoreHUD.map{w($0+0xfc)} ?? w(inventory+0xec)
        let score = threshold > 0 ? threshold-1:0
        put(actor+0xf8,score);put(inventory+0x44,score);put(inventory+0x7c,3)
    }
    func spawnCheckpointLootCheck(item: UInt32 = 33) throws {
        try resources.spawnCheckpointLootFixture(state:w(base.applicationToken+0x2c),item:item)
        customLevelEvidence["spawned_loot_fixture"] = "labelled native pickup factory setup; collection requires real input"
    }
    func saveCustomCheckpoint() throws {
        guard canSaveCustomCheckpoint, let url = customCheckpointURL else { throw ClawCustomCheckpoint.Failure.unavailable }
        let state = w(base.applicationToken+0x2c), actor = w(0x537e88), inventory = w(w(actor+0x6c)+0x14)
        let digest = customWorld.map {SHA256.hash(data:$0.data).map{String(format:"%02x",$0)}.joined()}
        let saved = ClawCustomCheckpoint(level:w(state+0x14),customPath:customCheckpointWorldURL?.path,
            mapSHA256:digest,values:crazyValues(),facing:w(actor+0x40)&2,weapon:w(inventory+0x30),
            removedPlacements:resources.removedPlacements,extraLifeThreshold:w(inventory+0xec),
            hudExtraLifeThreshold:scoreHUD.map{w($0+0xfc)},livesLost:w(inventory+0x80),
            treasure:(0..<10).map{w(inventory+0x88+UInt32($0*4))},
            totalTreasure:(0..<10).map{w(inventory+0xb0+UInt32($0*4))},
            powerKind:w(0x534eac),powerMilliseconds:w(0x534ea8),mechanisms:resources.checkpointMechanisms,loot:resources.checkpointLoot,
            progressLimits:resources.checkpointProgressLimits + (customLua == nil ? [] : ["Lua globals and script-owned controller progress restart"]),
            bossStage:resources.checkpointBossStage,framePhase:checkpointFramePhase?())
        try saved.push(url)
        customCheckpointMessage = (saved.progressLimits ?? []).isEmpty ? "Custom checkpoint saved" : "Custom checkpoint saved; some event progress will restart"
        customCheckpointEvents.append(checkpointStats().merging(["action":"save","progress_limits":saved.progressLimits ?? []]) {_,new in new})
    }
    func restoreCustomCheckpoint(from selectedURL: URL? = nil, slot: Int = 0) throws {
        guard loaded, !closed, !controlsActive, !playersActive, !customLevelsActive,
              let url = selectedURL ?? customCheckpointURL else {throw ClawCustomCheckpoint.Failure.unavailable}
        // Decode and validate before touching the running game.
        let source = FileManager.default.fileExists(atPath:url.path) ? url :
            saveDirectory!.appendingPathComponent("custom-checkpoint.clawcheckpoint")
        let saved = try ClawCustomCheckpoint.read(source,slot:slot)
        pendingCustomCheckpoint = saved
        defer {pendingCustomCheckpoint = nil}
        let app = base.applicationToken
        if w(w(app+0x2c)) == 0x50c044 {
            // The original Resume command destroys the pause surfaces and
            // returns to the suspended gameplay state before a level reload.
            _ = resources.invoke(0x426e30,app,[0,0x8036,0])
            guard w(w(app+0x2c)) == 0x50c264,resources.fault == 0 else {throw ClawCustomCheckpoint.Failure.loadFailed}
        }
        if let path = saved.customPath {
            // New Game is handled by the menu state, not the running world.
            // Return through the original menu lifecycle before remounting
            // the map and rebuilding its Lua, assets and placed objects.
            restoringCustomMenu = true
            defer {restoringCustomMenu = false}
            _ = resources.invoke(0x426e30,app,[0,0x8023,0])
            guard resources.fault == 0,menuLive else {throw ClawCustomCheckpoint.Failure.loadFailed}
            // The menu has freed the old world's dialog actors. A new map
            // can request NPC speech before its dialog actor's first tick;
            // do not publish an expired controller into that initialization.
            for slot:UInt32 in [0x53c9a4,0x53c9ac] {
                let actor = w(slot)
                if actor != 0,heap.containingAllocationIdentity(at:actor,count:0x1b4) == nil {put(slot,0)}
            }
            try startCustomLevel(URL(fileURLWithPath:path))
        } else {
            retireCustomSession()
            put(app+0xa8,0)
            guard resources.invoke(0x428c40,app,[3,saved.level,0,0]) != 0 else {throw ClawCustomCheckpoint.Failure.loadFailed}
        }
        guard resources.fault == 0,pendingCustomCheckpoint == nil else {throw ClawCustomCheckpoint.Failure.loadFailed}
        if ProcessInfo.processInfo.arguments.contains("--custom-checkpoint-check") {
            checkpointInitialPlacements = resources.checkpointPlacementEvidence
        }
        let actor = w(0x537e88), inventory = w(w(actor+0x6c)+0x14)
        // Initialize the original score HUD before restoring its private next
        // award field. Updating only inventory+ec leaves HUD+fc at 1,000,000.
        if let hud = scoreHUD {
            if w(w(hud+0x6c)+0x1c) == 0 {_ = resources.invoke(0x4908b0,0,[hud])}
            if let threshold = saved.hudExtraLifeThreshold {put(hud+0xfc,threshold)}
        }
        if let kind = saved.powerKind,kind != 0 {
            let scene = w(actor+0xc)
            guard let speech = heap.debugAllocationBases.first(where: { token in
                heap.containingAllocationIdentity(at:token,count:0x1b4) != nil &&
                [UInt32(0x513770),0x5137f0].contains(w(token)) && w(token+0xc) == scene &&
                w(w(token+0x6c)+0x10) == 0x48c630
            }) else {throw ClawCustomCheckpoint.Failure.loadFailed}
            if w(w(speech+0x6c)+0x1c) == 0 {_ = resources.invoke(0x48c630,0,[speech])}
            _ = resources.invoke(0x41f990,0,[actor,0,inventory,kind,saved.powerMilliseconds ?? 0])
        }
        try resources.restoreCheckpointMechanisms(saved.mechanisms ?? [])
        try resources.restoreCheckpointLoot(saved.loot ?? [],state:w(app+0x2c))
        if let stage = saved.bossStage {
            try resources.restoreCheckpointBossStage(stage,state:w(app+0x2c))
            // A live boss restarts through its fresh native constructor. That
            // constructor can settle its spawn position before binding the
            // meter. This is the initialized spawn baseline, not saved AI state.
            if let boss = stage.boss,ProcessInfo.processInfo.arguments.contains("--custom-checkpoint-check"),
               let row = resources.checkpointPlacementEvidence.first(where:{$0["plane"] as? UInt32 == boss.plane && $0["id"] as? UInt32 == boss.id}) {
                checkpointInitialPlacements.removeAll {$0["plane"] as? UInt32 == boss.plane && $0["id"] as? UInt32 == boss.id}
                checkpointInitialPlacements.append(row)
            }
        }
        guard resources.fault == 0 else {throw ClawCustomCheckpoint.Failure.loadFailed}
        // Loading polls timers synchronously. Resume both delta baselines at
        // the same current sample, excluding construction from simulated time.
        let now = clock();lastClock = now
        put(0x541328,now);put(0x54132c,0);put(0x541330,0)
        put(0x537208,now);put(0x5430c8,now)
        if let phase = saved.framePhase {restoreCheckpointFramePhase?(phase)}
        customCheckpointMessage = (saved.progressLimits ?? []).isEmpty ? "Custom checkpoint restored" : "Custom checkpoint restored; some event progress restarted"
        customCheckpointEvents.append(checkpointStats().merging(["action":"restore","progress_limits":saved.progressLimits ?? []]) {_,new in new})
    }
    private func finishCustomCheckpointLoad(state: UInt32) {
        guard let saved = pendingCustomCheckpoint, saved.level == w(state+0x14) else {return}
        pendingCustomCheckpoint = nil
        // State entry may request player speech before the new controller's
        // first tick. The retired scene's controller tokens are invalid here.
        for slot:UInt32 in [0x53c9a4,0x53c9ac,0x53c9b0,0x53c9a0,0x53c9a8] {put(slot,0)}
        resources.removePlacements(saved.removedPlacements ?? [])
        // A manual snapshot owns each flag's progress independently. It is
        // not a load from the original super checkpoint slot.
        applySuperCheckpoint(saved.values,state:state,retireLoadedFlag:false)
        let actor = w(0x537e88), inventory = w(w(actor+0x6c)+0x14)
        // Keep private facing, collision rectangles and rendered facing aligned.
        _ = resources.invoke(saved.facing == 0 ? 0x418120:0x418080,0,[actor,w(actor+0x6c),inventory])
        put(inventory+0x30,saved.weapon)
        if let threshold = saved.extraLifeThreshold {put(inventory+0xec,threshold)}
        if let lost = saved.livesLost {put(inventory+0x80,lost)}
        for (i,value) in (saved.treasure ?? []).enumerated() {put(inventory+0x88+UInt32(i*4),value)}
        for (i,value) in (saved.totalTreasure ?? []).enumerated() {put(inventory+0xb0+UInt32(i*4),value)}
    }
}

extension ClawNativeMenuInterface {
    private func paletteRGB() throws -> Data {
        let backend = w(w(customPaletteState+0x2c)+0x10),data = w(backend+0x10)
        guard customPaletteState != 0,let p = heap.lookupBytes(data,count:1024) else {throw AssetError.invalid("Custom palette backend unavailable")}
        var rgb = Data();for i in 0..<256 {rgb.append(contentsOf:UnsafeBufferPointer(start:p+i*4,count:3))};return rgb
    }
    private func renderCustomPalette(_ rgb:Data) throws {
        let backend = w(w(customPaletteState+0x2c)+0x10),data = w(backend+0x10)
        guard rgb.count == 768,let p = heap.lookupBytes(data,count:1024) else {throw AssetError.invalid("Custom palette backend unavailable")}
        for i in 0..<256 {for c in 0..<3 {p[i*4+c] = rgb[i*3+c]}}
        guard base.palette?.renderRGB(rgb) == true else {throw AssetError.invalid("Custom palette render failed")}
        let digest = SHA256.hash(data:rgb).map {String(format:"%02x",$0)}.joined()
        var events = customLevelEvidence["palette_events"] as? [[String:Any]] ?? []
        let sequence = (events.last?["sequence"] as? Int ?? 0)+1
        events.append(["sequence":sequence,"sha256":digest,"first_palette":rgb == customPaletteFirst])
        customLevelEvidence["palette_events"] = Array(events.suffix(64))
    }
    private func installCustomPalettes(_ state:UInt32) throws {
        customPaletteState = state
        customPaletteFirst = try paletteRGB()
        if let override = customPalettes?.main {
            let count = (customPalettes?.mainColorCount ?? 256)*3
            customPaletteFirst.replaceSubrange(0..<count,with:override.prefix(count))
            let main = customPaletteFirst
            guard let p = heap.lookupBytes(state+0x360,count:1024) else {throw AssetError.invalid("Level palette storage unavailable")}
            for i in 0..<256 {for c in 0..<3 {p[i*4+c] = main[i*3+c]}}
            try renderCustomPalette(main)
        }
        customPalettePending = try paletteRGB()
        for (name,data) in customPalettes?.tables ?? [:] {try installCustomTable(name,data)}
        // Retain hashes of actual renderer inputs, not screenshot judgments.
        customLevelEvidence["palettes"] = ["first_rgb":Array(customPaletteFirst),"tables":customPaletteTables.keys.sorted(),"installed":true]
    }
    private func installCustomTable(_ name:String,_ data:Data) throws {
        let name = name.uppercased()
        let table:UInt32
        if name == "LIGHT" || name == "AVERAGE" {table = w(customPaletteState+(name == "LIGHT" ? 0x768:0x76c))}
        else if let existing = customPaletteTables[name] {table = existing}
        else {
            table = resources.allocate(16);let bytes = resources.allocate(65536)
            customPaletteAllocations += [bytes,table];put(table,1);put(table+4,65536);put(table+8,bytes);put(table+12,0)
        }
        guard table != 0,data.count == 65536,let p = heap.lookupBytes(w(table+8),count:65536) else {throw AssetError.invalid("Color lookup table unavailable: \(name)")}
        data.copyBytes(to:p,count:65536);customPaletteTables[name] = table
    }
    private func paletteService(_ key:String,_ value:Double) throws -> Double {
        let p = key.split(separator:":",omittingEmptySubsequences:false).map(String.init)
        guard p.count >= 2,customPaletteState != 0 else {throw AssetError.invalid("No active palette session")}
        switch p[1] {
        case "Read":
            guard p.count == 4,let i = Int(p[3]),(0..<256).contains(i) else {throw AssetError.invalid("Palette index")}
            let rgb = p[2] == "First" ? customPaletteFirst:p[2] == "Loaded" ? customPaletteLoaded:try paletteRGB()
            guard rgb.count == 768 else {throw AssetError.invalid("Palette not loaded")}
            return Double(Int(rgb[i*3])*65536+Int(rgb[i*3+1])*256+Int(rgb[i*3+2]))
        case "Write":
            guard p.count == 3,let i = Int(p[2]),(0..<256).contains(i),value.isFinite,value >= 0,value <= 16777215 else {throw AssetError.invalid("Palette color")}
            let v = Int(value);for c in 0..<3 {customPalettePending[i*3+c] = UInt8((v >> ((2-c)*8))&255)};return 0
        case "Commit":try renderCustomPalette(customPalettePending);return 0
        case "Load":
            let name = p.dropFirst(2).joined(separator:":")
            guard let data = try customAssets?.data("PALETTES/"+name) else {throw AssetError.invalid("Missing palette: \(name)")}
            customPaletteLoaded = try ClawCustomPalette.decode(data,name:name);return 0
        case "LoadCLT":
            guard p.count == 4,let data = try customAssets?.data("PALETTES/"+p[3]) else {throw AssetError.invalid("Missing CLT file")}
            let name = p[2].isEmpty ? URL(fileURLWithPath:p[3]).deletingPathExtension().lastPathComponent:p[2]
            try installCustomTable(name,ClawCustomPalette.decodeTable(data));return 0
        case "Image":
            let clt = p.count > 3 && p[2] == "CLT", at = clt ? 4:3
            guard p.count > at+1 else {throw AssetError.invalid("Invalid image operation")}
            if !clt {
                guard value.isFinite,value.rounded(.towardZero) == value,
                      p[2] == "Color" ? (0...255).contains(value):p[2] == "Flag" && [1.0,2,3,5,6,7,8].contains(value) else {throw AssetError.invalid("Invalid image flag or color")}
            }
            let image:UInt32
            if p[at] == "Token" {image = UInt32(p[at+1]) ?? 0}
            else {
                let key = resources.textToken(p.dropFirst(at+1).joined(separator:":"));defer {resources.release(key)}
                image = customRegistryValue(w(base.sceneToken+16),key)
            }
            guard image != 0,let group = heap.lookup(image,words:7),group[6] <= 100000,
                  let frames = heap.lookup(group[5],words:group[6]) else {throw AssetError.invalid("Image set unavailable")}
            let table = clt ? customPaletteTables[p[3]] ?? w(customPaletteState+(p[3] == "LIGHT" ? 0x768:p[3] == "AVERAGE" ? 0x76c:0)):0
            if clt && !["LIGHT","AVERAGE"].contains(p[3]) && customPaletteTables[p[3]] == nil {throw AssetError.invalid("Unknown color lookup table")}
            for i in 0..<Int(group[6]) where frames[i] != 0 {
                let graph = w(frames[i]+0x30)
                guard let settings = heap.lookup(graph,words:8) else {continue}
                if customPaletteImages[graph] == nil,let identity = heap.allocationIdentity(at:graph,count:32) {
                    customPaletteImages[graph] = [settings[5],settings[6],settings[7]];customPaletteImageIdentities[graph] = identity
                }
                if clt {settings[7] = table}
                else if p[2] == "Flag" {
                    // CrazyHook's release renumbered the indexed effect modes.
                    // Keep the renderer on its original modes, with the level's
                    // live tables (including package LIGHT/AVERAGE overrides).
                    let mode:UInt32 = [1:1,2:2,3:4,5:22,6:50,7:7,8:0x43480008][Int(value)]!
                    settings[5] = mode
                    if value == 2 || value == 3 {settings[7] = w(customPaletteState+0x76c)}
                    else if value == 6 {settings[7] = w(customPaletteState+0x770)}
                    else if value == 5 && settings[7] == 0 {settings[7] = w(customPaletteState+0x76c)}
                }
                else if p[2] == "Color" {settings[6] = UInt32(value)}
            }
            return 0
        default:throw AssetError.invalid("Unknown palette operation: \(key)")
        }
    }
}

extension ClawNativeMenuInterface {
    func checkCustomPaletteValues() throws {
        defer {
            if let folder = ProcessInfo.processInfo.environment["CLAW_REAL_SPEED_LOG"] {
                try? JSONSerialization.data(withJSONObject:customLevelEvidence,options:[.sortedKeys]).write(to:URL(fileURLWithPath:folder).appendingPathComponent("palette-values.json"),options:.atomic)
            }
        }
        guard let customLua else {throw AssetError.invalid("Palette check requires a Lua session")}
        try checkCustomPackageLookupTables()
        // Real packages need no synthetic NAMED table to exercise the renderer.
        if customPaletteTables["NAMED"] == nil {return}
        guard (try? ClawCustomPalette.decode(Data(repeating:0,count:767),name:"MAIN.PAL")) == nil,
              (try? ClawCustomPalette.decode(Data(repeating:0,count:767),name:"MAIN.ACT")) == nil,
              (try? ClawCustomPalette.decodeTable(Data(repeating:0,count:65540))) == nil,
              (try? ClawCustomPalette.decodeTable(Data([0,0,1,0])+Data(repeating:0,count:65535))) == nil,
              let text = try? ClawCustomPalette.decode(Data("#aAbBcC\nbad\n#112233\n".utf8),name:"MAIN.TXT"),
              Array(text.prefix(6)) == [170,187,204,0,0,0] else {throw AssetError.invalid("Palette format bounds check failed")}
        let partial = try ClawCustomPalette.decode(Data("#010203\ninvalid\n#ffffff".utf8),name:"MAIN.TXT",base:Data(repeating:42,count:768))
        guard Array(partial.prefix(6)) == [1,2,3,42,42,42],partial.last == 42 else {throw AssetError.invalid("Partial TXT palette did not retain base colors")}
        let before = try paletteRGB()
        try customLua.evaluate("""
        local p=CreatePalette();p[0]={200,40,80};p[255]='#010203'
        local q=p:Copy();p[0].Red=1;assert(q[0].Red==200)
        p[0].Red=257;assert(p[0].Red==1)
        q:AdjustRGB(-10,20,300,0,0):Set()
        assert(q[0].Red==190 and q[0].Green==60 and q[0].Blue==255)
        assert(q[255].Red==1 and q[255].Green==2 and q[255].Blue==3)
        """)
        let rgb = try paletteRGB()
        try customLua.evaluate("""
        local p=CreatePalette();p[0]={200,40,80};p:AdjustHSL(-5,0,0,0,0):Render()
        """)
        let hsl = try paletteRGB()
        try customLua.evaluate("""
        local p=CreatePalette();p[0]={200,40,80};p:BlackAndWhite(0,0)
        assert(p[0].Red==92 and p[0].Green==92 and p[0].Blue==92)
        p:InvertColors(0,0):SwapChannels('red','blue'):InvertChannel('green',255,255)
        assert(p[0].Red==163 and p[255].Green==255)
        GetFirstPalette():Set()
        local ok=pcall(function() LoadPaletteFile('../MAIN.PAL') end);assert(not ok)
        ok=pcall(function() _paletteService('Image:Color:Token:1',3) end);assert(not ok)
        """)
        let restored = try paletteRGB()
        guard restored == customPaletteFirst,base.palette?.currentRGB == restored else {throw AssetError.invalid("Palette backend/display restoration mismatch")}
        customLevelEvidence["palette_values"] = ["before":Array(before),"rgb":Array(rgb),"hsl":Array(hsl),"restored":Array(restored),"display_matches":true]
        try customLua.evaluate("SetImgFlag(GetClaw().Image,ImageFlag.Ghost);SetImgColor(GetClaw().Image,9);SetImgCLT(GetClaw().Image,'NAMED')")
        let image = w(w(0x537e88)+0x170),count = w(image+24),frames = w(image+20)
        var checked = 0
        for i in 0..<count where w(frames+i*4) != 0 {
            let graph = w(w(frames+i*4)+0x30)
            if graph != 0 {
                guard w(graph+20) == 2,w(graph+24) == 9,w(graph+28) == customPaletteTables["NAMED"] else {throw AssetError.invalid("Image color/CLT settings mismatch")}
                checked += 1
            }
        }
        guard checked > 0 else {throw AssetError.invalid("Image color check had no resident frames")}
        customLevelEvidence["palette_image_frames"] = checked
        var flagModes:[String:UInt32] = [:]
        let mappings:[(Int,UInt32)] = [(1,1),(2,2),(3,4),(5,22),(6,50),(7,7),(8,0x43480008)]
        for (flag,mode) in mappings {
            try customLua.evaluate("SetImgFlag(GetClaw().Image,\(flag))")
            for i in 0..<count where w(frames+i*4) != 0 {
                let graph = w(w(frames+i*4)+0x30)
                guard graph == 0 || w(graph+20) == mode else {throw AssetError.invalid("Image flag mapping failed")}
                if graph != 0 && [2,3,6].contains(flag) {
                    guard w(graph+28) == w(customPaletteState+(flag == 6 ? 0x770:0x76c)) else {throw AssetError.invalid("Image default lookup table failed")}
                }
            }
            flagModes[String(flag)] = mode
        }
        customLevelEvidence["palette_flag_modes"] = flagModes
        try customLua.evaluate("SetImgFlag(GetClaw().Image,ImageFlag.Normal)")
        try checkPaletteRaster()
    }
    private func checkCustomPackageLookupTables() throws {
        guard let display = base.palette?.display else {throw AssetError.invalid("Palette display unavailable")}
        let rgb = try paletteRGB()
        guard rgb == base.palette?.currentRGB else {throw AssetError.invalid("Indexed display palette mismatch")}
        let raw = resources.allocate(40),payload = resources.allocate(4),rect = resources.allocate(16)
        defer {resources.release(raw);resources.release(payload);resources.release(rect)}
        for i in 0..<4 {put(rect+UInt32(i*4),0)}
        let host = ClawNativeMenuRawDisplayHost(resources),target = w(display.backToken+0x2c)
        var call = ClawCall();call.receiver = raw;call.argumentCount = 3
        call.arguments.0 = rect;call.arguments.1 = target;call.arguments.2 = rect
        call.stackPointer = UInt32(CLAW_STACK_BASE)+0x10000
        var results:[String:Any] = [:]
        for name in customPaletteTables.keys.sorted() {
            let table = customPaletteTables[name]!
            guard let bytes = heap.lookupBytes(w(table+8),count:65536),
                  let source = customPalettes?.tables[name],source == Data(bytes:bytes,count:65536) else {throw AssetError.invalid("Package lookup bytes differ: \(name)")}
            for (i,n) in [UInt32(0),1,1,payload,2,1,9,table,0,1].enumerated() {put(raw+UInt32(i*4),n)}
            var rows:[[String:Any]] = []
            for (s,d,c): (UInt32,UInt32,UInt32) in [(7,13,9),(200,41,127),(1,255,32)] {
                for (mode,index): (UInt32,UInt32) in [(2,d*256+s),(4,d*256+c),(8,s*256+c)] {
                    put(payload,(d<<8)|1);put(raw+20,1);call.function = 0x4c0920
                    guard display.rawActorService(host,call) != nil,display.surfacePixels(target)?.bytes.first == UInt8(d) else {throw AssetError.invalid("Package raster destination")}
                    put(payload,(s<<8)|1);put(raw+20,mode);put(raw+24,c);call.function = 0x4c1190
                    guard display.rawActorService(host,call) != nil,host.fault == nil,
                          let actual = display.surfacePixels(target)?.bytes.first else {throw AssetError.invalid("Package lookup output: \(name), mode \(mode)")}
                    let offset = Int(actual)*3
                    rows.append(["mode":mode,"source":s,"destination":d,"color":c,"index":actual,"expected_index":bytes[Int(index)],"rgb":Array(rgb[offset..<offset+3])])
                }
            }
            results[name] = ["sha256":SHA256.hash(data:source).map{String(format:"%02x",$0)}.joined(),"pixels":rows]
        }
        customLevelEvidence["palette_package_raster"] = results
        customLevelEvidence["palette_current_rgb"] = Array(rgb)
    }
    private func checkPaletteRaster() throws {
        guard let display = base.palette?.display,let table = customPaletteTables["NAMED"],
              let bytes = heap.lookupBytes(w(table+8),count:65536) else {throw AssetError.invalid("Raster check table unavailable")}
        let raw = resources.allocate(40),payload = resources.allocate(4),rect = resources.allocate(16)
        defer {resources.release(raw);resources.release(payload);resources.release(rect)}
        for i in 0..<4 {put(rect+UInt32(i*4),0)}
        // renderWord zero selects every row; the paired-row path deliberately
        // skips even rows and would conceal a broken lookup at pixel zero.
        let fields:[UInt32] = [0,1,1,payload,2,1,9,table,0,1]
        for (i,n) in fields.enumerated() {put(raw+UInt32(i*4),n)}
        let host = ClawNativeMenuRawDisplayHost(resources)
        // The display holder owns image wrappers; raw blitters receive the
        // wrapper's source-surface owner, rather than the wrapper itself.
        let target = w(display.backToken+0x2c)
        var call = ClawCall();call.function = 0x4c1190;call.receiver = raw;call.argumentCount = 3
        call.arguments.0 = rect;call.arguments.1 = target;call.arguments.2 = rect
        call.stackPointer = UInt32(CLAW_STACK_BASE)+0x10000
        var outputs:[String:UInt8] = [:]
        let expected:[UInt32:UInt8] = [2:88,3:13,4:102,5:13,6:13,8:84,22:9,50:139]
        for mode:UInt32 in [2,3,4,5,6,8,22,50] {
            put(payload,0x0d01);put(raw+20,1);call.function = 0x4c0920
            guard display.rawActorService(host,call) != nil,host.fault == nil,
                  display.surfacePixels(target)?.bytes.first == 13 else {throw AssetError.invalid("Normal indexed raster failed: \(String(describing:host.fault)), pixel \(String(describing:display.surfacePixels(target)?.bytes.first))")}
            put(payload,0x0701);put(raw+20,mode);call.function = 0x4c1190
            guard display.rawActorService(host,call) != nil,host.fault == nil,
                  let actual = display.surfacePixels(target)?.bytes.first else {throw AssetError.invalid("CLT raster failed")}
            outputs[String(mode)] = actual
            guard actual == expected[mode] else {throw AssetError.invalid("CLT mode \(mode): expected \(expected[mode]!), got \(actual)")}
        }
        put(raw+20,7);call.function = 0x4bffa0;call.argumentCount = 5
        let before = display.surfacePixels(target)?.bytes
        guard display.rawActorService(host,call) == 0,host.fault == nil,
              display.surfacePixels(target)?.bytes == before else {throw AssetError.invalid("Flag 7 indexed rejection failed")}
        // Last interpolated pixel is 139, retained by rejection.
        outputs["7"] = display.surfacePixels(target)?.bytes.first
        put(raw+20,0x43480008)
        guard display.rawActorService(host,call) == 1,host.fault == nil,
              let blob = display.surfacePixels(target)?.bytes,
              Array(blob.prefix(2)) == [0,0],blob.dropFirst(2) == before?.dropFirst(2) else {throw AssetError.invalid("Indexed packed-word Blob failed")}
        customLevelEvidence["palette_blob_bytes"] = Array(blob.prefix(2))
        customLevelEvidence["palette_raster"] = ["source":7,"destination":13,"color":9,"outputs":outputs,"source_destination":bytes[7*256+13],"destination_source":bytes[13*256+7],"color_destination":bytes[9*256+13],"destination_color":bytes[13*256+9]]
    }
}

/// Native MFC archive protocol. Tokens stay in the scene heap; only files and
/// buffers constructed through this owner may participate. No recovered MFC body.
final class ClawNativeArchiveServices {
    typealias Bytes = (UInt32,UInt32)->UnsafeMutablePointer<UInt8>?
    private struct Archive {
        let file:UInt32,mode:UInt32,buffer:UInt32,size:UInt32,owned:Bool
        var end:UInt32
    }
    private var archives:[UInt32:Archive] = [:]
    private var memoryFiles:Set<UInt32> = []
    private var fileBuffers:[UInt32:UInt32] = [:]
    private let bytes:Bytes,allocate:(UInt32)->UInt32,release:(UInt32)->Void
    private let fileService:(UInt32,UInt32,[UInt32])->UInt32?
    private let makeString:(Data)->UInt32
    private let empty:UInt32
    private let limit:UInt32 = 0x800000
    init(bytes:@escaping Bytes,allocate:@escaping (UInt32)->UInt32,release:@escaping (UInt32)->Void,
         fileService:@escaping (UInt32,UInt32,[UInt32])->UInt32?,empty:UInt32,makeString:@escaping (Data)->UInt32) {
        self.bytes = bytes;self.allocate = allocate;self.release = release
        self.fileService = fileService;self.empty = empty;self.makeString = makeString
    }
    private func w(_ p:UInt32)->UInt32 {UnsafeRawPointer(bytes(p,4)!).loadUnaligned(as:UInt32.self)}
    private func put(_ p:UInt32,_ value:UInt32) {
        var value = value;withUnsafeBytes(of:&value) {bytes(p,4)!.update(from:$0.baseAddress!.assumingMemoryBound(to:UInt8.self),count:4)}
    }
    private func span(_ p:UInt32,_ n:UInt32)->UnsafeMutablePointer<UInt8>? {
        guard p != 0,UInt64(p)+UInt64(n) <= UInt64(UInt32.max) else {return nil}
        return bytes(p,n)
    }
    private func fileValid(_ f:UInt32)->Bool {
        if memoryFiles.contains(f) {
            guard span(f,40) != nil,w(f) == 0x5142f4,w(f+20) <= limit,
                  w(f+28) <= w(f+24),w(f+24) <= limit else {return false}
            return w(f+24) == 0 || span(w(f+32),w(f+24)) != nil
        }
        return fileService(0x4f774d,f,[]) != nil
    }
    private func io(_ function:UInt32,_ f:UInt32,_ a:[UInt32])->UInt32? {
        guard fileValid(f) else {return nil}
        guard memoryFiles.contains(f) else {return fileService(function,f,a)}
        let position = w(f+20),length = w(f+28)
        if function == 0x4f75f5 {
            guard a.count == 2,a[1] <= 2 else {return nil}
            let base = a[1] == 0 ? 0:a[1] == 1 ? position:length
            let next = Int64(base)+Int64(Int32(bitPattern:a[0]))
            guard next >= 0,next <= limit else {return nil}
            put(f+20,UInt32(next));return UInt32(next)
        }
        guard a.count == 2,a[1] <= limit else {return nil}
        if a[1] == 0 {return 0}
        guard let data = span(a[0],a[1]) else {return nil}
        if function == 0x4f7570 {
            let count = min(a[1],position < length ? length-position:0)
            if count != 0 {
                guard let source = span(w(f+32)+position,count) else {return nil}
                memmove(data,source,Int(count))
            }
            put(f+20,position+count);return count
        }
        guard function == 0x4f75aa,UInt64(position)+UInt64(a[1]) <= limit else {return nil}
        // The write may name this file's own allocation. Keep its bytes alive
        // across growth, which retires that allocation before the final copy.
        let payload = Data(bytes:data,count:Int(a[1]))
        let end = position+a[1],capacity = w(f+24)
        if end > capacity {
            let growth = w(f+16)
            guard growth != 0,growth <= limit else {return nil}
            let size = min(limit,((end+growth-1)/growth)*growth),token = allocate(size)
            guard let target = span(token,size) else {return nil}
            target.update(repeating:0,count:Int(size))
            if length != 0 {
                guard let source = span(w(f+32),length) else {release(token);return nil}
                memmove(target,source,Int(length))
            }
            if let old = fileBuffers.removeValue(forKey:f) {release(old)}
            fileBuffers[f] = token;put(f+32,token);put(f+24,size);put(f+36,1)
        }
        guard let target = span(w(f+32),w(f+24)) else {return nil}
        if position > length {target.advanced(by:Int(length)).update(repeating:0,count:Int(position-length))}
        payload.copyBytes(to:target.advanced(by:Int(position)),count:payload.count)
        put(f+20,end);put(f+28,max(length,end));return 0
    }
    private func state(_ r:UInt32)->Archive? {
        guard let s = archives[r],span(r,68) != nil,w(r+20) == s.mode,w(r+28) == s.size,
              w(r+32) == s.file,w(r+44) == s.buffer,w(r+40) == s.end,
              w(r+36) >= s.buffer,w(r+36) <= s.end,
              span(s.buffer,s.size) != nil,fileValid(s.file) else {return nil}
        return s
    }
    private func flush(_ r:UInt32)->Bool {
        guard let s = state(r) else {return false}
        let cur = w(r+36)
        if s.mode & 1 != 0 {
            let unread = s.end-cur
            if unread != 0,io(0x4f75f5,s.file,[UInt32(bitPattern:-Int32(unread)),1]) == nil {return false}
            put(r+36,s.end)
        } else {
            if cur != s.buffer,io(0x4f75aa,s.file,[s.buffer,cur-s.buffer]) == nil {return false}
            put(r+36,s.buffer)
        }
        return true
    }
    /// Keep unread bytes while compacting/refilling. FillBuffer's argument is
    /// additional bytes, and it leaves the cursor before the preserved bytes.
    private func fill(_ r:UInt32,_ additional:UInt32)->Bool {
        guard var s = state(r),s.mode & 1 != 0 else {return false}
        let cur = w(r+36),unread = s.end-cur
        guard UInt64(unread)+UInt64(additional) <= s.size else {return false}
        if cur > s.buffer {
            let target = span(s.buffer,s.size)!
            if unread != 0 {memmove(target,span(cur,unread)!,Int(unread))}
            guard let count = io(0x4f7570,s.file,[s.buffer+unread,s.size-unread]) else {return false}
            s.end = s.buffer+unread+count;archives[r] = s
            put(r+36,s.buffer);put(r+40,s.end)
        }
        return s.end-w(r+36) >= unread+additional
    }
    private func read(_ r:UInt32,_ target:UInt32,_ count:UInt32)->UInt32? {
        guard let s = state(r),s.mode & 1 != 0,count <= limit else {return nil}
        if count == 0 {return 0}
        guard span(target,count) != nil else {return nil}
        var done:UInt32 = 0
        let first = min(count,s.end-w(r+36))
        if first != 0 {memmove(span(target,first)!,span(w(r+36),first)!,Int(first));put(r+36,w(r+36)+first);done = first}
        if done == count {return done}
        let direct = ((count-done)/s.size)*s.size
        if direct != 0 {
            guard let got = io(0x4f7570,s.file,[target+done,direct]) else {return nil}
            done += got;if got != direct {return done}
        }
        if done != count {
            guard let got = io(0x4f7570,s.file,[s.buffer,s.size]) else {return nil}
            var next = s;next.end = s.buffer+got;archives[r] = next
            let take = min(count-done,got)
            if take != 0 {memmove(span(target+done,take)!,span(s.buffer,take)!,Int(take))}
            put(r+36,s.buffer+take);put(r+40,next.end);done += take
        }
        return done
    }
    private func write(_ r:UInt32,_ source:UInt32,_ count:UInt32)->Bool {
        guard let s = state(r),s.mode & 1 == 0,count <= limit else {return false}
        if count == 0 {return true}
        guard let input = span(source,count) else {return false}
        let payload = Data(bytes:input,count:Int(count))
        let first = min(count,s.end-w(r+36))
        if first != 0 {
            _ = payload.withUnsafeBytes {memmove(span(w(r+36),first)!,$0.baseAddress!,Int(first))}
            put(r+36,w(r+36)+first)
        }
        if first == count {return true}
        guard flush(r) else {return false}
        let direct = ((count-first)/s.size)*s.size
        if direct != 0 {
            let token = allocate(direct);defer {release(token)}
            guard let target = span(token,direct) else {return false}
            _ = payload.withUnsafeBytes {memmove(target,$0.baseAddress!.advanced(by:Int(first)),Int(direct))}
            guard io(0x4f75aa,s.file,[token,direct]) != nil else {return false}
        }
        let tail = count-first-direct
        if tail != 0 {_ = payload.withUnsafeBytes {memmove(span(s.buffer,tail)!,$0.baseAddress!.advanced(by:Int(first+direct)),Int(tail))}}
        put(r+36,s.buffer+tail);return true
    }
    private func encoded(_ value:UInt32,_ size:Int)->Data {
        Data((0..<size).map{UInt8(truncatingIfNeeded:value >> ($0*8))})
    }
    private func store(_ r:UInt32,_ data:Data)->Bool {
        let token = allocate(UInt32(data.count));defer {release(token)}
        guard let target = span(token,UInt32(data.count)) else {return false}
        data.copyBytes(to:target,count:data.count)
        return write(r,token,UInt32(data.count))
    }
    private func load(_ r:UInt32,_ count:UInt32)->Data? {
        guard count <= limit else {return nil}
        if count == 0 {return Data()}
        let token = allocate(count);defer {release(token)}
        guard let source = span(token,count),read(r,token,count) == count else {return nil}
        return Data(bytes:source,count:Int(count))
    }
    private func scalar(_ r:UInt32,_ count:UInt32)->UInt32? {
        guard let data = load(r,count) else {return nil}
        return data.enumerated().reduce(UInt32(0)) {$0 | UInt32($1.element) << ($1.offset*8)}
    }
    func service(_ function:UInt32,_ r:UInt32,_ a:[UInt32])->UInt32? {
        switch function {
        case 0x4ff5f9:
            guard a.count == 1,a[0] <= limit,!memoryFiles.contains(r),let p = span(r,40) else {return nil}
            memoryFiles.insert(r);p.update(repeating:0,count:40)
            put(r,0x5142f4);put(r+4,.max);put(r+12,empty);put(r+16,a[0]);put(r+36,1);return r
        case 0x4ff645:
            guard a.count == 3,a[2] == 0,memoryFiles.contains(r),fileValid(r),!archives.values.contains(where:{$0.file == r}),
                  w(r+32) == 0,a[1] <= limit,span(a[0],a[1]) != nil else {return nil}
            put(r+16,0);put(r+20,0);put(r+24,a[1]);put(r+28,a[1]);put(r+32,a[0]);put(r+36,0);return 0
        case 0x4ff670,0x4ff682:
            guard a.isEmpty,fileValid(r),memoryFiles.contains(r),!archives.values.contains(where:{$0.file == r}) else {return nil}
            let data = w(r+32),owned = fileBuffers.removeValue(forKey:r)
            for off:UInt32 in [20,24,28,32] {put(r+off,0)}
            if function == 0x4ff682 {if let owned {release(owned)};memoryFiles.remove(r);put(r,0x50becc)}
            return function == 0x4ff670 ? data:0
        case 0x4ff79f:
            guard a.count == 2,memoryFiles.contains(r) else {return nil}
            return io(0x4f7570,r,a)
        case 0x4fda33:
            guard a.count == 4,a[1] <= 7,a[2] <= limit,fileValid(a[0]),archives[r] == nil,
                  !archives.values.contains(where:{$0.file == a[0]}),let p = span(r,68) else {return nil}
            let size = max(128,a[2]),owned = a[3] == 0 || a[2] < 128
            let buffer = owned ? allocate(size):a[3]
            guard span(buffer,size) != nil,UInt64(buffer)+UInt64(size) <= UInt32.max else {if owned {release(buffer)};return nil}
            p.update(repeating:0,count:68)
            let loading = a[1]&1 != 0,end = buffer+size
            for (off,value):(UInt32,UInt32) in [(4,1),(12,.max),(16,empty),(20,a[1]),(24,owned ? 0:1),(28,size),(32,a[0]),(36,loading ? end:buffer),(40,end),(44,buffer),(60,loading ? 64:16),(64,137)] {put(r+off,value)}
            archives[r] = Archive(file:a[0],mode:a[1],buffer:buffer,size:size,owned:owned,end:end);return r
        case 0x4fdb0f:
            guard a.isEmpty,let s = state(r),s.mode & 2 != 0 || flush(r) else {return nil}
            archives.removeValue(forKey:r);if s.owned {release(s.buffer)}
            put(r+32,0);put(r+36,0);put(r+40,0);put(r+44,0);return 0
        case 0x4fdd43:
            guard a.isEmpty,flush(r) else {return nil};return 0
        case 0x4fddbd:
            guard a.count == 1,fill(r,a[0]) else {return nil};return 0
        case 0x4fdcb3:
            guard a.count == 2,write(r,a[0],a[1]) else {return nil};return 0
        case 0x4fdba5:
            guard a.count == 2 else {return nil};return read(r,a[0],a[1])
        case 0x4fde7f:
            guard a.count == 1 else {return nil}
            let data = a[0] < 0xffff ? encoded(a[0],2):encoded(0xffff,2)+encoded(a[0],4)
            guard store(r,data) else {return nil};return 0
        case 0x4fdead:
            guard a.isEmpty,let short = scalar(r,2) else {return nil}
            return short == 0xffff ? scalar(r,4):short
        case 0x4fd7fd:
            guard a.count == 2,span(a[1],4) != nil else {return nil}
            let pointer = w(a[1])
            guard pointer >= 12,span(pointer-12,12) != nil else {return nil}
            let length = w(pointer-8),capacity = w(pointer-4)
            guard length <= capacity,capacity < limit,let source = span(pointer,capacity+1),source[Int(length)] == 0 else {return nil}
            let prefix = length < 255 ? encoded(length,1):length < 0xfffe ? encoded(255,1)+encoded(length,2):encoded(255,1)+encoded(0xffff,2)+encoded(length,4)
            guard store(a[0],prefix),write(a[0],pointer,length) else {return nil};return a[0]
        case 0x4fd877:
            guard a.count == 2,span(a[1],4) != nil,let first = scalar(a[0],1) else {return nil}
            var count = first
            if count == 255 {
                guard let short = scalar(a[0],2),short != 0xfffe else {return nil}
                if short == 0xffff {guard let long = scalar(a[0],4) else {return nil};count = long}
                else {count = short}
            }
            guard count < limit,let data = load(a[0],count) else {return nil}
            let token = makeString(data);guard token != 0 else {return nil}
            put(a[1],token);return a[0]
        default:return nil
        }
    }
}
