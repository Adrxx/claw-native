import Foundation
import CryptoKit
import AVFoundation
import AudioToolbox

// Native paused XMIDI sequences. Initialization retains and validates the real
// event stream. Playback requires an attached audio sequencer; it cannot report
// successful playback from a loaded file alone.
final class ClawNativeMenuMusic {
    private let resources:ClawNativeMenuResources
    private var started = false
    private var drivers:Set<UInt32> = []
    // Native playback of the same sequences: the game-visible state above
    // stays on the game clock; the sequencer below makes it audible.
    private let sequencer = ClawMusicSequencer()
    private var songs:[UInt32:ClawXMIDISong] = [:]
    private var synth:ClawMusicSynth?
    private var masterVolume:UInt32 = 127
    /// Output owner; music joins its engine and obeys its mute.
    weak var output:ClawNativeAudio?
    private var starts = 0
    private static let renderDirectory:URL? = {
        let arguments = ProcessInfo.processInfo.arguments
        guard let index = arguments.firstIndex(of:"--music-render"),index+1 < arguments.count else {return nil}
        return URL(fileURLWithPath:arguments[index+1],isDirectory:true)
    }()
    private static let renderQueue = DispatchQueue(label:"claw.music.render",qos:.utility)
    /// Blocks until every queued --music-render write has finished.
    static func waitForRenders() {renderQueue.sync {}}
    private struct Sequence {
        var data = Data();var events = 0;var ticks = 0;var loops:UInt32 = 1;var status:UInt32 = 2
        var elapsedUnits:UInt64 = 0;var clock:UInt32 = 0
        var tempo = 100.0,tempoStart = 100.0,tempoTarget = 100.0
        var tempoDuration:UInt32 = 0,tempoElapsed:UInt32 = 0
        var fractionalUnits = 0.0
    }
    /// Latest physical millisecond the game has observed; reading it never
    /// advances the clock. Playing sequences advance by it, as the Level 1
    /// join's sequence clock does (120 units per millisecond, 1000 per tick).
    var now:()->UInt32 = {0}
    private func advance() {
        let milliseconds = now()
        for (handle,sequence) in sequences where sequence.status == 4 {
            var s = sequence
            let delta = milliseconds &- s.clock
            let ramp = min(delta,s.tempoDuration &- s.tempoElapsed)
            let end = s.tempoDuration == 0 ? s.tempoTarget:s.tempoStart+(s.tempoTarget-s.tempoStart)*Double(s.tempoElapsed+ramp)/Double(s.tempoDuration)
            let units = Double(ramp)*(s.tempo+end)*0.6+Double(delta-ramp)*s.tempoTarget*1.2+s.fractionalUnits
            s.tempoElapsed += ramp;s.tempo = end
            let whole = UInt64(units);s.fractionalUnits = units-Double(whole)
            let elapsed = s.elapsedUnits+whole
            let limit = UInt64(s.ticks)*1000*UInt64(s.loops)
            s.elapsedUnits = limit != 0 ? min(elapsed,limit):elapsed;s.clock = milliseconds
            if limit != 0,elapsed >= limit {s.status = 2;s.loops = 1;sequencer.end(handle)}
            sequences[handle] = s
        }
    }
    private var sequences:[UInt32:Sequence] = [:]
    private(set) var events:[[String:Any]] = []
    var observePhysical:(([String:Any])->Void)?
    private func record(_ event:[String:Any]) {
        var timed = event;timed["clock_ms"] = now()
        events.append(timed);observePhysical?(event)
        // --music-render: the game's music service calls, with the game clock.
        if let directory = Self.renderDirectory {
            serviceLog.append(timed);let log = serviceLog
            Self.renderQueue.async {
                try? FileManager.default.createDirectory(at:directory,withIntermediateDirectories:true)
                try? JSONSerialization.data(withJSONObject:log,options:[.sortedKeys])
                    .write(to:directory.appendingPathComponent("services.log"),options:.atomic)
            }
        }
    }
    private var serviceLog:[[String:Any]] = []
    init(resources:ClawNativeMenuResources) {self.resources = resources}
    func service(_ function:UInt32,_ receiver:UInt32,_ a:[UInt32])->UInt32? {
        guard receiver == 0,resources.fault == 0 else {return nil}
        switch function {
        case 0x546e70:
            guard a.isEmpty,!started else {return nil}
            started = true;record(["service":"startup"]);return 1
        case 0x546e74:
            guard started,a.count == 3,a[1] == 0,a[2] == .max,
                  let out = resources.heap.lookup(a[0],words:1) else {return nil}
            let token = resources.allocate(16);drivers.insert(token);out.pointee = token
            record(["service":"open"]);return 0
        case 0x546e9c:
            guard a.count == 1,drivers.contains(a[0]) else {return nil}
            let token = resources.allocate(16);sequences[token] = Sequence()
            record(["service":"allocate"]);return token
        case 0x546e98:
            guard a.count == 3,a[2] == 0,sequences[a[0]] != nil,
                  let data = resources.allocationData(a[1]),let decoded = decode(data) else {return nil}
            sequences[a[0]] = Sequence(data:data,events:decoded.events,ticks:decoded.ticks)
            sequencer.end(a[0]);songs[a[0]] = ClawXMIDISong(data)
            record(["service":"initialize","handle":a[0],"bytes":data.count,"events":decoded.events,"ticks":decoded.ticks,
                           "sha256":SHA256.hash(data:data).map{String(format:"%02x",$0)}.joined()]);return 1
        case 0x546e7c,0x546e78,0x546e84,0x546e88,0x546e94,0x546e90,0x546e80:
            guard a.count == (function == 0x546e88 ? 2:1),sequences[a[0]]?.data.isEmpty == false else {return nil}
            advance()
            let sequence = sequences[a[0]]!
            if function == 0x546e90 || function == 0x546e80 {
                // Start restarts the clock; resume continues it.
                if function == 0x546e90 {sequences[a[0]]!.elapsedUnits = 0}
                sequences[a[0]]!.status = 4;sequences[a[0]]!.clock = now()
            }
            if function == 0x546e78 {sequences[a[0]]!.status = 2;sequencer.end(a[0])}
            if function == 0x546e84 {sequences[a[0]]!.status = 8;sequencer.pause(a[0])}
            if function == 0x546e88 {sequences[a[0]]!.loops = a[1];sequencer.setLoops(a[0],a[1])}
            if function == 0x546e94 {sequences.removeValue(forKey:a[0]);songs.removeValue(forKey:a[0]);sequencer.end(a[0]);resources.release(a[0])}
            if function == 0x546e90 {play(a[0],loops:sequences[a[0]]!.loops)}
            if function == 0x546e80 {sequencer.resume(a[0])}
            let status = sequences[a[0]]?.status ?? sequence.status
            record(["service":String(function,radix:16),"handle":a[0],"status":status]);return function == 0x546e7c ? status:0
        case 0x546e6c: // AIL_set_XMIDI_master_volume(driver, 0...127)
            guard a.count == 2,drivers.contains(a[0]) else {return nil}
            masterVolume = min(a[1],127);synth?.setMasterVolume(masterVolume)
            record(["service":"546e6c","volume":masterVolume]);return 0
        case 0x546e8c: // AIL_XMIDI_master_volume(driver)
            guard a.count == 1,drivers.contains(a[0]) else {return nil}
            return masterVolume
        case 0x546e68:
            guard a.isEmpty,started,sequences.isEmpty else {return nil}
            for driver in drivers {resources.release(driver)};drivers.removeAll();started = false
            record(["service":"shutdown"]);return 0
        default:return nil
        }
    }
    func acceptsTempo(_ handle:UInt32)->Bool {sequences[handle]?.data.isEmpty == false}
    func requestTempo(_ handle:UInt32,speed:UInt32,milliseconds:UInt32)->Bool {
        guard sequences[handle]?.data.isEmpty == false else {return false}
        advance()
        sequences[handle]!.tempoStart = sequences[handle]!.tempo
        sequences[handle]!.tempoTarget = Double(speed)
        sequences[handle]!.tempoElapsed = 0;sequences[handle]!.tempoDuration = milliseconds
        sequencer.setTempo(handle,percent:Double(speed),milliseconds:milliseconds)
        record(["service":"AIL_set_sequence_tempo","handle":handle,"tempo":speed,"milliseconds":milliseconds])
        return true
    }
    func close() {
        sequencer.endAll();songs.removeAll()
        for token in sequences.keys {resources.release(token)};sequences.removeAll()
        for token in drivers {resources.release(token)};drivers.removeAll();started = false
    }
    private func play(_ handle:UInt32,loops:UInt32) {
        guard let song = songs[handle],let data = sequences[handle]?.data else {return}
        if synth == nil,let output,let made = ClawMusicSynth(sequencer:sequencer) {
            made.setMasterVolume(masterVolume);synth = made;output.attachMusic(made)
        }
        sequencer.start(handle,song:song,loops:loops)
        starts += 1
        guard let directory = Self.renderDirectory else {return}
        // Offline check render: the same sequencer and synth in manual
        // rendering mode, one loop plus eight seconds, never the speakers.
        let sha = SHA256.hash(data:data).map{String(format:"%02x",$0)}.joined()
        let stem = String(format:"%02d-",starts)+sha.prefix(12),clock = now()
        Self.renderQueue.async {
            do {
                try FileManager.default.createDirectory(at:directory,withIntermediateDirectories:true)
                try data.write(to:directory.appendingPathComponent(stem+".xmi"))
                try ClawMusicSynth.renderOffline(song:song,seconds:Double(song.ticks)/120+8,
                    wav:directory.appendingPathComponent(stem+".wav"),log:directory.appendingPathComponent(stem+".json"),
                    extra:["sha256":sha,"game_clock_ms":clock,"game_loops":loops,"start":stem])
            } catch {
                try? JSONSerialization.data(withJSONObject:["status":"fail","error":"\(error)"])
                    .write(to:directory.appendingPathComponent(stem+".json"))
            }
        }
    }
    private func decode(_ data:Data)->(events:Int,ticks:Int)? {
        var eventStreams:[Data] = [],counts:[Int] = []
        func chunks(_ start:Int,_ end:Int,_ depth:Int)->Bool {
            guard depth <= 8 else {return false}
            var at = start
            while at < end {
                guard at+8 <= end else {return false}
                let tag = String(decoding:data[at..<at+4],as:UTF8.self)
                let count = data[at+4..<at+8].reduce(0){($0<<8)|Int($1)},body = at+8,limit = body+count
                guard limit+(count&1) <= end else {return false}
                switch tag {
                case "FORM","CAT ":
                    guard count >= 4,["XDIR","XMID"].contains(String(decoding:data[body..<body+4],as:UTF8.self)),
                          chunks(body+4,limit,depth+1) else {return false}
                case "INFO":
                    guard count == 2 else {return false};counts.append(Int(data[body])|Int(data[body+1])<<8)
                case "XDIR":
                    // Las Almenas's XMIDI writer uses a big-endian XDIR
                    // sequence-count chunk in place of little-endian INFO.
                    guard count == 2,depth == 1 else {return false}
                    counts.append(Int(data[body])<<8|Int(data[body+1]))
                case "EVNT":eventStreams.append(Data(data[body..<limit]))
                case "TIMB":
                    guard count >= 2,count == 2+2*(Int(data[body])|Int(data[body+1])<<8) else {return false}
                default:return false
                }
                at = limit+(count&1)
            }
            return at == end
        }
        guard chunks(0,data.count,0),counts == [1],eventStreams.count == 1 else {return nil}
        let stream = eventStreams[0];var cursor = 0,tick = 0,duration = 0,count = 0,ended = false
        func byte()->Int? {
            guard cursor < stream.count else {return nil}
            defer {cursor += 1};return Int(stream[cursor])
        }
        func variable()->Int? {
            var result = 0
            for _ in 0..<4 {guard let b = byte() else {return nil};result = result*128+(b&127);if b < 128 {return result}}
            return nil
        }
        while let status = byte() {
            if status < 128 {tick += status;continue}
            count += 1
            if status == 255 {
                guard let kind = byte(),let length = variable(),cursor+length <= stream.count else {return nil}
                cursor += length
                if kind == 47 {
                    guard length == 0,stream[cursor...].isEmpty || Array(stream[cursor...]) == [0] else {return nil}
                    cursor = stream.count;ended = true
                }
            } else if status == 240 || status == 247 {
                guard let length = variable(),cursor+length <= stream.count else {return nil};cursor += length
            } else if status < 240 {
                let message = status>>4
                for _ in 0..<(message == 12 || message == 13 ? 1:2) {guard let b = byte(),b < 128 else {return nil}}
                if message == 9 {guard let length = variable() else {return nil};duration = max(duration,tick+length)}
            } else {return nil}
        }
        return ended ? (count,max(tick,duration)):nil
    }
}

