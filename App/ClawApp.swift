import SwiftUI
import CoreGraphics
import Combine
import CryptoKit
import ImageIO
import UIKit
import UniformTypeIdentifiers

@main
struct ClawApp: App {
    init() {
        let arguments = ProcessInfo.processInfo.arguments
        if let index = arguments.firstIndex(of: "--game-version") {
            precondition(index + 1 < arguments.count && ["1.0", "1.3"].contains(arguments[index + 1]), "--game-version requires 1.0 or 1.3")
            setenv("CLAW_GAME_VERSION", arguments[index + 1], 1)
        }
    }
    @State private var selectedTab = ProcessInfo.processInfo.arguments.contains("--movement") ? 2 :
        ProcessInfo.processInfo.arguments.contains("--level1") ? 1 : 0
    var body: some Scene { WindowGroup {
        if ProcessInfo.processInfo.arguments.contains(where: { ["--lab", "--movement", "--level1"].contains($0) }) {
            TabView(selection: $selectedTab) {
                AssetPlaybackView().tabItem { Label("Animations", systemImage: "figure.walk") }.tag(0)
                LevelOnePreviewView().tabItem { Label("Level 1", systemImage: "map") }.tag(1)
                ClawNativePlayerView().tabItem { Label("Movement", systemImage: "gamecontroller") }.tag(2)
            }
        } else {
            // Full screen like the original: no status bar or home indicator over the game.
            ClawMainMenuView().statusBarHidden(true).persistentSystemOverlays(.hidden)
        }
    } }
}

