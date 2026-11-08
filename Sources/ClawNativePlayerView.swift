import SwiftUI
import Combine

struct ClawNativePlayerView: View {
    @State private var scene: ClawLevelScene?
    @State private var player: ClawNativePlayer?
    @State private var nativeScene: ClawNativeScene?
    @State private var failure: String?
    @State private var frame = 0
    @State private var heldInput: UInt32 = 0
    @State private var windowInput = ClawNativeWindowInput()
    @State private var pointerDown = false
    @State private var running = false
    @State private var audioMuted = true
    @FocusState private var keyboardFocus: Bool
    @State private var clock = ClawFrameClockAdapter()
    private let ticks = Timer.publish(every: 1.0 / 60, on: .main, in: .common).autoconnect()

    // MARK: - Presentation and window input

    var body: some View {
        VStack(spacing: 12) {
            Text("Captain Claw · Movement lab").font(.title2.bold())
            Text("Arrows to move, climb or duck · Space to jump · Z to attack · X to lift or throw").foregroundStyle(.secondary)
            Text("F to fire · 1 pistol · 2 magic · Hold and release 3 for dynamite · C to cycle weapons").font(.caption).foregroundStyle(.secondary)
            GeometryReader { geometry in
                Canvas { context, size in
                    let _ = frame
                    if let rendering = nativeScene?.rendering {
                        let viewport = ClawNativeCamera.viewport
                        let scale = min(size.width / viewport.width, size.height / viewport.height)
                        var projectedContext = context
                        projectedContext.translateBy(x: (size.width - viewport.width * scale) / 2, y: (size.height - viewport.height * scale) / 2)
                        projectedContext.scaleBy(x: scale, y: scale)
                        projectedContext.clip(to: Path(CGRect(origin: .zero, size: viewport)))
                        for command in rendering.commands {
                            var drawContext = projectedContext
                            if command.mirrored {
                                drawContext.translateBy(x: command.rect.minX + command.rect.maxX, y: 0)
                                drawContext.scaleBy(x: -1, y: 1)
                            }
                            drawContext.draw(Image(decorative: command.image, scale: 1).interpolation(.none), in: command.rect)
                        }
                        // Source4226b0 supplies text/RECT/flags/font selection;
                        // native font raster and line layout replace GDI.
                        for command in nativeScene?.statusMessages?.textDraws ?? [] {
                            let color = Color(red: Double(command.color & 255) / 255, green: Double(command.color >> 8 & 255) / 255, blue: Double(command.color >> 16 & 255) / 255)
                            var textContext = projectedContext
                            textContext.clip(to: Path(command.rect))
                            let text = textContext.resolve(Text(command.text).font(.custom("Arial", size: CGFloat(command.fontHeight))).foregroundColor(color))
                            let measured = text.measure(in: command.rect.size)
                            let centered = command.flags & 1 != 0, right = command.flags & 2 != 0
                            let x = centered ? command.rect.midX - measured.width / 2 : right ? command.rect.maxX - measured.width : command.rect.minX
                            textContext.draw(text, at: CGPoint(x: x, y: command.rect.minY), anchor: .topLeading)
                        }
                    }
                }.background(.black).clipped()
                    .gesture(DragGesture(minimumDistance: 0).onChanged { _ in
                        if !pointerDown {
                            windowInput.primary(down: true)
                            pointerDown = true
                        }
                        keyboardFocus = true
                    }.onEnded { _ in
                        if pointerDown {
                            windowInput.primary(down: false)
                            pointerDown = false
                        }
                    })
            }
            HStack(spacing: 24) {
                holdControl("←", held: heldInput & 0x01000000 != 0) { setInput(0x01000000, held: $0) }
                holdControl("→", held: heldInput & 0x02000000 != 0) { setInput(0x02000000, held: $0) }
                holdControl("↑", held: heldInput & 0x04000000 != 0) { setInput(0x04000000, held: $0) }
                holdControl("↓", held: heldInput & 0x08000000 != 0) { setInput(0x08000000, held: $0) }
                holdControl("Jump", held: heldInput & 1 != 0) { setInput(1, held: $0) }
                holdControl("Attack", held: heldInput & 2 != 0) { setInput(2, held: $0) }
                holdControl("Lift / throw", held: heldInput & 0x20 != 0) { setInput(0x20, held: $0) }
                Button(running ? "Pause" : "Resume") {
                    running.toggle()
                    clock.reset()
                    nativeScene?.resetClock()
                }
                Button("Return to start") { load() }
                Button(audioMuted ? "Unmute" : "Mute") {
                    audioMuted.toggle()
                    player?.audio?.setOutputMuted(audioMuted)
                    keyboardFocus = true
                }
                .accessibilityIdentifier("claw-lab-mute")
                .help(audioMuted ? "Sound is muted. Unmute for audio checks." : "Mute sound while working.")
            }
            HStack(spacing: 16) {
                holdControl("Fire", held: heldInput & 4 != 0) { setInput(4, held: $0) }
                holdControl("Pistol", held: heldInput & 0x40 != 0) { setInput(0x40, held: $0) }
                holdControl("Magic", held: heldInput & 0x80 != 0) { setInput(0x80, held: $0) }
                holdControl("Dynamite", held: heldInput & 0x100 != 0) { setInput(0x100, held: $0) }
                holdControl("Cycle", held: heldInput & 8 != 0) { setInput(8, held: $0) }
            }
            if let player {
                Text("x \(player.x) · y \(player.y) · State \(player.runtime.logicState) · \(player.sequence) · Frame \(player.imageID)")
                    .font(.caption.monospaced()).foregroundStyle(.secondary)
                if !player.pendingCommands.isEmpty {
                    Text("A game command is pending; a required scene service is not implemented yet.")
                        .font(.caption).foregroundStyle(.orange)
                } else if ![UInt32(24), 8, 9, 4, 25, 26, 27, 28, 31, 5000, 5001, 5002, 5003, 5004, 5005, 5006].contains(player.runtime.logicState) {
                    Text("This state still needs its update routine recovered. Return to start to continue.")
                        .font(.caption).foregroundStyle(.orange)
                }
            }
            if let message = failure ?? player?.failure {
                Text(message).foregroundStyle(.red)
            }
            if let nativeScene, nativeScene.fault != 0 || !nativeScene.unresolvedDependencies.isEmpty {
                Text("Scene service still needs recovery. Return to start to continue.").foregroundStyle(.orange)
            }
            if let enemy = nativeScene?.enemies.values.first(where: { $0.failure != nil || !$0.unresolved.isEmpty }) {
                Text(enemy.failure ?? "Enemy service \(enemy.unresolved.map { String($0, radix: 16) }.sorted().joined(separator: ", ")) requires recovery")
                    .font(.caption).foregroundStyle(.orange)
            }
            Text("Movement, enemies, pickups and dialog audio · Other actors and music still pending")
                .font(.caption).foregroundStyle(.secondary)
        }
        .padding(20).preferredColorScheme(.dark)
        .focusable().focused($keyboardFocus)
        .onKeyPress(phases: [.down, .up]) { press in
            let held = press.phase == .down
            switch press.key {
            case .leftArrow: setInput(0x01000000, held: held, keyboard: true)
            case .rightArrow: setInput(0x02000000, held: held, keyboard: true)
            case .upArrow: setInput(0x04000000, held: held, keyboard: true)
            case .downArrow: setInput(0x08000000, held: held, keyboard: true)
            case .space: setInput(1, held: held, keyboard: true)
            case KeyEquivalent("z"): setInput(2, held: held, keyboard: true)
            case KeyEquivalent("x"): setInput(0x20, held: held, keyboard: true)
            case KeyEquivalent("f"): setInput(4, held: held, keyboard: true)
            case KeyEquivalent("1"): setInput(0x40, held: held, keyboard: true)
            case KeyEquivalent("2"): setInput(0x80, held: held, keyboard: true)
            case KeyEquivalent("3"): setInput(0x100, held: held, keyboard: true)
            case KeyEquivalent("c"): setInput(8, held: held, keyboard: true)
            default: return .ignored
            }
            return .handled
        }
        .onAppear {
            if scene == nil {
                load()
            }
            clock.reset()
            nativeScene?.resetClock()
            running = true
            keyboardFocus = true
        }
        .onDisappear {
            running = false
            windowInput.key(mask: .max, down: false)
            windowInput.primary(mask: .max, down: false)
            heldInput = 0
            pointerDown = false
        }
        .onReceive(ticks) { _ in
            guard running, let nativeScene else {
                return
            }
            let input = windowInput.frameInput()
            // The display timer wakes the view; the adapter supplies the
            // recovered scene clock and accepts command-driven clock resets.
            let stage = clock.sampleScene()
            nativeScene.advance(now: stage.now, delta: stage.delta, accumulated: stage.accumulated,
                                held: input.held, pressed: input.pressed, clock: clock.snapshot)
            if nativeScene.processPlayerCommands() {
                clock.acceptSnapshot(nativeScene.currentClockSnapshot)
            }
            frame &+= 1
        }
    }

