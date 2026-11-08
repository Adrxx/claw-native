import Foundation

private final class AudioWitness:ClawNativeCanonicalHost.ObjectAudioProvider {
    let audio:ClawNativeAudio
    var events:[[String:Any]]=[]
    var omit:UInt32? = nil
    init(_ audio:ClawNativeAudio) {self.audio=audio}
    func validAudioBinding(for host:ClawNativeCanonicalHost)->Bool {audio.validAudioBinding(for:host)}
    func ownsAudioPool(_ token:UInt32)->Bool {audio.ownsAudioPool(token)}
    func retainAudioAllocation(_ token:UInt32,provider:ClawNativeCanonicalHost.ObjectAllocationProvider)->Bool {audio.retainAudioAllocation(token,provider:provider)}
    func audioPhysical(_ call:ClawCall,host:ClawNativeCanonicalHost)->UInt32? {
        if omit==call.function {return nil}
        let a=withUnsafeBytes(of:call.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))}
        let result=audio.audioPhysical(call,host:host)
        var event:[String:Any] = ["function":call.function,"arguments":a,"result":result as Any? ?? NSNull()]
        if call.function==0x71020014 || [UInt32(0x71010018),0x7101001c,0x71010020,0x71010024].contains(call.function),
           let output=host.bytes(a.last!,count:4) {event["output"]=UnsafeRawPointer(output).loadUnaligned(as:UInt32.self)}
        events.append(event);return result
    }
}
@main struct BossStagerAudioTransport {
    static let hash="350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263"
    static func main() throws {
        let directory=URL(fileURLWithPath:CommandLine.arguments[1])
        var profiles:[[String:Any]]=[],controls:[String]=[]
        let names=["playback-lifecycle","direct-allocation","disabled","missing-physical-service","missing-audio-owner","wrong-pool","wrong-device-target","foreign-audio","foreign-memory","replace-pool","replace-allocation","exhaustion"]
        for name in names {
            let heap=ClawTokenHeap(),host:ClawNativeCanonicalHost
            host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x40
            heap.store(token:0x510020,words:1)[0]=UInt32.max
            let audio=try ClawNativeAudio(root:URL(fileURLWithPath:"App/GameData"),outputEnabled:false,sharedHeap:heap,preload:false)
            try audio.load(name:"GAME_SDPT2",data:Data(contentsOf:URL(fileURLWithPath:"App/GameData/GAME/SOUNDS/SDPT2.WAV")))
            let sound=audio.resolve(name:"GAME_SDPT2")!,pool=sound.voicePoolToken
            precondition(heap.lookup(pool,words:14)![12]==0 && heap.lookup(pool,words:14)![13]==0)
            let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map{($0.element,UInt32(0x710000+$0.offset*4))})
            let memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:0x68000000)
            let witness=AudioWitness(audio)
            func w(_ t:UInt32)->UInt32 {heap.lookup(t,words:1)![0]}
            func segment(_ t:UInt32,_ n:UInt32)->[String:Any] {
                let b=heap.lookupBytes(t,count:n)!
                return ["address":t,"hex":Data(bytes:b,count:Int(n)).map{String(format:"%02x",$0)}.joined()]
            }
            let buffer=w(pool+12),device=w(audio.managerIdentity+20),scene=w(sound.resourceToken+12)
            let ranges:[(UInt32,UInt32)]=[(pool,56),(audio.managerIdentity,128),(sound.resourceToken,64),(scene,48),(buffer,16),(w(buffer),80),(device,16),(w(device),28),(0x541178,404),(0x510020,4)]
            if name=="disabled" {heap.lookup(audio.managerIdentity,words:32)![30]=0}
            if name=="missing-physical-service" {witness.omit=0x71020014}
            if name=="wrong-device-target" {heap.lookup(w(device)+20,words:1)![0]=0x71020018}
            if name=="replace-pool" {memory.beforeObjectAllocation={_ in heap.free(pool);_=heap.store(token:pool,words:14)}}
            if name=="replace-allocation" {memory.afterService={f,a,t in if f==0x4a48e0 && t != 0 {heap.free(t);_=heap.store(token:t,words:14)}}}
            if name=="exhaustion" {memory.failAllocation={_ in true}}
            var allocated:[UInt32]=[]
            memory.beforeService={f,a in if f==0x4a48e0 {precondition(a==[56])}}
            if name=="playback-lifecycle" {
                let initialVolume = Data(repeating:0,count:404)
                precondition(audio.acceptsInitialVolumeMetadata(initialVolume,in:heap))
                precondition(!audio.acceptsInitialVolumeMetadata(Data(repeating:0,count:400),in:heap))
                var corruptVolume = initialVolume;corruptVolume[0] = 1
                precondition(!audio.acceptsInitialVolumeMetadata(corruptVolume,in:heap))
                precondition(!audio.acceptsInitialVolumeMetadata(initialVolume,in:ClawTokenHeap()))
                let table = heap.lookup(0x541178,words:101)!,first = table[0]
                table[0] ^= 1
                precondition(!audio.acceptsInitialVolumeMetadata(initialVolume,in:heap))
                table[0] = first
                controls.append("startup-volume-metadata-ownership")
                var physical=ClawCall();physical.function=0x71010024;physical.argumentCount=2;physical.arguments.0=buffer;physical.arguments.1=0xdead0000
                precondition(audio.audioPhysical(physical,host:ClawNativeCanonicalHost(heap:heap))==nil);controls.append("invalid-output-span")
                physical.receiver=1;precondition(audio.audioPhysical(physical,host:host)==nil);controls.append("incorrect-physical-receiver")
                physical.receiver=0;physical.function=0x71010028
                precondition(audio.audioPhysical(physical,host:host)==nil);controls.append("incorrect-physical-target")
                physical.function=0x71010048;physical.argumentCount=1;physical.arguments.0=0xdead0000
                precondition(audio.audioPhysical(physical,host:host)==0x80070057);controls.append("physical-failure-hresult")
                var state=ClawX87State();state.size=UInt32(MemoryLayout<ClawX87State>.size);state.version=1;state.control=0x023f;state.count=1;state.popCount=1
                state.slots.0.significand=UInt64(1)<<63;state.slots.0.signExponent=16383+5
                var math=ClawCall();math.function=0x4a30e0;math.x87ArgumentCount=UInt32(CLAW_X87_EXACT)
                withUnsafeMutablePointer(to:&state) {pointer in
                    math.x87State=pointer
                    precondition((host.withObjectAllocation(provider:memory,audio:witness){host.callNativeDependency(math)} ?? nil)==32)
                }
                precondition(state.returned==1 && state.count==0 && state.eax==32 && state.edx==0)
                controls.append("exact-x87-consumed-return")
                math.x87State=nil;math.x87ArgumentCount=1;math.x87Argument=32.75
                precondition((host.withObjectAllocation(provider:memory,audio:witness){host.callNativeDependency(math)} ?? nil)==32)
                math.x87Argument = -32.75
                precondition((host.withObjectAllocation(provider:memory,audio:witness){host.callNativeDependency(math)} ?? nil)==UInt32(bitPattern:-32))
                controls.append("boss-stager-binary64-truncation")
            }
            let initial=ranges.map{segment($0.0,$0.1)}
            var steps:[[String:Any]]=[]
            func play(_ args:[UInt32],root:UInt32=0x4b45f0,receiver:UInt32?=nil)->Bool {
                var c=ClawCall();c.function=root;c.receiver=receiver ?? pool;c.argumentCount=UInt32(args.count)
                withUnsafeMutableBytes(of:&c.arguments){d in args.withUnsafeBytes{d.copyBytes(from:$0)}}
                witness.events=[]
                var result:ClawNativeCanonicalHost.Completion?
                let scoped=host.withObjectAllocation(provider:memory,audio:name=="missing-audio-owner" ? nil:witness){result=host.invoke(c)} != nil
                allocated=memory.localPointers
                let final=[segment(pool,56)]+allocated.compactMap{heap.lookupBytes($0,count:56)==nil ? nil:segment($0,56)}
                steps.append(["function":root,"receiver":c.receiver,"arguments":args,"completed":result?.completed ?? false,"eax":result?.eax as Any? ?? NSNull(),"fault":host.fault?.address as Any? ?? NSNull(),"events":witness.events,"allocations":allocated,"final":final])
                return scoped && result?.completed==true
            }
            if name=="foreign-audio" {
                let foreign=try ClawNativeAudio(root:URL(fileURLWithPath:"App/GameData"),outputEnabled:false,sharedHeap:ClawTokenHeap(),preload:false)
                precondition(host.withObjectAllocation(provider:memory,audio:foreign){0}==nil);controls.append(name);continue
            }
            if name=="foreign-memory" {
                let other=ClawNativeCanonicalHost(heap:heap)
                precondition(other.withObjectAllocation(provider:memory,audio:witness){0}==nil);controls.append(name);continue
            }
            if name=="direct-allocation" {
                precondition(play([1],root:0x4b42e0) && allocated.count==1 && audio.activeVoiceCount==0)
                profiles.append(["name":name,"segments":initial,"pool":pool,"manager":audio.managerIdentity,"sound":sound.resourceToken,"steps":steps]);continue
            }
            let ok=play([100,0,0,0],receiver:name=="wrong-pool" ? sound.resourceToken:nil)
            if name=="playback-lifecycle" {
                precondition(ok && allocated.count==1 && audio.activeVoiceCount==1)
                let first=allocated[0]
                precondition(play([55,UInt32(bitPattern:-25),10,1]) && allocated.count==2 && audio.activeVoiceCount==2)
                // Stop through the same physical owner before source idle selection.
                var stop=ClawCall();stop.function=0x4b3e30;stop.receiver=first
                precondition(host.withObjectAllocation(provider:memory,audio:witness){host.invoke(stop)}?.completed==true)
                precondition(play([80,25,UInt32(bitPattern:-10),0]) && allocated.count==2)
                precondition(w(pool+0x34)==first+4)
                var releases:[UInt32]=[]
                audio.observePhysical={event in if event["service"] as? String=="IDirectSoundBuffer::Release",let token=event["object"] as? UInt32 {releases.append(token)}}
                var fault:UInt32=0
                audio.unloadSceneSound(sound.resourceToken,fault:&fault)
                precondition(fault==0 && audio.loadedBufferCount==0 && memory.localPointers.isEmpty)
                precondition(allocated.allSatisfy{heap.lookupBytes($0,count:4)==nil})
                precondition(allocated.allSatisfy{!memory.releaseAudioAllocation($0)})
                steps.append(["teardown":true,"releases":releases,"retired":memory.tlsSnapshot().allocationBytes,
                    "sound":segment(sound.resourceToken,64),"manager":segment(audio.managerIdentity,128)])
                controls.append("source-teardown-owned-release")
            } else if name=="disabled" {precondition(ok && allocated.isEmpty)}
            else {precondition(!ok);controls.append(name)}
            profiles.append(["name":name,"segments":initial,"pool":pool,"manager":audio.managerIdentity,"sound":sound.resourceToken,"steps":steps])
        }
        // The rejected owner must not retire a replacement at the same token.
        let replacementHeap=ClawTokenHeap()
        var retiredAudio:ClawNativeAudio?=try ClawNativeAudio(root:URL(fileURLWithPath:"App/GameData"),outputEnabled:false,sharedHeap:replacementHeap,preload:false)
        try retiredAudio!.load(name:"GAME_SDPT2",data:Data(contentsOf:URL(fileURLWithPath:"App/GameData/GAME/SOUNDS/SDPT2.WAV")))
        let replaced=retiredAudio!.resolve(name:"GAME_SDPT2")!.voicePoolToken
        replacementHeap.free(replaced)
        replacementHeap.store(token:replaced,words:14).initialize(repeating:0x87654321,count:14)
        let replacementIdentity=replacementHeap.allocationIdentity(at:replaced,count:56)
        retiredAudio=nil
        precondition(replacementHeap.allocationIdentity(at:replaced,count:56) === replacementIdentity)
        precondition((0..<14).allSatisfy{replacementHeap.lookup(replaced,words:14)![$0]==0x87654321})
        controls.append("owner-teardown-preserves-replacement")
        try JSONSerialization.data(withJSONObject:["profiles":profiles,"controls":controls,"outputEnabled":false],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("audio-transport-native.json"))
        print("PASS native audio transport: \(profiles.count) profiles, \(controls.count) ownership/failure controls")
    }
}