// The UI only presents the primary surface. Resource selection, animation,
// palette changes and drawing run through the recovered menu frame graph.
@MainActor
final class ClawMainMenuPresentation: ObservableObject {
    @Published private(set) var image: CGImage?
    @Published private(set) var failure: String?
    struct ControlsState {
        var keys:[UInt32]
        var buttons:[UInt32]
        var disableJoystick:Bool
        var touchControls = false
        var selected = 0
        var capturing = false
        var error:String?
    }
    #if !targetEnvironment(macCatalyst)
    @Published private(set) var touchControlsEnabled = UserDefaults.standard.bool(forKey: "ClawTouchControls")
    @Published private(set) var touchGameplay = false
    var touchControlsVisible: Bool {
        UIDevice.current.userInterfaceIdiom == .pad && touchControlsEnabled && touchGameplay &&
            !checkpointOverlay && controls == nil && players == nil && customLevels == nil && !movieActive
    }
    func touchKey(_ action: Int) -> UInt32 {
        if action < 4 { return [37, 39, 38, 40][action] }
        if action == 8 { return 27 }
        return owner?.controlKeys[action - 4] ?? 0
    }
    #endif
    @Published var controls:ControlsState?
    @Published var checkpointOverlay = false
    @Published private(set) var checkpointToast: String?
    private var checkpointToastGeneration = 0
    @Published var checkpointSelectedSlot = 0
    private var pendingCustomSave = false
    private var pendingCustomRestore: Int?
    var customCheckpointLabels: [String] {
        let dates = owner?.customCheckpointDates ?? []
        return (0..<3).map { index in
            guard dates.indices.contains(index) else {return "Restore custom checkpoint \(index+1) · Empty"}
            let seconds = max(0,Int(Date().timeIntervalSince(dates[index])))
            let age = seconds < 60 ? "\(seconds)s" : seconds < 3600 ? "\(seconds/60)m" : seconds < 86400 ? "\(seconds/3600)h" : "\(seconds/86400)d"
            return "Restore custom checkpoint \(index+1) · \(age) ago"
        }
    }
    func hasCustomCheckpointSlot(_ slot: Int) -> Bool { (0..<3).contains(slot) && (owner?.customCheckpointDates.count ?? 0) > slot }
    var canSaveCustomCheckpointNow: Bool {owner?.canSaveCustomCheckpoint == true}
    private func customToast(_ text: String) {
        checkpointToast = text;checkpointToastGeneration += 1
        let generation = checkpointToastGeneration
        DispatchQueue.main.asyncAfter(deadline:.now()+2) { [weak self] in
            if self?.checkpointToastGeneration == generation {self?.checkpointToast = nil}
        }
    }
    private func performCustomCheckpoint() throws {
        guard let owner else {return}
        if pendingCustomSave {
            pendingCustomSave = false
            do {try owner.saveCustomCheckpoint();customToast(owner.customCheckpointMessage)}
            catch {customToast("Custom checkpoint could not be saved: \(error)")}
        }
        guard let slot = pendingCustomRestore else {return}
        pendingCustomRestore = nil
        let previousQueryStep = gateQueryStep
        if inputGate {gateQueryStep = 1}
        defer {gateQueryStep = previousQueryStep}
        do {
            try owner.restoreCustomCheckpoint(slot:slot)
            customToast(owner.customCheckpointMessage)
            if let realSpeedURL {
                let evidence = owner.checkpointStats().merging([
                    "status":"pass", "placements":owner.resources.checkpointPlacementEvidence,
                    "initial_placements":owner.checkpointInitialPlacements,
                    "mechanisms":owner.resources.checkpointRecipeEvidence,
                    "held_keys":owner.base.windowInput?.virtualKeys.sorted() ?? []]) {_,new in new}
                try JSONSerialization.data(withJSONObject:evidence,options:[.sortedKeys])
                    .write(to:realSpeedURL.appendingPathComponent("custom-restore.json"),options:.atomic)
            }
        } catch {
            customToast(error.localizedDescription)
            if let realSpeedURL {
                try JSONSerialization.data(withJSONObject:["status":"fail","error":String(describing:error)],options:[.sortedKeys])
                    .write(to:realSpeedURL.appendingPathComponent("custom-restore.json"),options:.atomic)
            }
        }
    }
    var canRestoreCustomCheckpoint: Bool {
        owner?.hasCustomCheckpoint ?? false
    }
    func requestCustomRestore(slot: Int = 0) {
        guard !movieActive,controls == nil,players == nil,(slot == 0 && canRestoreCustomCheckpoint) || hasCustomCheckpointSlot(slot) else {return}
        checkpointOverlay = false;pendingCustomRestore = slot
    }
    func showCustomCheckpoint() {
        guard !movieActive, controls == nil, players == nil, owner != nil else {return}
        releaseInput();checkpointOverlay.toggle()
        checkpointSelectedSlot = 0
    }
    func requestCustomSave() {
        guard !movieActive,controls == nil,players == nil,canSaveCustomCheckpointNow else {return}
        checkpointOverlay = false;pendingCustomSave = true
    }
    struct PlayersState {
        var choices:[ClawNativeMenuInterface.PlayerChoice]
        var selected:UInt32
        var page = 0 // EDITPLAYERS, USERNEW, USERREMOVECONFIRM
        var name = "",location = "",email = ""
        var field = 0
        var error:String?
    }
    @Published var customLevels:[URL]?
    @Published var customSelected = 0
    @Published var customRestartSlot = 0
    func cycleCustomRestart() {
        guard let levels = customLevels,levels.indices.contains(customSelected),let owner else {return}
        do {
            let slots = [0] + (try owner.customRestartSlots(levels[customSelected]))
            customRestartSlot = slots[(slots.firstIndex(of:customRestartSlot).map{$0+1} ?? 0) % slots.count]
            customError = nil
        } catch {customRestartSlot = 0;customError = error.localizedDescription}
    }
    @Published var customError:String?
    @Published var customImporter = false
    private var pendingCustomLevel:URL?
    private var importedCustomLevel:URL?
    var customDirectory:URL {
        let args = ProcessInfo.processInfo.arguments
        if let i = args.firstIndex(of:"--custom-dir"),i+1 < args.count {return URL(fileURLWithPath:args[i+1],isDirectory:true)}
        #if targetEnvironment(macCatalyst)
        return FileManager.default.urls(for:.applicationSupportDirectory,in:.userDomainMask)[0].appendingPathComponent("Claw/Custom",isDirectory:true)
        #else
        return FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("Custom",isDirectory:true)
        #endif
    }
    func showCustomLevels() {
        releaseInput();customError = nil;customSelected = 0;customRestartSlot = 0
        do {
            try FileManager.default.createDirectory(at:customDirectory,withIntermediateDirectories:true)
            customLevels = try FileManager.default.contentsOfDirectory(at:customDirectory,includingPropertiesForKeys:[.isRegularFileKey])
                .filter{$0.pathExtension.lowercased() == "wwd"}.sorted{$0.lastPathComponent.localizedStandardCompare($1.lastPathComponent) == .orderedAscending}
            if let importedCustomLevel,let index = customLevels?.firstIndex(of:importedCustomLevel) {customSelected = index}
        } catch {customLevels = [];customError = error.localizedDescription}
    }
    func closeCustomLevels() {
        releaseInput();owner?.customLevelsActive = false;customLevels = nil;customError = nil
    }
    func chooseCustomLevel() {
        guard let levels = customLevels,levels.indices.contains(customSelected) else {return}
        pendingCustomLevel = levels[customSelected];releaseInput()
    }
    func importCustomLevel(_ url:URL) {
        let access = url.startAccessingSecurityScopedResource()
        defer {if access {url.stopAccessingSecurityScopedResource()}}
        do {
            let imported = try ClawCustomAssets.importPackage(url,into:customDirectory)
            guard let destination = imported.first else {return}
            importedCustomLevel = destination
            if owner?.menuLive == true {owner?.customLevelsActive = true;showCustomLevels()}
            else {customError = "Imported \(destination.lastPathComponent). Choose Load Custom Level from Single Player."}
        } catch {customError = error.localizedDescription}
    }
    private func performCustomLoad() {
        guard let url = pendingCustomLevel,let owner else {return}
        pendingCustomLevel = nil
        let old = gateQueryStep
        if inputGate {gateQueryStep = 1}
        defer {gateQueryStep = old}
        do {try owner.startCustomLevel(url,checkpoint:customRestartSlot);customLevels = nil;customError = nil;customRestartSlot = 0}
        catch {
            if owner.resources.fault != 0 {
                customLevels = nil;owner.customLevelsActive = false;stop(error:error)
            } else {
                customError = error.localizedDescription
                _ = owner.takeCustomRequirementFailure()
                owner.customLevelsActive = true
            }
        }
    }
    @Published var players:PlayersState?
    private var playerDialogEvents:[[String:Any]] = []
    func playerAction(_ action:String) {
        guard let owner,var draft = players else {return}
        draft.error = nil
        do {
            switch action {
            case "close","accept":
                owner.finishPlayerDialog(cancelled:action == "close")
                playerDialogEvents.append(["action":action,"page":draft.page,"result":action == "close" ? 2:1,
                    "selected":owner.playerChoices.first(where:{$0.id == owner.selectedPlayer})?.name ?? ""])
                owner.base.windowInput?.releaseMenuKeys();owner.playersActive = false;players = nil;return
            case "new":draft.page = 1;draft.name = "";draft.location = "";draft.email = "";draft.field = 0
            case "cancel":owner.finishPlayerDialog(cancelled:true);draft.page = 0
            case "create":
                draft.selected = try owner.createPlayer(name:draft.name,location:draft.location,email:draft.email)
                owner.finishPlayerDialog(cancelled:false)
                draft.choices = owner.playerChoices;draft.page = 0
            case "select":try owner.selectPlayer(draft.selected)
            case "remove":
                if draft.choices.first(where:{$0.id == draft.selected})?.name.lowercased() != "player" {draft.page = 2}
            case "confirm":
                try owner.removePlayer(draft.selected)
                owner.finishPlayerDialog(cancelled:false)
                draft.selected = owner.selectedPlayer;draft.choices = owner.playerChoices;draft.page = 0
            default:break
            }
        } catch {draft.error = String(describing:error)}
        playerDialogEvents.append(["action":action,"page":draft.page,"error":draft.error ?? "",
            "selected":owner.playerChoices.first(where:{$0.id == owner.selectedPlayer})?.name ?? ""])
        players = draft
    }
    private func playersKey(_ key:UInt32,down:Bool,fromScript:Bool = false)->Bool {
        guard var draft = players else {return false}
        guard down else {return true}
        if key == 27 {playerAction(draft.page == 0 ? "close":"cancel");return true}
        if draft.page == 1 {
            if key == 13 {playerAction("create")}
            else {
                if key == 9 {draft.field = (draft.field+1)%3}
                else {
                    var text = [draft.name,draft.location,draft.email][draft.field]
                    if key == 8 {if !text.isEmpty {text.removeLast()}}
                    else if (32...126).contains(key),text.utf8.count < ClawNativeMenuInterface.playerTextLimits[draft.field] {text.append(Character(UnicodeScalar(key)!))}
                    if draft.field == 0 {draft.name = text} else if draft.field == 1 {draft.location = text} else {draft.email = text}
                }
                players = draft
            }
        } else if draft.page == 2 {
            if key == 13 || key == 89 {playerAction("confirm")}
            else if key == 78 {playerAction("cancel")}
        } else {
            if key == 78 {playerAction("new")}
            else if key == 82 {playerAction("remove")}
            else if key == 13 {playerAction("accept")}
            else if key == 38 || key == 40,let index = draft.choices.firstIndex(where:{$0.id == draft.selected}),!draft.choices.isEmpty {
                draft.selected = draft.choices[(index+(key == 38 ? draft.choices.count-1:1))%draft.choices.count].id
                players = draft
                playerAction("select")
            }
        }
        return true
    }
    static func controlKeyName(_ key:UInt32)->String {
        if key == 0 {return "None"}
        if (0x30...0x39).contains(key) || (0x41...0x5a).contains(key) {return String(UnicodeScalar(key)!)}
        if (0x60...0x69).contains(key) {return "Keypad \(key-0x60)"}
        return [UInt32(0x20):"Space",0x11:"Control",0x12:"Option / Alt",0x10:"Shift",
                0x2d:"Insert",0x2e:"Delete",0x21:"Page Up",0x22:"Page Down",0x24:"Home",0x23:"End"][key] ?? "Key \(key)"
    }
    func chooseControl(_ index:Int) {
        guard var draft = controls else {return}
        draft.selected = index;draft.capturing = index < 9;draft.error = nil;controls = draft
    }
    func controlsDefaults() {
        controls?.keys = ClawNativeMenuInterface.controlActions.map(\.key)
        controls?.buttons = ClawNativeMenuInterface.controlActions.map(\.button)
        controls?.capturing = false
    }
    func closeControls(save:Bool) {
        guard let owner,let draft = controls else {return}
        do {
            if save {
                try owner.applyControls(keys:draft.keys,buttons:draft.buttons,disableJoystick:draft.disableJoystick)
                #if !targetEnvironment(macCatalyst)
                touchControlsEnabled = draft.touchControls
                UserDefaults.standard.set(draft.touchControls, forKey: "ClawTouchControls")
                #endif
            }
            owner.base.windowInput?.releaseMenuKeys()
            owner.controlsActive = false;controls = nil
        } catch {controls?.error = String(describing:error)}
    }
    private func controlsKey(_ key:UInt32,down:Bool,repeatKey:Bool = false)->Bool {
        guard var draft = controls else {return false}
        guard down,!repeatKey else {return true}
        if draft.capturing {
            if key == 27 {draft.capturing = false}
            else if key == 8 {draft.keys[draft.selected] = 0;draft.capturing = false}
            else if (0x30...0x39).contains(key) || (0x41...0x5a).contains(key) || (0x60...0x69).contains(key)
                        || [UInt32(0x10),0x11,0x12,0x20,0x21,0x22,0x23,0x24,0x2d,0x2e].contains(key) {
                draft.keys[draft.selected] = key;draft.capturing = false;draft.error = nil
            } else {draft.error = "Choose a letter, number, Space, modifier, or navigation key. Esc cancels; Backspace clears."}
            controls = draft;return true
        }
        switch key {
        case 27:closeControls(save:false)
        case 38:draft.selected = (draft.selected+11)%12;controls = draft
        case 40,9:draft.selected = (draft.selected+1)%12;controls = draft
        case 37,39:
            if draft.selected < 9 {
                let choices: [UInt32] = [0,1,2,4,8,0x10,0x20,0x40,0x80,0x38]
                let old = choices.firstIndex(of:draft.buttons[draft.selected]) ?? 0
                draft.buttons[draft.selected] = choices[(old + (key == 39 ? 1:choices.count-1)) % choices.count]
                controls = draft
            }
        case 13:
            if draft.selected < 9 {chooseControl(draft.selected)}
            else if draft.selected == 9 {controlsDefaults()}
            else {closeControls(save:draft.selected == 11)}
        default:break
        }
        return true
    }
    // The window's screen. Each primary Flip reaches it at once and is
    // committed even while game code keeps the main thread (level loading).
    let surfaceLayer: CALayer = {
        let layer = CALayer()
        layer.contentsGravity = .resizeAspect
        layer.magnificationFilter = .nearest
        layer.actions = ["contents": NSNull(), "bounds": NSNull(), "position": NSNull()]
        return layer
    }()
    // --menu-check: every Flip of the current tick, and the ticks that
    // presented more than one (the loading screen inside the launch command).
    private var tickFlips: [(pixels: String, palette: String, nonzero: Int, image: CGImage)] = []
    private var multiFlipFrames: [[String: Any]] = []
    // The front buffer as last flipped; palette changes re-present it.
    private var front: (pixels: Data, width: UInt32, height: UInt32, stride: UInt32, hash: String)?
    // --menu-check: the screen states (front pixels, palette) of the current
    // tick, consecutive repeats collapsed, as Flip and palette changes made them.
    private var tickScreens: [[String]] = []
    private var tickPaletteChanges = 0
    // --menu-check: game writes to the primary surface between Flips in the
    // current tick (the loading progress bar), each with the front it left.
    private var tickPrimaryWrites: [[String: Any]] = []
    var logicalSize:CGSize {guard let owner,owner.w(owner.base.applicationToken+0x7c)>0,owner.w(owner.base.applicationToken+0x80)>0 else {return CGSize(width:640,height:480)};return CGSize(width:Int(owner.w(owner.base.applicationToken+0x7c)),height:Int(owner.w(owner.base.applicationToken+0x80)))}
    var customPresentationActive:Bool {owner?.customPresentationActive == true}
    private var owner: ClawNativeMenuInterface?
    // A nested native event pump may deliver display timers. Queue input but
    // never run a second recovered frame over the suspended invocation/heap.
    private var gameBusy = false
    private let heartbeat = ClawMainThreadHeartbeat()
    private var heartbeatScopes: [Int] = []
    private var frameCount = 0
    private var checkFrames = 61
    private var clock: UInt32 = 1000
    private var checkpointCadenceOffset = 0
    // --new-game-clock: the Level 1 tracer's physical clock. Each frame
    // advances 17 ms; until Level 1 is live each timer query advances 1 ms,
    // so busy waits such as 0x4b8960 complete as they do in the join.
    private let tracerClock = ProcessInfo.processInfo.arguments.contains("--new-game-clock") || ProcessInfo.processInfo.arguments.contains("--test-level")
    // --fast-clock (with --menu-check): frames run back to back instead of on
    // the 60 Hz display timer. The game already sees only the check's own
    // clock (the 17 ms or 1000/60 ms steps above), so it sees the same values;
    // only scripted input reaches it, and the app quits once the evidence is
    // written.
    let fastClock = ProcessInfo.processInfo.arguments.contains("--fast-clock")
    // Movies: the original's numeric movies through AVFoundation, silent under
    // --mute and every check flag (ClawNativeMoviePlayback.silent). The
    // deterministic frame comparisons omit movies. --movie-check <dir>
    // checks startup and exits; --movie-flow-check <dir> enables movies during
    // real-input menu/level checks without the startup sequence. Both report
    // movie-state.json so the driver can confirm playback and input delivery.
    let moviePlayback = ClawNativeMoviePlayback()
    @Published private(set) var movieActive = false
    private var movieStage = false
    private var movieCatalog: ClawNativeMovieCatalog?
    private var movieRecords: [[String: Any]] = []
    private lazy var movieCheckURL: URL? = {
        let arguments = ProcessInfo.processInfo.arguments
        guard let index = arguments.firstIndex(where: { ["--movie-check", "--movie-flow-check"].contains($0) }), index + 1 < arguments.count else { return nil }
        return URL(fileURLWithPath: arguments[index + 1], isDirectory: true)
    }()
    private var movieStarted = 0.0
    private var movieFlags: UInt32 = 1
    private var movieSkipResult: UInt32 = 1
    private var movieFlowCheck: Bool { ProcessInfo.processInfo.arguments.contains("--movie-flow-check") }
    private var startupMoviesEnabled: Bool {
        !movieFlowCheck && (movieCheckURL != nil || !ProcessInfo.processInfo.arguments.contains {
            ["--menu-check", "--menu-live-check", "--play-script", "--fast-clock", "--new-game-clock",
             "--menu-input-script", "--music-render", "--test-level"].contains($0) } && realSpeedURL == nil)
    }
    // The original's 0x4f0380 is a blocking loop that pumps window messages
    // until the movie ends or a WM_KEYDOWN arrives (play flags 1); this pumps
    // the window's events the same way (ClawWindowEventPump) while AVPlayer
    // presents the movie, so real key presses reach key() and the window
    // stays responsive.
    private func playMovie(_ movie: UInt32, flags: UInt32) -> UInt32 {
        guard let catalog = movieCatalog, let file = try? catalog.file(movieID: movie) else { return 0 }
        final class Completion { var outcome: ClawNativeMoviePlayback.Outcome?; var failed: String? }
        let completion = Completion()
        let probe = heartbeat.begin("movie-\(movie)")
        defer { heartbeat.end(probe) }
        let began = ProcessInfo.processInfo.systemUptime
        movieActive = true
        movieStarted = began
        movieFlags = flags; movieSkipResult = 1
        writeMovieState(["movie": movie, "playing": true, "uptime": began])
        do {
            try moviePlayback.begin(movieID: movie, file: file) { result in
                switch result {
                case .success(let outcome): completion.outcome = outcome
                case .failure(let error): completion.failed = String(describing: error)
                }
            }
        } catch { completion.failed = String(describing: error) }
        var audio: [String: Any] = [:]
        var played = 0.0, size = CGSize.zero, reported = 0.0
        while completion.outcome == nil && completion.failed == nil {
            ClawWindowEventPump.pump(for: 0.02)
            moviePlayback.poll()
            if audio.isEmpty && moviePlayback.ready { audio = moviePlayback.audioState }
            if moviePlayback.ready, let item = moviePlayback.player.currentItem {
                played = item.currentTime().seconds; size = item.presentationSize
            }
            let now = ProcessInfo.processInfo.systemUptime
            if now - reported > 0.25 {
                writeMovieState(["movie": movie, "playing": true, "ready": moviePlayback.ready,
                    "media_seconds": played, "flags": flags, "uptime": now, "input_received": liveInputCount])
                reported = now
            }
            // A shorter deadline is available only to the muted movie check,
            // so its failure/exit path can be exercised without a broken file.
            let args = ProcessInfo.processInfo.arguments
            if movieCheckURL != nil, let i = args.firstIndex(of: "--movie-timeout"), i + 1 < args.count,
               let limit = Double(args[i + 1]), now - began > limit {
                moviePlayback.cancel(); completion.failed = "timeout"
            }
        }
        movieActive = false
        writeMovieState(["movie": movie, "playing": false, "uptime": ProcessInfo.processInfo.systemUptime])
        let outcome = completion.outcome, failed = completion.failed
        let result: UInt32 = outcome == .finished ? 0x11111111 : outcome == .skipped ? movieSkipResult : 0
        movieRecords.append(["movie": movie, "file": file.lastPathComponent, "outcome": failed ?? "\(outcome!)",
            "result": result, "seconds": ProcessInfo.processInfo.systemUptime - began,
            "media_seconds": played, "presentation": [size.width, size.height],
            "audio": audio.isEmpty ? moviePlayback.audioState : audio])
        if let failed { failure = "Movie \(movie): \(failed)" }
        writeMovieState(["movie": movie, "playing": false, "uptime": ProcessInfo.processInfo.systemUptime,
            "records": movieRecords, "input_received": liveInputCount, "error": failure ?? ""])
        return result
    }
    private func writeMovieState(_ state: [String: Any]) {
        guard let url = movieCheckURL else { return }
        try? FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        let report = state.merging(["records": movieRecords, "events": owner?.movieEvents ?? [],
            "input_received": liveInputCount, "silent": ClawNativeMoviePlayback.silent,
            "responsiveness": heartbeat.records]) { old, _ in old }
        try? JSONSerialization.data(withJSONObject: report, options: [.sortedKeys])
            .write(to: url.appendingPathComponent("movie-state.json"), options: .atomic)
    }
    private func runStartupMovies(_ menu: ClawNativeMenuInterface) {
        do {
            try menu.playStartupMovies()
            movieStage = false
            gameBusy = true
            defer { gameBusy = false }
            try menu.enter()
            gameBusy = false
            tick()
            if movieCheckURL != nil && !movieFlowCheck {
                DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self] in self?.finishMovieCheck() }
            }
        } catch { movieStage = false; stop(error: error); finishMovieCheck() }
    }
    private func finishMovieCheck() {
        guard let url = movieCheckURL else { return }
        try? FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        let state = owner.map { $0.w($0.base.applicationToken + 0x2c) } ?? 0
        let report: [String: Any] = ["status": failure == nil ? "pass" : "fail", "error": failure ?? "",
            "movies": movieRecords, "events": owner?.movieEvents ?? [], "frames_after_movies": frameCount,
            "state": state, "state_vtable": state == 0 ? 0 : (owner?.w(state) ?? 0), "menu_live": owner?.menuLive ?? false,
            "silent": ClawNativeMoviePlayback.silent, "audio": moviePlayback.audioState,
            "responsiveness": heartbeat.records]
        var settingsReport = report
        if let owner, owner.menuLive, owner.resources.fault == 0 {
            let page = owner.resources.invoke(0x4dd0c0, owner.menuToken + 0x154)
            settingsReport["menu_page"] = page == 0 ? 0 : owner.w(page + 80)
            settingsReport["intro_count"] = owner.w(owner.base.applicationToken + 0x74)
            settingsReport["startup_intro_result"] = owner.w(0x53ec58)
        }
        if let owner, owner.settingsDirectory != nil {
            // The original teardown's settings point, before the check exits.
            owner.writeSettings()
            settingsReport["settings"] = owner.settings?.events ?? []
            settingsReport["settings_written"] = owner.settingsWritten
            settingsReport["settings_failure"] = owner.settings?.writeFailure ?? ""
        }
        try? JSONSerialization.data(withJSONObject: settingsReport, options: [.prettyPrinted, .sortedKeys])
            .write(to: url.appendingPathComponent("movie-check.json"), options: .atomic)
        if let image { try? save(image, to: url.appendingPathComponent("menu-after-movies.png")) }
        exit(failure == nil ? 0 : 1)
    }
    private var clockQueryStep: UInt32 = 1
    private var clockReads:[[String:UInt32]] = []
    // The join delivers a posted command in the pump turn that posted it, then
    // steps 17 ms: a frame that starts with posted commands takes its step
    // after delivery instead of before.
    private var deferredFrameStep = false
    // --play-script: the Level 1 join's fixed input plan. Held keys reach the
    // original poller only through GetAsyncKeyState, as in the join.
    // An entry may also carry "set_x"/"set_y": a debug-only placement of the player
    // actor (+0x4c, +0x50) once when the entry begins, so a regression check can start
    // next to a far object (work/super-checkpoint) without playing the level to it.
    // It writes no cheat state: the game's cheat flag stays clear.
    private struct PlayAction { let start: Int, end: Int, action: String, keys: Set<UInt32>; var place: (x: UInt32, y: UInt32)? = nil; var cheat: String? = nil; var chaseBoss = false; var diagnostic: [String: Int] = [:] }
    private var playPlaced: Set<Int> = []
    private var playPlan: [PlayAction] = []
    private var playStart: UInt32?
    private var playAction = ""
    private var playFrames: [[String: Any]] = []
    private var playComplete = false
    private static let playKeys: [UInt32] = [0x25, 0x27, 0x26, 0x28, 0x20, 0x11, 0x12, 0x10, 0x58, 0x5a, 0x31, 0x32, 0x33]
    private static func parsePlayPlan(_ plan: [[String: Any]]) throws -> [PlayAction] {
        try plan.map { entry in
            guard let start = entry["start_ms"] as? Int, let end = entry["end_ms"] as? Int, start < end,
                  let action = entry["action"] as? String, let keys = entry["keys"] as? [Int],
                  keys.allSatisfy({ Self.playKeys.contains(UInt32($0)) }) else {
                throw AssetError.invalid("Invalid play script entry")
            }
            var place: (x: UInt32, y: UInt32)?
            if entry["set_x"] != nil || entry["set_y"] != nil {
                guard let x = entry["set_x"] as? Int, let y = entry["set_y"] as? Int, (0..<0x100000).contains(x), (0..<0x100000).contains(y) else {
                    throw AssetError.invalid("Invalid play script placement")
                }
                place = (UInt32(x), UInt32(y))
            }
            let diagnostic = entry["diagnostic"] as? [String: Int] ?? [:]
            guard diagnostic.allSatisfy({ key, value in
                switch key {
                case "ammo", "lives": return (0...99).contains(value)
                case "health": return (1...100).contains(value)
                case "score": return (0...99999999).contains(value)
                case "near_target": return (1...100).contains(value)
                case "remaining_ms": return (0...1000).contains(value)
                case "key": return (0x31...0x33).contains(value)
                case "command": return [0x808d, 0x808e, 0x8091, 0x8092, 0x8093].contains(value)
                default: return false
                }
            }) else { throw AssetError.invalid("Invalid combat HUD setup") }
            let cheat = entry["cheat"] as? String
            guard cheat == nil || cheat == "MPKFA" else { throw AssetError.invalid("Unsupported route cheat") }
            return PlayAction(start: start, end: end, action: action, keys: Set(keys.map(UInt32.init)), place: place, cheat: cheat,
                              chaseBoss: entry["chase_boss"] as? Bool ?? false, diagnostic: diagnostic)
        }
    }
    // Debug only, off unless set. CLAW_PLAY_STEP=<file> with --fast-clock and
    // --play-script: when play reaches the plan's end, the app writes the last
    // play frame to <file> (and <file>-<frame>.png if the last action's name
    // starts with "shot") and waits up to 300 s for the plan file to be
    // extended, so an external driver can author a fixed plan in lockstep.
    private let playStepPath = ProcessInfo.processInfo.environment["CLAW_PLAY_STEP"]
    private var playScriptPath: String?
    private func extendPlayPlan(beyond end: Int, frame: CGImage) -> Bool {
        guard let playStepPath, let playScriptPath, fastClock else { return false }
        let snapshot: [String: Any] = ["play_frame": playFrames.last ?? [:], "frame": frameCount, "plan_end": end]
        if playAction.hasPrefix("shot") { try? save(frame, to: URL(fileURLWithPath: playStepPath + "-\(frameCount).png")) }
        try? JSONSerialization.data(withJSONObject: snapshot, options: [.sortedKeys])
            .write(to: URL(fileURLWithPath: playStepPath), options: .atomic)
        let began = ProcessInfo.processInfo.systemUptime
        while ProcessInfo.processInfo.systemUptime - began < 300 {
            if let data = FileManager.default.contents(atPath: playScriptPath),
               let raw = try? JSONSerialization.jsonObject(with: data) as? [[String: Any]],
               let plan = try? Self.parsePlayPlan(raw), (plan.map(\.end).max() ?? 0) > end {
                playPlan = plan
                return true
            }
            usleep(20000)
        }
        return false
    }
    // --level-two-route <plan.json> (with --menu-check, --new-game-clock): the
    // original Level 2 trace's route (Tests/NativeLevelTwo/trace.py). Level 1
    // stands 1000 ms, the eight MPSCULLY letters reach the single-player state's
    // own key-down virtual (+0x30) before each of eight frames, the results wait
    // and get one Return whenever their state object has waited 12000 ms, and
    // Level 2 replays the plan through GetAsyncKeyState for 60000 ms. Timer
    // queries advance 1 ms from the cheat until Level 2 is live, as in the trace.
    // Evidence: <menu-check>/level-two-route.json (scripts/check-level-two-play.py).
    // --level-three-route through --level-thirteen-route (spelled-out level names):
    // MPSCULLY in each earlier
    // level, results Return every 1000 ms, then the supplied target plan.
    // --level-four-boss / --level-six-boss / --level-eight-boss record the boss and continue to the next level.
    private enum RoutePhase { case off, waiting, stand, cheat(Int), results, levelTwo, levelThree, done }
    private let routeTargetSix = ProcessInfo.processInfo.arguments.contains("--level-six-route")
    private let routeTargetSeven = ProcessInfo.processInfo.arguments.contains("--level-seven-route")
    private let routeTargetFourteen = ProcessInfo.processInfo.arguments.contains("--level-fourteen-route")
    private let routeTargetThirteen = ProcessInfo.processInfo.arguments.contains("--level-thirteen-route")
    private let routeTargetTwelve = ProcessInfo.processInfo.arguments.contains("--level-twelve-route")
    private let routeTargetEleven = ProcessInfo.processInfo.arguments.contains("--level-eleven-route")
    private let routeTargetTen = ProcessInfo.processInfo.arguments.contains("--level-ten-route")
    private let routeTargetNine = ProcessInfo.processInfo.arguments.contains("--level-nine-route")
    private let routeTargetEight = ProcessInfo.processInfo.arguments.contains("--level-eight-route")
    private let routeTargetFour = ProcessInfo.processInfo.arguments.contains("--level-four-route")
    // Staged references may retain the authentic Level 2 tracer prefix.
    private var routeLevelTwoPrefix: Bool { (routeTargetFour || routeTargetFive || routeTargetSeven) && routeSourceLevel == 1 && ProcessInfo.processInfo.arguments.contains("--route-level-two-prefix") }
    private let routeTargetFive = ProcessInfo.processInfo.arguments.contains("--level-five-route")
    private var routeLaterLevel: Bool { routeTargetFourteen || routeTargetThirteen || routeTargetTwelve || routeTargetEleven || routeTargetTen || routeTargetNine || routeTargetEight || routeTargetSeven || routeTargetSix || routeTargetFive || routeTargetFour || ProcessInfo.processInfo.arguments.contains("--level-three-route") }
    private var routeTargetLevel: Int { routeTargetFourteen ? 14 : routeTargetThirteen ? 13 : routeTargetTwelve ? 12 : routeTargetEleven ? 11 : routeTargetTen ? 10 : routeTargetNine ? 9 : routeTargetEight ? 8 : routeTargetSeven ? 7 : routeTargetSix ? 6 : routeTargetFive ? 5 : (routeTargetFour ? 4 : (routeLaterLevel ? 3 : 2)) }
    private var routeSourceLevel = 1
    private var routeFileStem: String { routeTargetFourteen ? "level-fourteen" : routeTargetThirteen ? "level-thirteen" : routeTargetTwelve ? "level-twelve" : routeTargetEleven ? "level-eleven" : routeTargetTen ? "level-ten" : routeTargetNine ? "level-nine" : routeTargetEight ? "level-eight" : routeTargetSeven ? "level-seven" : routeTargetSix ? "level-six" : routeTargetFive ? "level-five" : (routeTargetFour ? "level-four" : (routeLaterLevel ? "level-three" : "level-two")) }
    private let routeBoss = ProcessInfo.processInfo.arguments.contains("--level-fourteen-boss") || ProcessInfo.processInfo.arguments.contains("--level-thirteen-boss") || ProcessInfo.processInfo.arguments.contains("--level-twelve-boss") || ProcessInfo.processInfo.arguments.contains("--level-ten-boss") || ProcessInfo.processInfo.arguments.contains("--level-six-boss") || ProcessInfo.processInfo.arguments.contains("--level-eight-boss") || ProcessInfo.processInfo.arguments.contains("--level-two-boss") || ProcessInfo.processInfo.arguments.contains("--level-four-boss")
    // Levels 7, 9 and 11 have no original boss. Their end checks use MPSCULLY after the supplied route.
    private var routeCompletesLevel: Bool { routeBoss || (routeTargetEleven && ProcessInfo.processInfo.arguments.contains("--level-eleven-end")) || (routeTargetSeven && ProcessInfo.processInfo.arguments.contains("--level-seven-end")) || (routeTargetNine && ProcessInfo.processInfo.arguments.contains("--level-nine-end")) }
    private var routeFinishingBoss = false
    private let routeBossFightOnly = ProcessInfo.processInfo.arguments.contains("--boss-fight-only")
    private let routeBossEndOnDefeat = ProcessInfo.processInfo.arguments.contains("--boss-end-on-defeat")
    private var routeBossActor: UInt32 = 0
    private var routeBossWasAlive = false
    private var routeEndingScreens: [[String]] = []
    private var routeEndingScreenLimit: Int?
    private var routeGabrielCalls: [String: UInt64] = [:]
    private var routeCheatProgress: [Int: Int] = [:]
    private var routeSecondCompletion = false
    private var routeLevelThree: [[String: Any]] = []
    private var routePhase = RoutePhase.off
    private var routePlan: [PlayAction] = []
    private var routeStart: UInt32 = 0
    // Retain every scripted input frame across paper respawns; clock still includes the fade.
    private var routeRetainsInputPlan: Bool { !routeBoss && ((routeTargetTwelve && ProcessInfo.processInfo.arguments.contains("--level-twelve-retained-plan")) || (routeTargetThirteen && ProcessInfo.processInfo.arguments.contains("--level-thirteen-retained-plan"))) }
    // Opt-in original-observed waits keep the next frame's deadline anchored
    // to the resume sample. Synchronous fade queries still advance the clock.
    private var routeFrameWaits: [UInt32] = []
    private var routeRespawnQueryEvents: [[String: Int]] = []
    private var routeFrameStep: UInt32 {
        guard routeTargetTwelve, routeRetainsInputPlan, routeInLevelThree,
              !routeFrameWaits.isEmpty else { return 17 }
        let index = max(0, routeLevelThree.count - 1)
        return index < routeFrameWaits.count ? routeFrameWaits[index] : 17
    }
    private var routeResultsStart: UInt32 = 0
    private var routeWaiting: (object: UInt32, since: UInt32)?
    private var routeLevelOne: [[String: Any]] = []
    private var routeLevelTwo: [[String: Any]] = []
    private var routeStates: [[String: Any]] = []
    private var routeKeys: [[String: Any]] = []
    private var routeAction = ""
    private var routeFlipOffset = 0
    private var routePending: [String: Any]?
    // Debug only: CLAW_ROUTE_SHOTS=<frame,...> saves those Level 2 route frames as PNG.
    private let routeShots = Set((ProcessInfo.processInfo.environment["CLAW_ROUTE_SHOTS"] ?? "").split(separator: ",").compactMap { Int($0) })
    private static let routeLetters: [(String, UInt32, UInt32)] = [("M", 0x4d, 0x32), ("P", 0x50, 0x19), ("S", 0x53, 0x1f),
        ("C", 0x43, 0x2e), ("U", 0x55, 0x16), ("L", 0x4c, 0x26), ("L", 0x4c, 0x26), ("Y", 0x59, 0x15)]
    // The route ends when Level 2 has played to its plan's last end (60000 ms for the trace's own plan).
    private var routeEnd: Int { routePlan.map(\.end).max() ?? 60000 }
    private var routeInLevelThree: Bool { if case .levelThree = routePhase { return true }; return false }
    private var routeInLevelTwo: Bool { if case .levelTwo = routePhase { return true }; return false }
    private func routeState(_ owner: ClawNativeMenuInterface, label: String) -> [String: Any] {
        let state = owner.w(owner.base.applicationToken + 0x2c)
        let vtable = state == 0 ? 0 : owner.w(state)
        var entry: [String: Any] = ["label": label, "milliseconds": Int(clock), "object": "0x" + String(state, radix: 16),
                                    "vtable": "0x" + String(vtable, radix: 16)]
        if vtable == 0x50c264 { entry["level"] = Int(owner.w(state + 0x14)) }
        let last = routeStates.last
        if last == nil || last!["object"] as? String != entry["object"] as? String || last!["vtable"] as? String != entry["vtable"] as? String {
            routeStates.append(entry)
        }
        return entry
    }
    private func routeKey(_ owner: ClawNativeMenuInterface, vk: UInt32, scan: UInt32, phase: String) throws {
        let state = owner.w(owner.base.applicationToken + 0x2c)
        let target = owner.w(owner.w(state) + 0x30)
        routeKeys.append(["phase": phase, "key": Int(vk), "scan": Int(scan), "target": "0x" + String(target, radix: 16),
                          "vtable": "0x" + String(owner.w(state), radix: 16), "milliseconds": Int(clock)])
        owner.postingAfterFrame { _ = owner.invokeBranch(target, state, [vk, (scan << 16) | 1]) }
        guard owner.resources.fault == 0 else {
            throw AssetError.invalid("Route key \(phase) faulted at \(String(owner.resources.faultAddress, radix: 16))")
        }
    }
    /// The route's work before a frame's 17 ms step, at the trace's clock.
    private func routeBeforeFrame(_ owner: ClawNativeMenuInterface) throws {
        guard let input = owner.base.windowInput else { return }
        if var pending = routePending {
            // Posted commands finish the previous frame in the original pump;
            // include synchronous fade time before sealing that frame's record.
            pending["elapsed_ms"] = Int(clock &- routeStart)
            pending["player"] = playerSnapshot(owner)
            if routeBoss { pending["boss"] = bossSnapshot(owner) }
            if routeLaterLevel && !routeCompletesLevel { routeLevelThree.append(pending) } else { routeLevelTwo.append(pending) }
            routePending = nil
            if routeRetainsInputPlan && (routeLevelThree.count - 1) * 17 >= routeEnd {
                routePhase = .done
                deferredFrameStep = false
                owner.skipIdleFrameOnce = true
                return
            }
            if !routeLaterLevel, !routeCompletesLevel, Int(clock &- routeStart) >= routeEnd {
                // A synchronous command can finish the plan before another idle
                // frame, just as the original records after draining commands.
                routePhase = .done
                deferredFrameStep = false
                owner.skipIdleFrameOnce = true
                return
            }
        }
        if case .stand = routePhase, clock &- routeStart >= 1000 {
            clockQueryStep = 1
            routePhase = .cheat(0)
        }
        if case .cheat(let index) = routePhase {
            if index < Self.routeLetters.count {
                let (letter, vk, scan) = Self.routeLetters[index]
                try routeKey(owner, vk: vk, scan: scan, phase: "\(routeSecondCompletion ? (routeLaterLevel ? "advance-level-\(routeSourceLevel)-cheat" : "level-two-complete-key") : "cheat-key")-\(index)-\(letter)")
                routePhase = .cheat(index + 1)
            } else {
                _ = routeState(owner, label: routeSecondCompletion ? "level-two-results" : "after-level-complete-command")
                routeResultsStart = clock
                routeWaiting = nil
                routePhase = .results
            }
        }
        if case .results = routePhase {
            guard clock &- routeResultsStart < 120000 else { throw AssetError.invalid("Results did not continue into Level 2") }
            let entry = routeState(owner, label: routeLaterLevel ? "level-\(routeSourceLevel)-results" : (routeSecondCompletion ? "level-two-results" : "results"))
            let state = owner.w(owner.base.applicationToken + 0x2c)
            if routeTargetFourteen && routeFinishingBoss && entry["vtable"] as? String == "0x50c1e4" {
                // Keep .results until routeAfterFrame writes the completed
                // route, including this frame's ending presentations.
                return
            }
            if entry["vtable"] as? String == "0x50c264", let level = entry["level"] as? Int, level != (routeLaterLevel ? routeSourceLevel : (routeSecondCompletion ? 2 : 1)) {
                guard level == (routeLaterLevel ? routeSourceLevel + 1 : (routeSecondCompletion ? 3 : 2)) else { throw AssetError.invalid("Results continued into level \(level)") }
                clockQueryStep = 0
                routeStart = clock
                if routeLaterLevel && level < routeTargetLevel {
                    routeSourceLevel = level
                    routeSecondCompletion = true
                    clockQueryStep = 1
                    routePhase = .cheat(0)
                    try routeBeforeFrame(owner)
                    return
                }
                if (routeTargetFour || routeTargetSix || routeTargetSeven || routeTargetEight || routeTargetNine || routeTargetTen || routeTargetEleven || routeTargetTwelve || routeTargetThirteen || routeTargetFourteen) && routeCompletesLevel && !routeFinishingBoss {
                    routePhase = .levelTwo
                    var first: [String: Any] = ["elapsed_ms": 0, "action": "loaded", "player": playerSnapshot(owner)]
                    if routeBoss { first["boss"] = bossSnapshot(owner) }
                    routeLevelTwo.append(first)
                } else if routeSecondCompletion {
                    routePhase = .levelThree
                    if routeLaterLevel && !routeFinishingBoss { routeLevelThree.append(["elapsed_ms": 0, "action": "loaded", "player": playerSnapshot(owner)]) }
                } else {
                    if routeLaterLevel {
                        routeSecondCompletion = true
                        clockQueryStep = 1
                        routePhase = .cheat(0)
                        try routeBeforeFrame(owner)
                        return
                    }
                    routePhase = .levelTwo
                    var first: [String: Any] = ["elapsed_ms": 0, "action": "loaded", "player": playerSnapshot(owner)]
                    if routeBoss { first["boss"] = bossSnapshot(owner) }
                    routeLevelTwo.append(first)
                }
            } else if state != routeWaiting?.object {
                routeWaiting = (state, clock)
            } else if clock &- routeWaiting!.since >= (routeLaterLevel && !routeLevelTwoPrefix ? 1000 : 12000) {
                try routeKey(owner, vk: 13, scan: 0x1c, phase: routeLaterLevel && !routeLevelTwoPrefix ? "level-\(routeSourceLevel)-results-return" : (routeSecondCompletion ? "level-two-results-return-" : "results-key-return-") + (entry["vtable"] as? String ?? ""))
                routeWaiting = (state, clock)
            }
        }
        var held: Set<UInt32> = []
        if case .levelThree = routePhase { routeFlipOffset = tickFlips.count }
        if routeInLevelTwo || (routeLaterLevel && !routeFinishingBoss && routeInLevelThree) {
            let elapsed = routeRetainsInputPlan ? max(0, routeLevelThree.count - 1) * 17 : Int(clock &- routeStart)
            guard let action = routePlan.first(where: { $0.start <= elapsed && elapsed < $0.end }) else {
                throw AssetError.invalid("Level 2 route plan has no action at \(elapsed) ms")
            }
            routeAction = action.action
            routeFlipOffset = tickFlips.count
            // A route entry's "set_x"/"set_y" places the player once when the entry begins, as --play-script
            // does (work/new-game Level 2 sections); the original trace writes the same words before the same frame.
            if let place = action.place, !playPlaced.contains(action.start), let actor = owner.base.heap.lookup(0x537e88, words: 1)?.pointee,
               owner.base.heap.lookup(actor + 0x4c, words: 2) != nil {
                playPlaced.insert(action.start)
                owner.put(actor + 0x4c, place.x); owner.put(actor + 0x50, place.y)
            }
            held = action.keys
            if routeBoss && action.chaseBoss {
                held.remove(0x25); held.remove(0x27)
                let actor = owner.w(0x537e88), boss = owner.w(0x5349dc)
                if actor != 0 && boss != 0 {
                    let playerX = owner.w(actor + 0x4c), bossX = owner.w(boss + 0x4c)
                    if bossX < playerX { held.insert(0x25) }
                    if bossX > playerX { held.insert(0x27) }
                }
            }
            if routeBoss, let cheat = action.cheat {
                let index = routeCheatProgress[action.start] ?? 0
                let letters: [(String, UInt32, UInt32)] = [("M", 0x4d, 0x32), ("P", 0x50, 0x19),
                    ("K", 0x4b, 0x25), ("F", 0x46, 0x21), ("A", 0x41, 0x1e)]
                if cheat == "MPKFA", index < letters.count {
                    let (letter, vk, scan) = letters[index]
                    try routeKey(owner, vk: vk, scan: scan, phase: "boss-cheat-\(action.start)-\(index)-\(letter)")
                    routeCheatProgress[action.start] = index + 1
                }
            }

        }
        for key in Self.playKeys { input.virtualKey(key, down: held.contains(key)) }
    }
    /// The route's record after a frame; returns true when the route is complete.
    private func routeAfterFrame(_ owner: ClawNativeMenuInterface) -> Bool {
        if routeTargetFourteen && routeFinishingBoss {
            routeEndingScreens.append(contentsOf: tickFlips.prefix(routeEndingScreenLimit ?? tickFlips.count).map { [String($0.pixels.prefix(16)), String($0.palette.prefix(16))] })
        }
        switch routePhase {
        case .stand:
            routeLevelOne.append(["elapsed_ms": Int(clock &- routeStart), "action": "stand", "player": playerSnapshot(owner)])
        case .levelTwo:
            let elapsed = Int(clock &- routeStart)
            var record: [String: Any] = ["elapsed_ms": elapsed, "action": routeAction, "player": playerSnapshot(owner)]
            var bossDefeated = false
            if routeBoss {
                let boss = bossSnapshot(owner)
                record["boss"] = boss
                if let health = boss["health"] as? Int {
                    let signed = Int32(bitPattern: UInt32(health))
                    bossDefeated = routeBossWasAlive && signed <= 0
                    if signed > 0 { routeBossWasAlive = true }
                }
            }
            record["screens"] = tickFlips.dropFirst(routeFlipOffset).map { [String($0.pixels.prefix(16)), String($0.palette.prefix(16))] }
            if owner.hasPostedCommands && elapsed < routeEnd {
                // The trace records a frame after its posted commands are drained;
                // here they are delivered at the start of the next pump turn.
                routePending = record
                return false
            }
            routeLevelTwo.append(record)
            // Gabriel's final handler creates EndLevelGem without the shared
            // base death callback. Replay his complete reference plan.
            if elapsed >= routeEnd || (routeBossEndOnDefeat && !routeTargetEight && bossDefeated &&
                owner.resources.transportCounts["boss-base-direct", default: 0] > 0) {
                if routeCompletesLevel && !routeBossFightOnly {
                    routeFinishingBoss = true
                    if routeLaterLevel { routeSourceLevel = routeTargetLevel }
                    routeSecondCompletion = true
                    clockQueryStep = 1
                    routePhase = .cheat(0)
                } else { routePhase = .done; return true }
            }
        case .levelThree where routeLaterLevel && !routeFinishingBoss:
            let elapsed = Int(clock &- routeStart)
            let record: [String: Any] = ["elapsed_ms": elapsed, "action": routeAction, "player": playerSnapshot(owner),
                "screens": tickFlips.dropFirst(routeFlipOffset).map { [String($0.pixels.prefix(16)), String($0.palette.prefix(16))] }]
            let planElapsed = routeRetainsInputPlan ? routeLevelThree.count * 17 : elapsed
            if owner.hasPostedCommands && planElapsed < routeEnd { routePending = record; return false }
            routeLevelThree.append(record)
            let scheduledElapsed = routeRetainsInputPlan ? (routeLevelThree.count - 1) * 17 : elapsed
            if scheduledElapsed >= routeEnd { routePhase = .done; return true }
        case .levelThree:
            routeLevelThree.append(["index": routeLevelThree.count, "player": playerSnapshot(owner),
                "screens": tickFlips.dropFirst(routeFlipOffset).map { [String($0.pixels.prefix(16)), String($0.palette.prefix(16))] }])
            if routeLevelThree.count >= 10 { routePhase = .done; return true }
        case .results where routeTargetFourteen && routeFinishingBoss:
            let state = owner.w(owner.base.applicationToken + 0x2c)
            if state != 0 && owner.w(state) == 0x50c1e4 {
                _ = routeState(owner, label:"level-\(routeSourceLevel)-results")
                routePhase = .done
                return true
            }
        case .done: return true
        default: break
        }
        return false
    }
    // Bounded diagnostic authoring: extend a boss plan at a completed frame boundary.
    // The retained plan still supplies every key/placement to the original comparison.
    private func extendBossRoute(_ owner: ClawNativeMenuInterface, frame: CGImage) {
        guard routeBossFightOnly, routeInLevelTwo, let playStepPath, fastClock,
              Int(clock &- routeStart) >= routeEnd else { return }
        let arguments = ProcessInfo.processInfo.arguments
        guard let index = arguments.firstIndex(of: "--\(routeFileStem)-route"), index + 1 < arguments.count else { return }
        let end = routeEnd
        let watched: Set<UInt32> = [0x50b21c, 0x50da04]
        let actors: [[String: Any]] = owner.base.heap.debugAllocationBases.compactMap { token in
            guard let first = owner.base.heap.lookup(token, words: 1) else { return nil }
            let table = first.pointee
            guard watched.contains(table) else { return nil }
            let actor = owner.w(token + 0xc), record = owner.w(actor + 0x6c)
            return ["vtable": String(table, radix: 16), "private": String(token, radix: 16),
                "x": owner.w(actor + 0x4c), "y": owner.w(actor + 0x50), "state": owner.w(record + 0x1c),
                "kind": owner.w(actor + 0xd0), "mask": owner.w(actor + 0xd4),
                "hit": owner.w(actor + 0x74), "attack_rect": (0..<4).map { owner.w(actor + 0x138 + UInt32($0 * 4)) },
                "bounds": (0..<4).map { owner.w(actor + 0x128 + UInt32($0 * 4)) }]
        }
        let snapshot: [String: Any] = ["elapsed_ms": Int(clock &- routeStart), "plan_end": end,
            "player": playerSnapshot(owner), "boss": bossSnapshot(owner), "weapon": weaponSnapshot(owner),
            "actors": actors, "calls": Dictionary(uniqueKeysWithValues: owner.resources.invokeCounts.filter {
                (0x406400...0x406d00).contains($0.key) || (0x43a850...0x43b400).contains($0.key)
            }.map { (String($0.key, radix: 16), $0.value) })]
        try? save(frame, to: URL(fileURLWithPath: playStepPath + ".png"))
        try? JSONSerialization.data(withJSONObject: snapshot, options: [.sortedKeys])
            .write(to: URL(fileURLWithPath: playStepPath), options: .atomic)
        let deadline = Date().addingTimeInterval(300)
        while Date() < deadline {
            if let data = try? Data(contentsOf: URL(fileURLWithPath: arguments[index + 1])),
               let raw = try? JSONSerialization.jsonObject(with: data) as? [[String: Any]],
               let plan = try? Self.parsePlayPlan(raw), (plan.map(\.end).max() ?? 0) > end {
                routePlan = plan
                return
            }
            usleep(20000)
        }
    }
    private var evidenceURL: URL?
    // Image encoding is evidence work, not part of a synchronous game
    // transition. Keep the immutable images alive on one serial writer.
    private let evidenceImages = DispatchQueue(label: "claw.evidence-images", qos: .utility)
    private let pendingEvidenceImages = DispatchGroup()
    private lazy var paperTimingURL: URL? = {
        let args = ProcessInfo.processInfo.arguments
        guard let index = args.firstIndex(of: "--paper-timing-check"), index + 1 < args.count else { return nil }
        return URL(fileURLWithPath: args[index + 1], isDirectory: true)
    }()
    private var paperTimingStart: Double?
    private var paperTimerValues: [UInt32] = []
    private var paperScreens: [String] = []
    private var evidence: [[String: Any]] = []
    private var scriptedInput: [[String: Int]] = []
    private lazy var liveURL: URL? = {
        let arguments = ProcessInfo.processInfo.arguments
        guard let index = arguments.firstIndex(of: "--menu-live-check"), index + 1 < arguments.count else { return nil }
        return URL(fileURLWithPath: arguments[index + 1], isDirectory: true)
    }()
    private var liveEvents: [[String: Any]] = []
    private var audioPoolInputs: [[String: Any]] = []
    // Debug only, off unless set. CLAW_REAL_SPEED_LOG=<dir> logs each frame's
    // original frame time and presentation count and, on failure, the failing
    // frame check. CLAW_REAL_SPEED_KEYS=<events.json> ([{"ms","key","down"}])
    // delivers keys through the live key path at wall-clock times. An event
    // {"ms","wait":<timeout ms>,"x_ge"/"x_le"/"y_ge"/"y_le"} pauses the script
    // clock until the player's position meets every bound or the timeout ends.
    private let realSpeedURL = ProcessInfo.processInfo.environment["CLAW_REAL_SPEED_LOG"].map { URL(fileURLWithPath: $0, isDirectory: true) }
    private var realSpeedKeys: [(ms: Int, event: [String: Int])] = []
    private var realSpeedStart: Double?
    private var realSpeedWaitBegan: Double?
    private var realSpeedWaited = 0
    private var realSpeedFrames: [[String: Any]] = []
    private var realSpeedLastState: UInt32?
    private var realSpeedLatestLive: [String: Any]?
    // Debug only, with CLAW_REAL_SPEED_LOG. CLAW_REAL_SPEED_CONTROL=<file> lets
    // an external controller append lines "k <code> <0|1>" (key) or "s <name>"
    // (save the next presented frame as <name>.png); the player snapshot of
    // every frame goes to <log>/live.json.
    private let realSpeedControl = ProcessInfo.processInfo.environment["CLAW_REAL_SPEED_CONTROL"]
    private var realSpeedControlOffset: UInt64 = 0
    private var realSpeedShots: [String] = []
    // Input gate: --fast-clock with CLAW_REAL_SPEED_LOG and CLAW_REAL_SPEED_CONTROL.
    // Frames run back to back on the same frame clock as the real-time run
    // (1000/60 ms per frame), but only as far as the controller allows: the app
    // starts paused at frame 0 and the control file's gate lines move it on.
    //   "run <n>"      run n more frames, then pause again;
    //   "await <key> <down|up> <n>" waits for that specific transition count
    //                  (key or mouse button, posted through the window like
    //                  hardware, scripts/post-window-input.swift) have arrived;
    //   "quit"         write real-speed.json and exit.
    // Each pause writes <log>/gate.json {"seq": gate lines done, "frame",
    // "received"}. Real events reach key() while the app is paused, between
    // two frames, as they do between two display ticks in the real-time run,
    // so the game sees them at the frame the controller chose.
    private lazy var inputGate = fastClock && realSpeedURL != nil && realSpeedControl != nil
    private var gateCommands: [(verb: String, count: Int, input: String)] = []
    private var gateQueryStep: UInt32 = 1
    private var gateQueryOverride: UInt32?
    private var landingFrameStep: UInt32?
    private var landingMove: [String: Any] = [:]
    private var gateTarget = 0
    private var gateDone = 0
    private var gateReceived = 0
    private var gateReported = -1
    private var controllerCheckSample: ClawNativeJoystickSample?
    // Every key or touch transition that reached the input view, on either clock; live.json
    // reports it so the real-time checks can tell a window event the system dropped
    // (scripts/real_input.py) from one the game ignored. Only the gate counts gateReceived.
    private var liveInputCount = 0
    private var liveInputTransitions: [String: Int] = [:]
    func liveInputArrived(_ key: UInt32, down: Bool) {
        liveInputCount += 1
        let name = "\(key):\(down ? "down" : "up")"
        liveInputTransitions[name, default: 0] += 1
        if inputGate { gateReceived += 1 }
        if let realSpeedURL {
            realSpeedFrames.append(["frame": frameCount + 1, "received_key": key, "down": down, "input_count": liveInputCount])
            try? JSONSerialization.data(withJSONObject: ["received": liveInputCount, "frame": frameCount,
                "transitions": liveInputTransitions], options: [.sortedKeys])
                .write(to: realSpeedURL.appendingPathComponent("input.json"), options: .atomic)
        }
    }
    private func pollRealSpeedControl() {
        guard let realSpeedControl, let handle = FileHandle(forReadingAtPath: realSpeedControl) else { return }
        defer { try? handle.close() }
        try? handle.seek(toOffset: realSpeedControlOffset)
        guard let data = try? handle.readToEnd(), let end = data.lastIndex(of: 10) else { return }
        realSpeedControlOffset += UInt64(end - data.startIndex + 1)
        for line in String(decoding: data[data.startIndex...end], as: UTF8.self).split(separator: "\n") {
            let parts = line.split(separator: " ")
            if inputGate, parts.count == 2, parts[0] == "query-step",
               let step = Int(parts[1]), (0...1).contains(step) {
                gateCommands.append(("query-step", step, ""))
            } else if inputGate, ProcessInfo.processInfo.arguments.contains("--platform-landing-check"),
                      parts.count == 2, parts[0] == "landing-frame-ms", let step = Int(parts[1]), (1...250).contains(step) {
                gateCommands.append(("landing-frame-ms", step, ""))
            } else if inputGate, parts.count == 2, parts[0] == "grab-place",
                      ProcessInfo.processInfo.arguments.contains("--enemy-grab-check"), let callback = UInt32(parts[1]) {
                gateCommands.append(("grab-place", Int(callback), ""))
            } else if inputGate, parts.count == 2, parts[0] == "sweep-place",
                      ProcessInfo.processInfo.arguments.contains("--crash-sweep"),
                      ProcessInfo.processInfo.arguments.contains("--mute"),let callback = UInt32(parts[1]),
                      [UInt32(0x470430),0x4232c0].contains(callback) {
                gateCommands.append(("sweep-place",Int(callback),""))
            } else if inputGate, parts.count == 2, parts[0] == "v13-boss-init",
                      ProcessInfo.processInfo.arguments.contains("--v13-boss-initialization-check"),
                      let actor = UInt32(parts[1]) {
                gateCommands.append(("v13-boss-init", Int(actor), ""))
            } else if inputGate, ProcessInfo.processInfo.arguments.contains("--custom-checkpoint-check"), parts.count == 1, ["checkpoint-score","checkpoint-loot","checkpoint-enemy","checkpoint-loot-spawn","checkpoint-drop"].contains(String(parts[0])) {
                gateCommands.append((String(parts[0]),0,""))
            } else if inputGate, ProcessInfo.processInfo.arguments.contains("--custom-checkpoint-check"), parts.count == 2, parts[0] == "checkpoint-loot-kind",let item = Int(parts[1]),(1...18).contains(item) || (41...52).contains(item) || item == 33 {
                gateCommands.append(("checkpoint-loot-kind",item,""))
            } else if inputGate, ProcessInfo.processInfo.arguments.contains("--custom-checkpoint-check"), parts.count == 2, parts[0] == "checkpoint-source",let id = Int(parts[1]),id >= 0,id <= Int(UInt32.max) {
                gateCommands.append(("checkpoint-source",id,""))
            } else if inputGate, ProcessInfo.processInfo.arguments.contains("--custom-checkpoint-check"), parts.count == 2, parts[0] == "checkpoint-mechanism",let id = Int(parts[1]),id >= 0,id <= Int(UInt32.max) {
                gateCommands.append(("checkpoint-mechanism",id,""))
            } else if inputGate, ProcessInfo.processInfo.arguments.contains("--crazyhook-checkpoint-check"), parts.count == 2, parts[0] == "checkpoint-place",let slot = Int(parts[1]),(1...2).contains(slot) {
                gateCommands.append(("checkpoint-place",slot,""))
            } else if inputGate, ProcessInfo.processInfo.arguments.contains("--lua-runtime-check"), parts.count == 2, parts[0] == "lua-gameplay-check" {
                gateCommands.append(("lua-gameplay-check",0,String(parts[1])))
            } else if inputGate, ProcessInfo.processInfo.arguments.contains("--lua-runtime-check"), parts.count == 2, parts[0] == "lua-place" {
                gateCommands.append(("lua-place",0,String(parts[1])))
            } else if inputGate, ProcessInfo.processInfo.arguments.contains("--lua-runtime-check"), parts.count == 1, ["lua-values","lua-stale","lua-gameplay","palette-values"].contains(String(parts[0])) {
                gateCommands.append((String(parts[0]),0,""))
            } else if inputGate, ["run", "await", "quit"].contains(String(parts[0])) {
                if parts[0] == "await", parts.count == 4, let count = Int(parts[3]) {
                    gateCommands.append(("await", count, "\(parts[1]):\(parts[2])"))
                } else if parts[0] != "await" {
                    gateCommands.append((String(parts[0]), parts.count > 1 ? Int(parts[1]) ?? 0 : 0, ""))
                }
            } else if parts.count == 5, parts[0] == "j", inputGate,
                      ProcessInfo.processInfo.arguments.contains("--controller-input-check"),
                      let connected = UInt32(parts[1]), let x = UInt32(parts[2]),
                      let y = UInt32(parts[3]), let buttons = UInt32(parts[4]), x <= 65535, y <= 65535 {
                // Explicit diagnostic physical samples, never labelled real hardware.
                controllerCheckSample = connected == 0 ? nil:ClawNativeJoystickSample(x:x,y:y,buttons:buttons)
            } else if parts.count == 3, parts[0] == "k", let code = UInt32(parts[1]), let down = Int(parts[2]) {
                key(code, down: down != 0)
                realSpeedFrames.append(["frame": frameCount + 1, "key": Int(code), "down": down, "control": 1])
            } else if parts.count == 2, parts[0] == "s" {
                realSpeedShots.append(String(parts[1]))
            }
        }
    }
    private func saveRealSpeed(_ extra: [String: Any]) {
        guard let realSpeedURL else { return }
        try? FileManager.default.createDirectory(at: realSpeedURL, withIntermediateDirectories: true)
        var counts: [String: UInt64] = [:]
        for (function, count) in owner?.resources.invokeCounts ?? [:] { counts[String(function, radix: 16)] = count }
        let report = extra.merging(["frames": realSpeedFrames, "completed_frames": frameCount, "invoke_counts": counts]) { current, _ in current }
        try? JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
            .write(to: realSpeedURL.appendingPathComponent("real-speed.json"), options: .atomic)
    }
    func observeInput(_ event: [String: Any]) {
        guard liveURL != nil || realSpeedURL != nil else { return }
        liveEvents.append(event.merging(["frame": frameCount]) { current, _ in current })
        if liveEvents.count > 256 { liveEvents.removeFirst(liveEvents.count - 256) }
        if let realSpeedURL {
            try? JSONSerialization.data(withJSONObject: liveEvents, options: [.sortedKeys])
                .write(to: realSpeedURL.appendingPathComponent("input-boundary.json"), options: .atomic)
        }
    }
    private func saveLiveState() throws {
        guard let liveURL, let owner else { return }
        if compactSweep && failure == nil && frameCount < gateTarget {return}
        try FileManager.default.createDirectory(at: liveURL, withIntermediateDirectories: true)
        // The menu interface exists only while the state-five object lives.
        let menuLive = owner.menuLive && owner.resources.fault == 0
        let selected = menuLive ? owner.resources.invoke(0x4dd480, owner.menuToken + 0x154) : 0
        let page = menuLive ? owner.resources.invoke(0x4dd0c0, owner.menuToken + 0x154) : 0
        let state = owner.base.heap.lookupBytes(owner.base.applicationToken + 0x2c, count: 4) == nil ? 0 : owner.w(owner.base.applicationToken + 0x2c)
        let vtable = state == 0 || owner.base.heap.lookupBytes(state, count: 4) == nil ? 0 : owner.w(state)
        let report: [String: Any] = ["status": failure == nil ? "running" : "fail", "frames": frameCount,
            "menu_live": menuLive, "state": state, "state_vtable": String(vtable, radix: 16),
            "state_level": vtable == 0 || owner.base.heap.lookupBytes(state + 0x14, count: 4) == nil ? -1 : Int(owner.w(state + 0x14)),
            "player": playerSnapshot(owner),
            "live_allocations": owner.resources.liveAllocationCount, "posted_commands": owner.postedHistory,
            "selected": selected, "page_id": page == 0 ? 0 : owner.w(page + 80),
            "events": liveEvents, "error": failure ?? "", "trace": owner.resources.failureTrace,
            "transports": owner.resources.transportCounts,
            "profiles": owner.playerChoices.map{["name":$0.name,"location":$0.location,"email":$0.email,"selected":$0.id == owner.selectedPlayer] as [String:Any]},
            "players_dialog":players?.page ?? -1,"player_dialog_events":playerDialogEvents,
            "custom_checkpoint": owner.customCheckpointEvents, "custom_checkpoint_message": owner.customCheckpointMessage,
            "saved_games": owner.saveFiles.map { ["reads": $0.reads, "writes": $0.writes, "opens": $0.opens] } ?? [:]]
        try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
            .write(to: liveURL.appendingPathComponent("live-state.json"), options: .atomic)
        if let image,!compactSweep || failure != nil { try save(image, to: liveURL.appendingPathComponent("live.png")) }
    }

    // Evidence runs opt into physical input explicitly. The controlled input
    // gate is already such an opt-in; scripts retain their existing priority.
    private var acceptsLiveInput: Bool {
        let arguments = ProcessInfo.processInfo.arguments
        return scriptedInput.isEmpty && (inputGate || arguments.contains("--menu-allow-live-input") ||
            (!arguments.contains("--menu-check") && !fastClock))
    }
    private func acceptInput(_ event: [String: Any], fromScript: Bool = false) -> Bool {
        guard fromScript || acceptsLiveInput else {
            observeInput(event.merging(["ignored": true]) { current, _ in current })
            return false
        }
        return true
    }
    func key(_ key: UInt32, down: Bool, repeatKey: Bool = false, fromScript: Bool = false) {
        guard acceptInput(["key": key, "down": down, "repeat": repeatKey], fromScript: fromScript) else { return }
        if checkpointOverlay {
            observeInput(["key":key,"down":down,"repeat":repeatKey])
            if down {
                if key == 27 {checkpointOverlay = false}
                else if key == 38 {checkpointSelectedSlot = (checkpointSelectedSlot+2)%3}
                else if key == 40 {checkpointSelectedSlot = (checkpointSelectedSlot+1)%3}
                else if key == 13 {requestCustomRestore(slot:checkpointSelectedSlot)}
            }
            return
        }
        if players != nil {
            observeInput(["key":key,"down":down,"repeat":repeatKey])
            _ = playersKey(key,down:down,fromScript:fromScript);return
        }
        if let levels = customLevels {
            observeInput(["key":key,"down":down,"repeat":repeatKey])
            if down {
                if key == 27 {closeCustomLevels()}
                else if key == 13 {chooseCustomLevel()}
                else if key == 37 || key == 39 {cycleCustomRestart()}
                else if !levels.isEmpty && (key == 38 || key == 40) {
                    customSelected = (customSelected + (key == 40 ? 1:levels.count-1)) % levels.count
                    customError = nil;customRestartSlot = 0
                }
            }
            return
        }
        if controlsKey(key,down:down,repeatKey:repeatKey) {return}
        // Movie play flags 1: any WM_KEYDOWN ends the movie and is consumed
        // (WM_SYSKEYDOWN, Option combinations here, never reaches key()).
        if movieActive {
            if down, movieFlags & 1 != 0, let movie = moviePlayback.movieID {
                movieSkipResult = 1
                moviePlayback.skip()
                movieRecords.append(["skip_key": key, "uptime": ProcessInfo.processInfo.systemUptime,
                    "movie": movie, "into": ProcessInfo.processInfo.systemUptime - movieStarted])
            }
            return
        }
        observeInput(["key": key, "down": down, "repeat": repeatKey])
        owner?.base.windowInput?.menuKey(key, down: down, repeatKey: repeatKey)
    }
    /// WM_SYSKEYDOWN/WM_SYSKEYUP (Alt, and keys held with Alt): only the
    /// GetAsyncKeyState state changes. The movie loop swallows these (0x4f0380).
    func systemKey(_ key: UInt32, down: Bool) {
        guard acceptInput(["key": key, "down": down, "system": true]) else { return }
        if playersKey(key,down:down) {return}
        if controlsKey(key,down:down) {return}
        guard !movieActive else { return }
        observeInput(["key": key, "down": down, "system": true])
        owner?.base.windowInput?.virtualKey(key, down: down)
    }
    func pointer(_ message: ClawNativeWindowInputQueue.Message, x: Int32, y: Int32, fromScript: Bool = false) {
        guard acceptInput(["message": message.rawValue, "x": x, "y": y], fromScript: fromScript) else { return }
        if controls != nil || players != nil {return}
        // Play flags 1 lack 0x100: the movie loop swallows WM_LBUTTONDOWN
        // without ending the movie, and the menu window does not exist yet.
        if movieActive {
            if message == .primaryDown && movieFlags & 0x100 != 0 {
                movieSkipResult = 0x100
                movieRecords.append(["skip_click": [x, y], "uptime": ProcessInfo.processInfo.systemUptime,
                    "movie": moviePlayback.movieID ?? 0])
                moviePlayback.skip()
            } else if message == .primaryDown {
                movieRecords.append(["ignored_click": [x, y], "uptime": ProcessInfo.processInfo.systemUptime,
                    "movie": moviePlayback.movieID ?? 0])
            }
            return
        }
        // A keyboard-only parity route elects the same stationary physical
        // cursor as the original fixture. Ignore ambient desktop hover only
        // in that gated diagnostic profile; ordinary input remains live.
        if inputGate && ProcessInfo.processInfo.arguments.contains("--stationary-cursor") && message == .mouseMove { return }
        observeInput(["message": message.rawValue, "x": x, "y": y])
        owner?.base.windowInput?.menuPointer(message: message, x: x, y: y)
    }
    func releaseInput() {
        guard acceptsLiveInput else { return }
        owner?.base.windowInput?.releaseMenuKeys()
    }

    private var windowActive = true
    func windowActivationChanged(_ active: Bool) {
        // Original WM_ACTIVATEAPP -> 0x4b88a0 sets host +0x240;
        // 0x4b9070 does not dispatch a game frame while that flag is clear.
        windowActive = active
        if !active { releaseInput() }
        if let realSpeedURL {
            let observation: [String: Any] = ["active": active, "frame": frameCount,
                "uptime": ProcessInfo.processInfo.systemUptime, "game_ms": clock]
            try? JSONSerialization.data(withJSONObject: observation, options: [.sortedKeys])
                .write(to: realSpeedURL.appendingPathComponent("activation.json"), options: .atomic)
        }
    }

    func start() {
        guard owner == nil, failure == nil, !gameBusy else { return }
        gameBusy = true
        defer { gameBusy = false }
        do {
            guard let root = Bundle.main.resourceURL?.appendingPathComponent("GameData/MENU") else {
                throw AssetError.invalid("Missing menu resources")
            }
            let arguments = ProcessInfo.processInfo.arguments
            if let index = arguments.firstIndex(of: "--menu-check"), index + 1 < arguments.count {
                evidenceURL = URL(fileURLWithPath: arguments[index + 1], isDirectory: true)
                try FileManager.default.createDirectory(at: evidenceURL!, withIntermediateDirectories: true)
                try JSONSerialization.data(withJSONObject: ["status": "running"])
                    .write(to: evidenceURL!.appendingPathComponent("app-menu.json"), options: .atomic)
                if let countIndex = arguments.firstIndex(of: "--menu-frames"), countIndex + 1 < arguments.count {
                    guard let count = Int(arguments[countIndex + 1]), (61...36001).contains(count) else {
                        throw AssetError.invalid("Menu check requires 61 through 36001 frames")
                    }
                    checkFrames = count
                }
                if let scriptIndex = arguments.firstIndex(of: "--menu-input-script"), scriptIndex + 1 < arguments.count {
                    let data = try Data(contentsOf: URL(fileURLWithPath: arguments[scriptIndex + 1]))
                    guard let events = try JSONSerialization.jsonObject(with: data) as? [[String: Any]] else {
                        throw AssetError.invalid("Invalid menu input script")
                    }
                    scriptedInput = events.map { $0.compactMapValues { $0 as? Int } }
                }
                if let playIndex = arguments.firstIndex(of: "--play-script"), playIndex + 1 < arguments.count {
                    let data = try Data(contentsOf: URL(fileURLWithPath: arguments[playIndex + 1]))
                    guard let plan = try JSONSerialization.jsonObject(with: data) as? [[String: Any]] else {
                        throw AssetError.invalid("Invalid play script")
                    }
                    playPlan = try Self.parsePlayPlan(plan)
                    playScriptPath = arguments[playIndex + 1]
                }
                if let routeIndex = arguments.firstIndex(of: "--\(routeFileStem)-route"), routeIndex + 1 < arguments.count {
                    let data = try Data(contentsOf: URL(fileURLWithPath: arguments[routeIndex + 1]))
                    guard tracerClock, playPlan.isEmpty, let plan = try JSONSerialization.jsonObject(with: data) as? [[String: Any]] else {
                        throw AssetError.invalid("Invalid Level 2 route (needs --new-game-clock and no --play-script)")
                    }
                    routePlan = try Self.parsePlayPlan(plan)
                    if routeTargetTwelve, routeRetainsInputPlan,
                       let index = arguments.firstIndex(of: "--level-twelve-frame-waits"), index + 1 < arguments.count {
                        routeFrameWaits = try JSONDecoder().decode([UInt32].self,
                            from: Data(contentsOf: URL(fileURLWithPath: arguments[index + 1])))
                        guard routeFrameWaits.count * 17 == routeEnd,
                              routeFrameWaits.allSatisfy({ $0 > 0 && $0 <= 17 }) else {
                            throw AssetError.invalid("Invalid Level 12 physical frame waits")
                        }
                    }
                    routePhase = .waiting
                }
            }
            func metadata(_ name: String) throws -> [UInt32: Data] {
                let raw = try JSONDecoder().decode([String: [UInt8]].self,
                    from: Data(contentsOf: root.appendingPathComponent(name)))
                var result: [UInt32: Data] = [:]
                for (key, bytes) in raw {
                    guard let address = UInt32(key, radix: 16) else { throw AssetError.invalid("Invalid menu metadata") }
                    result[address] = Data(bytes)
                }
                return result
            }
            let base = try ClawNativeMenuBase(root: root, literals: metadata("literals.json"))
            if inputGate, arguments.contains("--controller-input-check") {
                base.windowInput?.joystickSampler = { [weak self] in self?.controllerCheckSample }
            }
            try base.palette!.display!.installMenuFont(Data(contentsOf: root.appendingPathComponent("font.json")))
            base.palette!.display!.recordsCreditsEvidence = routeTargetFourteen && routeBoss
            let menu = try ClawNativeMenuInterface(base: base,
                archiveURL: root.appendingPathComponent("CLAW.REZ"), metadata: metadata("metadata.json"),
                clock: { [weak self] in
                    if let self, self.evidenceURL != nil || self.inputGate || arguments.contains("--test-level") || arguments.contains("--object-coverage") {
                        // The tracer's timer service steps before it answers.
                        // The native game also polls time inside blocking transitions
                        // (paper rolls, fades and level completion). The gated clock
                        // advances deterministically on those queries as well as frames.
                        if self.inputGate { self.clock &+= self.owner?.deliveringAccelerator == true || self.owner?.resizingPresentation == true || self.owner?.restoringCustomMenu == true ? 1 : self.gateQueryStep }
                        else if self.tracerClock {
                            // The paper respawn command polls timers synchronously,
                            // between route frames, as in the original recorder.
                            let paperRespawn = self.owner?.deliveringPostedCommand == 0x803a
                                && !arguments.contains("--no-paper-startup")
                            let before = self.clock
                            self.clock &+= paperRespawn || self.owner?.resizingPresentation == true ? 1 : self.clockQueryStep
                            if paperRespawn, self.routeTargetTwelve, self.routeRetainsInputPlan, self.routeInLevelThree {
                                self.routeRespawnQueryEvents.append(["scheduled_ms": self.routeLevelThree.count * 17,
                                    "elapsed_ms": Int(self.clock &- self.routeStart), "increment_ms": Int(self.clock &- before)])
                            }
                        }
                        if self.paperTimingStart != nil { self.paperTimerValues.append(self.clock) }
                        return self.clock
                    }
                    let value = UInt32(truncatingIfNeeded: UInt64(ProcessInfo.processInfo.systemUptime * 1000))
                    if let self, self.paperTimingStart != nil { self.paperTimerValues.append(value) }
                    return value
                })
            menu.checkpointFramePhase = { [weak self] in
                guard let self,self.inputGate else {return nil}
                return UInt32((self.frameCount+self.checkpointCadenceOffset) % 3)
            }
            menu.restoreCheckpointFramePhase = { [weak self] phase in
                guard let self,self.inputGate else {return}
                self.checkpointCadenceOffset = (Int(phase)+3-self.frameCount % 3) % 3
            }
            let yieldEvents: () -> Void = { ClawWindowEventPump.yieldIfNeeded() }
            if arguments.contains("--paper-clock-check") {
                menu.observeClockRead = { [weak self] caller,value in
                    guard let self else {return}
                    self.clockReads.append(["caller":caller,"milliseconds":value])
                }
            }
            menu.yieldWindowEvents = yieldEvents
            base.palette?.yieldWindowEvents = yieldEvents
            base.windowInput?.queue.yieldWindowEvents = yieldEvents
            if arguments.contains("--responsiveness-check") || movieCheckURL != nil || paperTimingURL != nil {
                heartbeat.enabled = true
                menu.resources.observeBlockingInvocation = { [weak self] function, entering in
                    guard let self else { return }
                    if entering { self.heartbeatScopes.append(self.heartbeat.begin(String(format:"0x%x",function))) }
                    else if let scope = self.heartbeatScopes.popLast() { self.heartbeat.end(scope) }
                    if function == 0x4ec9c0, let directory = self.paperTimingURL {
                        if entering {
                            self.paperScreens.removeAll(); self.paperTimerValues.removeAll()
                            self.paperTimingStart = ProcessInfo.processInfo.systemUptime
                        } else if let began = self.paperTimingStart {
                            let seconds = ProcessInfo.processInfo.systemUptime - began
                            self.paperTimingStart = nil
                            let report: [String: Any] = ["seconds": seconds,
                                "primary_writes": self.paperScreens, "timer_values": self.paperTimerValues,
                                "fast_clock": self.fastClock, "input_gate": self.inputGate,
                                "responsiveness": self.heartbeat.records]
                            try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
                            try? JSONSerialization.data(withJSONObject: report, options: [.sortedKeys])
                                .write(to: directory.appendingPathComponent("paper-timing.json"), options: .atomic)
                        }
                    }
                }
            }
            let acceleratorURL = root.appendingPathComponent("accelerators.json")
            if FileManager.default.fileExists(atPath: acceleratorURL.path) {
                let entries = try JSONDecoder().decode([[String: UInt32]].self, from: Data(contentsOf: acceleratorURL))
                menu.accelerators = try entries.map {
                    guard let flags = $0["flags"], let key = $0["key"], let command = $0["command"] else {
                        throw AssetError.invalid("Invalid accelerator table")
                    }
                    return (flags, key, command)
                }
            }
            if FileManager.default.fileExists(atPath: root.appendingPathComponent("level-one-data.json").path) {
                menu.levelOneData = try metadata("level-one-data.json")
            }
            // Saved games (CLAW.USR): --save-dir <dir>, else the app's data folder
            // for a normal launch; deterministic check launches keep none.
            let launchArguments = ProcessInfo.processInfo.arguments
            if let index = launchArguments.firstIndex(of: "--save-dir"), index + 1 < launchArguments.count {
                menu.saveDirectory = URL(fileURLWithPath: launchArguments[index + 1], isDirectory: true)
            } else if startupMoviesEnabled, movieCheckURL == nil, let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first {
                menu.saveDirectory = support.appendingPathComponent("Claw/Saves", isDirectory: true)
            }
            // Registry settings: --settings-dir <dir>, else the app's data
            // folder for a normal launch; check launches keep none, so each
            // starts from the original's fresh-install defaults.
            if let index = launchArguments.firstIndex(of: "--settings-dir"), index + 1 < launchArguments.count {
                menu.settingsDirectory = URL(fileURLWithPath: launchArguments[index + 1], isDirectory: true)
            } else if startupMoviesEnabled, movieCheckURL == nil, let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first {
                menu.settingsDirectory = support.appendingPathComponent("Claw/Settings", isDirectory: true)
            }
            if let index = launchArguments.firstIndex(of: "--screen-dump-dir"), index + 1 < launchArguments.count {
                menu.screenDumpDirectory = URL(fileURLWithPath: launchArguments[index + 1], isDirectory: true)
            } else if let documents = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first {
                menu.screenDumpDirectory = documents.appendingPathComponent("Screen Dumps", isDirectory: true)
            }
            if let data = try? Data(contentsOf: root.appendingPathComponent("level-one-transports.json")) {
                try menu.resources.installLevelTransports(data)
            }
            menu.showControls = { [weak self, unowned menu] in
                self?.controls = ControlsState(keys:menu.controlKeys,buttons:menu.controlButtons,disableJoystick:menu.joystickDisabled)
                #if !targetEnvironment(macCatalyst)
                self?.controls?.touchControls = self?.touchControlsEnabled ?? false
                #endif
            }
            menu.showCustomLevels = { [weak self] in self?.showCustomLevels() }
            try FileManager.default.createDirectory(at:customDirectory,withIntermediateDirectories:true)
            menu.showPlayers = { [weak self, unowned menu] in
                self?.players = PlayersState(choices:menu.playerChoices,selected:menu.selectedPlayer)
            }
            menu.postedCommandsDelivered = { [weak self, unowned menu] in
                guard let self, self.tracerClock else { return }
                let current = menu.w(menu.base.applicationToken + 0x2c)
                if self.routeTargetFourteen && self.routeFinishingBoss && current != 0 && menu.w(current) == 0x50c1e4 && self.routeEndingScreenLimit == nil {
                    // The original ending observer stops when the return
                    // command selects the menu, before its next idle frame.
                    self.routeEndingScreenLimit = self.tickFlips.count
                }
                defer { if self.deferredFrameStep { self.clock &+= self.routeFrameStep; self.deferredFrameStep = false } }
                defer {
                    if self.deferredFrameStep, self.failure == nil {
                        switch self.routePhase {
                        case .off, .waiting, .done: break
                        default: do { try self.routeBeforeFrame(menu) } catch { self.stop(error: error) }
                        }
                    }
                }
                guard self.clockQueryStep != 0 else { return }
                // The launch command loaded Level 1 (the join's play phase):
                // timer queries stop advancing the clock; only the 17 ms
                // frame step does.
                let state = menu.w(menu.base.applicationToken + 0x2c)
                guard state != 0, menu.w(state) == 0x50c264, menu.w(state + 0x14) == 1 else { return }
                self.clockQueryStep = 0
                if case .waiting = self.routePhase {
                    self.routeStart = self.clock
                    self.routePhase = .stand
                    _ = self.routeState(menu, label: "level-one-loaded")
                    self.routeLevelOne.append(["elapsed_ms": 0, "action": "loaded", "player": self.playerSnapshot(menu)])
                }
                if !self.playPlan.isEmpty {
                    // The join's "loaded" record, taken when the launch
                    // command returns, then its 17 ms step to the first
                    // gameplay frame, which runs later in this pump turn.
                    self.playStart = self.clock
                    self.recordPlayFrame(menu, elapsed: 0, action: "loaded")
                    self.holdPlayKeys(menu, elapsed: 0)
                }
            }
            if realSpeedURL != nil, let path = ProcessInfo.processInfo.environment["CLAW_REAL_SPEED_KEYS"] {
                guard let events = try JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: path))) as? [[String: Int]] else {
                    throw AssetError.invalid("Invalid real-speed key script")
                }
                realSpeedKeys = try events.map { event in
                    guard let ms = event["ms"], (event["key"] != nil && event["down"] != nil) || event["wait"] != nil ||
                          (event["message"] != nil && event["x"] != nil && event["y"] != nil) else {
                        throw AssetError.invalid("Invalid real-speed input event")
                    }
                    return (ms, event)
                }.sorted { $0.ms < $1.ms }
            }
            base.palette?.display?.presented = { [weak self] pixels, width, height, stride in
                self?.flipped(pixels, width: width, height: height, stride: stride)
            }
            base.palette?.display?.primaryWritten = { [weak self] pixels, width, height, stride, detail in
                self?.primaryWritten(pixels, width: width, height: height, stride: stride, detail: detail)
            }
            base.palette?.screenPaletteChanged = { [weak self] in self?.paletteChanged() }
            owner = menu
            menu.customMessageBox = { title,text in
                guard let scene = UIApplication.shared.connectedScenes.compactMap({$0 as? UIWindowScene}).first,
                      var controller = scene.windows.first(where:{$0.isKeyWindow})?.rootViewController else {
                    throw ClawCustomLua.Failure.script("MessageBox: no foreground window")
                }
                while let presented = controller.presentedViewController {controller = presented}
                let alert = UIAlertController(title:title,message:text,preferredStyle:.alert)
                var acknowledged = false
                let action = UIAlertAction(title:"OK",style:.default) {_ in acknowledged = true}
                alert.addAction(action);alert.preferredAction = action
                let diagnosticURL = ProcessInfo.processInfo.arguments.contains("--lua-runtime-check") && ProcessInfo.processInfo.arguments.contains("--mute") ? ProcessInfo.processInfo.environment["CLAW_REAL_SPEED_LOG"].map {URL(fileURLWithPath:$0).appendingPathComponent("script-message.json")}:nil
                func recordMessage(_ waiting:Bool) {
                    if let diagnosticURL {try? JSONSerialization.data(withJSONObject:["title":title,"text":text,"waiting":waiting]).write(to:diagnosticURL,options:.atomic)}
                }
                controller.present(alert,animated:false)
                recordMessage(true)
                // Keep native event delivery alive while the script waits for
                // the sheet, as the original synchronous MessageBox does.
                while !acknowledged {ClawWindowEventPump.pump(for:0.01)}
                recordMessage(false)
            }
            if arguments.contains("--platform-landing-check"), arguments.contains("--mute"), inputGate {
                let previous = menu.resources.observeInvocation
                menu.resources.observeInvocation = { [weak self, weak menu] function, receiver, args in
                    previous?(function, receiver, args)
                    guard let self, let menu, function == 0x4cbb60, args.count == 4,
                          args[0] == menu.w(0x537e88) else { return }
                    let actor = args[0]
                    self.landingMove = ["frame": self.frameCount + 1, "x": menu.w(actor + 0x4c),
                        "y": menu.w(actor + 0x50), "mode": menu.w(actor + 0xcc), "flags": menu.w(actor + 8),
                        "target_x": args[1], "target_y": args[2], "options": args[3],
                        "step_x": menu.w(actor + 0xdc), "step_y": menu.w(actor + 0xe0),
                        "rectangle": (0..<4).map { menu.w(actor + 0x118 + UInt32($0 * 4)) }]
                }
            }
            if ProcessInfo.processInfo.environment["CLAW_AUDIO_POOL_EVIDENCE"] == "1" {
                let previous = menu.resources.observeInvocation
                menu.resources.observeInvocation = { [weak self, weak menu] function, receiver, arguments in
                    previous?(function, receiver, arguments)
                    if function == 0x4b4430, let audio = menu?.base.audio {
                        self?.audioPoolInputs.append(audio.poolInputEvidence(receiver))
                    }
                }
            }
            if (routeTargetEight || routeTargetFourteen) && routeBoss {
                let previous = menu.resources.observeInvocation
                menu.resources.observeInvocation = { [weak self] function, receiver, arguments in
                    previous?(function, receiver, arguments)
                    guard let self, self.routeInLevelTwo,
                          [UInt32(0x443290), 0x491fa0, 0x445720, 0x40e5c0,
                           0x464360, 0x4642b0, 0x464a60, 0x464b90].contains(function) else { return }
                    self.routeGabrielCalls["0x" + String(function, radix: 16), default: 0] += 1
                }
            }
            if startupMoviesEnabled || movieFlowCheck, let movies = Bundle.main.resourceURL?.appendingPathComponent("GameData/MOVIES"),
               FileManager.default.fileExists(atPath: movies.appendingPathComponent("movies.json").path) {
                let catalog = try ClawNativeMovieCatalog(directory: movies)
                movieCatalog = catalog
                menu.movieAvailable = { [weak self] movie in
                    guard let self else { return false }
                    // The retained deterministic prefix omits movies. This
                    // acceptance run enables playback at the Level 14 ending.
                    if self.routeTargetFourteen && self.routeBoss && self.movieFlowCheck && !self.routeFinishingBoss { return false }
                    return (try? catalog.file(movieID: movie)) != nil
                }
                menu.moviePlay = { [weak self] in self?.playMovie($0, flags: $1) ?? 0 }
                menu.movieBackgroundFile = { try? catalog.file(movieID:$0) }
                menu.configureMovieContainer(movies.path.replacingOccurrences(of: "/", with: "\\") + "\\CLAW.FEC")
            }
            // Menu initialization queries archive availability to enable
            // Replay Movies, so the movie service must exist before it runs.
            try menu.initialize()
            if movieCatalog != nil {
                // Outside SwiftUI's appearance update and outside a main-queue
                // block (GCD's main queue does not drain re-entrantly, and the
                // player completes through it): a run-loop block.
                if !movieFlowCheck {
                movieStage = true
                RunLoop.main.perform(inModes: [.default]) { [weak self, unowned menu] in self?.runStartupMovies(menu) }
                return
                }
            }
            try menu.enter()
            if let index = arguments.firstIndex(of:"--capability-package-check"),index+1 < arguments.count {
                let request = URL(fileURLWithPath:arguments[index+1])
                let paths = try JSONDecoder().decode([String:String].self,from:Data(contentsOf:request))
                var reports:[String:Any] = [:]
                var imports:[String:String] = [:]
                for (name,path) in paths {
                    do {reports[name] = try JSONSerialization.jsonObject(with:JSONEncoder().encode(ClawCustomCapabilities.preflight(URL(fileURLWithPath:path))))}
                    catch {reports[name] = ["error":error.localizedDescription]}
                    let url = URL(fileURLWithPath:path)
                    do {_ = try ClawCustomAssets.importPackage(url,into:url.deletingLastPathComponent());imports[name] = "same shared preflight accepted"}
                    catch {imports[name] = error.localizedDescription}
                }
                var apiReport:[String:String] = [:]
                let apiURL = request.deletingLastPathComponent().appendingPathComponent("apis.json")
                if let data = try? Data(contentsOf:apiURL),let names = try? JSONDecoder().decode([String].self,from:data),let first = paths.values.sorted().first {
                    apiReport = try menu.checkCapabilityAPIs(names,worldURL:URL(fileURLWithPath:first))
                }
                let result:[String:Any] = ["registry":ClawCustomCapabilities.groups,"packages":reports,"apis":apiReport,"imports":imports]
                try JSONSerialization.data(withJSONObject:result,options:[.sortedKeys]).write(to:request.deletingLastPathComponent().appendingPathComponent("capabilities.json"),options:.atomic)
            }
            if let index = arguments.firstIndex(of:"--checkpoint-package-check"),index+1 < arguments.count {
                let request = URL(fileURLWithPath:arguments[index+1])
                let paths = try JSONDecoder().decode([String:String].self,from:Data(contentsOf:request))
                var result:[String:Any] = [:]
                for (key,path) in paths {
                    let package = try ClawCustomAssets(worldURL:URL(fileURLWithPath:path))
                    result[key] = ["script_owned":ClawCrazyHookSaves.scriptOwned(package),
                                   "restart_slots":try menu.customRestartSlots(URL(fileURLWithPath:path))] as [String:Any]
                }
                try JSONSerialization.data(withJSONObject:result,options:[.sortedKeys]).write(to:request.deletingLastPathComponent().appendingPathComponent("ownership.json"),options:.atomic)
            }
            if let index = arguments.firstIndex(of:"--checkpoint-store-check"),index+1 < arguments.count {
                let output = URL(fileURLWithPath:arguments[index+1])
                let result = try ClawCrazyHookSaves.checkStore(output.deletingLastPathComponent())
                _ = try menu.createPlayer(name:"CheckpointCheck",location:"Fixture",email:"")
                try JSONSerialization.data(withJSONObject:result,options:[.sortedKeys]).write(to:output,options:.atomic)
            }
            if let index = arguments.firstIndex(of:"--asset-package-check"),index+1 < arguments.count {
                let request = URL(fileURLWithPath:arguments[index+1])
                try menu.checkAssetPackages(request,request.deletingLastPathComponent().appendingPathComponent("packages.json"))
            }
            if let index = arguments.firstIndex(of:"--audio-package-check"),index+1 < arguments.count {
                let request = URL(fileURLWithPath:arguments[index+1])
                try menu.checkAudioPackages(request,request.deletingLastPathComponent().appendingPathComponent("audio-packages.json"))
            }
            if let index = arguments.firstIndex(of:"--plane-geometry-check"),index+1 < arguments.count {
                let request = URL(fileURLWithPath:arguments[index+1])
                try menu.checkPlaneGeometry(request,request.deletingLastPathComponent().appendingPathComponent("geometry.json"))
            }
            if arguments.contains("--object-coverage") {
                runObjectCoverage(menu: menu, arguments: arguments)
                return
            }
            if let index = arguments.firstIndex(of:"--crash-sweep-level") ??
                (arguments.contains("--custom-checkpoint-check") ? arguments.firstIndex(of:"--custom-checkpoint-level") : nil) {
                guard index+1 < arguments.count,let level = UInt32(arguments[index+1]),(1...14).contains(level) else {throw ClawCustomCheckpoint.Failure.invalidFile}
                // Diagnostic entry uses the original menu transitions and New
                // Game command; no test world, player edits or level finishing.
                for _ in 0..<2 {
                    let state = menu.w(base.applicationToken+0x2c)
                    _ = menu.invokeBranch(menu.w(menu.w(state)+0x30),state,[13,0x001c0001])
                    for _ in 0..<24 {clock &+= 17;try menu.frame()}
                }
                _ = menu.invokeBranch(0x426e30,base.applicationToken,[0,0x807f,level])
                let state = menu.w(base.applicationToken+0x2c)
                guard menu.resources.fault == 0,menu.w(state) == 0x50c264,menu.w(state+0x14) == level else {throw ClawCustomCheckpoint.Failure.unavailable}
                gateQueryStep = 0
            }
            if let index = arguments.firstIndex(of: "--crash-sweep-custom") {
                guard inputGate, arguments.contains("--mute"), index + 1 < arguments.count else {
                    throw AssetError.invalid("Crash sweep requires muted frame-gated input and a custom level path")
                }
                try menu.startCustomLevel(URL(fileURLWithPath: arguments[index + 1]))
                gateQueryStep = 0
            }
            if let index = arguments.firstIndex(of: "--test-level") {
                guard index + 1 < arguments.count else {throw AssetError.invalid("--test-level needs a local WWD path")}
                // Follow the original Single Player / New Game transitions
                // before its launch command: they establish the scene owners
                // which replacing the main menu directly would retire.
                for _ in 0..<2 {
                    let state = menu.w(base.applicationToken+0x2c)
                    let target = menu.w(menu.w(state)+0x30)
                    _ = menu.invokeBranch(target,state,[13,0x001c0001])
                    for _ in 0..<24 {clock &+= 17;try menu.frame()}
                }
                let level = try menu.resources.installLocalTestWorld(URL(fileURLWithPath:arguments[index+1]))
                // Use the original New Game command, with the same explicit
                // compressed-file fixture as the original test-level observer.
                _ = menu.invokeBranch(0x426e30,base.applicationToken,[0,0x807f,level])
                let state = menu.w(base.applicationToken+0x2c)
                guard menu.resources.fault == 0,state != 0,menu.w(state) == 0x50c264,menu.w(state+0x14) == level,
                      menu.resources.localTestWorldEvidence["substitutions"] as? Int == 1 else {
                    throw AssetError.invalid("Local test world launch failed at \(String(menu.resources.faultAddress,radix:16))")
                }
                clockQueryStep = 0
            }
            gameBusy = false
            tick()
        } catch { stop(error: error) }
    }

    // Diagnostic only: observe the normal game's canonical WWD loader before
    // any gameplay frame. One process per level keeps startup ownership intact.
    private func runObjectCoverage(menu: ClawNativeMenuInterface, arguments: [String]) {
        do {
            guard arguments.contains("--mute"), arguments.contains("--new-game-clock"),
                  let index = arguments.firstIndex(of: "--object-coverage"), index + 1 < arguments.count,
                  let levelIndex = arguments.firstIndex(of: "--object-coverage-level"), levelIndex + 1 < arguments.count,
                  let level = Int(arguments[levelIndex + 1]), (1...14).contains(level),
                  let root = Bundle.main.resourceURL?.appendingPathComponent("GameData") else {
                throw AssetError.invalid("Object coverage requires --mute, --new-game-clock, output directory and level 1...14")
            }
            let directory = URL(fileURLWithPath: arguments[index + 1], isDirectory: true)
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            let data = try Data(contentsOf: root.appendingPathComponent("LEVEL\(level)/WORLDS/WORLD.WWD"))
            let world = try ClawWorld(data: data)
            for _ in 0..<2 {
                let state = menu.w(menu.base.applicationToken + 0x2c)
                _ = menu.invokeBranch(menu.w(menu.w(state) + 0x30), state, [13, 0x001c0001])
                for _ in 0..<24 { clock &+= 17; try menu.frame() }
            }
            var outcomes: [Int: String] = [:], actors: [Int: UInt32] = [:], cursors: [Int: Int] = [:]
            var active: ClawWorld.Object?, allocated: UInt32 = 0
            var errors: [String] = [], duplicateVisits = 0
            menu.resources.observeInvocation = { [unowned menu] function, receiver, args in
                guard function == 0x4d17e0 else { return }
                let plane = Int(menu.w(receiver + 4)), ordinal = cursors[Int(menu.w(receiver + 4)), default: 0]
                guard active == nil, world.planes.indices.contains(plane),
                      world.planes[plane].objects.indices.contains(ordinal), let record = args.first else {
                    errors.append("Unmatched WWD loader invocation"); return
                }
                let object = world.planes[plane].objects[ordinal]
                cursors[plane] = ordinal + 1
                guard menu.w(record) == UInt32(bitPattern: Int32(object.id)),
                      menu.w(record + 0x14) == UInt32(bitPattern: Int32(object.x)),
                      menu.w(record + 0x18) == UInt32(bitPattern: Int32(object.y)),
                      let bytes = menu.resources.heap.lookupBytes(record, count: UInt32(object.encodedRecord.count)),
                      Data(bytes: bytes, count: object.encodedRecord.count) == object.encodedRecord else {
                    errors.append("WWD placement bytes differ at \(object.encodedRecordOffset)"); return
                }
                active = object; allocated = 0
                if outcomes.updateValue("load-error", forKey: object.encodedRecordOffset) != nil { duplicateVisits += 1 }
            }
            menu.resources.observeAllocation = { token, bytes in
                if active != nil, allocated == 0, bytes == 0x1b4 { allocated = token }
            }
            menu.resources.completedInvocation = { [unowned menu] function, consumed in
                guard function == 0x4d17e0, let object = active else { return }
                let live = allocated != 0 && menu.resources.allocationData(allocated) != nil && menu.w(allocated + 0x6c) != 0
                outcomes[object.encodedRecordOffset] = consumed != object.encodedRecord.count ? "load-error" : live ? "instantiated" : "loader-returned-no-actor"
                if live { actors[object.encodedRecordOffset] = allocated }
                active = nil; allocated = 0
            }
            _ = menu.invokeBranch(0x426e30, menu.base.applicationToken, [0, 0x807f, UInt32(level)])
            var skipped: [String: [[String: Any]]] = [:]
            var placed = 0, instantiated = 0
            for (planeIndex, plane) in world.planes.enumerated() {
                for object in plane.objects {
                    placed += 1
                    let outcome = outcomes[object.encodedRecordOffset] ?? "not-visited"
                    if outcome == "instantiated" { instantiated += 1; continue }
                    let callback = object.logic.withCString { claw_logic_registry_find($0)?.pointee.callback ?? 0 }
                    skipped[object.logic, default: []].append([
                        "id": object.id, "x": object.x, "y": object.y, "z": object.z,
                        "plane": planeIndex, "plane_name": plane.name, "record_offset": object.encodedRecordOffset,
                        "reason": outcome, "callback": String(format: "0x%08x", callback)])
                }
            }
            let state = menu.w(menu.base.applicationToken + 0x2c)
            if menu.resources.fault != 0 || menu.w(state) != 0x50c264 || menu.w(state + 0x14) != level {
                errors.append("Level launch failed at \(String(menu.resources.faultAddress, radix: 16))")
            }
            var row: [String: Any] = ["level": level, "placed": placed, "instantiated": instantiated,
                "visited": outcomes.count, "duplicate_visits": duplicateVisits, "skipped_count": placed - instantiated,
                "fault": menu.resources.fault, "wwd_sha256": SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined(),
                "skipped": skipped.keys.sorted().map { ["logic": $0, "count": skipped[$0]!.count, "placements": skipped[$0]!] as [String: Any] },
                "instantiated_placements": actors.keys.sorted().map { ["record_offset": $0, "actor": Int(actors[$0]!)] }]
            if !errors.isEmpty { row["error"] = errors.joined(separator: "; ") }
            try JSONSerialization.data(withJSONObject: row, options: [.prettyPrinted, .sortedKeys])
                .write(to: directory.appendingPathComponent("level-\(level).json"), options: .atomic)
            exit(errors.isEmpty ? 0 : 1)
        } catch {
            fputs("Object coverage: \(error)\n", stderr)
            exit(1)
        }
    }

    private func indexedImage(_ pixels: Data, width: UInt32, height: UInt32, stride: UInt32, palette: Data) -> CGImage? {
        guard palette.count == 768, let provider = CGDataProvider(data: pixels as CFData) else { return nil }
        let colors = palette.withUnsafeBytes { bytes in
            CGColorSpace(indexedBaseSpace: CGColorSpaceCreateDeviceRGB(), last: 255,
                colorTable: bytes.baseAddress!.assumingMemoryBound(to: UInt8.self))
        }
        guard let colors else { return nil }
        return CGImage(width: Int(width), height: Int(height), bitsPerComponent: 8, bitsPerPixel: 8,
            bytesPerRow: Int(stride), space: colors, bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.none.rawValue),
            provider: provider, decode: nil, shouldInterpolate: false, intent: .defaultIntent)
    }
    private func show(_ frame: CGImage) {
        CATransaction.begin(); CATransaction.setDisableActions(true)
        surfaceLayer.contents = frame
        CATransaction.commit()
    }
    // A primary Flip, through the palette current at that moment. Committed
    // now: the launch command flips the loading screen and then loads the
    // level before it returns to the run loop.
    private static func hash(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }
    private static func paletteHash(_ rgb: Data) -> String {
        var entries = Data()
        for offset in Swift.stride(from: 0, to: rgb.count, by: 3) { entries.append(rgb[offset..<offset + 3]); entries.append(0) }
        return hash(entries)
    }
    private func flipped(_ pixels: Data, width: UInt32, height: UInt32, stride: UInt32) {
        defer { ClawWindowEventPump.yieldIfNeeded() }
        let pixelHash = evidenceURL == nil ? "" : Self.hash(pixels)
        front = (pixels, width, height, stride, pixelHash)
        guard let palette = owner?.base.palette?.currentRGB,
              let frame = indexedImage(pixels, width: width, height: height, stride: stride, palette: palette) else { return }
        show(frame)
        CATransaction.flush()
        if evidenceURL != nil {
            let paletteHash = Self.paletteHash(palette)
            tickFlips.append((pixelHash, paletteHash, pixels.reduce(0) { $1 == 0 ? $0 : $0 + 1 }, frame))
            if tickScreens.last != [pixelHash, paletteHash] { tickScreens.append([pixelHash, paletteHash]) }
        }
    }
    // Game code wrote the primary surface itself: the screen shows it at once,
    // through the current palette, with no Flip.
    private func primaryWritten(_ pixels: Data, width: UInt32, height: UInt32, stride: UInt32, detail: [String: Any]) {
        defer { ClawWindowEventPump.yieldIfNeeded() }
        let before = front
        let pixelHash = evidenceURL == nil && paperTimingStart == nil ? "" : Self.hash(pixels)
        if paperTimingStart != nil { paperScreens.append(pixelHash) }
        front = (pixels, width, height, stride, pixelHash)
        guard let palette = owner?.base.palette?.currentRGB,
              let frame = indexedImage(pixels, width: width, height: height, stride: stride, palette: palette) else { return }
        show(frame)
        CATransaction.flush()
        guard let evidenceURL else { return }
        var write = detail
        write["pixels_sha256"] = pixelHash
        write["before_sha256"] = before?.hash ?? ""
        write["width"] = Int(width); write["height"] = Int(height); write["stride"] = Int(stride)
        if tickPrimaryWrites.isEmpty, let before {
            // The front the first write started from, so a check can replay the original's writes on it.
            let name = String(format: "primary-%04d-base.raw", frameCount + 1)
            try? before.pixels.write(to: evidenceURL.appendingPathComponent(name))
            write["base"] = name
        }
        let name = String(format: "primary-%04d-%02d.png", frameCount + 1, tickPrimaryWrites.count + 1)
        let destination = evidenceURL.appendingPathComponent(name)
        evidenceImages.async(group: pendingEvidenceImages) {
            try? Self.saveImage(frame, to: destination)
        }
        write["png"] = name
        tickPrimaryWrites.append(write)
        let screen = [pixelHash, Self.paletteHash(palette)]
        if tickScreens.last != screen { tickScreens.append(screen) }
    }
    // The attached palette changed: the screen shows the same front pixels
    // through it at once.
    private func paletteChanged() {
        defer { ClawWindowEventPump.yieldIfNeeded() }
        guard let front, let palette = owner?.base.palette?.currentRGB,
              let frame = indexedImage(front.pixels, width: front.width, height: front.height, stride: front.stride, palette: palette) else { return }
        show(frame)
        CATransaction.flush()
        if evidenceURL != nil {
            tickPaletteChanges += 1
            let screen = [front.hash, Self.paletteHash(palette)]
            if tickScreens.last != screen {
                tickScreens.append(screen)
                if tickScreens.count % 50 == 0, let evidenceURL {
                    try? save(frame, to: evidenceURL.appendingPathComponent(String(format: "screen-%04d-%04d.png", frameCount + 1, tickScreens.count)))
                }
            }
        }
    }

    private var controllerNavigation = ClawControllerNavigation()

    func tick() {
        #if !targetEnvironment(macCatalyst)
        defer {
            let state = owner.map { $0.w($0.base.applicationToken + 0x2c) } ?? 0
            let playing = state != 0 && owner?.w(state) == 0x50c264 && failure == nil
            if touchGameplay != playing { touchGameplay = playing }
        }
        #endif
        guard windowActive, !movieStage, !movieActive, !gameBusy else { return }
        guard let owner, failure == nil, evidenceURL == nil || frameCount < checkFrames else { return }
        gameBusy = true
        defer { gameBusy = false }
        tickFlips.removeAll(); combatFlipOffset = 0; tickPaletteChanges = 0;routeEndingScreenLimit = nil
        // Primary writes made by the menu entry before the first frame (its paper
        // unroll) are recorded with frame 1.
        if frameCount > 0 { tickScreens.removeAll(); tickPrimaryWrites.removeAll() }
        do {
            performCustomLoad()
            if failure != nil {return}
            try performCustomCheckpoint()
            let routeStep = routeFrameStep
            if tracerClock { if owner.hasPostedCommands { deferredFrameStep = true } else { clock &+= routeStep } } else if inputGate {
                let phase = (frameCount+checkpointCadenceOffset) % 3
                clock &+= landingFrameStep ?? UInt32((phase+1)*1000/60-phase*1000/60)
            } else { clock = 1000 + UInt32((frameCount + 1) * 1000 / 60) }
            for event in scriptedInput where event["frame"] == frameCount + 1 {
                guard let raw = event["message"], let message = ClawNativeWindowInputQueue.Message(rawValue: UInt32(raw)) else {
                    throw AssetError.invalid("Invalid menu input message")
                }
                if let code = event["key"] {
                    key(UInt32(code), down: message == .keyDown, fromScript: true)
                } else if let x = event["x"], let y = event["y"] {
                    pointer(message, x: Int32(x), y: Int32(y), fromScript: true)
                }
            }
            if let playStart, !playComplete, !deferredFrameStep { holdPlayKeys(owner, elapsed: Int(clock &- 17 &- playStart)) }
            if !deferredFrameStep {
                switch routePhase {
                case .off, .waiting, .done: break
                default:
                    // The route acts at the clock before this frame's step.
                    clock &-= routeStep; defer { clock &+= routeStep }
                    try routeBeforeFrame(owner)
                }
            }
            // Under the input gate the real-speed script runs on the frame clock.
            let uptime = inputGate ? Double(frameCount) / 60 : ProcessInfo.processInfo.systemUptime
            if realSpeedURL != nil {
                let start = realSpeedStart ?? uptime
                realSpeedStart = start
                var elapsed = Int((uptime - start) * 1000) - realSpeedWaited
                while let event = realSpeedKeys.first, event.ms <= elapsed {
                    if let timeout = event.event["wait"] {
                        let began = realSpeedWaitBegan ?? uptime
                        realSpeedWaitBegan = began
                        let player = playerSnapshot(owner)
                        func meets(_ bound: String, _ value: Int?, _ atLeast: Bool) -> Bool {
                            guard let limit = event.event[bound] else { return true }
                            guard let value else { return false }
                            return atLeast ? value >= limit : value <= limit
                        }
                        let x = player["x"] as? Int, y = player["y"] as? Int
                        let met = meets("x_ge", x, true) && meets("x_le", x, false) && meets("y_ge", y, true) && meets("y_le", y, false)
                        let waited = Int((uptime - began) * 1000)
                        guard met || waited >= timeout else { break }
                        realSpeedKeys.removeFirst()
                        realSpeedWaitBegan = nil
                        realSpeedWaited += waited
                        elapsed -= waited
                        realSpeedFrames.append(["frame": frameCount + 1, "wait": met ? "met" : "timeout", "waited_ms": waited,
                            "x": x ?? -1, "y": y ?? -1])
                        continue
                    }
                    realSpeedKeys.removeFirst()
                    if let code = event.event["key"], let down = event.event["down"] {
                        key(UInt32(code), down: down != 0)
                    } else if let raw = event.event["message"], let message = ClawNativeWindowInputQueue.Message(rawValue: UInt32(raw)),
                              let x = event.event["x"], let y = event.event["y"] {
                        pointer(message, x: Int32(x), y: Int32(y))
                    }
                    realSpeedFrames.append(event.event.merging(["frame": frameCount + 1, "elapsed_ms": elapsed]) { _, new in new })
                }
                pollRealSpeedControl()
            }
            if inputGate {
                // Commands and non-gameplay states contain synchronous fades
                // that poll the timer. Ordinary gameplay advances by frames.
                let state = owner.w(owner.base.applicationToken + 0x2c)
                gateQueryStep = gateQueryOverride ?? (owner.hasPostedCommands || state == 0 || owner.w(state) != 0x50c264 ? 1 : 0)
            }
            if acceptsLiveInput, let input = owner.base.windowInput {
                let state = owner.w(owner.base.applicationToken+0x2c)
                let playing = state != 0 && owner.w(state) == 0x50c264 && controls == nil && players == nil && customLevels == nil
                let sample = owner.joystickDisabled ? nil:input.joystickSampler()
                for code in controllerNavigation.keys(sample:sample,playing:playing,now:Double(clock)/1000) {
                    if code == 13, let draft = controls, draft.selected < 9 {
                        _ = controlsKey(39,down:true)
                    } else {
                        let wasHeld = input.virtualKeys.contains(code)
                        key(code,down:true)
                        // Preserve a simultaneous physical keyboard hold.
                        input.virtualKey(code,down:wasHeld)
                    }
                }
            }
            try owner.frame()
            if let requirement = owner.takeCustomRequirementFailure() {
                releaseInput();showCustomLevels();owner.customLevelsActive = true;customError = requirement
            }
            if let input = owner.base.windowInput,
               try input.queue.takeCloseRequest(window: input.window) {
                // The original Quit command posts WM_CLOSE asynchronously.
                // Consume it at the native pump boundary, after the callback.
                if let realSpeedURL {
                    try JSONSerialization.data(withJSONObject: ["status": "pass", "message": 0x10,
                        "input": liveInputTransitions], options: [.sortedKeys])
                        .write(to: realSpeedURL.appendingPathComponent("quit.json"), options: .atomic)
                }
                owner.writeSettings()
                close()
                #if targetEnvironment(macCatalyst)
                ClawNativeMenuMusic.waitForRenders()
                exit(0)
                #else
                if let scene = UIApplication.shared.connectedScenes.first {
                    UIApplication.shared.requestSceneSessionDestruction(scene.session, options: nil)
                }
                return
                #endif
            }
            if realSpeedURL != nil {
                let state = owner.w(owner.base.applicationToken + 0x2c)
                let stateVtable = state == 0 ? 0 : owner.w(state)
                realSpeedFrames.append(["frame": frameCount + 1, "uptime_ms": Int(uptime * 1000),
                    "frame_ms": owner.lastFrameCheck["frame_ms"] ?? -1, "presentations": owner.lastFrameCheck["presentations"] ?? -1,
                    "state_vtable": String(stateVtable, radix: 16)])
                // State-boundary samples let both clocks check pause/resume at
                // the actual transition, independent of checker scheduling.
                if (frameCount + 1) % 30 == 0 || realSpeedLastState != stateVtable {
                    realSpeedFrames[realSpeedFrames.count - 1]["player"] = playerSnapshot(owner)
                    if let audio = owner.base.audio { realSpeedFrames[realSpeedFrames.count - 1]["audio"] = audio.outputState }
                }
                realSpeedLastState = stateVtable
                if realSpeedFrames.count > 12000 { realSpeedFrames.removeFirst(realSpeedFrames.count - 12000) }
                // The input gate saves it at quit and on failure instead.
                if (frameCount + 1) % 30 == 0 && !inputGate { saveRealSpeed(["status": "running"]) }
            }
            guard let display = owner.base.palette?.display,
                  let surface = display.surfacePixels(owner.w(display.primaryToken + 44)),
                  let palette = owner.base.palette?.currentRGB, palette.count == 768,
                  let provider = CGDataProvider(data: surface.bytes as CFData) else {
                throw AssetError.invalid("Menu has no presented surface")
            }
            let colors = palette.withUnsafeBytes { bytes in
                CGColorSpace(indexedBaseSpace: CGColorSpaceCreateDeviceRGB(), last: 255,
                    colorTable: bytes.baseAddress!.assumingMemoryBound(to: UInt8.self))
            }
            guard let colors, let frame = CGImage(width: Int(surface.width), height: Int(surface.height),
                bitsPerComponent: 8, bitsPerPixel: 8, bytesPerRow: Int(surface.stride), space: colors,
                bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.none.rawValue), provider: provider,
                decode: nil, shouldInterpolate: false, intent: .defaultIntent) else {
                throw AssetError.invalid("Cannot present menu pixels")
            }
            image = frame
            show(frame)
            frameCount += 1
            if let realSpeedURL, !compactSweep, frameCount % 300 == 0 {
                try? save(frame, to: realSpeedURL.appendingPathComponent(String(format: "frame-%05d.png", frameCount)))
            }
            if let realSpeedURL, realSpeedControl != nil,
               !compactSweep || frameCount >= gateTarget || !realSpeedShots.isEmpty {
                for name in realSpeedShots {
                    try? save(frame, to: realSpeedURL.appendingPathComponent(name + ".png"))
                    // The native dialog is a UIKit/SwiftUI overlay, outside the
                    // game's indexed surface. Retain the actual view hierarchy
                    // too, so Controls checks can inspect the visible screen.
                    if controls != nil,let window = UIApplication.shared.connectedScenes
                        .compactMap({$0 as? UIWindowScene}).flatMap(\.windows).first(where:{$0.isKeyWindow}) {
                        let shot = UIGraphicsImageRenderer(bounds:window.bounds).image { _ in
                            window.drawHierarchy(in:window.bounds,afterScreenUpdates:false)
                        }
                        try? shot.pngData()?.write(to:realSpeedURL.appendingPathComponent(name + "-dialog.png"),options:.atomic)
                    }
                    // The presented indexed pixels and palette, hashed as the original traces hash them.
                    var hashes: [String: Any] = ["frame": frameCount, "pixels_sha256": Self.hash(surface.bytes),
                        "palette_sha256": Self.paletteHash(palette), "width": Int(surface.width), "height": Int(surface.height)]
                    // The application object's first 0x140 bytes (display settings such as front
                    // layer +0x128 and movie mode +0x120; -1 where unmapped), read by checks.
                    hashes["application_words"] = (0..<0x50).map { (index: Int) -> Int in
                        let address = owner.base.applicationToken + UInt32(index * 4)
                        return owner.base.heap.lookupBytes(address, count: 4) == nil ? -1 : Int(owner.w(address)) }
                    // Audio options evidence (scripts/check-ingame-audio-options.py): cross-family
                    // invoke counts so far, the effects master flag 0x532c0c and volume 0x532c10,
                    // the ambient group (application +0x5c), the music manager (+0x50), the native
                    // music service log and the native output state. Reads only; no game call.
                    func words(_ base: UInt32, _ count: Int) -> [Int] {
                        (0..<count).map { (index: Int) -> Int in
                            let address = base &+ UInt32(index * 4)
                            return base == 0 || owner.base.heap.lookupBytes(address, count: 4) == nil ? -1 : Int(owner.w(address)) }
                    }
                    hashes["display_viewport"] = words(0x5370c8, 4)
                    let displayWorld = owner.w(owner.w(owner.base.applicationToken + 0x30) + 0x24)
                    let planeCount = owner.w(displayWorld + 0x3c)
                    if planeCount <= 16 {
                        hashes["display_plane_flags"] = (0..<planeCount).map { index in
                            words(owner.w(owner.w(displayWorld + 0x38) + 4 * index) + 8, 1)[0]
                        }
                    }
                    let displayState = owner.w(owner.base.applicationToken + 0x2c)
                    if owner.w(displayState) == 0x50c264 {
                        let parent = owner.w(displayState + 0xc)
                        var node = owner.w(owner.w(parent + 8) + 0x14)
                        var visited = Set<UInt32>(), tagged = 0, hidden = 0
                        while node != 0, visited.insert(node).inserted {
                            let entity = owner.w(node + 8)
                            if entity != 0, owner.w(entity + 0x164) & 0x2000 != 0 {
                                tagged += 1
                                if owner.w(entity + 8) & 0x10000 != 0 { hidden += 1 }
                            }
                            node = owner.w(node)
                        }
                        hashes["display_detail_entities"] = ["tagged": tagged, "hidden": hidden]
                    }
                    // Pause/respawn parity: record the physical cursor and both
                    // timer domains without changing the game or advancing it.
                    hashes["clock_words"] = [UInt32(0x537208), 0x53720c, 0x537210, 0x5430c4, 0x5430c8].map { words($0, 1)[0] }
                    hashes["random_snapshot"] = owner.randomSnapshot
                    if let input = owner.base.windowInput {
                        hashes["cursor_position"] = [input.cursorPosition.x, input.cursorPosition.y]
                    }
                    var counts: [String: UInt64] = [:]
                    for (function, count) in owner.resources.invokeCounts { counts[String(function, radix: 16)] = count }
                    hashes["invoke_counts"] = counts
                    if ProcessInfo.processInfo.arguments.contains("--crt-rand-check") {
                        hashes["crt_random"] = owner.probeRandom()
                    }
                    // Pause and game-over evidence (scripts/check-pause-gameover.py): current state, player counters.
                    let markState = owner.base.heap.lookupBytes(owner.base.applicationToken + 0x2c, count: 4) == nil ? 0 : owner.w(owner.base.applicationToken + 0x2c)
                    hashes["state_vtable"] = "0x" + String(markState == 0 || owner.base.heap.lookupBytes(markState, count: 4) == nil ? 0 : owner.w(markState), radix: 16)
                    hashes["player"] = playerSnapshot(owner)
                    let bossCallbacks: [UInt32:String] = [0x47e210:"Raux", 0x453d30:"Katherine", 0x49fb30:"Wolvington", 0x443290:"Gabriel", 0x458680:"Marrow", 0x4041f0:"Aquatis", 0x47f6e0:"RedTail", 0x4633a0:"Omar"]
                    var bossDamage: [String:[String:UInt32]] = [:]
                    var bossActors: [[String:Any]] = []
                    var hudLives: [UInt32] = []
                    for candidate in owner.base.heap.debugAllocationBases {
                        guard owner.base.heap.lookupBytes(candidate, count: 0x110) != nil else { continue }
                        let logic = owner.w(candidate + 0x6c)
                        guard logic != 0, owner.base.heap.lookupBytes(logic, count: 0x20) != nil else { continue }
                        let callback = owner.w(logic + 0x10)
                        if let name = bossCallbacks[callback] {
                            bossDamage[name] = ["damage":owner.w(candidate + 0x104), "health":owner.w(candidate + 0x10c)]
                            bossActors.append(["name":name, "actor":candidate, "logic":logic,
                                "damage":owner.w(candidate + 0x104), "health":owner.w(candidate + 0x10c),
                                "state":owner.w(logic + 0x1c)])
                        }
                        if callback == 0x4912a0 {
                            let display = owner.w(logic + 0x18)
                            if display != 0, owner.base.heap.lookupBytes(display, count: 0x30) != nil {
                                hudLives.append(owner.w(display + 0x2c))
                            }
                        }
                    }
                    hashes["boss_damage"] = bossDamage
                    hashes["boss_actors"] = bossActors
                    hashes["boss_scale_words"] = words(0x5262b0, 3)
                    hashes["hud_lives"] = hudLives.sorted()
                    hashes["posted_commands"] = owner.postedHistory.map { "0x" + String($0["wparam"] ?? 0, radix: 16) }
                    hashes["audio_globals"] = words(0x532c0c, 2)
                    if ProcessInfo.processInfo.environment["CLAW_AUDIO_POOL_EVIDENCE"] == "1" {
                        hashes["audio_pool_inputs"] = audioPoolInputs
                    }
                    hashes["ambient_group"] = words(owner.w(owner.base.applicationToken + 0x5c), 12)
                    hashes["music_manager"] = words(owner.w(owner.base.applicationToken + 0x50), 11)
                    let music = owner.musicEvidence
                    hashes["music_events"] = ["count": music.count, "tail": Array(music.suffix(ProcessInfo.processInfo.environment["CLAW_AUDIO_EVIDENCE"] == "1" ? 256:6))]
                    if let audio = owner.base.audio {
                        hashes["audio_output"] = audio.outputState.merging(["active_voices": audio.activeVoiceCount]) { _, new in new }
                        if ProcessInfo.processInfo.environment["CLAW_AUDIO_EVIDENCE"] == "1" {
                            hashes["audio_lifetimes"] = audio.lifetimeEvidence
                            hashes["speech"] = owner.speechSnapshot
                            let group = owner.w(owner.base.applicationToken + 0x5c)
                            var node = group == 0 ? 0:owner.w(group + 0xc)
                            var ambient:[[String:Any]] = []
                            var visited:Set<UInt32> = []
                            while node != 0,visited.insert(node).inserted,visited.count <= 128 {
                                let object = owner.w(node + 8),voice = owner.w(object + 4)
                                ambient.append(["object":object,"words":words(object,18),"voice":voice,
                                                "buffer":voice == 0 ? 0:owner.w(voice + 0xc)])
                                node = owner.w(node)
                            }
                            hashes["ambient_objects"] = ambient
                        }
                    }
                    try? JSONSerialization.data(withJSONObject: hashes, options: [.sortedKeys])
                        .write(to: realSpeedURL.appendingPathComponent(name + ".json"), options: .atomic)
                }
                realSpeedShots.removeAll()
                var live = playerSnapshot(owner).merging(["frame": frameCount, "uptime_ms": Int(uptime * 1000)]) { _, new in new }
                live["hud"] = hudProbe(owner, frame: frame, url: realSpeedURL)
                live["weapons"] = weaponSnapshot(owner)
                live["input_received"] = liveInputCount
                if ProcessInfo.processInfo.arguments.contains("--platform-landing-check") {
                    live["landing_move"] = landingMove
                    live["landing_physics"] = ["speed": owner.w(0x418432), "jump_base": owner.w(0x41b750),
                        "fall_cap": owner.heap.lookupBytes(0x534e98, count: 8).map { UnsafeRawPointer($0).loadUnaligned(as: Double.self) } ?? 0]
                }
                live["custom_checkpoint"] = owner.customCheckpointEvents
                live["custom_checkpoint_message"] = owner.customCheckpointMessage
                if ProcessInfo.processInfo.arguments.contains("--custom-checkpoint-check") {
                    live["checkpoint_chooser"] = ["visible":checkpointOverlay,"selected":checkpointSelectedSlot,
                        "labels":customCheckpointLabels,"count":owner.customCheckpointDates.count]
                    live["checkpoint_clock"] = ["physical":clock,"frame_phase":UInt32((frameCount+checkpointCadenceOffset) % 3),"words":[UInt32(0x537208),0x53720c,0x537210,0x5430c4,0x5430c8].map {owner.w($0)}]
                    live["checkpoint_boss_phase"] = owner.w(0x53c9c0)
                    live["placements"] = owner.resources.checkpointPlacementEvidence
                    live["checkpoint_pickups"] = owner.resources.checkpointPickupEvidence
                }
                live["profiles"] = owner.playerChoices.map{["name":$0.name,"selected":$0.id == owner.selectedPlayer] as [String:Any]}
                live["custom_dialog"] = customLevels != nil
                live["custom_files"] = customLevels?.map{$0.lastPathComponent} ?? []
                live["custom_selected"] = customSelected
                live["custom_restart_slot"] = customRestartSlot
                live["custom_error"] = customError ?? ""
                live["custom_level"] = owner.customLevelEvidence
                live["logical_resolution"] = [owner.w(owner.base.applicationToken+0x7c),owner.w(owner.base.applicationToken+0x80)]
                live["level_actions_available"] = owner.customPresentationActive
                let customState = owner.w(owner.base.applicationToken+0x2c)
                live["custom_flag"] = customState != 0 && owner.w(customState) == 0x50c264 ? owner.w(customState+0x258):0
                live["players_dialog"] = players?.page ?? -1
                live["player_dialog_events"] = playerDialogEvents
                live["controls"] = ["open":controls != nil,"keys":owner.controlKeys,"buttons":owner.controlButtons,
                    "draft":controls?.keys ?? [],"selected":controls?.selected ?? -1,
                    "draft_buttons":controls?.buttons ?? [],"disabled":owner.joystickDisabled,
                    "capturing":controls?.capturing ?? false,"error":controls?.error ?? "",
                    "save_writes":owner.saveFiles?.writes ?? 0]
                #if !targetEnvironment(macCatalyst)
                live["touch_controls"] = ["enabled":touchControlsEnabled,"visible":touchControlsVisible]
                #endif
                live["controller"] = owner.controllerEvidence
                if movieFlowCheck || realSpeedURL != nil {
                    let interface = owner.activeInterfaceToken
                    let page = interface != 0 ? owner.resources.invoke(0x4dd0c0, interface + 0x154) : 0
                    live["menu_page"] = page == 0 ? 0 : owner.w(page + 80)
                    let selected = interface != 0 ? owner.resources.invoke(0x4dd480, interface + 0x154) : 0
                    let control = interface != 0 ? owner.resources.invoke(0x4dd450, interface + 0x154, [selected]) : 0
                    live["menu_index"] = selected
                    live["menu_selected"] = control == 0 ? 0 : owner.w(control + 0x14)
                    live["menu_selected_disabled"] = control != 0 && owner.w(control + 0x44) & 0x20 != 0
                    live["unavailable_menu_flags"] = owner.unavailableMenuFlags
                    if ProcessInfo.processInfo.arguments.contains("--menu-disabled-audit") {live["menu_audit"] = owner.menuAudit}
                    live["movies"] = movieRecords
                    live["responsiveness"] = heartbeat.records
                    live["movie_events"] = owner.movieEvents
                }
                // The application's current state (+0x2c) and every posted command, for
                // state-boundary checks (scripts/check-end-of-level.py).
                let current = owner.base.heap.lookupBytes(owner.base.applicationToken + 0x2c, count: 4) == nil ? 0 : owner.w(owner.base.applicationToken + 0x2c)
                live["app_state"] = "0x" + String(current, radix: 16)
                live["state_vtable"] = "0x" + String(current == 0 || owner.base.heap.lookupBytes(current, count: 4) == nil ? 0 : owner.w(current), radix: 16)
                live["posted_commands"] = owner.postedHistory.map { "0x" + String($0["wparam"] ?? 0, radix: 16) }
                let cheatActor = owner.base.heap.lookup(0x537e88,words:1)?.pointee ?? 0
                let cheatController = owner.w(owner.base.applicationToken+0x48)
                live["v13_cheats"] = owner.v13CheatEvidence.merging(["sprite_flags":cheatActor == 0 ? 0:(owner.base.heap.lookup(cheatActor+0x40,words:1)?.pointee ?? 0),
                    "cheated":cheatController == 0 ? 0:owner.w(cheatController+0x128)]) { _,new in new }
                // Accelerator checks (scripts/check-accelerators.py): translated commands,
                // the pause flag (+0x0c) and the viewport size step (+0x68).
                live["accelerators"] = owner.acceleratorHistory.map { ["command": "0x" + String($0["command"] ?? 0, radix: 16),
                    "key": Int($0["key"] ?? 0), "character": Int($0["character"] ?? 0), "delivered": Int($0["delivered"] ?? 0)] }
                live["screen_dumps"] = owner.screenDumps
                live["screen_dump_count"] = owner.settings?.dword("Screen Dump Count") ?? 0
                for (name, offset) in [("app_paused", UInt32(0x0c)), ("app_viewport", 0x68)] {
                    let address = owner.base.applicationToken + offset
                    live[name] = owner.base.heap.lookupBytes(address, count: 4) == nil ? -1 : Int(owner.w(address))
                }
                // Under the input gate the controller reads it only at a pause.
                realSpeedLatestLive = live
                if !inputGate || frameCount >= gateTarget {
                    try? JSONSerialization.data(withJSONObject: live, options: [.sortedKeys])
                        .write(to: realSpeedURL.appendingPathComponent("live.json"), options: .atomic)
                }
            }
            switch routePhase {
            case .off, .waiting: break
            default:
                extendBossRoute(owner, frame: frame)
                let finished = routeAfterFrame(owner)
                if let evidenceURL, routeInLevelTwo || routeInLevelThree || finished, routeShots.contains((routeLaterLevel && !routeCompletesLevel ? routeLevelThree : routeLevelTwo).count - 1) {
                    try save(frame, to: evidenceURL.appendingPathComponent(String(format: "\(routeFileStem)-%04d.png", (routeLaterLevel && !routeCompletesLevel ? routeLevelThree : routeLevelTwo).count - 1)))
                }
                if finished, let evidenceURL {
                    for key in Self.playKeys { owner.base.windowInput?.virtualKey(key, down: false) }
                    try save(frame, to: evidenceURL.appendingPathComponent("\(routeFileStem)-after.png"))
                    try JSONSerialization.data(withJSONObject: ["status": "pass", "level_one_frames": routeLevelOne,
                        "level_two_frames": routeLevelTwo, "level_three_frames": routeLevelThree,
                        "level_four_frames": routeTargetFour ? (routeBoss ? routeLevelTwo : routeLevelThree) : [],
                        "level_five_frames": routeTargetFive || (routeTargetFour && routeBoss) ? routeLevelThree : [],
                        "level_six_frames": routeTargetSix ? (routeBoss ? routeLevelTwo : routeLevelThree) : [],
                        "level_seven_frames": routeTargetSeven ? (routeCompletesLevel ? routeLevelTwo : routeLevelThree) : (routeTargetSix && routeBoss ? routeLevelThree : []),
                        "level_eight_frames": routeTargetEight ? (routeBoss ? routeLevelTwo : routeLevelThree) : (routeTargetSeven && routeCompletesLevel ? routeLevelThree : []),
                        "level_nine_frames": routeTargetNine ? (routeCompletesLevel ? routeLevelTwo : routeLevelThree) : (routeTargetEight && routeBoss ? routeLevelThree : []),
                        "level_ten_frames": routeTargetTen ? (routeBoss ? routeLevelTwo : routeLevelThree) : (routeTargetNine && routeCompletesLevel ? routeLevelThree : []),
                        "level_eleven_frames": routeTargetEleven ? (routeCompletesLevel ? routeLevelTwo : routeLevelThree) : (routeTargetTen && routeBoss ? routeLevelThree : []),
                        "level_twelve_frames": routeTargetTwelve ? (routeCompletesLevel ? routeLevelTwo : routeLevelThree) : (routeTargetEleven && routeCompletesLevel ? routeLevelThree : []),
                        "level_thirteen_frames": routeTargetThirteen ? (routeCompletesLevel ? routeLevelTwo : routeLevelThree) : (routeTargetTwelve && routeCompletesLevel ? routeLevelThree : []),
                        "level_fourteen_frames": routeTargetFourteen ? (routeCompletesLevel ? routeLevelTwo : routeLevelThree) : (routeTargetThirteen && routeCompletesLevel ? routeLevelThree : []),
                        "respawn_query_events": routeRespawnQueryEvents,
                        "boss_route_functions": routeGabrielCalls, "movie_events": owner.movieEvents, "ending_screens": routeEndingScreens,
                        "credits_services": owner.base.palette?.display?.creditsEvidence ?? [],
                        "state_transitions": routeStates, "key_deliveries": routeKeys, "transports": owner.resources.transportCounts,
                        "posted_commands": owner.postedHistory.map { "0x" + String($0["wparam"] ?? 0, radix: 16) },
                        "frame": frameCount], options: [.sortedKeys])
                        .write(to: evidenceURL.appendingPathComponent("\(routeFileStem)-route.json"), options: .atomic)
                    checkFrames = frameCount
                }
            }
            if let evidenceURL, !routeInLevelTwo && !(routeLaterLevel && !routeFinishingBoss && routeInLevelThree), tickFlips.count > 1 || !tickPrimaryWrites.isEmpty {
                var flips: [[String: Any]] = []
                for (index, flip) in tickFlips.enumerated() {
                    let name = String(format: "flip-%04d-%d.png", frameCount, index + 1)
                    try save(flip.image, to: evidenceURL.appendingPathComponent(name))
                    flips.append(["pixels_sha256": flip.pixels, "palette_sha256": flip.palette,
                                  "nonzero_pixels": flip.nonzero, "png": name])
                }
                multiFlipFrames.append(["frame": frameCount, "flips": flips,
                    "palette_changes": tickPaletteChanges, "screens": tickScreens, "primary_writes": tickPrimaryWrites])
            }
            if let playStart, !playComplete, let evidenceURL {
                let elapsed = Int(clock &- playStart)
                recordPlayFrame(owner, elapsed: elapsed, action: playAction)
                if playFrames.count == 2 { try save(frame, to: evidenceURL.appendingPathComponent("play-before.png")) }
                if elapsed >= 10000 && elapsed - 17 < 10000 { try save(frame, to: evidenceURL.appendingPathComponent("play-10s.png")) }
                // The join's plan runs 30 s; a longer fixed plan (work/officer-strike) runs to its end.
                let planEnd = playPlan.map(\.end).max() ?? 0
                let requested = playStepPath != nil ? planEnd : max(30000, planEnd)
                if elapsed >= requested && !extendPlayPlan(beyond: requested, frame: frame) {
                    playComplete = true
                    for key in Self.playKeys { owner.base.windowInput?.virtualKey(key, down: false) }
                    try save(frame, to: evidenceURL.appendingPathComponent("play-after.png"))
                    try JSONSerialization.data(withJSONObject: ["status": "pass", "play_frames": playFrames,
                        "requested_play_ms": requested, "completed_play_ms": elapsed, "frame": frameCount],
                        options: [.sortedKeys]).write(to: evidenceURL.appendingPathComponent("play-frames.json"), options: .atomic)
                    checkFrames = frameCount
                }
            }
            if frameCount % 30 == 0 || (inputGate && frameCount >= gateTarget) { try saveLiveState() }
            if let evidenceURL {
                func hash(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }
                var paletteEntries = Data()
                for offset in stride(from: 0, to: palette.count, by: 3) {
                    paletteEntries.append(palette[offset..<offset + 3]); paletteEntries.append(0)
                }
                let menuLive = owner.menuLive
                let selected = menuLive ? owner.resources.invoke(0x4dd480, owner.menuToken + 0x154) : 0
                let page = menuLive ? owner.resources.invoke(0x4dd0c0, owner.menuToken + 0x154) : 0
                let state = owner.w(owner.base.applicationToken + 0x2c)
                evidence.append(["frame": frameCount, "width": surface.width, "height": surface.height,
                    "milliseconds": clock, "frame_ms": owner.lastFrameCheck["frame_ms"] ?? -1,
                    "clock_reads": clockReads,
                    "pixels": hash(surface.bytes), "palette": hash(paletteEntries), "presentations": display.presentations,
                    "selected": selected, "page_id": page == 0 ? 0 : owner.w(page + 80),
                    "state_vtable": state == 0 ? 0 : owner.w(state),
                    "resourceFault": owner.resources.fault, "displayFault": display.fault])
                clockReads.removeAll()
                if !scriptedInput.isEmpty && ([1, 9, 17, 26, 33, 41, 50, 61].contains(frameCount) || frameCount == checkFrames) {
                    try save(frame, to: evidenceURL.appendingPathComponent(String(format: "native-%02d.png", frameCount)))
                }
                if frameCount == checkFrames {
                    // Publish the report only once every named image exists.
                    // Keep delivering window events while the writer finishes.
                    while pendingEvidenceImages.wait(timeout: .now()) == .timedOut {
                        ClawWindowEventPump.pump(for: 0.001)
                    }
                    let imageURL = evidenceURL.appendingPathComponent("menu.png")
                    guard let destination = CGImageDestinationCreateWithURL(imageURL as CFURL, "public.png" as CFString, 1, nil) else {
                        throw AssetError.invalid("Cannot save menu frame")
                    }
                    CGImageDestinationAddImage(destination, frame, nil)
                    guard CGImageDestinationFinalize(destination) else { throw AssetError.invalid("Cannot save menu frame") }
                    let report: [String: Any] = ["status": "pass", "frames": evidence, "multi_flip_frames": multiFlipFrames,
                        "resource": "bundled original CLAW.REZ", "initializer": "45ace0", "frameEntry": "428b60",
                        "ceilCalls": owner.resources.mathServiceCounts[0x4a4250] ?? 0,
                        "directSoundCalls": owner.calls.filter { $0 == 0x4208e0 }.count,
                        "responsiveness": heartbeat.records,"test_level":owner.resources.testLevelEvidence]
                    try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
                        .write(to: evidenceURL.appendingPathComponent("app-menu.json"), options: .atomic)
                }
            }
        } catch { stop(error: error) }
    }

    private let combatHUD = ProcessInfo.processInfo.environment["CLAW_COMBAT_HUD"] == "1"
    // Full rendering and gameplay still run on every frame. Fuzzing only
    // records JSON at input gates; failures retain their screenshot and trace.
    private let compactSweep = ProcessInfo.processInfo.arguments.contains("--crash-sweep") &&
        !ProcessInfo.processInfo.arguments.contains("--crash-sweep-every-frame")
    private var combatSetups: Set<Int> = []
    private var grabCheckActor: UInt32 = 0
    // Explicit placement fixture only; lifting and throwing still require real
    // delivered keys and the normal collision, state and animation paths.
    private func placeForGrabCheck(_ owner: ClawNativeMenuInterface, callback: UInt32, centered:Bool = false) throws {
        let heap = owner.base.heap
        func matches(_ actor: UInt32) -> Bool {
            guard heap.lookupBytes(actor, count: 0x180) != nil else { return false }
            if centered && callback == 0x470430 {
                // SpecialPowerup also owns warps and extra lives. Select an
                // actual timed effect from the original loaded powerup table.
                let count = owner.w(0x52a190),image = owner.w(actor + 0x170)
                guard count <= 128,(0..<count).contains(where:{index in
                    owner.w(0x537ec8 + index*4) == image &&
                    [UInt32(0x26b7),0x26b8,0x26b9,0x26ba,0x26bd].contains(owner.w(0x537fd0 + index*4))
                }) else {return false}
            }
            let logic = owner.w(actor + 0x6c)
            return logic != 0 && heap.lookupBytes(logic, count: 0x20) != nil && owner.w(logic + 0x10) == callback &&
                (centered || owner.w(logic + 0x1c) == 0 || Int32(bitPattern: owner.w(actor + 0x10c)) > 0)
        }
        let player = owner.w(0x537e88)
        if !matches(grabCheckActor) {
            func distance(_ actor: UInt32) -> Int64 {
                abs(Int64(owner.w(actor + 0x4c)) - Int64(owner.w(player + 0x4c))) +
                    abs(Int64(owner.w(actor + 0x50)) - Int64(owner.w(player + 0x50)))
            }
            grabCheckActor = heap.debugAllocationBases.filter(matches).min {
                let left = distance($0), right = distance($1)
                return left == right ? $0 < $1 : left < right
            } ?? 0
        }
        guard grabCheckActor != 0 else { throw AssetError.invalid("No live grab target for \(String(callback, radix:16))") }
        owner.put(player + 0x4c, owner.w(grabCheckActor + 0x4c) &- 25)
        // Pickups have no enemy feet rectangle. Place beside their center;
        // ordinary collision must still award the powerup/checkpoint.
        if centered {owner.put(player + 0x50,owner.w(grabCheckActor + 0x50));return}
        // Align feet just above the target's floor. Soldier and officer
        // collision boxes differ; a fixed offset can put Claw below a ledge.
        owner.put(player + 0x50, owner.w(grabCheckActor + 0x50) &+ owner.w(grabCheckActor + 0x124)
            &- owner.w(player + 0x124) &- 1)
    }
    private var combatTargetActor: UInt32 = 0
    private var combatTargetIdentity: ClawTokenHeap.AllocationIdentity?
    private var combatLogicIdentity: ClawTokenHeap.AllocationIdentity?
    private var combatFlipOffset = 0
    private func combatTargetLive(_ owner: ClawNativeMenuInterface) -> Bool {
        guard let identity = combatTargetIdentity, let logicIdentity = combatLogicIdentity,
              owner.base.heap.containingAllocationIdentity(at: combatTargetActor, count: 0x110) === identity else { return false }
        let info = owner.w(combatTargetActor + 0x6c)
        return owner.base.heap.containingAllocationIdentity(at: info, count: 0x20) === logicIdentity
    }
    private func holdPlayKeys(_ owner: ClawNativeMenuInterface, elapsed: Int) {
        guard let input = owner.base.windowInput,
              let action = playPlan.first(where: { $0.start <= elapsed && elapsed < $0.end }) else { return }
        playAction = action.action
        if let place = action.place, !playPlaced.contains(action.start), let actor = owner.base.heap.lookup(0x537e88, words: 1)?.pointee,
           owner.base.heap.lookup(actor + 0x4c, words: 2) != nil {
            playPlaced.insert(action.start)
            owner.put(actor + 0x4c, place.x); owner.put(actor + 0x50, place.y)
        }
        // Explicit same-input diagnostic setup, mirrored by combat_trace.py. The
        // remaining timer fixture checks the expiry boundary, not full duration.
        if combatHUD && !combatSetups.contains(action.start) {
            combatSetups.insert(action.start)
            let actor = owner.w(0x537e88), state = owner.w(owner.w(actor + 0x6c) + 0x14)
            if let ammo = action.diagnostic["ammo"] {
                for offset in [UInt32(0x70), 0x74, 0x78] { owner.put(state + offset, UInt32(ammo)) }
            }
            if let distance = action.diagnostic["near_target"], combatTargetLive(owner) {
                owner.put(actor + 0x4c, owner.w(combatTargetActor + 0x4c) &- UInt32(distance))
                owner.put(actor + 0x50, owner.w(combatTargetActor + 0x50) &- 9)
            }
            if let health = action.diagnostic["health"] { owner.put(actor + 0x10c, UInt32(health)) }
            if let score = action.diagnostic["score"] { owner.put(actor + 0xf8, UInt32(score)) }
            if let lives = action.diagnostic["lives"] { owner.put(state + 0x7c, UInt32(lives)) }
            if let remaining = action.diagnostic["remaining_ms"] { owner.put(0x534ea8, UInt32(remaining)) }
            if let key = action.diagnostic["key"] {
                let game = owner.w(owner.base.applicationToken + 0x2c)
                let scan = UInt32(key == 0x31 ? 2 : (key == 0x32 ? 3 : 4))
                owner.postingAfterFrame { _ = owner.invokeBranch(owner.w(owner.w(game) + 0x30), game, [UInt32(key), (scan << 16) | 1]) }
            }
            if let command = action.diagnostic["command"] {
                let app = owner.base.applicationToken
                owner.postingAfterFrame { _ = owner.invokeBranch(0x426e30, app, [0x111, UInt32(command), 0]) }
            }
        }
        for key in Self.playKeys { input.virtualKey(key, down: action.keys.contains(key)) }
    }

    // The join's player snapshot fields (Tests/NativeLevelOne/trace.py player_snapshot).
    private func recordPlayFrame(_ owner: ClawNativeMenuInterface, elapsed: Int, action: String) {
        var record: [String: Any] = ["elapsed_ms": elapsed, "action": action, "player": playerSnapshot(owner)]
        if playPegs, let player = record["player"] as? [String: Any], let x = player["x"] as? Int, let y = player["y"] as? Int,
           x < 4900, y < 4400, elapsed > 38000 {
            record["pegs"] = pegSnapshot(owner)
        }
        if combatHUD {
            if action == "loaded" {
                // The launch command returns before gameplay in this pump turn.
                record["loading_screens"] = tickFlips.map { [String($0.pixels.prefix(16)), String($0.palette.prefix(16))] }
                combatFlipOffset = tickFlips.count
            }
            record["screens"] = tickFlips.dropFirst(combatFlipOffset).map { [String($0.pixels.prefix(16)), String($0.palette.prefix(16))] }
        }
        playFrames.append(record)
    }
    // Debug only (CLAW_PLAY_PEGS=1): toggle-peg actor fields, as work/toggle-peg/peg_state.py records them in the original.
    private let playPegs = ProcessInfo.processInfo.environment["CLAW_PLAY_PEGS"] != nil
    private var pegActors: [UInt32] = []
    private func pegSnapshot(_ owner: ClawNativeMenuInterface) -> [String: Any] {
        func word(_ address: UInt32) -> UInt32? {
            guard let pointer = owner.base.heap.lookupBytes(address, count: 4) else { return nil }
            return UnsafeRawPointer(pointer).loadUnaligned(as: UInt32.self)
        }
        let variants: Set<UInt32> = [0x49e4e0, 0x49e7b0, 0x49e7d0, 0x49e7f0]
        if pegActors.isEmpty, let player = word(0x537e88) {
            var address = (player &- 0x800000) & ~0xf
            while address < player &+ 0x800000 {
                if let record = word(address &+ 0x6c), record & 3 == 0, let variant = word(record &+ 0x10), variants.contains(variant),
                   word(address &+ 0x1a4) != nil {
                    pegActors.append(address)
                }
                address &+= 8
            }
        }
        let objectFields: [(String, UInt32)] = [("flags", 0x8), ("x", 0x4c), ("y", 0x50), ("attr", 0xd0), ("r0", 0x128), ("r1", 0x12c),
            ("r2", 0x130), ("r3", 0x134), ("frame", 0x16c), ("f19c", 0x19c), ("f1a4", 0x1a4)]
        let recordFields: [(String, UInt32)] = [("variant", 0x10), ("state", 0x1c), ("mid", 0x64), ("phase", 0xbc), ("period", 0x4c)]
        var result: [String: Any] = [:]
        for actor in pegActors {
            guard let record = word(actor + 0x6c) else { continue }
            var fields: [String: Int] = [:]
            for (name, offset) in objectFields { fields[name] = word(actor + offset).map(Int.init) ?? -1 }
            for (name, offset) in recordFields { fields[name] = word(record + offset).map(Int.init) ?? -1 }
            result["\(fields["x"]!),\(fields["y"]!)"] = fields
        }
        return result
    }
    private func bossSnapshot(_ owner: ClawNativeMenuInterface) -> [String: Any] {
        func word(_ address: UInt32) -> UInt32? {
            guard let pointer = owner.base.heap.lookupBytes(address, count: 4) else { return nil }
            return UnsafeRawPointer(pointer).loadUnaligned(as: UInt32.self)
        }
        func hex(_ value: UInt32) -> String { "0x" + String(value, radix: 16) }
        let active = word(0x5349dc) ?? 0
        if routeTargetTwelve, let aquatis = word(0x534874), aquatis != 0, let actor = word(aquatis + 0xc) { routeBossActor = actor }
        if active != 0 { routeBossActor = active }
        let actor = active != 0 ? active : routeBossActor
        guard actor != 0, let health = word(actor + 0x10c) else { return ["actor": hex(actor), "live": false, "active": active != 0] }
        let record = word(actor + 0x6c) ?? 0, object = word(record + 0x18) ?? 0
        var result: [String: Any] = ["actor": hex(actor), "live": true, "active": active != 0, "health": Int(health),
            "x": Int(word(actor + 0x4c) ?? 0), "y": Int(word(actor + 0x50) ?? 0),
            "actor_flags": Int(word(actor + 8) ?? 0), "record": hex(record), "private": hex(object),
            "logic_state": Int(word(record + 0x1c) ?? 0), "damage": Int(word(actor + 0x104) ?? 0)]
        if object != 0, let table = word(object) {
            let animation = word(object + 0x10) ?? 0
            result.merge(["vtable": hex(table), "state": Int(animation),
                "animation_id": word(animation + 0x1c).map { Int($0) } as Any? ?? NSNull(),
                "callback": hex(word(object + 0x14) ?? 0), "action_phase": Int(word(object + 0x20) ?? 0),
                "mode": Int(word(object + 0x184) ?? 0), "facing": Int(word(object + 0x18c) ?? 0)]) { _, new in new }
        }
        if routeTargetTwelve, let aquatis = word(0x534874), aquatis != 0 {
            let offsets: [UInt32] = [0x4a8, 0x4b4, 0x4b8, 0x4bc, 0x4c0, 0x4c4, 0x4c8, 0x4ec]
            result["mechanism"] = Dictionary(uniqueKeysWithValues: offsets.map { (hex($0), Int(word(aquatis + $0) ?? 0)) })
        }
        return result
    }
    private func playerSnapshot(_ owner: ClawNativeMenuInterface) -> [String: Any] {
        func word(_ address: UInt32) -> UInt32? {
            guard let pointer = owner.base.heap.lookupBytes(address, count: 4) else { return nil }
            return UnsafeRawPointer(pointer).loadUnaligned(as: UInt32.self)
        }
        var player: [String: Any] = ["error": "player not live"]
        if let state = word(owner.base.applicationToken + 0x2c), let vtable = word(state), let level = word(state + 0x14),
           let actor = word(0x537e88), let logic = word(actor + 0x6c), let privateState = word(logic + 0x14),
           let controller = word(0x537204), let mask = word(controller + 8), let gameMs = word(0x537210),
           let x = word(actor + 0x4c), let y = word(actor + 0x50), let health = word(actor + 0x10c),
           let score = word(actor + 0xf8), let playerState = word(privateState), let logicState = word(logic + 0x1c) {
            let counts = (0..<10).map { word(privateState + 0x88 + UInt32($0 * 4)).map(Int.init) ?? -1 }
            func hex(_ value: UInt32) -> String { "0x" + String(value, radix: 16) }
            player = ["state": hex(state), "vtable": hex(vtable), "level": Int(level), "actor": hex(actor),
                "private": hex(privateState), "x": Int(x), "y": Int(y), "health": Int(health), "score": Int(score),
                "player_state": Int(playerState), "logic_state": Int(logicState), "treasure_counts": counts,
                "render_flags": Int(word(actor + 0x40) ?? 0),
                "velocity_x": Int(Int32(bitPattern: word(actor + 0x148) ?? 0)),
                "velocity_y": Int(Int32(bitPattern: word(actor + 0x14c) ?? 0)),
                "motion_state": Int(word(actor + 0xcc) ?? 0),
                "collision_steps": [UInt32(0x64), 0x68].map { Int(word((word((word(actor + 0xc) ?? 0) + 0x24) ?? 0) + $0) ?? 0) },
                "frame_ms": Int(word(0x53720c) ?? 0),
                "facing_rectangles": [UInt32(0x118), 0x128, 0x138].map { offset in
                    (0..<4).map { Int(Int32(bitPattern: word(actor + offset + UInt32($0 * 4)) ?? 0)) }
                },
                "input_mask": Int(mask), "game_ms": Int(gameMs),
                "ammo": [UInt32(0x70), 0x74, 0x78].map { word(privateState + $0).map(Int.init) ?? -1 },
                // Lives (+0x7c) and lives lost (+0x80), as 0x41c440 counts them (scripts/check-pause-gameover.py).
                "lives": word(privateState + 0x7c).map(Int.init) ?? -1, "lives_lost": word(privateState + 0x80).map(Int.init) ?? -1,
                "spare_lives": max(0, Int(Int32(bitPattern: word(privateState + 0x7c) ?? 0)) - 1),
                "inventory_extra_life_threshold": word(privateState + 0xec).map(Int.init) ?? -1]
        }
        if combatHUD || ProcessInfo.processInfo.arguments.contains("--crash-sweep"),
           let actor = word(0x537e88), let logic = word(actor + 0x6c), let state = word(logic + 0x14) {
            player["combat"] = ["weapon": word(state + 0x30) ?? 0, "attack": word(state + 4) ?? 0,
                "attack_code": word(state + 0x3c) ?? 0, "owner_tag": word(state + 0xe8) ?? 0, "carrying": (word(state + 0x12c) ?? 0) != 0 ? 1 : 0,
                "image_id": word(actor + 0x16c) ?? 0, "animation_frame": word(actor + 0x198) ?? 0,
                "flags": word(actor + 0xd4) ?? 0, "power_kind": word(0x534eac) ?? 0, "power_ms": word(0x534ea8) ?? 0]
            if ProcessInfo.processInfo.arguments.contains("--crash-sweep") {
                let game = word(owner.base.applicationToken + 0x2c) ?? 0
                player["checkpoint_position"] = [word(game + 0x44) ?? 0, word(game + 0x48) ?? 0]
                player["random_snapshot"] = owner.randomSnapshot
            }
        }
        if ProcessInfo.processInfo.arguments.contains("--enemy-grab-check"), let actor = word(0x537e88),
           let logic = word(actor + 0x6c), let state = word(logic + 0x14) {
            let held = word(state + 0x12c) ?? 0
            player["grab_check"] = ["target": grabCheckActor, "held": held,
                "target_x": word(grabCheckActor + 0x4c) ?? 0, "target_y": word(grabCheckActor + 0x50) ?? 0,
                "target_mode": word(grabCheckActor + 0xcc) ?? 0,
                "callback": word((word(grabCheckActor + 0x6c) ?? 0) + 0x10) ?? 0,
                "held_callback": word((word(held + 0x6c) ?? 0) + 0x10) ?? 0]
        }
        if combatHUD {
            if combatTargetActor == 0 {
                combatTargetActor = owner.base.heap.debugAllocationBases.first(where: { candidate in
                    guard owner.base.heap.containingAllocationIdentity(at: candidate, count: 0x180) != nil,
                          word(candidate + 0x4c) == 1092, let info = word(candidate + 0x6c), info != 0,
                          owner.base.heap.containingAllocationIdentity(at: info, count: 0x20) != nil else { return false }
                    return word(info + 0x10) == 0x462350
                }) ?? 0
                combatTargetIdentity = owner.base.heap.containingAllocationIdentity(at: combatTargetActor, count: 0x110)
                if combatTargetIdentity != nil {
                    combatLogicIdentity = owner.base.heap.containingAllocationIdentity(at: owner.w(combatTargetActor + 0x6c), count: 0x20)
                }
            }
            if var combat = player["combat"] as? [String: UInt32] {
                let live = combatTargetLive(owner)
                combat["target_live"] = live ? 1 : 0
                if live {
                    let target = combatTargetActor, info = owner.w(target + 0x6c)
                    combat["target_health"] = owner.w(target + 0x10c)
                    combat["target_x"] = owner.w(target + 0x4c); combat["target_y"] = owner.w(target + 0x50)
                    combat["target_state"] = owner.w(info + 0x1c)
                }
                player["combat"] = combat
            }
        }
        if routeLaterLevel { player["speech"] = owner.speechSnapshot }
        return player
    }

    // Debug only (CLAW_REAL_SPEED_CONTROL): the selected weapon (player state +0x30:
    // 1 pistol, 2 magic, 3 dynamite), its ammo (+0x70, +0x74, +0x78), the keys
    // GetAsyncKeyState reports held, and how often each projectile logic
    // (PistolBullet 0x40ff80, MagicBullet 0x410040, Dynamite 0x43a850) was invoked.
    private func weaponSnapshot(_ owner: ClawNativeMenuInterface) -> [String: Any] {
        func word(_ address: UInt32) -> UInt32? {
            guard let pointer = owner.base.heap.lookupBytes(address, count: 4) else { return nil }
            return UnsafeRawPointer(pointer).loadUnaligned(as: UInt32.self)
        }
        var result: [String: Any] = ["held_keys": (owner.base.windowInput?.virtualKeys ?? []).sorted().map { Int($0) }]
        let counts = owner.resources.invokeCounts
        result["projectile_invokes"] = ["pistol": counts[0x40ff80] ?? 0, "magic": counts[0x410040] ?? 0, "dynamite": counts[0x43a850] ?? 0]
        if let actor = word(0x537e88), let logic = word(actor + 0x6c), let state = word(logic + 0x14),
           let weapon = word(state + 0x30), let pistol = word(state + 0x70), let magic = word(state + 0x74),
           let dynamite = word(state + 0x78), let controller = word(0x537204), let events = word(controller + 4) {
            result.merge(["weapon": Int(weapon), "ammo": ["pistol": Int(Int32(bitPattern: pistol)),
                "magic": Int(Int32(bitPattern: magic)), "dynamite": Int(Int32(bitPattern: dynamite))],
                "attack_active":word(state+4).map(Int.init) ?? -1,
                "attack_code":word(state+0x3c).map(Int.init) ?? -1,
                "attack_sequence":word(state+0xe8).map(Int.init) ?? -1,
                "input_events": Int(events)]) { _, new in new }
        }
        return result
    }

    // Debug only (CLAW_REAL_SPEED_CONTROL): the power-up timer, the view bounds the
    // HUD frames place against, and every HUD number-group actor (group vtable
    // 0x50b5c4 at info+0x18, bound back to the actor). Logs changes to hud.log and
    // saves the frames around a change of the power-up timer or an actor's hide bit.
    private var hudActors: [UInt32] = []
    private var hudLast: [String] = []
    private var hudShots = 0
    private func hudProbe(_ owner: ClawNativeMenuInterface, frame: CGImage, url: URL) -> [String: Any] {
        let heap = owner.base.heap
        func word(_ address: UInt32) -> UInt32? {
            guard let pointer = heap.lookupBytes(address, count: 4) else { return nil }
            return UnsafeRawPointer(pointer).loadUnaligned(as: UInt32.self)
        }
        func isHUD(_ actor: UInt32) -> Bool {
            guard let info = word(actor &+ 0x6c), let group = word(info &+ 0x18), word(group) == 0x50b5c4,
                  word(group &+ 0x24) == actor else { return false }
            return true
        }
        if frameCount % 60 == 0 || hudActors.contains(where: { !isHUD($0) }) {
            hudActors = heap.debugAllocationBases.filter(isHUD)
        }
        let actors: [[String: Any]] = hudActors.map { actor in
            ["actor": String(actor, radix: 16), "x": Int(Int32(bitPattern: word(actor + 0x4c) ?? 0)),
             "y": Int(Int32(bitPattern: word(actor + 0x50) ?? 0)), "flags8": word(actor + 8) ?? 0,
             "flags40": word(actor + 0x40) ?? 0, "image": String(word(actor + 0x174) ?? 0, radix: 16)]
        }
        let view = [0x5370c8, 0x5370cc, 0x5370d0, 0x5370d4].map { Int(Int32(bitPattern: word(UInt32($0)) ?? 0)) }
        let ms = Int(word(0x534ea8) ?? 0), kind = Int(word(0x534eac) ?? 0)
        let app = owner.base.applicationToken
        let layout = [Int(word(app &+ 0x68) ?? 0xdead), Int(word(app &+ 0x38) ?? 0xdead)]
        let summary = ["ms0=\(ms == 0)", "kind=\(kind)", "view=\(view)", "layout=\(layout)"] +
            actors.map { "\($0["actor"]!):\($0["x"]!),\($0["y"]!),f40=\($0["flags40"]!),f8=\($0["flags8"]!)" }
        if summary != hudLast {
            let line = "frame=\(frameCount) ms=\(ms) " + summary.joined(separator: " ") + "\n"
            if let handle = try? FileHandle(forWritingTo: url.appendingPathComponent("hud.log")) {
                handle.seekToEndOfFile(); handle.write(line.data(using: .utf8)!); try? handle.close()
            } else { try? line.data(using: .utf8)!.write(to: url.appendingPathComponent("hud.log")) }
            if !hudLast.isEmpty { hudShots = 4 }
            hudLast = summary
        }
        if hudShots > 0 {
            hudShots -= 1
            try? save(frame, to: url.appendingPathComponent(String(format: "hud-%05d.png", frameCount)))
        }
        return ["ms": ms, "kind": kind, "view": view, "actors": actors]
    }

    private func save(_ image: CGImage, to url: URL) throws {
        try Self.saveImage(image, to: url)
    }
    nonisolated private static func saveImage(_ image: CGImage, to url: URL) throws {
        guard let destination = CGImageDestinationCreateWithURL(url as CFURL, "public.png" as CFString, 1, nil) else {
            throw AssetError.invalid("Cannot save menu input frame")
        }
        CGImageDestinationAddImage(destination, image, nil)
        guard CGImageDestinationFinalize(destination) else { throw AssetError.invalid("Cannot save menu input frame") }
    }

    // --fast-clock: run frames back to back, yielding to the run loop about
    // every 50 ms so the window and the input views stay responsive, until the
    // check ends; then wait for offline music renders and quit.
    func runFast() {
        if inputGate { scheduleGated(); return }
        guard fastClock, evidenceURL != nil else { return }
        if !windowActive {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) { [weak self] in self?.runFast() }
            return
        }
        // A recovered frame may block in movie playback and pump events.
        // Leave GCD's main queue free to deliver AVPlayer's startup work.
        RunLoop.main.perform(inModes: [.default]) { [weak self] in
            MainActor.assumeIsolated { self?.runFastBatch() }
        }
    }

    private func runFastBatch() {
        func running() -> Bool { owner != nil && failure == nil && frameCount < checkFrames }
        let began = ProcessInfo.processInfo.systemUptime
        while running() && ProcessInfo.processInfo.systemUptime - began < 0.05 { tick() }
        if running() { runFast(); return }
        ClawNativeMenuMusic.waitForRenders()
        if let owner, owner.settingsDirectory != nil { owner.writeSettings() }
        exit(failure == nil ? 0 : 1)
    }

    // The input gate's loop (see inputGate): frames back to back up to the
    // controller's target, yielding to the run loop about every 50 ms; while
    // paused, the run loop delivers window events and the control file is read
    // every 2 ms.
    private func scheduleGated(after delay: TimeInterval = 0) {
        // A frame can synchronously pump events while playing a movie. GCD's
        // main queue cannot drain recursively, so running that frame inside a
        // dispatch callback starves AVPlayer startup. The delayed callback
        // only schedules a run-loop block and returns before any frame runs.
        if delay > 0 {
            DispatchQueue.main.asyncAfter(deadline: .now() + delay) { [weak self] in self?.scheduleGated() }
        } else {
            RunLoop.main.perform(inModes: [.default]) { [weak self] in
                MainActor.assumeIsolated { self?.runGated() }
            }
        }
    }

    private func runGated() {
        guard owner != nil || failure != nil else {
            scheduleGated(after: 0.01); return
        }
        let began = ProcessInfo.processInfo.systemUptime
        while windowActive, owner != nil, failure == nil, frameCount < gateTarget,
              ProcessInfo.processInfo.systemUptime - began < 0.05 { tick() }
        if owner != nil, failure == nil, frameCount < gateTarget {
            scheduleGated(after: windowActive ? 0 : 0.05); return
        }
        pollRealSpeedControl()
        while let command = gateCommands.first {
            if command.verb == "await" && liveInputTransitions[command.input, default: 0] < command.count { break }
            gateCommands.removeFirst()
            gateDone += 1
            if command.verb == "query-step" {
                gateQueryOverride = UInt32(command.count)
                gateQueryStep = UInt32(command.count)
            }
            if command.verb == "landing-frame-ms" { landingFrameStep = UInt32(command.count) }
            if command.verb == "checkpoint-enemy",let owner {
                do {try owner.placeCheckpointEnemyCheck()} catch {stop(error:error)}
            }
            if command.verb == "checkpoint-source",let owner {
                do {try owner.placeCheckpointEnemyCheck(UInt32(command.count))} catch {stop(error:error)}
            }
            if command.verb == "checkpoint-loot",let owner {
                do {try owner.placeCheckpointLootCheck()} catch {stop(error:error)}
            }
            if command.verb == "checkpoint-score",let owner {owner.prepareCheckpointScoreCheck()}
            if command.verb == "checkpoint-drop",let owner {
                do {try owner.placeCheckpointDropCheck()} catch {stop(error:error)}
            }
            if command.verb == "checkpoint-loot-kind",let owner {
                do {try owner.spawnCheckpointLootCheck(item:UInt32(command.count))} catch {stop(error:error)}
            }
            if command.verb == "checkpoint-loot-spawn",let owner {
                do {try owner.spawnCheckpointLootCheck()} catch {stop(error:error)}
            }
            if command.verb == "checkpoint-mechanism",let owner {
                do {try owner.placeCheckpointMechanismCheck(UInt32(command.count))} catch {stop(error:error)}
            }
            if command.verb == "checkpoint-place",let owner {
                do {try owner.placeCrazyCheckpointCheck(command.count)} catch {stop(error:error)}
            }
            if command.verb == "lua-place",let owner {
                do {try owner.placeCustomLuaCheck(command.input)} catch {stop(error:error)}
            }
            if command.verb == "lua-values",let owner {
                do {try owner.checkCustomLuaValues()} catch {stop(error:error)}
            }
            if command.verb == "lua-gameplay-check",let owner {
                do {try owner.checkCustomGameplayScript(command.input)} catch {stop(error:error)}
            }
            if command.verb == "lua-gameplay",let owner {
                do {try owner.checkCustomGameplayValues()} catch {stop(error:error)}
            }
            if command.verb == "palette-values",let owner {
                do {try owner.checkCustomPaletteValues()} catch {stop(error:error)}
            }
            if command.verb == "lua-stale",let owner {
                do {try owner.checkCustomLuaStale()} catch {stop(error:error)}
            }
            if command.verb == "grab-place", let owner {
                do { try placeForGrabCheck(owner, callback: UInt32(command.count)) } catch { stop(error:error) }
            }
            if command.verb == "sweep-place",let owner {
                do {try placeForGrabCheck(owner,callback:UInt32(command.count),centered:true)} catch {stop(error:error)}
            }
            if command.verb == "v13-boss-init", let owner {
                // Explicit fixture: execute the normal registered initializer
                // of a deferred, offscreen boss. Never replace its field values.
                let actor = UInt32(command.count)
                let game = owner.w(owner.base.applicationToken + 0x2c)
                if owner.w(game) == 0x50c264, owner.base.heap.lookupBytes(actor, count: 0x110) != nil {
                    let logic = owner.w(actor + 0x6c)
                    if logic != 0, owner.base.heap.lookupBytes(logic, count: 0x20) != nil {
                        let callback = owner.w(logic + 0x10)
                        if [UInt32(0x47e210),0x453d30,0x49fb30,0x443290,0x458680,0x4041f0,0x47f6e0,0x4633a0].contains(callback), owner.w(logic + 0x1c) == 0 {
                            _ = owner.resources.invoke(callback, 0, [actor])
                        }
                    }
                }
            }
            if command.verb == "run" { gateTarget = frameCount + max(command.count, 0); break }
            if command.verb == "quit" {
                saveRealSpeed(["status": failure == nil ? "running" : "fail"])
                exit(failure == nil ? 0 : 1)
            }
        }
        if frameCount >= gateTarget || failure != nil || owner == nil {
            let state = gateDone * 1_000_000 + gateReceived
            if state != gateReported, let realSpeedURL {
                gateReported = state
                try? JSONSerialization.data(withJSONObject: ["seq": gateDone, "frame": frameCount, "received": gateReceived,
                    "status": failure == nil ? "paused" : "fail"], options: [.sortedKeys])
                    .write(to: realSpeedURL.appendingPathComponent("gate.json"), options: .atomic)
            }
            scheduleGated(after: 0.002)
        } else {
            scheduleGated()
        }
    }

    func close() { owner?.close(); owner?.base.shutdown(); owner = nil }
    private func stop(error: Error) {
        failure = String(describing: error)
        // A failed frame can interrupt a gated batch before its target. Publish
        // the last completed frame, as the real-time logger already does, so
        // the checker retains the command that led to the fault.
        if let realSpeedURL, let live = realSpeedLatestLive {
            try? JSONSerialization.data(withJSONObject: live, options: [.sortedKeys])
                .write(to: realSpeedURL.appendingPathComponent("live.json"), options: .atomic)
        }
        if let realSpeedURL, let image { try? save(image, to: realSpeedURL.appendingPathComponent("frame-fail.png")) }
        if let realSpeedURL, let trace = owner?.resources.failureTrace, trace.count > 40 {
            try? trace.joined(separator: "\n").write(to: realSpeedURL.appendingPathComponent("trace.txt"), atomically: true, encoding: .utf8)
        }
        saveRealSpeed(["status": "fail", "error": failure!, "failing_frame": frameCount + 1,
            "frame_check": owner?.lastFrameCheck ?? [:], "trace": owner?.resources.failureTrace.suffix(40).map { $0 } ?? []])
        try? saveLiveState()
        if let evidenceURL {
            try? JSONSerialization.data(withJSONObject: ["status": "fail", "error": failure!,
                "completedFrames": frameCount, "frames": evidence, "multi_flip_frames": multiFlipFrames, "play_frames": playFrames, "trace": owner?.resources.failureTrace ?? [],
                "frame_check": owner?.lastFrameCheck ?? [:]])
                .write(to: evidenceURL.appendingPathComponent("app-menu.json"), options: .atomic)
        }
        close()
    }
}