// MARK: - Native General MIDI playback (replaces the Windows MIDI synth)

/// The XMIDI event stream as timed MIDI channel messages on the fixed 120 Hz
/// XMIDI clock. Note-on durations become explicit note-offs; XMIDI-only
/// controllers (110-120) and meta/system events are not sent to the synth.
struct ClawXMIDISong {
    struct Message {let tick:Int;let status:UInt8;let data1:UInt8;let data2:UInt8}
    let messages:[Message]
    let ticks:Int
    init?(_ data:Data) {
        let bytes = [UInt8](data)
        func be32(_ at:Int)->Int {Int(bytes[at])<<24|Int(bytes[at+1])<<16|Int(bytes[at+2])<<8|Int(bytes[at+3])}
        func find(_ start:Int,_ end:Int,_ depth:Int)->ArraySlice<UInt8>? {
            var at = start
            while depth <= 8,at+8 <= end {
                let tag = String(decoding:bytes[at..<at+4],as:UTF8.self),count = be32(at+4),body = at+8
                guard body+count <= end else {return nil}
                if tag == "FORM" || tag == "CAT ",count >= 4,let found = find(body+4,body+count,depth+1) {return found}
                if tag == "EVNT" {return bytes[body..<body+count]}
                at = body+count+(count&1)
            }
            return nil
        }
        guard let stream = find(0,bytes.count,0) else {return nil}
        var cursor = stream.startIndex,tick = 0,order = 0
        var timed:[(tick:Int,order:Int,message:Message)] = []
        func byte()->UInt8? {guard cursor < stream.endIndex else {return nil};defer {cursor += 1};return stream[cursor]}
        func variable()->Int? {
            var result = 0
            for _ in 0..<4 {guard let b = byte() else {return nil};result = result*128+Int(b&127);if b < 128 {return result}}
            return nil
        }
        // Note-offs sort before any other message at the same tick.
        func add(_ at:Int,_ s:UInt8,_ a:UInt8,_ b:UInt8,off:Bool = false) {
            order += 1;timed.append((at,off ? -order:order,Message(tick:at,status:s,data1:a,data2:b)))
        }
        var end = 0
        while let status = byte() {
            if status < 128 {tick += Int(status);continue}
            if status == 255 {
                guard let kind = byte(),let length = variable(),cursor+length <= stream.endIndex else {return nil}
                cursor += length;if kind == 47 {end = tick;break}
            } else if status == 240 || status == 247 {
                guard let length = variable(),cursor+length <= stream.endIndex else {return nil};cursor += length
            } else if status < 240 {
                let kind = status>>4
                guard let a = byte(),a < 128 else {return nil}
                var b:UInt8 = 0
                if kind != 12 && kind != 13 {guard let value = byte(),value < 128 else {return nil};b = value}
                if kind == 9 {
                    guard let length = variable() else {return nil}
                    add(tick,status,a,b)
                    add(tick+length,0x80|status&15,a,0,off:true);end = max(end,tick+length)
                } else if kind == 11 && (110...120).contains(a) {
                    continue
                } else {add(tick,status,a,b)}
            } else {return nil}
        }
        // Same loop length the game-visible sequence clock uses.
        ticks = max(tick,end)
        messages = timed.sorted {$0.tick != $1.tick ? $0.tick < $1.tick:$0.order < $1.order}.map {$0.message}
    }
}

