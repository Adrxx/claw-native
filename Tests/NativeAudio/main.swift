import Foundation
let root = URL(fileURLWithPath: CommandLine.arguments[1])
let output = CommandLine.arguments.contains("--output")
let audio = try ClawNativeAudio(root: root, outputEnabled: output)
let manager = audio.ambientMetadata(token:audio.managerIdentity,words:32)!
precondition(manager[0] == 0x513514 && manager[30] == 1 && manager[5] != 0)
precondition(audio.lifecycleFault == 0 && audio.lifecycleCounts[0x4b4710] == 1 && audio.lifecycleCounts[0x4b47e0] == 1)
if output {
    precondition(audio.play(name: "CLAW_LAND") == 1)
    RunLoop.current.run(until: Date().addingTimeInterval(0.25))
    let stats = audio.renderStatistics
    audio.stopOutput()
    precondition(stats.0 > 0 && stats.1 > 0 && audio.reports.isEmpty)
    print("PASS CoreAudio source callback: \(stats.0) frames rendered, \(stats.1) frames with nonzero original PCM; physical listening remains separate")
    exit(0)
}
let foot = audio.resolve(name: "CLAW_LEFTFOOT1")!
precondition(audio.duration(resource: foot.resourceToken) == 39)
let land = audio.resolve(name: "CLAW_LAND")!
precondition(audio.duration(resource: land.resourceToken) == 1004)
for name in ["LEVEL_OFFICER_00340014", "LEVEL_SOLDIER_00320006"] {
    let sound = audio.resolve(name: name)!
    precondition(audio.duration(resource: sound.resourceToken) > 0)
    precondition(audio.speechMetadata(token: sound.resourceToken + 0x10, words: 1)!.pointee == sound.voicePoolToken)
    precondition(audio.speechMetadata(token: sound.voicePoolToken + 0x28, words: 1)!.pointee == audio.duration(resource: sound.resourceToken))
}
precondition(audio.speechMetadata(token: audio.managerIdentity, words: 1) == nil)
precondition(audio.play(name: "CLAW_LEFTFOOT1") == 1 && audio.activeVoiceCount == 1)
var left = [Float](repeating: 0, count: 48000), right = left
func render(_ frames: Int) {
    left.withUnsafeMutableBufferPointer { l in
        right.withUnsafeMutableBufferPointer { r in audio.render(left: l.baseAddress!, right: r.baseAddress!, frames: frames, sampleRate: 48000) }
    }
}
render(2000)
precondition(audio.activeVoiceCount == 0 && audio.renderStatistics.1 > 0)
precondition(left.prefix(2000).elementsEqual(right.prefix(2000)))
precondition(audio.play(name: "CLAW_LEFTFOOT1") == 1)
precondition(audio.play(name: "CLAW_LEFTFOOT1") == 1 && audio.activeVoiceCount == 2)
render(2000); precondition(audio.activeVoiceCount == 0)
let silentLoop = ClawAudioRequest(volume: 0, pan: 0, pitchPercent: 0, looping: 1)
precondition(audio.play(name: "CLAW_LEFTFOOT1", request: silentLoop) == 1)
render(2000)
precondition(left.prefix(2000).allSatisfy { $0 == 0 } && right.prefix(2000).allSatisfy { $0 == 0 } && audio.activeVoiceCount == 1)
audio.stopAll(); precondition(audio.activeVoiceCount == 0)
precondition(audio.play(name: "CLAW_LAND", request: ClawAudioRequest(volume:100,pan:100,pitchPercent:200,looping:0)) == 1)
render(48000); precondition(audio.activeVoiceCount == 0)
let leftPeak = left.map { abs($0) }.max()!, rightPeak = right.map { abs($0) }.max()!
precondition(rightPeak > 0 && leftPeak < rightPeak * 0.001)
precondition(audio.reports.isEmpty)
let expectedPools = audio.lifecycleCounts[0x4b4ae0,default:0]
precondition(expectedPools == 0 && manager[1] != 0 && manager[2] != 0)
_ = audio.sourceManagerEntry(0x4b4860)
precondition(audio.lifecycleFault == 0 && manager[1] == 0 && manager[2] == 0 && manager[30] == 0 && audio.activeVoiceCount == 0)
precondition(audio.lifecycleCounts[0x4b4ae0,default:0] == 170 && audio.lifecycleCounts[0x71020008] == 1)
precondition(audio.ambientMetadata(token:foot.voicePoolToken,words:1) == nil)
_ = audio.sourceManagerEntry(0x4b4860)
precondition(audio.lifecycleFault == 0 && audio.lifecycleCounts[0x71020008] == 1)
print("PASS source audio manager constructor/startup, original Stop/duplicate ordering and shutdown of all170 loaded WAV pools; repeated shutdown preserves source gate")
print("PASS native audio host: original PCM loading/duration, nonzero render, independent overlapping voices, completion/reuse, silent looping, full pitch and pan controls")
print("This is native output-adapter verification; original Windows mixing/resampling and device timing identity remain unproved")