struct ClawMainMenuView: View {
    @StateObject private var menu = ClawMainMenuPresentation()
    @Environment(\.scenePhase) private var scenePhase
    private let ticks = Timer.publish(every: 1.0 / 60, on: .main, in: .common).autoconnect()
    var body: some View {
        ZStack {
            Color.black
            // Until the game presents its first frame the window stays black, as the original's screen does.
            ClawSurfaceView(surface: menu.surfaceLayer).accessibilityLabel("Captain Claw")
            if menu.movieActive {
                // Original 640x480 screen: the 640x240 logo is line-doubled and
                // the 320x240 movies fill it, so every movie shows at 4:3.
                ClawNativeMovieView(playback: menu.moviePlayback, allowsSkipping: false)
                    .aspectRatio(4.0 / 3.0, contentMode: .fit)
            }
            ClawMenuInputView(menu: menu)
            if let levels = menu.customLevels {
                Color.black.opacity(0.7)
                VStack(alignment:.leading,spacing:12) {
                    Text("Load Custom Level").font(.title2.bold())
                    Text("Import the folder containing a .wwd and its same-name asset folder, or a standalone .wwd.").font(.caption)
                    Text(menu.customDirectory.path).font(.caption2).textSelection(.enabled)
                    ScrollViewReader { proxy in
                        ScrollView {
                            VStack(alignment:.leading) {
                                ForEach(Array(levels.enumerated()),id:\.offset) { index,url in
                                    Button(url.deletingPathExtension().lastPathComponent) {menu.customSelected = index;menu.customRestartSlot = 0}
                                        .tint(menu.customSelected == index ? .orange:.accentColor).id(index)
                                }
                            }.frame(maxWidth:.infinity,alignment:.leading)
                        }.frame(maxHeight:230)
                            .onChange(of:menu.customSelected) { _,value in proxy.scrollTo(value) }
                    }
                    if levels.isEmpty {Text("No custom levels yet.")}
                    Button(menu.customRestartSlot == 0 ? "Start from beginning (← / →)":"Resume super checkpoint \(menu.customRestartSlot) (← / →)") {menu.cycleCustomRestart()}.disabled(levels.isEmpty)
                    if let error = menu.customError {Text(error).foregroundStyle(.orange).font(.caption)}
                    HStack {
                        Button("Import…") {menu.customImporter = true}
                        Spacer()
                        Button("Cancel") {menu.closeCustomLevels()}
                        Button("Load") {menu.chooseCustomLevel()}.disabled(levels.isEmpty)
                    }
                }.buttonStyle(.bordered).padding(20).frame(width:550)
                    .background(.regularMaterial,in:RoundedRectangle(cornerRadius:14))
            }
            if menu.players != nil {
                Color.black.opacity(0.7)
                ClawPlayersSheet(menu:menu)
            }
            if let controls = menu.controls {
                Color.black.opacity(0.7)
                VStack(spacing:4) {
                    Text("Controls").font(.title2.bold())
                    Text(controls.capturing ? "Press a new key · Esc cancels · Backspace clears" : "Return changes a key. Left / Right or controller A changes its button.")
                        .font(.caption)
                    ForEach(Array(ClawNativeMenuInterface.controlActions.enumerated()),id:\.offset) { index, action in
                        HStack {
                            Text(action.name).frame(width:160,alignment:.leading)
                            Button {
                                menu.chooseControl(index)
                            } label: {
                                Text(controls.selected == index && controls.capturing ? "Press a key…" : ClawMainMenuPresentation.controlKeyName(controls.keys[index]))
                                    .frame(width:130)
                            }
                            .tint(controls.selected == index ? .orange:.accentColor)
                            Picker("Joystick",selection:Binding(get:{menu.controls?.buttons[index] ?? 0},set:{menu.controls?.buttons[index] = $0})) {
                                Text("None").tag(UInt32(0))
                                ForEach(Array(["A", "B", "X", "Y", "L1", "R1", "L2", "R2"].enumerated()),id:\.offset) { button,label in
                                    Text(label).tag(UInt32(1)<<button)
                                }
                                Text("Y / L1 / R1").tag(UInt32(0x38))
                            }.labelsHidden().frame(width:110)
                        }
                    }
                    #if !targetEnvironment(macCatalyst)
                    if UIDevice.current.userInterfaceIdiom == .pad {
                        Toggle("On-screen touch controls", isOn: Binding(get: {menu.controls?.touchControls ?? false}, set: {menu.controls?.touchControls = $0}))
                            .toggleStyle(.switch)
                        Text("Claw needs quick, precise and simultaneous presses, so a keyboard or game controller plays best; touch controls are there for when you have neither.")
                            .font(.caption)
                    }
                    #endif
                    Toggle("Disable Joystick",isOn:Binding(get:{menu.controls?.disableJoystick ?? false},set:{menu.controls?.disableJoystick = $0}))
                        .toggleStyle(.switch)
                        .toggleStyle(.switch)
                    Text("Stick / D-pad moves · A selects · B backs · Menu pauses. Y / L1 / R1 cycles projectiles by default.").font(.caption)
                    let shared = controls.keys.filter{$0 != 0}.count != Set(controls.keys.filter{$0 != 0}).count
                    Text(controls.error ?? (shared ? "Shared key: both actions will run, as in the original." : "Arrow keys move. Try X for Hand Attack to avoid Control + arrow shortcuts."))
                        .font(.caption).foregroundStyle(controls.error != nil || shared ? Color.orange:Color.secondary)
                    HStack {
                        Button("Defaults") {menu.controlsDefaults()}.tint(controls.selected == 9 ? .orange:.accentColor)
                        Spacer()
                        Button("Cancel") {menu.closeControls(save:false)}.tint(controls.selected == 10 ? .orange:.accentColor)
                        Button("Save") {menu.closeControls(save:true)}.tint(controls.selected == 11 ? .orange:.accentColor)
                    }
                }
                .buttonStyle(.bordered).padding(20).frame(width:510)
                .background(.regularMaterial,in:RoundedRectangle(cornerRadius:14))
            }
            if menu.customPresentationActive {
                #if targetEnvironment(macCatalyst)
                VStack {Spacer();ClawLevelActions(menu:menu)}
                #else
                // Developer text-key panel remains available through an explicit launch flag.
                if ProcessInfo.processInfo.arguments.contains("--level-keys") {
                    VStack {Spacer();ClawLevelActions(menu:menu)}
                }
                #endif
            }
            if menu.checkpointOverlay {
                VStack {
                    Button("Save custom checkpoint") { menu.requestCustomSave() }.disabled(!menu.canSaveCustomCheckpointNow)
                    ForEach(0..<3,id: \.self) { slot in
                        Button(menu.customCheckpointLabels[slot]) { menu.requestCustomRestore(slot:slot) }
                            .disabled(!menu.hasCustomCheckpointSlot(slot))
                            .tint(menu.checkpointSelectedSlot == slot ? .orange : .accentColor)
                    }
                    Button("Cancel") {menu.checkpointOverlay = false}
                }.buttonStyle(.borderedProminent).padding()
                    .background(.regularMaterial,in:RoundedRectangle(cornerRadius:12))
            }
            if let toast = menu.checkpointToast {
                VStack { Text(toast).padding(12).background(.regularMaterial,in:Capsule()); Spacer() }
                    .padding(.top,24).allowsHitTesting(false)
            }
            if let failure = menu.failure { Text(failure).foregroundStyle(.white).padding() }
        }
        .frame(minWidth: 640, minHeight: 480)
        .ignoresSafeArea()
        .onAppear { menu.start(); menu.runFast() }
        .onOpenURL {menu.importCustomLevel($0)}
        .fileImporter(isPresented:$menu.customImporter,allowedContentTypes:[.folder,UTType(filenameExtension:"wwd") ?? .data]) { result in
            switch result {
            case .success(let url):menu.importCustomLevel(url)
            case .failure(let error):menu.customError = error.localizedDescription
            }
        }
        .alert("Custom Level",isPresented:Binding(get:{menu.customError != nil && menu.customLevels == nil},set:{if !$0 {menu.customError = nil}})) {
            Button("OK") {menu.customError = nil}
        } message: {Text(menu.customError ?? "")}
        .onDisappear { menu.close() }
        .onReceive(NotificationCenter.default.publisher(for: UIApplication.willTerminateNotification)) { _ in menu.close() }
        .onReceive(ticks) { _ in if !menu.fastClock { menu.tick() } }
        .onChange(of: scenePhase) { _, phase in menu.windowActivationChanged(phase == .active) }
    }
}