    // MARK: - Physical input controls

    private func setInput(_ mask: UInt32, held: Bool, keyboard: Bool = false) {
        // Drag updates are not additional physical button-down events. Keep
        // this separate from keyboard-held state for the same action.
        if !keyboard && held && windowInput.primaryIsHeld(mask) {
            return
        }
        if keyboard {
            windowInput.key(mask: mask, down: held)
        }
        else {
            windowInput.primary(mask: mask, down: held)
        }
        heldInput = windowInput.held
    }

    private func holdControl(_ title: String, held: Bool, change: @escaping (Bool) -> Void) -> some View {
        Text(title).font(.headline).padding(.horizontal, 22).padding(.vertical, 12)
            .background(held ? Color.blue : Color.gray.opacity(0.3), in: RoundedRectangle(cornerRadius: 8))
            .gesture(DragGesture(minimumDistance: 0).onChanged { _ in change(true) }.onEnded { _ in change(false) })
            .accessibilityAddTraits(.isButton)
    }

    // MARK: - Scene lifecycle

    private func load() {
        do {
            let loaded = try ClawLevelScene.bundled()
            let assets = try ClawPlayerAssets(root: loaded.root)
            let loadedPlayer = try ClawNativePlayer(world: loaded.world, assets: assets, enableAudioOutput: true)
            loadedPlayer.audio?.setOutputMuted(audioMuted)
            let input = ClawNativeWindowInput()
            let runtime = ClawNativeScene(player: loadedPlayer, windowInput: input)
            let directory = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!.appendingPathComponent("CaptainClaw/SaveGames", isDirectory: true)
            try runtime.loadRecoveredObjects(world: loaded.world, root: loaded.root, saveDirectory: directory)
            player = loadedPlayer
            nativeScene = runtime
            scene = loaded
            windowInput = input
            failure = nil
            heldInput = 0
            pointerDown = false
            clock.reset()
            frame &+= 1
        } catch {
            failure = String(describing: error)
            player = nil
            nativeScene = nil
        }
    }
}