/// Sample-accurate XMIDI sequencer. It runs on the audio render thread and
/// schedules each message at its exact frame inside the render slice; the
/// game thread only changes play state (start, stop, resume, end, loops).
final class ClawMusicSequencer {
    typealias Emit = (_ offset:Int,_ status:UInt8,_ data1:UInt8,_ data2:UInt8)->Void
    private struct Voice {
        let song:ClawXMIDISong;var index = 0;var frame:Int64 = 0;var playing = true;var loops:UInt32
        var seekTicks: Double? = nil
        var tempo = 100.0,tempoStart = 100.0,tempoTarget = 100.0
        var tempoMilliseconds = 0.0,tempoElapsed = 0.0,position:Double? = nil
    }
    private let lock = NSLock()
    private var voices:[UInt32:Voice] = [:]
    private var silence = false
    private(set) var renderedFrames:Int64 = 0
    /// Offline checks: absolute frame of every note-on actually scheduled.
    var noteOnLog:[(frame:Int64,channel:UInt8,key:UInt8)]? = nil
    func start(_ handle:UInt32,song:ClawXMIDISong,loops:UInt32) {
        lock.lock();voices[handle] = Voice(song:song,loops:loops);silence = true;lock.unlock()
    }
    func setTempo(_ handle:UInt32,percent:Double,milliseconds:UInt32) {
        lock.lock();defer{lock.unlock()}
        guard voices[handle] != nil else {return}
        voices[handle]!.tempoStart = voices[handle]!.tempo
        voices[handle]!.tempoTarget = percent;voices[handle]!.tempoMilliseconds = Double(milliseconds)
        voices[handle]!.tempoElapsed = 0
        if voices[handle]!.position == nil {voices[handle]!.position = Double(voices[handle]!.frame)}
    }
    func setLoops(_ handle:UInt32,_ loops:UInt32) {lock.lock();voices[handle]?.loops = loops;lock.unlock()}
    func pause(_ handle:UInt32) {lock.lock();if voices[handle] != nil {voices[handle]!.playing = false;silence = true};lock.unlock()}
    func resume(_ handle:UInt32) {lock.lock();voices[handle]?.playing = true;lock.unlock()}
    func seek(_ handle:UInt32,ticks:Double,tempo:Double,target:Double,remaining:UInt32,paused:Bool) {
        lock.lock();defer {lock.unlock()}
        guard voices[handle] != nil else {return}
        voices[handle]!.seekTicks = ticks
        voices[handle]!.tempo = tempo;voices[handle]!.tempoStart = tempo;voices[handle]!.tempoTarget = target
        voices[handle]!.tempoMilliseconds = Double(remaining);voices[handle]!.tempoElapsed = 0
        voices[handle]!.playing = !paused;silence = true
    }