// Level scripts may bind any letter/number, independently of retail controls.
// Each touch holds its key until lift/cancel, through the same native input port.
private struct ClawLevelActions:View {
    @ObservedObject var menu:ClawMainMenuPresentation
    @State private var expanded = false
    private let keys:[UInt32] = [37,38,40,39,13,32,8,9,160,16,17,18,0xbb,0xbd,0xdb,0xdc,0xdd]+Array(65...90)+Array(48...57)
    private func label(_ key:UInt32)->String {
        [37:"←",38:"↑",40:"↓",39:"→",13:"Enter",32:"Space",8:"⌫",9:"Tab",160:"L Shift",16:"Shift",17:"Ctrl",18:"Alt",0xbb:"=",0xbd:"−",0xdb:"[",0xdc:"\\",0xdd:"]"][key] ?? String(UnicodeScalar(key)!)
    }
    var body:some View {
        VStack {
            Button(expanded ? "Hide level keys":"Level keys") {expanded.toggle()}.buttonStyle(.bordered)
            if expanded {
                LazyVGrid(columns:Array(repeating:GridItem(.flexible()),count:10),spacing:4) {
                    ForEach(keys,id:\.self) {key in
                        ClawHeldLevelKey(label:label(key)) {down in
                            menu.liveInputArrived(key,down:down);menu.key(key,down:down)
                        }
                    }
                }.padding(8).background(.regularMaterial,in:RoundedRectangle(cornerRadius:12))
            }
        }.padding(12).frame(maxWidth:760)
    }
}
private struct ClawHeldLevelKey:View {
    let label:String
    let send:(Bool)->Void
    @State private var held = false
    var body:some View {
        Text(label).font(.caption).frame(maxWidth:.infinity,minHeight:36)
            .background(held ? Color.orange.opacity(0.8):Color.gray.opacity(0.4),in:RoundedRectangle(cornerRadius:5))
            .gesture(DragGesture(minimumDistance:0).onChanged {_ in
                if !held {held = true;send(true)}
            }.onEnded {_ in held = false;send(false)})
            .onDisappear {if held {held = false;send(false)}}
            .accessibilityLabel(label)
    }
}

