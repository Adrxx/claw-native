import Foundation

// Exercise the actual adapter callback entry points using native effect spies.
// Family equivalence and original-formatted messages are checked by the separate join.
func verifyNativeDiagnosticRoutes() throws {
    let url = URL(fileURLWithPath:"App/GameData/DiagnosticPolicy.json")
    let diagnostics = ClawNativeDiagnostics(assetURL:url,effects:.init(beep:{_ in true},log:{_ in true},dialog:{_,_,_,_ in true}))
    diagnostics.setFlags(display:false,[1,1,1,0])
    diagnostics.setFlags(display:true,[1,1,1,0])
    var effects:[ClawNativeDiagnostics.Effect] = []
    diagnostics.observe = {effects.append($0)}
    let audio = try ClawNativeAudio(root:URL(fileURLWithPath:"App/GameData"),outputEnabled:false,preload:false,diagnostics:diagnostics)
    let resource = audio.resourceHost
    resource.report!(resource.context,0x46,1)
    precondition(audio.reports.last?.0 == 0x46 && audio.reports.last?.1 == 1)
    precondition(diagnostics.entries[0x4b4ed0] == 1 && audio.lifecycleFault == 0)
    precondition(effects.map(\.kind) == ["beep","format","format","log","format","dialog"])
    precondition(effects.last!.text.contains("line 70"))
    let backend = audio.backend
    backend.report!(backend.context,0x12a,0x88780096)
    var call = ClawAudioManagerLifecycleCall()
    call.function = 0x4b4ed0;call.argumentCount = 3
    call.arguments.0 = 0;call.arguments.1 = UInt32.max;call.arguments.2 = 0x80070057
    _ = audio.lifecycleDependency(call)
    precondition(diagnostics.entries[0x4b4ed0] == 3 && audio.lifecycleFault == 0)
    precondition(!effects.last!.text.contains("line"))

    let heap = ClawTokenHeap()
    let owner = heap.allocate(bytes:256),parent = heap.allocate(bytes:256)
    let image = UnsafeMutablePointer<ClawGameImageGlobals>.allocate(capacity:1)
    image.initialize(to:ClawGameImageGlobals())
    defer {image.deinitialize(count:1);image.deallocate()}
    let palette = try ClawNativePaletteResources(heap:heap,owner:owner,parent:parent,image:image,diagnostics:diagnostics)
    var surface = ClawSurfaceBlitCall()
    surface.function = 0x4bd260;surface.argumentCount = 3
    surface.arguments.0 = 0x532500;surface.arguments.1 = 75;surface.arguments.2 = 0x80004005
    effects.removeAll()
    _ = palette.display!.surfaceService(surface)
    precondition(palette.display!.lastSurfaceFault == 0 && palette.fault == 0)
    precondition(effects.map(\.kind) == ["beep","format","format","display-sink","format","dialog"])
    var graphics = ClawGraphicsManagerLifecycleCall()
    graphics.function = surface.function;graphics.argumentCount = 3;graphics.arguments = surface.arguments
    _ = palette.graphicsService(graphics)
    var resourceCall = ClawPaletteResourceCall()
    resourceCall.function = surface.function;resourceCall.argumentCount = 3;resourceCall.arguments = surface.arguments
    _ = palette.service(resourceCall)
    precondition(diagnostics.entries[0x4bd260] == 3 && diagnostics.fault == 0 && palette.fault == 0)
    precondition(palette.fadeDiagnostics.count == 3)

    // A missing physical effect reaches each adapter's fault channel.
    let broken = ClawNativeDiagnostics(assetURL:url,effects:.init())
    broken.setFlags(display:false,[0,0,1,0])
    let badAudio = try ClawNativeAudio(root:URL(fileURLWithPath:"App/GameData"),outputEnabled:false,preload:false,diagnostics:broken)
    let badHost = badAudio.resourceHost
    badHost.report!(badHost.context,0x46,1)
    precondition(broken.fault != 0 && badAudio.lifecycleFault == broken.fault)
    diagnostics.effects.dialog = nil
    _ = palette.display!.surfaceService(surface)
    precondition(diagnostics.fault != 0 && palette.fault != 0 && palette.display!.lastSurfaceFault != 0)
    palette.shutdown()
    print("PASS native diagnostic routes: audio resource/backend/lifecycle and display surface/graphics/palette callbacks reach shared policy; missing effects propagate faults; no visible UI or device acceptance")
}