    func end(_ handle:UInt32) {lock.lock();if voices.removeValue(forKey:handle) != nil {silence = true};lock.unlock()}
    func endAll() {lock.lock();voices.removeAll();silence = true;lock.unlock()}
    func render(frames:Int,sampleRate:Double,emit:Emit) {
        lock.lock();defer {lock.unlock()}
        guard frames > 0,sampleRate > 0 else {return}
        if silence {
            silence = false
            for channel:UInt8 in 0..<16 {emit(0,0xb0|channel,123,0)}
            emit(0,0xb9,0,0x78) // Channel 10 stays the percussion bank.
        }
        func frameOf(_ tick:Int)->Int64 {Int64((Double(tick)*sampleRate/120).rounded())}
        for handle in voices.keys.sorted() {
            guard var voice = voices[handle],voice.playing else {continue}
            let messages = voice.song.messages,loopFrames = frameOf(voice.song.ticks)
            if let ticks = voice.seekTicks {
                let loop = Double(max(1,voice.song.ticks))
                let completed = UInt32(min(Double(UInt32.max),floor(ticks/loop)))
                if voice.loops > 0 {voice.loops = voice.loops > completed ? voice.loops-completed:1}
                let at = ticks.truncatingRemainder(dividingBy:loop)
                voice.index = 0
                // Reapply MIDI programs/controllers and active notes at the
                // restored position before scheduling the remaining stream.
                while voice.index < messages.count,Double(messages[voice.index].tick) <= at {
                    let m = messages[voice.index]
                    var status = m.status,value = m.data2
                    if status>>4 == 11 && (m.data1 == 0 || m.data1 == 32) {value = status == 0xb9 && m.data1 == 0 ? 0x78:0}
                    if status>>4 == 9 && value == 0 {status = 0x80|status&15}
                    emit(0,status,m.data1,value);voice.index += 1
                }
                voice.frame = Int64(at*sampleRate/120)
                voice.position = Double(voice.frame);voice.seekTicks = nil
            }

            if var position = voice.position {
                // Tempo requests change event time, including note-off time.
                // Integrate the linear transition in physical sample time.
                for offset in 0..<frames {
                    while voice.index < messages.count,Double(frameOf(messages[voice.index].tick)) <= position {
                        let m = messages[voice.index]
                        var status = m.status,value = m.data2
                        if status>>4 == 11 && (m.data1 == 0 || m.data1 == 32) {value = status == 0xb9 && m.data1 == 0 ? 0x78:0}
                        if status>>4 == 9 && value == 0 {status = 0x80|status&15}
                        emit(offset,status,m.data1,value)
                        if status>>4 == 9 {noteOnLog?.append((renderedFrames+Int64(offset),status&15,m.data1))}
                        voice.index += 1
                    }
                    if voice.index == messages.count,loopFrames > 0,position >= Double(loopFrames) {
                        if voice.loops == 1 {voice.playing = false;break}
                        if voice.loops > 1 {voice.loops -= 1}
                        voice.index = 0;position -= Double(loopFrames)
                    }
                    let step = 1000/sampleRate
                    let remaining = max(0,voice.tempoMilliseconds-voice.tempoElapsed),ramp = min(step,remaining)
                    let end = voice.tempoMilliseconds == 0 ? voice.tempoTarget:voice.tempoStart+(voice.tempoTarget-voice.tempoStart)*(voice.tempoElapsed+ramp)/voice.tempoMilliseconds
                    position += (ramp*(voice.tempo+end)/2+(step-ramp)*voice.tempoTarget)*sampleRate/100000
                    voice.tempo = end;voice.tempoElapsed += ramp
                }
                voice.position = position
                if voice.playing {voices[handle] = voice} else {voices.removeValue(forKey:handle)}
                continue
            }
            var base = voice.frame // song frame at offset 0 of this slice
            while true {
                while voice.index < messages.count {
                    let message = messages[voice.index],at = frameOf(message.tick)
                    guard at < base+Int64(frames) else {break}
                    let offset = Int(max(0,at-base))
                    var status = message.status,data2 = message.data2
                    // Bank select: the disc SoundFont has one melodic bank and
                    // the drum kits, so a missing variation bank falls back to
                    // the capital tone, as GS synths do; channel 10 stays drums.
                    if status>>4 == 11 && (message.data1 == 0 || message.data1 == 32) {
                        data2 = status == 0xb9 && message.data1 == 0 ? 0x78:0
                    }
                    if status>>4 == 9 && data2 == 0 {status = 0x80|status&15}
                    emit(offset,status,message.data1,data2)
                    if status>>4 == 9 {noteOnLog?.append((renderedFrames+Int64(offset),status&15,message.data1))}
                    voice.index += 1
                }
                guard voice.index >= messages.count,loopFrames > 0,loopFrames < base+Int64(frames) else {break}
                if voice.loops == 1 {voice.playing = false;break}
                if voice.loops > 1 {voice.loops -= 1}
                voice.index = 0;base -= loopFrames
            }
            voice.frame = base+Int64(frames)
            if voice.playing {voices[handle] = voice} else {voices.removeValue(forKey:handle)}
        }
        renderedFrames += Int64(frames)
    }
}