// Native modal surfaces retain original records; game code owns every mutation.
private struct ClawPlayersSheet:View {
    @ObservedObject var menu:ClawMainMenuPresentation
    var body:some View {
        if let draft = menu.players {
            VStack(alignment:.leading,spacing:12) {
                Text(draft.page == 1 ? "New Player":draft.page == 2 ? "Remove Player?":"Edit Players").font(.title2.bold())
                if draft.page == 1 {
                    TextField("Name",text:Binding(get:{menu.players?.name ?? ""},set:{menu.players?.name = String($0.prefix(ClawNativeMenuInterface.playerTextLimits[0]))}))
                    TextField("Location",text:Binding(get:{menu.players?.location ?? ""},set:{menu.players?.location = String($0.prefix(ClawNativeMenuInterface.playerTextLimits[1]))}))
                    TextField("Comment",text:Binding(get:{menu.players?.email ?? ""},set:{menu.players?.email = String($0.prefix(ClawNativeMenuInterface.playerTextLimits[2]))}))
                    HStack {
                        Button("Cancel") {menu.playerAction("cancel")}
                        Spacer()
                        Button("Create") {menu.playerAction("create")}
                    }
                } else if draft.page == 2 {
                    Text("Remove \(draft.choices.first(where:{$0.id == draft.selected})?.name ?? "") and all their saved games?")
                    HStack {
                        Button("Cancel") {menu.playerAction("cancel")}
                        Spacer()
                        Button("Remove",role:.destructive) {menu.playerAction("confirm")}
                    }
                } else {
                    Text("Choose a player. N: New · R: Remove · Esc: Cancel").font(.caption)
                    ScrollView {
                        VStack(alignment:.leading) {
                            ForEach(draft.choices) { choice in
                                Button {menu.players?.selected = choice.id;menu.playerAction("select")} label: {
                                    HStack {
                                        Image(systemName:draft.selected == choice.id ? "largecircle.fill.circle":"circle")
                                        VStack(alignment:.leading) {
                                            Text(choice.name)
                                            if !choice.location.isEmpty {Text(choice.location).font(.caption)}
                                            if !choice.email.isEmpty {Text(choice.email).font(.caption)}
                                        }
                                        Spacer()
                                    }
                                }
                            }
                        }
                    }.frame(maxHeight:220)
                    HStack {
                        Button("New") {menu.playerAction("new")}
                        Button("Remove") {menu.playerAction("remove")}
                            .disabled(draft.choices.first(where:{$0.id == draft.selected})?.name.lowercased() == "player")
                        Spacer()
                        Button("Cancel") {menu.playerAction("close")}
                        Button("OK") {menu.playerAction("accept")}
                    }
                }
                if let error = draft.error {Text(error).font(.caption).foregroundStyle(.orange)}
            }
            .onSubmit {menu.playerAction("create")}
            .textFieldStyle(.roundedBorder).buttonStyle(.bordered).padding(20).frame(width:510)
            .background(.regularMaterial,in:RoundedRectangle(cornerRadius:14))
        }
    }
}

