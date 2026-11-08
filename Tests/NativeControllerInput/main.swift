import Foundation
import GameController

struct Event: Codable, Equatable {
    let function: UInt32
    let arguments: [UInt32]
    let stackPointer: UInt32
}
struct Profile: Decodable {
    let label: String
    let arguments: [UInt32]?
    let failure: String?
    let count: UInt32?
    let x: UInt32?, y: UInt32?, buttons: UInt32?
    let keys: [String:UInt32]?
}
struct Reference: Decodable {
    let profile: Profile
    let token: UInt32, function: UInt32, receiver: UInt32
    let before: String, after: String
    let events: [Event]
    let eax: UInt32
}
func unhex(_ text: String) -> Data {
    let values = Array(text.utf8)
    return Data(stride(from: 0, to: values.count, by: 2).map {
        UInt8(String(decoding: values[$0..<$0+2], as: UTF8.self), radix: 16)!
    })
}
let rows = try JSONDecoder().decode([Reference].self,
    from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
for row in rows {
    let heap=ClawTokenHeap(), before=unhex(row.before)
    before.copyBytes(to: heap.storeBytes(token:row.token,count:UInt32(before.count)),count:before.count)
    heap.store(token:0x5134e0,words:1).pointee=0x3f28f5c3
    var events:[Event]=[]
    let owner=ClawNativeCanonicalHost(heap:heap) { owner, call in
        if call.function == 0x4a30e0 {
            // Physical native CRT conversion; the original side executes its CRT.
            var request=call, result:UInt32=0
            precondition(claw_native_menu_math_service(&request,&result)==1)
            return result
        }
        precondition(call.receiver==0 && call.receiver2==0 && call.x87ArgumentCount==0)
        let a=withUnsafeBytes(of:call.arguments) {Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))}
        events.append(Event(function:call.function,arguments:a,stackPointer:call.stackPointer))
        func put(_ token:UInt32,_ values:[UInt32]) {
            let bytes=UnsafeMutableRawPointer(owner.bytes(token,count:UInt32(values.count*4))!)
            values.withUnsafeBytes {bytes.copyMemory(from:$0.baseAddress!,byteCount:$0.count)}
        }
        switch call.function {
        case 0x546df8:return row.profile.failure == "no-device" ? 0:1
        case 0x546de8:
            if row.profile.failure == "position" {return 167}
            put(a[1]+8,[row.profile.x ?? 32767,row.profile.y ?? 32767])
            put(a[1]+32,[row.profile.buttons ?? 0]);return 0
        case 0x546df4:
            if row.profile.failure == "caps" {return 165}
            owner.bytes(a[1],count:404)!.initialize(repeating:0,count:404)
            put(a[1]+0x24,[0,65535,0,65535]);put(a[1]+0x3c,[row.profile.count ?? 9]);return 0
        case 0x546ce4:return row.profile.keys?[String(a[0])] ?? 0
        case 0x546cd0:put(a[0],[123,456]);return 1
        case 0x546c44:return [UInt32(640),480][Int(a[0])]
        case 0x546d9c:return 1
        default:return nil
        }
    }
    var call=ClawCall();call.function=row.function;call.receiver=row.receiver
    let arguments=row.profile.arguments ?? []
    call.argumentCount=UInt32(arguments.count)
    withUnsafeMutableBytes(of:&call.arguments) { buffer in
        for (i,value) in arguments.enumerated() {buffer.bindMemory(to:UInt32.self)[i]=value}
    }
    let result=owner.invoke(call)
    guard result.completed && result.fault == nil else {fatalError("\(row.profile.label): \(result)")}
    if row.function == 0x4b3240 || row.function == 0x430ec0 {precondition(result.eax==row.eax,row.profile.label+" return")}
    let actual=Data(bytes:heap.lookupBytes(row.token,count:UInt32(before.count))!,count:before.count)
    precondition(actual==unhex(row.after),row.profile.label+" bytes")
    precondition(events==row.events,row.profile.label+" physical calls")
}
// The adapter only packages physical samples; the unchanged game poller
// above owns thresholds, masks and edges. Test the documented WinMM layouts.
precondition(ClawNativeJoystickSample.axis(-1)==0)
precondition(ClawNativeJoystickSample.axis(0)==32767)
precondition(ClawNativeJoystickSample.axis(1)==65535)
precondition(ClawNativeJoystickSample.axis(-2)==0)
precondition(ClawNativeJoystickSample.axis(2)==65535)
let sample=ClawNativeJoystickSample(x:1234,y:5678,buttons:0x1a5,buttonCount:9)
let caps=sample.capabilities
precondition(caps.count==101 && caps[9]==0 && caps[10]==65535 && caps[11]==0 && caps[12]==65535 && caps[15]==9)
let position=sample.position(size:52,flags:0x83)
precondition(position == [52,0x83,1234,5678,0,0,0,0,0x1a5,0,0,0,0])
// A mutable GameController snapshot exercises the actual SDK-to-WinMM path.
// This is a software controller profile, not hardware acceptance.
let snapshotController=GCController.withExtendedGamepad()
let pad=snapshotController.extendedGamepad!
precondition(ClawNativeJoystickSample.sample(pad)==ClawNativeJoystickSample())
let snapshotButtons=[pad.buttonA,pad.buttonB,pad.buttonX,pad.buttonY,
                     pad.leftShoulder,pad.rightShoulder,pad.leftTrigger,pad.rightTrigger,pad.buttonMenu]