/// The General MIDI synth: Apple's multitimbral MIDI synth unit loaded with
/// the original disc's SoundFont, driven by a sequencer from its render notify.
final class ClawMusicSynth {
    static let soundBankURL:URL? = {
        let candidates = [Bundle.main.resourceURL?.appendingPathComponent("GameData/MENU/CLAW4.SF2"),
            // Apple's General MIDI bank is present on some OS installations.
            URL(fileURLWithPath:"/System/Library/Components/CoreAudio.component/Contents/Resources/gs_instruments.dls")]
        return candidates.compactMap { $0 }.first { FileManager.default.fileExists(atPath:$0.path) }
    }()
    let node:AVAudioUnitMIDIInstrument
    let sequencer:ClawMusicSequencer
    private var sampleRate:Double = 44100
    private(set) weak var engine:AVAudioEngine?
    init?(sequencer:ClawMusicSequencer,soundBank:URL? = ClawMusicSynth.soundBankURL) {
        guard let url = soundBank,FileManager.default.fileExists(atPath:url.path) else {return nil}
        var bank = url as CFURL
        self.sequencer = sequencer
        node = AVAudioUnitMIDIInstrument(audioComponentDescription:AudioComponentDescription(
            componentType:kAudioUnitType_MusicDevice,componentSubType:kAudioUnitSubType_MIDISynth,
            componentManufacturer:kAudioUnitManufacturer_Apple,componentFlags:0,componentFlagsMask:0))
        let status = AudioUnitSetProperty(node.audioUnit,kMusicDeviceProperty_SoundBankURL,kAudioUnitScope_Global,0,
                                          &bank,UInt32(MemoryLayout<CFURL>.size))
        guard status == noErr else {return nil}
        AudioUnitAddRenderNotify(node.audioUnit,clawMusicRenderNotify,Unmanaged.passUnretained(self).toOpaque())
    }
    deinit {AudioUnitRemoveRenderNotify(node.audioUnit,clawMusicRenderNotify,Unmanaged.passUnretained(self).toOpaque())}
    fileprivate func renderNotify(frames:UInt32) {
        let unit = node.audioUnit
        sequencer.render(frames:Int(frames),sampleRate:sampleRate) {offset,s,a,b in
            MusicDeviceMIDIEvent(unit,UInt32(s),UInt32(a),UInt32(b),UInt32(offset))
        }
    }
    /// Attach before the engine is prepared; call `preload` once it is.
    func attach(to graph:AVAudioEngine) {
        graph.attach(node);graph.connect(node,to:graph.mainMixerNode,format:nil)
        sampleRate = node.outputFormat(forBus:0).sampleRate;engine = graph
    }
    /// Loads every General MIDI program and the drum kits before playback, so
    /// program changes in the song never load samples on the render thread.
    func preload() {
        var on:UInt32 = 1
        AudioUnitSetProperty(node.audioUnit,kAUMIDISynthProperty_EnablePreload,kAudioUnitScope_Global,0,&on,4)
        for program:UInt32 in 0..<128 {MusicDeviceMIDIEvent(node.audioUnit,0xc0,program,0,0)}
        MusicDeviceMIDIEvent(node.audioUnit,0xb9,0,0x78,0)
        for kit:UInt32 in [0,8,16,24,25,32,40,48] {MusicDeviceMIDIEvent(node.audioUnit,0xc9,kit,0,0)}
        on = 0
        AudioUnitSetProperty(node.audioUnit,kAUMIDISynthProperty_EnablePreload,kAudioUnitScope_Global,0,&on,4)
        sampleRate = node.outputFormat(forBus:0).sampleRate
    }
    /// AIL XMIDI master volume, 0...127. The SoundFont synth runs about 12 dB
    /// hotter than the sound effects at full volume; this gain keeps the
    /// densest passages of the shipped songs below full scale.
    static let headroom:Float = 0.25
    func setMasterVolume(_ volume:UInt32) {node.volume = Float(min(volume,127))/127*Self.headroom}