// Hosts the presentation's screen layer, scaled to fit with square pixels.
private struct ClawSurfaceView: UIViewRepresentable {
    let surface: CALayer
    func makeUIView(context: Context) -> SurfaceView { SurfaceView(surface: surface) }
    func updateUIView(_ view: SurfaceView, context: Context) {}
    final class SurfaceView: UIView {
        private let surface: CALayer
        init(surface: CALayer) {
            self.surface = surface
            super.init(frame: .zero)
            backgroundColor = .clear
            isUserInteractionEnabled = false
            layer.addSublayer(surface)
        }
        required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
        override func layoutSubviews() {
            super.layoutSubviews()
            CATransaction.begin(); CATransaction.setDisableActions(true)
            surface.frame = bounds
            CATransaction.commit()
        }
    }
}

#if targetEnvironment(macCatalyst)
// UIKit drops an unmatched key-up after cancelling UIPress on deactivation.
// Observe the actual AppKit event before UIKit handles it, including releases
// posted to this process while another window is active. The defined native
// load shortcuts are consumed before Catalyst handles key equivalents; all
// other events pass through and duplicate UIKit releases are suppressed.
@MainActor private enum ClawCatalystKeyUpMonitor {
    static let virtualKeys: [Int: UInt32] = [
        0:65,1:83,2:68,3:70,4:72,5:71,6:90,7:88,8:67,9:86,11:66,12:81,13:87,14:69,15:82,
        10:0xe2,16:89,17:84,18:49,19:50,20:51,21:52,22:54,23:53,24:0xbb,25:57,26:55,27:0xbd,28:56,29:48,
        30:0xdd,33:0xdb,39:0xde,41:0xba,42:0xdc,43:0xbc,44:0xbf,47:0xbe,50:0xc0,31:79,32:85,34:73,35:80,36:13,37:76,38:74,40:75,45:78,46:77,48:9,49:32,51:8,53:27,
        56:16,58:18,59:17,60:16,61:18,62:17,69:0x6b,78:0x6d,76:13,113:0x13,
        82:0x60,83:0x61,84:0x62,85:0x63,86:0x64,87:0x65,88:0x66,89:0x67,91:0x68,92:0x69,
        114:0x2d,115:0x24,116:0x21,117:0x2e,119:0x23,121:0x22,
        122:0x70,120:0x71,99:0x72,118:0x73,96:0x74,97:0x75,98:0x76,100:0x77,101:0x78,
        109:0x79,103:0x7a,111:0x7b,123:37,124:39,125:40,126:38]
    private typealias Handler = @convention(block) (NSObject) -> NSObject?
    private typealias Add = @convention(c) (AnyClass, Selector, UInt64, Handler) -> Unmanaged<NSObject>?
    private typealias Remove = @convention(c) (AnyClass, Selector, NSObject) -> Void
    static func install(_ received: @escaping @MainActor (Int, UInt64) -> Void, shortcut: @escaping @MainActor (Int, UInt64) -> Bool) -> NSObject? {
        let selector = NSSelectorFromString("addLocalMonitorForEventsMatchingMask:handler:")
        guard let type = NSClassFromString("NSEvent"), let method = class_getClassMethod(type, selector) else { return nil }
        let add = unsafeBitCast(method_getImplementation(method), to: Add.self)
        let handler: Handler = { event in
            let handled = MainActor.assumeIsolated { () -> Bool in
                let kind = (event.value(forKey: "type") as? NSNumber)?.intValue ?? 0
                let code = (event.value(forKey: "keyCode") as? NSNumber)?.intValue ?? -1
                let flags = (event.value(forKey: "modifierFlags") as? NSNumber)?.uint64Value ?? 0
                let modifier: UInt64 = [56:1 << 17,60:1 << 17,59:1 << 18,62:1 << 18,58:1 << 19,61:1 << 19][code] ?? 0
                if kind == 10, shortcut(code, flags) { return true }
                if kind == 11 || (kind == 12 && modifier != 0 && flags & modifier == 0) { received(code, flags) }
                return false
            }
            return handled ? nil : event
        }
        return add(type, selector, (1 << 10) | (1 << 11) | (1 << 12), handler)?.takeUnretainedValue()
    }
    static func remove(_ monitor: NSObject) {
        let selector = NSSelectorFromString("removeMonitor:")
        guard let type = NSClassFromString("NSEvent"), let method = class_getClassMethod(type, selector) else { return }
        unsafeBitCast(method_getImplementation(method), to: Remove.self)(type, selector, monitor)
    }
}
#endif

