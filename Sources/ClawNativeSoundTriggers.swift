import Foundation

// Source trigger/dialog and ambient callbacks share actual speech controller
// aliases and WAV metadata. Ambient list, voice and fade calls compose the
// recovered backend through the native physical audio transport.
final class ClawNativeSoundTriggers {
    // Reviewed Level 1 class roots delegated to claw_sound_trigger_entry below.
    // claw-progress-class-owner: sound_trigger_logic 0x48c1e0 0x48c410 0x48c430 0x48ca40 0x48ca60
    static let nonAmbientCallbacks:Set<UInt32> = [0x48c1e0,0x48c410,0x48c430,0x48c450,0x48c470,0x48c490,0x48c4b0,0x48c8f0,0x48ca40,0x48ca60,0x48ca80,0x48caa0,0x48cac0,0x48cae0]
    // claw-progress-class-owner: sound_trigger_logic 0x402ca0 0x402cc0 0x402e20
    static let ambientCallbacks:Set<UInt32> = [0x402ca0,0x402cc0,0x402e00,0x402e20]
    static let callbacks = nonAmbientCallbacks.union(ambientCallbacks)
    weak var scene:ClawNativeScene?
    private(set) var tokens:Set<UInt32> = []
    private(set) var originalRecords:[UInt32:ClawInteractionActor] = [:]
    private(set) var initialized:Set<UInt32> = []
    private(set) var callbackCounts:[UInt32:UInt64] = [:]
    private(set) var directVoiceRequests:[UInt32] = []
    private(set) var fault:UInt32 = 0
    private(set) var unresolved:Set<UInt32> = []
    private var triggerProfile:UInt32 = 0, ambientProfile:UInt32 = 0
    init(scene:ClawNativeScene) { self.scene = scene }
    func attach(_ snapshot:ClawInteractionActor) { tokens.insert(snapshot.token); originalRecords[snapshot.token] = snapshot }
    func remove(_ token:UInt32) { tokens.remove(token) }
    func callback(_ function:UInt32,actor:UInt32) {
        guard let scene else { fault = 1;return }
        let wasNew = scene.snapshotActor(actor)?.primary.7 == 0
        _ = service(function,receiver:0,arguments:[actor])
        callbackCounts[actor,default:0] &+= 1
        if wasNew && fault == 0 { initialized.insert(actor) }
    }
    private func context(host:ClawSceneActorHost? = nil) -> ClawSoundTriggerContext? {
        guard let scene,let speech = scene.speech else { fault = 1;return nil }
        speech.globals.pointee.stageDelta = scene.stageDelta
        return ClawSoundTriggerContext(scene:host ?? scene.ambientAudio?.actorHost ?? speech.actorHost,
            globals:speech.globals,masterVolume:scene.player.audio?.routing.masterVolume ?? 0,
            triggerProfile:triggerProfile,ambientProfile:ambientProfile,composeSpeech:1,fault:0)
    }
    func constructAmbientManager(_ token:UInt32,host:ClawSceneActorHost) -> Bool {
        guard var context = context(host:host) else { return false }
        let accepted = claw_sound_trigger_construct_manager(token,&context)
        fault = max(fault,context.fault);return accepted == 1 && fault == 0
    }
    @discardableResult func service(_ function:UInt32,receiver:UInt32,arguments:[UInt32],host:ClawSceneActorHost? = nil) -> UInt32 {
        guard arguments.count <= 9,var context = context(host:host) else { fault = 1;return 0 }
        var raw = ClawSoundTriggerArguments();raw.count = UInt32(arguments.count)
        withUnsafeMutableBytes(of:&raw.words){target in arguments.withUnsafeBytes{source in UnsafeMutableRawBufferPointer(rebasing:target.prefix(source.count)).copyMemory(from:source)}}
        var result:UInt32 = 0
        let accepted = claw_sound_trigger_entry(function,receiver,raw,&context,nativeSoundTriggerDependency,
            Unmanaged.passUnretained(self).toOpaque(),&result)
        triggerProfile = context.triggerProfile;ambientProfile = context.ambientProfile
        fault = max(fault,context.fault);if accepted != 1 { unresolved.insert(function) }
        if let ambient = scene?.ambientAudio { fault = max(fault,ambient.fault) };return result
    }
    fileprivate func dependency(_ event:ClawSoundTriggerCall) -> UInt32 {
        guard let scene else { fault = 1; return 0 }
        if let result = scene.ambientAudio?.service(event) { return result }
        switch event.function {
        case 0x4b45f0:
            guard event.argumentCount == 4 else { fault = 2; return 0 }
            directVoiceRequests.append(event.receiver)
            return scene.player.audio?.playVoicePool(event.receiver,request:ClawAudioRequest(volume:event.arguments.0,
                pan:event.arguments.1,pitchPercent:event.arguments.2,looping:event.arguments.3)) ?? 0
        default: unresolved.insert(event.function); fault = 1; return 0
        }
    }
}
private let nativeSoundTriggerDependency:ClawSoundTriggerDependency = { _,event,user in
    guard let event,let user else { return 0 }
    return Unmanaged<ClawNativeSoundTriggers>.fromOpaque(user).takeUnretainedValue().dependency(event.pointee)
}

extension ClawNativeSoundTriggers {
    struct SavedState: Codable, Equatable {
        let tokens: Set<UInt32>, initialized: Set<UInt32>, fault: UInt32, unresolved: Set<UInt32>
        let originalRecords: [UInt32: ClawSnapshotValue<ClawInteractionActor>]
        let callbackCounts: [UInt32: UInt64], directVoiceRequests: [UInt32]
        let triggerProfile: UInt32, ambientProfile: UInt32
    }
    func savedState() -> SavedState {
        .init(tokens: tokens, initialized: initialized, fault: fault, unresolved: unresolved,
            originalRecords: originalRecords.mapValues(ClawSnapshotValue.init), callbackCounts: callbackCounts,
            directVoiceRequests: directVoiceRequests, triggerProfile: triggerProfile, ambientProfile: ambientProfile)
    }
    func restoreState(_ saved: SavedState) {
        tokens = saved.tokens; initialized = saved.initialized; fault = saved.fault; unresolved = saved.unresolved
        originalRecords = saved.originalRecords.mapValues(\.value); callbackCounts = saved.callbackCounts
        directVoiceRequests = saved.directVoiceRequests; triggerProfile = saved.triggerProfile; ambientProfile = saved.ambientProfile
    }
}