for (index,button) in snapshotButtons.enumerated() {
    button.setValue(1)
    precondition(ClawNativeJoystickSample.sample(pad).buttons == UInt32(1)<<index,"snapshot button \(index+1)")
    button.setValue(0)
    precondition(ClawNativeJoystickSample.sample(pad).buttons==0,"snapshot button release")
}
for button in snapshotButtons {button.setValue(1)}
precondition(ClawNativeJoystickSample.sample(pad).buttons==0x1ff)
for button in snapshotButtons {button.setValue(0)}
pad.leftThumbstick.setValueForXAxis(1,yAxis:1)
precondition(ClawNativeJoystickSample.sample(pad).x==65535 && ClawNativeJoystickSample.sample(pad).y==0,"snapshot stick and Y inversion")
pad.dpad.setValueForXAxis(-1,yAxis:-1)
precondition(ClawNativeJoystickSample.sample(pad).x==0 && ClawNativeJoystickSample.sample(pad).y==65535,"snapshot D-pad precedence")
pad.dpad.setValueForXAxis(0,yAxis:-1)
precondition(ClawNativeJoystickSample.sample(pad).x==65535 && ClawNativeJoystickSample.sample(pad).y==65535,"snapshot independent axis precedence")
pad.dpad.setValueForXAxis(0,yAxis:0)
pad.leftThumbstick.setValueForXAxis(0,yAxis:0)
precondition(ClawNativeJoystickSample.sample(pad)==ClawNativeJoystickSample(),"snapshot neutral release")
// Menu taps, repeat timing, dead zone, held-button boundaries and safe detach.
var navigation = ClawControllerNavigation()
func navigationKeys(_ sample:ClawNativeJoystickSample?, _ time:Double, playing:Bool = false) -> [UInt32] {
    navigation.keys(sample:sample,playing:playing,now:time)
}
precondition(navigationKeys(nil,0).isEmpty)
precondition(navigationKeys(.init(x:40000,y:25000),0).isEmpty,"stick drift")
precondition(navigationKeys(.init(y:65535),0.1)==[40],"menu down")
precondition(navigationKeys(.init(y:65535),0.3).isEmpty,"repeat initial delay")
precondition(navigationKeys(.init(y:65535),0.46)==[40],"menu held repeat")
precondition(navigationKeys(.init(),0.5).isEmpty)
precondition(navigationKeys(.init(buttons:1),0.6)==[13],"A selects")
precondition(navigationKeys(.init(buttons:1),0.7).isEmpty,"A cannot repeat")
precondition(navigationKeys(.init(),0.8).isEmpty)
precondition(navigationKeys(.init(buttons:2),0.9,playing:true).isEmpty,"B gameplay stays in binding path")
precondition(navigationKeys(.init(buttons:2),1).isEmpty,"held attack cannot back out of new menu")
precondition(navigationKeys(.init(),1.1).isEmpty)
precondition(navigationKeys(.init(buttons:2),1.2)==[27],"B backs")
precondition(navigationKeys(.init(),1.3,playing:true).isEmpty)
precondition(navigationKeys(.init(buttons:256),1.4,playing:true)==[27],"Menu pauses")
precondition(navigationKeys(.init(buttons:256),1.5).isEmpty,"held Menu cannot resume")
precondition(navigationKeys(nil,1.6,playing:true)==[27],"detach pauses")
precondition(navigationKeys(nil,1.7,playing:true).isEmpty,"detach pauses once")
precondition(navigationKeys(.init(),1.8).isEmpty,"neutral reconnect")
precondition(navigationKeys(nil,1.9).isEmpty,"menu detach does not leave menu")
print("{\"status\":\"pass\",\"cases\":\(rows.count),\"scope\":\"Fresh original/native controller, mouse, modes and binding comparisons; physical APIs scripted, hardware acceptance separate\"}")