// Catalyst uses UIKit. This view translates physical events into the original
// window message payloads; all menu decisions remain in recovered game code.
private struct ClawMenuInputView: UIViewRepresentable {
    #if targetEnvironment(macCatalyst)
    let menu: ClawMainMenuPresentation
    #else
    @ObservedObject var menu: ClawMainMenuPresentation
    #endif
    func makeUIView(context: Context) -> InputView { InputView(menu: menu) }
    func updateUIView(_ view: InputView, context: Context) {
        view.updateFocus()
        #if !targetEnvironment(macCatalyst)
        view.updateTouchControls()
        #endif
    }

    final class InputView: UIView {
        private let menu: ClawMainMenuPresentation
        private var held: Set<UInt32> = []
        private var customPickerVisible = false
        func updateFocus() {
            let pickerClosed = customPickerVisible && menu.customLevels == nil
            customPickerVisible = menu.customLevels != nil
            // The picker's SwiftUI buttons can retain keyboard focus after
            // loading. Hand it back to the physical-input responder on exit.
            if pickerClosed || (menu.controls != nil && !isFirstResponder) {
                DispatchQueue.main.async { [weak self] in
                    guard let self,self.window != nil else {return}
                    let restored = self.becomeFirstResponder()
                    self.menu.observeInput(["boundary":"picker-focus","restored":restored])
                }
            }
        }
        #if !targetEnvironment(macCatalyst)
        private var movieTouches: Set<UITouch> = []
        private var controlTouches: [UITouch: UInt32] = [:]
        private var touchKeys: Set<UInt32> = []
        private var overlayVisible = false
        func updateTouchControls() {
            let visible = menu.touchControlsVisible
            if visible != overlayVisible {
                overlayVisible = visible
                if !visible { clearTouchControls() }
                setNeedsDisplay()
            }
        }
        private func clearTouchControls() {
            // Consume the rest of an overlay contact even if Pause hides it.
            controlTouches = controlTouches.mapValues { _ in 0 }
            deliverTouchKeys([])
        }
        private func deliverTouchKeys(_ keys: Set<UInt32>) {
            for key in touchKeys.subtracting(keys) { menu.liveInputArrived(key,down:false); menu.key(key,down:false) }
            for key in keys.subtracting(touchKeys) { menu.liveInputArrived(key,down:true); menu.key(key,down:true) }
            touchKeys = keys
            setNeedsDisplay()
        }
        private func updateTouches(_ touches: Set<UITouch>, ended: Bool = false) -> Bool {
            let consumed = overlayVisible ? touches : touches.filter { controlTouches[$0] != nil }
            guard !consumed.isEmpty else { return false }
            for touch in consumed {
                menu.observeInput(["touch":ended ? "up":"down/move", "point":[touch.location(in:self).x,touch.location(in:self).y], "contacts":touches.count])
                if ended { controlTouches.removeValue(forKey:touch) }
                else if overlayVisible {
                    let action = ClawTouchLayout.action(at:touch.location(in:self), size:bounds.size)
                    controlTouches[touch] = action.map { menu.touchKey($0) } ?? 0
                }
            }
            deliverTouchKeys(Set(controlTouches.values.filter {$0 != 0}))
            return true
        }
        override func draw(_ rect: CGRect) {
            guard overlayVisible else { return }
            for (action, label, frame) in ClawTouchLayout.buttons(size:bounds.size) {
                let path = UIBezierPath(roundedRect:frame,cornerRadius:18)
                (touchKeys.contains(menu.touchKey(action)) ? UIColor.systemOrange.withAlphaComponent(0.6) : UIColor.black.withAlphaComponent(0.28)).setFill()
                path.fill()
                UIColor.white.withAlphaComponent(0.45).setStroke(); path.lineWidth = 2; path.stroke()
                let attributes: [NSAttributedString.Key:Any] = [.font:UIFont.boldSystemFont(ofSize:18),.foregroundColor:UIColor.white.withAlphaComponent(0.75)]
                let size = (label as NSString).size(withAttributes:attributes)
                (label as NSString).draw(at:CGPoint(x:frame.midX-size.width/2,y:frame.midY-size.height/2),withAttributes:attributes)
            }
        }
        #endif
        #if targetEnvironment(macCatalyst)
        private var keyUpMonitor: NSObject?
        private var nativeReleased: Set<UInt32> = []
        private var nativeObserved: Set<UInt32> = []
        #endif
        override var canBecomeFirstResponder: Bool { true }
        override var keyCommands: [UIKeyCommand]? {
            var commands = ["3"].map { slot in
                let command = UIKeyCommand(input: slot, modifierFlags: [.command, .shift], action: #selector(loadCustomKey(_:)))
                command.wantsPriorityOverSystemBehavior = true
                return command
            }
            let save = UIKeyCommand(input:"3",modifierFlags:[.command],action:#selector(saveCustomKey(_:)))
            save.wantsPriorityOverSystemBehavior = true
            commands.append(save)
            return commands
        }
        @objc private func saveCustomKey(_ command: UIKeyCommand) {
            #if targetEnvironment(macCatalyst)
            nativeReleased.remove(0x33);nativeObserved.insert(0x33)
            #endif
            menu.liveInputArrived(0x33,down:true);menu.requestCustomSave()
        }
        @objc private func loadCustomKey(_ command: UIKeyCommand) {
            guard let input = command.input, let slot = UInt32(input) else { return }
            #if targetEnvironment(macCatalyst)
            nativeReleased.remove(0x30+slot);nativeObserved.insert(0x30+slot)
            #endif
            menu.liveInputArrived(0x30+slot,down:true)
            menu.requestCustomRestore()
        }
        init(menu: ClawMainMenuPresentation) {
            self.menu = menu
            super.init(frame: .zero)
            backgroundColor = .clear
            #if !targetEnvironment(macCatalyst)
            isOpaque = false
            isMultipleTouchEnabled = true
            contentMode = .redraw
            #endif
            addGestureRecognizer(UIHoverGestureRecognizer(target: self, action: #selector(hover(_:))))
            let saves = UITapGestureRecognizer(target: self, action: #selector(showSaves(_:)))
            saves.numberOfTouchesRequired = 3
            addGestureRecognizer(saves)
            NotificationCenter.default.addObserver(self, selector: #selector(deactivate),
                name: UIApplication.willResignActiveNotification, object: nil)
        }
        required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
        override func didMoveToWindow() {
            super.didMoveToWindow()
            #if targetEnvironment(macCatalyst)
            if window != nil, keyUpMonitor == nil {
                keyUpMonitor = ClawCatalystKeyUpMonitor.install({ [weak self] code, flags in
                    self?.nativeKeyUp(code, flags: flags)
                }, shortcut: { [weak self] code, flags in
                    self?.nativeCustomCheckpoint(code, flags: flags) ?? false
                })
            } else if window == nil, let keyUpMonitor {
                ClawCatalystKeyUpMonitor.remove(keyUpMonitor)
                self.keyUpMonitor = nil
            }
            #endif
            if window != nil { DispatchQueue.main.async { [weak self] in self?.becomeFirstResponder() } }
            else { deactivate() }
        }
        #if targetEnvironment(macCatalyst)
        private func nativeCustomCheckpoint(_ mac: Int, flags: UInt64) -> Bool {
            let command: UInt64 = 1 << 20, shift: UInt64 = 1 << 17, option: UInt64 = 1 << 19
            guard mac == 20, flags & command != 0,
                  flags & (1 << 18) == 0, flags & option == 0 || flags & shift != 0 else { return false }
            let slot: UInt32 = 3
            nativeReleased.remove(0x30+slot);nativeObserved.insert(0x30+slot)
            menu.liveInputArrived(0x30+slot,down:true)
            if flags & option != 0 {menu.showCustomCheckpoint()}
            else if flags & shift != 0 {menu.requestCustomRestore()} else {menu.requestCustomSave()}
            return true
        }
        private func nativeKeyUp(_ mac: Int, flags: UInt64) {
            guard let code = ClawCatalystKeyUpMonitor.virtualKeys[mac] else { return }
            // Command belongs to macOS, except the custom checkpoint shortcut.
            let command = flags & (1 << 20) != 0
            let slot = command && flags & (1 << 18) == 0 && mac == 20 && (flags & (1 << 19) == 0 || flags & (1 << 17) != 0)
            let received = command && !slot ? 0 : code
            // Only releases paired with a down delivered to this responder
            // belong to the game. Cancellation clears held game state but
            // leaves this physical pairing until the actual event arrives.
            guard nativeObserved.remove(received) != nil else { return }
            nativeReleased.insert(received)
            menu.liveInputArrived(received, down: false)
            if !command {
                if let side = [56:UInt32(160),60:161,59:162,62:163,58:164,61:165][mac] {menu.systemKey(side,down:false)}
                if flags & (1 << 19) != 0 || code == 0x12 { menu.systemKey(code, down: false) }
                else { menu.key(code, down: false) }
            }
            held.remove(code)
        }
        #endif
        @objc private func deactivate() {
            menu.observeInput(["boundary": "deactivate", "held": held.sorted()])
            #if !targetEnvironment(macCatalyst)
            clearTouchControls()
            controlTouches.removeAll()
            #endif
            held.removeAll(); menu.releaseInput()
        }
        @objc private func showSaves(_ gesture: UITapGestureRecognizer) {
            if gesture.state == .ended { menu.showCustomCheckpoint() }
        }
        private func customCheckpointSlot(_ key: UIKey) -> UInt32? {
            guard key.modifierFlags.contains(.command), !key.modifierFlags.contains(.control),
                  !key.modifierFlags.contains(.alternate) || key.modifierFlags.contains(.shift) else { return nil }
            return key.keyCode == .keyboard3 ? 3 : nil
        }
        private func virtualKey(_ key: UIKey) -> UInt32? {
            // The original's default bindings (0x430d80), polled through
            // GetAsyncKeyState: arrows, Space jump, Control attack (VK_CONTROL),
            // Alt fire (VK_MENU, Option here), Shift weapon cycle (VK_SHIFT),
            // Z, and 1 to 4 weapon select. Command stays with macOS for its
            // application and window shortcuts.
            switch key.keyCode {
            case .keyboardLeftControl, .keyboardRightControl: return 0x11
            case .keyboardLeftAlt, .keyboardRightAlt: return 0x12
            case .keyboardLeftShift, .keyboardRightShift: return 0x10
            default: break
            }
            guard !key.modifierFlags.contains(.command) else { return nil }
            switch key.keyCode {
            case .keyboardUpArrow: return 38
            case .keyboardDownArrow: return 40
            case .keyboardLeftArrow: return 37
            case .keyboardRightArrow: return 39
            case .keyboardReturnOrEnter, .keypadEnter: return 13
            case .keyboardEscape: return 27
            case .keyboardSpacebar: return 32
            case .keyboardDeleteOrBackspace: return 8
            case .keyboardTab: return 9
            case .keyboardInsert: return 0x2d
            case .keyboardDeleteForward: return 0x2e
            case .keyboardHome: return 0x24
            case .keyboardEnd: return 0x23
            case .keyboardPageUp: return 0x21
            case .keyboardPageDown: return 0x22
            case .keypad0: return 0x60
            case .keypad1: return 0x61
            case .keypad2: return 0x62
            case .keypad3: return 0x63
            case .keypad4: return 0x64
            case .keypad5: return 0x65
            case .keypad6: return 0x66
            case .keypad7: return 0x67
            case .keypad8: return 0x68
            case .keypad9: return 0x69
            // '-', '=' (VK_OEM_MINUS, VK_OEM_PLUS) and the keypad's - and + carry
            // the viewport accelerators.
            case .keyboardOpenBracket: return 0xdb
            case .keyboardCloseBracket: return 0xdd
            case .keyboardBackslash: return 0xdc
            case .keyboardSemicolon: return 0xba
            case .keyboardQuote: return 0xde
            case .keyboardComma: return 0xbc
            case .keyboardPeriod: return 0xbe
            case .keyboardSlash: return 0xbf
            case .keyboardGraveAccentAndTilde: return 0xc0
            case .keyboardHyphen: return 0xbd
            case .keyboardEqualSign: return 0xbb
            case .keypadHyphen: return 0x6d
            case .keypadPlus: return 0x6b
            // VK_PAUSE: the Pause key, or F15 where Apple's extended keyboard has it.
            case .keyboardPause, .keyboardF15: return 0x13
            default:
                if let character = key.charactersIgnoringModifiers.uppercased().unicodeScalars.first,
                   key.charactersIgnoringModifiers.count == 1, (0x30...0x5a).contains(character.value) { return character.value }
                // Shift or Option can change the reported character (Shift-1 is
                // "!"); Windows virtual keys name the key, so fall back to its position.
                let usage = key.keyCode.rawValue
                if (UIKeyboardHIDUsage.keyboardA.rawValue...UIKeyboardHIDUsage.keyboardZ.rawValue).contains(usage) {
                    return 0x41 + UInt32(usage - UIKeyboardHIDUsage.keyboardA.rawValue)
                }
                if (UIKeyboardHIDUsage.keyboard1.rawValue...UIKeyboardHIDUsage.keyboard9.rawValue).contains(usage) {
                    return 0x31 + UInt32(usage - UIKeyboardHIDUsage.keyboard1.rawValue)
                }
                // F1 to F12: VK_F1 0x70 to VK_F12 0x7b.
                if (UIKeyboardHIDUsage.keyboardF1.rawValue...UIKeyboardHIDUsage.keyboardF12.rawValue).contains(usage) {
                    return 0x70 + UInt32(usage - UIKeyboardHIDUsage.keyboardF1.rawValue)
                }
                return usage == UIKeyboardHIDUsage.keyboard0.rawValue ? 0x30 : nil
            }
        }
        // Windows reports Alt, and any key while Alt is held, as WM_SYSKEYDOWN
        // and WM_SYSKEYUP, which the game's window procedure never sees as key
        // messages; the game reads them only through GetAsyncKeyState.
        private func modifierSide(_ key:UIKey)->UInt32? {
            switch key.keyCode {
            case .keyboardLeftShift:return 160
            case .keyboardRightShift:return 161
            case .keyboardLeftControl:return 162
            case .keyboardRightControl:return 163
            case .keyboardLeftAlt:return 164
            case .keyboardRightAlt:return 165
            default:return nil
            }
        }
        private func isSystemKey(_ key: UIKey) -> Bool {
            key.modifierFlags.contains(.alternate) || [.keyboardLeftAlt, .keyboardRightAlt].contains(key.keyCode)
        }
        override func pressesBegan(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
            var unhandled = Set<UIPress>()
            for press in presses {
                #if targetEnvironment(macCatalyst)
                if let key = press.key {
                    let code = customCheckpointSlot(key).map { 0x30 + $0 } ?? virtualKey(key) ?? 0
                    nativeReleased.remove(code); nativeObserved.insert(code)
                }
                #endif
                if let key = press.key, let slot = customCheckpointSlot(key) {
                    menu.liveInputArrived(0x30+slot,down:true)
                    if key.modifierFlags.contains(.alternate) {menu.showCustomCheckpoint()}
                    else if key.modifierFlags.contains(.shift) { menu.requestCustomRestore() }
                    else { menu.requestCustomSave() }
                    continue
                }
                if let key = press.key { menu.liveInputArrived(virtualKey(key) ?? 0, down: true) }
                // During a movie every key Windows reports as WM_KEYDOWN ends
                // it, mapped or not; Command and Option (WM_SYSKEYDOWN) do not.
                if menu.movieActive, let key = press.key, key.modifierFlags.intersection([.command, .alternate]).isEmpty,
                   ![.keyboardLeftAlt, .keyboardRightAlt, .keyboardLeftGUI, .keyboardRightGUI].contains(key.keyCode) {
                    menu.key(virtualKey(key) ?? 0, down: true); continue
                }
                if let key = press.key, let code = virtualKey(key) {
                    if let side = modifierSide(key),!menu.movieActive {menu.systemKey(side,down:true)}
                    if isSystemKey(key) { if !menu.movieActive { menu.systemKey(code, down: true) } }
                    else { menu.key(code, down: true, repeatKey: held.contains(code)) }
                    held.insert(code)
                } else { unhandled.insert(press) }
            }
            if !unhandled.isEmpty { super.pressesBegan(unhandled, with: event) }
        }
        override func pressesEnded(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
            // AppKit observes the actual release even after UIKit cancelled
            // its UIPress on a focus change. Let UIKit finish tracking that
            // press, but do not deliver the same physical release twice.
            let ended = presses.filter { press in
                #if targetEnvironment(macCatalyst)
                if let key = press.key {
                    let code = customCheckpointSlot(key).map { 0x30 + $0 } ?? virtualKey(key) ?? 0
                    if nativeReleased.remove(code) != nil { return false }
                }
                #endif
                return true
            }
            for press in ended { if let key = press.key {
                if let slot = customCheckpointSlot(key) { menu.liveInputArrived(0x30+slot,down:false);held.remove(0x100+slot) }
                else { menu.liveInputArrived(virtualKey(key) ?? 0, down: false) }
            } }
            for press in ended { if let key = press.key, let code = virtualKey(key) {
                if let side = modifierSide(key) {menu.systemKey(side,down:false)}
                if isSystemKey(key) { menu.systemKey(code, down: false) } else { menu.key(code, down: false) }
                held.remove(code)
            } }
            super.pressesEnded(presses, with: event)
        }
        override func pressesCancelled(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
            menu.observeInput(["boundary": "cancelled", "keys": presses.compactMap { $0.key.map { virtualKey($0) ?? 0 } }])
            deactivate(); super.pressesCancelled(presses, with: event)
        }
        private func send(_ message: ClawNativeWindowInputQueue.Message, at point: CGPoint) {
            menu.observeInput(["point": [point.x, point.y], "bounds": [bounds.width, bounds.height]])
            let size = menu.logicalSize
            let scale = min(bounds.width / size.width, bounds.height / size.height)
            guard scale > 0 else { return }
            let x = (point.x - (bounds.width - size.width * scale) / 2) / scale
            let y = (point.y - (bounds.height - size.height * scale) / 2) / scale
            menu.pointer(message, x: Int32(x), y: Int32(y))
        }
        @objc private func hover(_ gesture: UIHoverGestureRecognizer) {
            // UIKit can report the origin when hover ends (including focus
            // changes). That is not physical motion inside the game surface.
            guard gesture.state == .began || gesture.state == .changed else { return }
            send(.mouseMove, at: gesture.location(in: self))
        }
        override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
            becomeFirstResponder()
            #if !targetEnvironment(macCatalyst)
            // Touch is the iPad equivalent of a movie key-down, even in the
            // letterbox margins. Consume its whole lifetime across transitions.
            if menu.movieActive || !movieTouches.isEmpty {
                let first = movieTouches.isEmpty
                movieTouches.formUnion(touches)
                if first && !touches.isEmpty {
                    menu.liveInputArrived(0, down: true)
                    menu.key(0, down: true)
                }
                return
            }
            if updateTouches(touches) { return }
            #endif
            if let touch = touches.first { menu.liveInputArrived(1, down: true); send(.primaryDown, at: touch.location(in: self)) }
        }
        override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent?) {
            #if !targetEnvironment(macCatalyst)
            if !movieTouches.isDisjoint(with: touches) { return }
            if updateTouches(touches) { return }
            #endif
            if let touch = touches.first { send(.mouseMove, at: touch.location(in: self)) }
        }
        override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent?) {
            #if !targetEnvironment(macCatalyst)
            if !movieTouches.isDisjoint(with: touches) {
                movieTouches.subtract(touches)
                return
            }
            if updateTouches(touches, ended:true) { return }
            #endif
            if let touch = touches.first { menu.liveInputArrived(1, down: false); send(.primaryUp, at: touch.location(in: self)) }
        }
        override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent?) {
            touchesEnded(touches, with: event)
        }
    }
}

struct Playback {
    let animation: ClawAnimation
    let images: [Int: CGImage]