    /// Offline render of one song (manual rendering mode, never the speakers):
    /// writes `<stem>.wav` and `<stem>.json` with every scheduled note-on frame.
    static func renderOffline(song:ClawXMIDISong,seconds:Double,wav:URL,log:URL,extra:[String:Any],
                              soundBank:URL? = ClawMusicSynth.soundBankURL) throws {
        let rate = 44100.0
        guard let format = AVAudioFormat(standardFormatWithSampleRate:rate,channels:2) else {return}
        let graph = AVAudioEngine(),sequencer = ClawMusicSequencer()
        try graph.enableManualRenderingMode(.offline,format:format,maximumFrameCount:1024)
        guard let synth = ClawMusicSynth(sequencer:sequencer,soundBank:soundBank) else {throw AssetError.invalid("Music sound bank unavailable")}
        synth.setMasterVolume(127);synth.attach(to:graph);graph.prepare();synth.preload();try graph.start()
        sequencer.noteOnLog = [];sequencer.start(1,song:song,loops:0)
        let file = try AVAudioFile(forWriting:wav,settings:[AVFormatIDKey:kAudioFormatLinearPCM,AVSampleRateKey:rate,
            AVNumberOfChannelsKey:2,AVLinearPCMBitDepthKey:16,AVLinearPCMIsFloatKey:false,AVLinearPCMIsBigEndianKey:false],
            commonFormat:.pcmFormatFloat32,interleaved:false)
        guard let buffer = AVAudioPCMBuffer(pcmFormat:graph.manualRenderingFormat,frameCapacity:1024) else {return}
        let total = AVAudioFramePosition(seconds*rate);var peak:Float = 0,nonzero = 0
        while graph.manualRenderingSampleTime < total {
            let frames = AVAudioFrameCount(min(Int64(1024),total-graph.manualRenderingSampleTime))
            guard try graph.renderOffline(frames,to:buffer) == .success else {throw AssetError.invalid("Offline music render")}
            for channel in 0..<2 {
                let samples = buffer.floatChannelData![channel]
                for i in 0..<Int(buffer.frameLength) where samples[i] != 0 {nonzero += 1;peak = max(peak,abs(samples[i]))}
            }
            try file.write(from:buffer)
        }
        graph.stop()
        var report = extra
        report["sample_rate"] = rate;report["frames"] = total;report["loop_ticks"] = song.ticks
        report["loop_frames"] = Int64((Double(song.ticks)*rate/120).rounded())
        report["peak"] = peak;report["nonzero_samples"] = nonzero
        report["note_on_frames"] = (sequencer.noteOnLog ?? []).map {[$0.frame,Int64($0.channel),Int64($0.key)]}
        report["status"] = "done"
        try JSONSerialization.data(withJSONObject:report,options:[.sortedKeys]).write(to:log,options:.atomic)
    }
}

private let clawMusicRenderNotify:AURenderCallback = {refcon,flags,_,_,frames,_ in
    guard flags.pointee.contains(.unitRenderAction_PreRender) else {return noErr}
    Unmanaged<ClawMusicSynth>.fromOpaque(refcon).takeUnretainedValue().renderNotify(frames:frames)
    return noErr
}