    init(name: String) throws {
        guard let root = Bundle.main.resourceURL?.appendingPathComponent("GameData") else {
            throw AssetError.invalid("Missing GameData")
        }
        let palette = try Data(contentsOf: root.appendingPathComponent("MAIN.PAL"))
        animation = try ClawAnimation(data: Data(contentsOf: root.appendingPathComponent("ANIS/\(name).ANI")))
        var loaded: [Int: CGImage] = [:]
        let urls = try FileManager.default.contentsOfDirectory(at: root.appendingPathComponent("IMAGES"), includingPropertiesForKeys: nil)
        for url in urls where url.pathExtension.uppercased() == "PID" {
            let filename = url.deletingPathExtension().lastPathComponent
            guard filename.hasPrefix("FRAME"), let imageID = Int(filename.dropFirst(5)) else { continue }
            let sprite = try ClawSprite(pid: Data(contentsOf: url), palette: palette)
            guard let provider = CGDataProvider(data: Data(sprite.rgba) as CFData),
                  let image = CGImage(width: sprite.width, height: sprite.height,
                      bitsPerComponent: 8, bitsPerPixel: 32, bytesPerRow: sprite.width * 4,
                      space: CGColorSpaceCreateDeviceRGB(),
                      bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.last.rawValue),
                      provider: provider, decode: nil, shouldInterpolate: false, intent: .defaultIntent) else {
                throw AssetError.invalid("Cannot create sprite image")
            }
            loaded[imageID] = image
        }
        images = loaded
    }
}

struct AssetPlaybackView: View {
    @State private var name = "IDLE"
    @State private var playback: Playback?
    @State private var runtime: ClawAnimationPlayback?
    @State private var failure: String?
    @State private var previousMilliseconds: UInt64 = 0
    private let ticks = Timer.publish(every: 1.0 / 60, on: .main, in: .common).autoconnect()
    let choices = ["IDLE", "WALK", "JUMP", "SWIPE", "DUCK", "CLIMB"]

    var body: some View {
        VStack(spacing: 24) {
            Text("Captain Claw").font(.largeTitle.bold())
            Text("Original animation commands • Reconstruction in progress")
                .foregroundStyle(.secondary)
            ZStack {
                    RoundedRectangle(cornerRadius: 20).fill(Color(red: 0.07, green: 0.09, blue: 0.14))
                    if let playback, let runtime, runtime.actor.imageToken != 0 {
                        if let image = playback.images[Int(runtime.actor.imageID)] {
                            Image(decorative: image, scale: 1).interpolation(.none)
                                .resizable().scaledToFit()
                                .frame(width: CGFloat(image.width * 3), height: CGFloat(image.height * 3))
                        }
                    }
                    if let failure { Text(failure).foregroundStyle(.red).padding() }
                }.frame(maxWidth: 650, maxHeight: 440)
            Picker("Animation", selection: $name) {
                ForEach(choices, id: \.self) { Text($0.capitalized).tag($0) }
            }.pickerStyle(.segmented).frame(maxWidth: 650)
            Button("Replay") { runtime?.restart(); previousMilliseconds = milliseconds() }
            Text("\(runtime?.state.stopped == 1 ? "Stopped" : "Playing") · Frame \(runtime?.actor.imageID ?? 0)")
                .monospacedDigit().foregroundStyle(.secondary)
            Text("Original stop and loop commands are honored.\nMovement, collision, audio and gameplay are still being reconstructed.")
                .font(.footnote).foregroundStyle(.secondary).multilineTextAlignment(.center)
        }
        .padding(32).preferredColorScheme(.dark)
        .onAppear { load() }
        .onChange(of: name) { _, _ in load() }
        .onReceive(ticks) { _ in
            let now = milliseconds()
            let delta = min(now - previousMilliseconds, UInt64(UInt32.max))
            previousMilliseconds = now
            runtime?.update(delta: UInt32(delta))
        }
    }
    private func milliseconds() -> UInt64 { UInt64(ProcessInfo.processInfo.systemUptime * 1000) }
    private func load() {
        do {
            let loaded = try Playback(name: name)
            runtime = try ClawAnimationPlayback(animation: loaded.animation, availableImages: Array(loaded.images.keys))
            playback = loaded; failure = nil; previousMilliseconds = milliseconds()
        } catch { playback = nil; runtime = nil; failure = String(describing: error) }
    }
}

struct LevelOnePreviewView: View {
    @State private var scene: ClawLevelScene?
    @State private var failure: String?
    @State private var camera = CGPoint.zero
    @State private var savedCamera = CGPoint.zero
    @State private var viewport = CGSize.zero
    var body: some View {
        VStack(spacing: 12) {
            Text("La Roca · Level 1").font(.title.bold())
            Text("Background, Action and Front · Drag to explore").foregroundStyle(.secondary)
            GeometryReader { geometry in
                Canvas { context, size in
                    guard let scene else { return }
                    for draw in ClawLevelRenderer(scene: scene).commands(camera: camera, viewport: size) {
                        context.draw(Image(decorative: draw.image, scale: 1).interpolation(.none), in: draw.rect)
                    }
                }.background(Color.black).clipped()
                .gesture(DragGesture().onChanged { value in
                    guard let scene else { return }
                    camera = ClawLevelRenderer(scene: scene).clampedCamera(
                        CGPoint(x: savedCamera.x - value.translation.width, y: savedCamera.y - value.translation.height),
                        viewport: geometry.size)
                }.onEnded { _ in savedCamera = camera })
                .onAppear { viewport = geometry.size; centerOnSpawn() }
                .onChange(of: geometry.size) { _, size in
                    viewport = size
                    if let scene { camera = ClawLevelRenderer(scene: scene).clampedCamera(camera, viewport: size); savedCamera = camera }
                }
            }
            HStack {
                Button("Return to start") { centerOnSpawn() }
                Text("Camera \(Int(camera.x)), \(Int(camera.y))").monospacedDigit().foregroundStyle(.secondary)
            }
            if let failure { Text(failure).foregroundStyle(.red) }
            Text("CD-rip asset preview · Plane parallax and wrapping follow format metadata.\n1,479 objects are not rendered. Gameplay and original rendering parity remain unverified.")
                .font(.footnote).foregroundStyle(.secondary).multilineTextAlignment(.center)
        }.padding(20).preferredColorScheme(.dark)
        .onAppear {
            guard scene == nil else { return }
            do { scene = try ClawLevelScene.bundled(); failure = nil; centerOnSpawn() }
            catch { failure = String(describing: error) }
        }
    }
    private func centerOnSpawn() {
        guard let scene else { return }
        let size = viewport == .zero ? CGSize(width: 800, height: 600) : viewport
        camera = ClawLevelRenderer(scene: scene).cameraCentered(
            at: CGPoint(x: scene.world.startX, y: scene.world.startY), viewport: size)
        savedCamera = camera
    }
}

// Mac Catalyst delivers window events to UIKit through NSApplication's event
// queue: a bare RunLoop pump leaves them queued, so the window hangs (beach
// ball) and no key reaches the responder chain. The original's blocking movie
// loop (0x4f0380) pumps its window messages; this does the same with AppKit's
// queue when there is one, and runs the run loop otherwise (iPadOS).
@MainActor enum ClawWindowEventPump {
    private static var pumping = false
    private static var lastYield = 0.0
    static func yieldIfNeeded() {
        let now = ProcessInfo.processInfo.systemUptime
        guard !pumping, now - lastYield >= 0.008 else { return }
        // Synchronous rendering only needs to drain ready events. Waiting for
        // a future event on every yield adds wall time to virtual-clock checks.
        pump(for: 0)
        lastYield = ProcessInfo.processInfo.systemUptime
    }
    #if targetEnvironment(macCatalyst)
    private typealias Next = @convention(c) (NSObject, Selector, UInt64, NSDate, NSString, ObjCBool) -> Unmanaged<NSObject>?
    private typealias Send = @convention(c) (NSObject, Selector, NSObject) -> Void
    private static let nextSelector = NSSelectorFromString("nextEventMatchingMask:untilDate:inMode:dequeue:")
    private static let sendSelector = NSSelectorFromString("sendEvent:")
    private static let appKit: (app: NSObject, next: Next, send: Send)? = {
        guard let type = NSClassFromString("NSApplication") as? NSObject.Type,
              let app = type.perform(NSSelectorFromString("sharedApplication"))?.takeUnretainedValue() as? NSObject,
              app.responds(to: nextSelector), app.responds(to: sendSelector) else { return nil }
        return (app, unsafeBitCast(app.method(for: nextSelector), to: Next.self),
                unsafeBitCast(app.method(for: sendSelector), to: Send.self))
    }()
    #endif
    /// Dispatches window events (and runs the default run-loop mode) for up to `seconds`.
    static func pump(for seconds: TimeInterval) {
        guard !pumping else { return }
        pumping = true
        defer { pumping = false }
        let deadline = Date(timeIntervalSinceNow: seconds)
        #if targetEnvironment(macCatalyst)
        if let appKit {
            let mode = RunLoop.Mode.default.rawValue as NSString
            var more = true
            while more {
                more = autoreleasepool {
                    guard let event = appKit.next(appKit.app, nextSelector, .max, deadline as NSDate, mode, true)?
                        .takeUnretainedValue() else { return false }
                    appKit.send(appKit.app, sendSelector, event)
                    return Date() < deadline
                }
            }
            if seconds == 0 {
                // A nonblocking AppKit poll need not service run-loop timers;
                // dispatch ready timers/sources as well, without sleeping.
                CFRunLoopRunInMode(.defaultMode, 0, true)
            }
            return
        }
        #endif
        _ = RunLoop.main.run(mode: .default, before: deadline)
    }
}

// A real run-loop timer, independent of the game clock and yield callback.
// Start/end samples include stalls before the first and after the last beat.
@MainActor final class ClawMainThreadHeartbeat {
    var enabled = false
    private struct Scope {
        let name: String
        let began: Double
        var last: Double
        var maximum = 0.0
        var beats = 0
    }
    private var scopes: [Int: Scope] = [:]
    private var serial = 0
    private var timer: Timer?
    private(set) var records: [[String: Any]] = []
    func begin(_ name: String) -> Int {
        guard enabled else { return -1 }
        serial += 1
        let now = ProcessInfo.processInfo.systemUptime
        scopes[serial] = Scope(name:name,began:now,last:now)
        if timer == nil {
            let timer = Timer(timeInterval:0.01,repeats:true) { [weak self] _ in
                MainActor.assumeIsolated { self?.beat() }
            }
            self.timer = timer
            RunLoop.main.add(timer,forMode:.common)
        }
        return serial
    }
    private func beat() {
        let now = ProcessInfo.processInfo.systemUptime
        for id in Array(scopes.keys) {
            scopes[id]!.maximum = max(scopes[id]!.maximum,now-scopes[id]!.last)
            scopes[id]!.last = now
            scopes[id]!.beats += 1
        }
    }
    func end(_ id: Int) {
        guard let scope = scopes.removeValue(forKey:id) else { return }
        let now = ProcessInfo.processInfo.systemUptime
        records.append(["scope":scope.name,"seconds":now-scope.began,
                        "beats":scope.beats,"max_gap_ms":max(scope.maximum,now-scope.last)*1000])
        if scopes.isEmpty { timer?.invalidate();timer = nil }
    }
}

#if !targetEnvironment(macCatalyst)
// Bottom corners leave the score/health HUD clear. The full input surface keeps
// the three-finger recognizer above these zones; no child view consumes a finger.
private enum ClawTouchLayout {
    static func buttons(size: CGSize) -> [(Int, String, CGRect)] {
        let unit = min(76.0, size.height / 7)
        let left = 24.0, bottom = size.height - 28
        let right = size.width - 24
        return [
            (0,"←",CGRect(x:left,y:bottom-unit*2,width:unit,height:unit)),
            (1,"→",CGRect(x:left+unit*2,y:bottom-unit*2,width:unit,height:unit)),
            (2,"↑",CGRect(x:left+unit,y:bottom-unit*3,width:unit,height:unit)),
            (3,"↓",CGRect(x:left+unit,y:bottom-unit,width:unit,height:unit)),
            (4,"Jump",CGRect(x:right-unit,y:bottom-unit,width:unit,height:unit)),
            (5,"Attack",CGRect(x:right-unit*2.15,y:bottom-unit*1.6,width:unit,height:unit)),
            (6,"Fire",CGRect(x:right-unit,y:bottom-unit*2.2,width:unit,height:unit)),
            (7,"Weapon",CGRect(x:right-unit*2.15,y:bottom-unit*2.65,width:unit,height:unit*0.65)),
            (8,"Pause",CGRect(x:size.width/2-unit/2,y:bottom-unit*0.65,width:unit,height:unit*0.65))]
    }
    static func action(at point: CGPoint, size: CGSize) -> Int? {
        buttons(size:size).first { $0.2.contains(point) }?.0
    }
}
#endif
