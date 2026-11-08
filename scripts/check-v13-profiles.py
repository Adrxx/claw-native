#!/usr/bin/env python3
"""Run actual native profile join methods with a recording platform transport.

This checks request order and UI state, including failed persistence. It is not
an original-instruction comparison, canonical admission, or live UI acceptance.
"""
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def section(text, start, end):
    return text.split(start, 1)[1].split(end, 1)[0]


def main():
    native = (ROOT / 'Sources/ClawNativeMenuInterface.swift').read_text()
    app = (ROOT / 'App/ClawApp.swift').read_text()
    methods = '    private func savePlayers() throws {' + section(
        native, '    private func savePlayers() throws {', '    struct ControlAction {')
    startup = '    private func selectStoredPlayer(_ profiles:UInt32)->UInt32 {' + section(
        native, '    private func selectStoredPlayer(_ profiles:UInt32)->UInt32 {',
        '    /// Original startup\'s stored sound and display options')
    presentation = '    struct PlayersState {' + section(
        app, '    struct PlayersState {', '    static func controlKeyName(')
    presentation = presentation.replace('@Published ', '')
    source = r'''
import Foundation
@_silgen_name("claw_v13_profile_close_result")
func claw_v13_profile_close_result(_ cancelled: UInt32) -> UInt32
struct ClawNativeMenuResources {
    enum Failure:Error {case invalid(String)}
}
final class Memory {
    var blocks:[UInt32:UnsafeMutablePointer<UInt8>] = [:]
    var sizes:[UInt32:UInt32] = [:]
    var next:UInt32 = 0x100000
    func allocate(_ size:UInt32)->UInt32 {
        let result = next;next += size+16
        let ptr = UnsafeMutablePointer<UInt8>.allocate(capacity:Int(size));ptr.initialize(repeating:0,count:Int(size))
        blocks[result] = ptr;sizes[result] = size;return result
    }
    func lookupBytes(_ token:UInt32,count:UInt32)->UnsafeMutablePointer<UInt8>? {
        for (start,p) in blocks where token >= start && token+count <= start+sizes[start]! {return p.advanced(by:Int(token-start))}
        return nil
    }
    func text(_ token:UInt32)->String {
        let staticText:[UInt32:String] = [0x5255e8:"Player",0x534938:"",0x52560c:"User Name",0x5255fc:"User Location",0x5255f0:"User Email"]
        if let value = staticText[token] {return value}
        guard let p = lookupBytes(token,count:1) else {return ""}
        return String(cString:p)
    }
    func write(_ text:String,_ token:UInt32,_ capacity:UInt32) {
        guard let p = lookupBytes(token,count:capacity) else {fatalError("bad buffer")}
        let bytes = Array(text.utf8.prefix(Int(capacity)-1))+[0]
        for (index,byte) in bytes.enumerated() {p[index] = byte}
    }
    deinit {for p in blocks.values {p.deallocate()}}
}
final class Settings {
    var values:[String:String] = [:]
    func text(_ key:String)->String? {values[key]}
}
final class Input {func releaseMenuKeys() {}}
struct Base {let applicationToken:UInt32 = 0x7000;var windowInput:Input? = Input()}
final class Transport {
    unowned let host:ClawNativeMenuInterface
    var fault:UInt32 = 0,faultAddress:UInt32 = 0
    var failCreate = false,failSave = false
    var events:[String] = []
    var saved:[ClawNativeMenuInterface.PlayerChoice] = []
    var nextRecord:UInt32 = 100
    init(_ host:ClawNativeMenuInterface) {self.host = host}
    func allocate(_ n:UInt32)->UInt32 {host.heap.allocate(n)}
    func textToken(_ text:String)->UInt32 {
        let n = UInt32(text.utf8.count+1),p = allocate(n);host.heap.write(text,p,n);return p
    }
    func release(_ token:UInt32) {}
    func invoke(_ address:UInt32,_ this:UInt32,_ args:[UInt32] = [])->UInt32 {
        switch address {
        case 0x49bbc0:
            events.append("save");if !failSave {saved = host.playerChoices};return failSave ? 0:1
        case 0x42bf90:
            events.append("select:\(args[0])");host.put(host.base.applicationToken+0x64,args[0]);return 0
        case 0x49bee0:
            let name = host.heap.text(args[0]);events.append("find:\(name)")
            return host.playerChoices.first{$0.name.lowercased() == name.lowercased()}?.id ?? 0
        case 0x49bdb0:
            let name = host.heap.text(args[0]);events.append("create:\(name)")
            if failCreate || host.playerChoices.contains(where:{$0.name.lowercased() == name.lowercased()}) {return 0}
            nextRecord += 1
            host.playerChoices.append(.init(id:nextRecord,name:name,location:host.heap.text(args[1]),email:host.heap.text(args[2])))
            return nextRecord
        case 0x49bf30:
            events.append("remove:\(args[0])");host.playerChoices.removeAll{$0.id == args[0]};return 1
        case 0x4b5e90:
            let key = host.heap.text(args[0]);events.append("read:\(key)")
            host.heap.write(host.settings?.text(key) ?? "",args[1],host.w(args[2]));return 1
        case 0x4b5f80:
            let key = host.heap.text(args[0]);events.append("delete:\(key)");host.settings?.values.removeValue(forKey:key);return 1
        default:fatalError("unexpected entry \(String(address,radix:16))")
        }
    }
}
final class ClawNativeMenuInterface {
    struct PlayerChoice:Identifiable {let id:UInt32;let name:String;let location:String;let email:String}
    var base = Base(),heap = Memory(),settings:Settings? = Settings()
    lazy var resources = Transport(self)
    var playerChoices:[PlayerChoice] = [.init(id:1,name:"Player",location:"",email:"")]
    var words:[UInt32:UInt32] = [0x7064:1]
    var profileManagerToken:UInt32 = 0x8000,configuration:UInt32 = 1
    var saveFiles:Int? = 1
    var nativeStartupBlocks:[UInt32] = [],startupSettings:[UInt32:UInt32] = [:]
    var playersActive = true
    var selectedPlayer:UInt32 {w(base.applicationToken+0x64)}
    func w(_ p:UInt32)->UInt32 {words[p] ?? 0}
    func put(_ p:UInt32,_ value:UInt32) {words[p] = value}
    func importMetadata()->UInt32 {selectStoredPlayer(profileManagerToken)}
''' + methods + startup + r'''
}
final class Presentation {
    var owner:ClawNativeMenuInterface?
    init(_ owner:ClawNativeMenuInterface) {
        self.owner = owner;players = PlayersState(choices:owner.playerChoices,selected:owner.selectedPlayer)
    }
    func key(_ key:UInt32) {_ = playersKey(key,down:true)}
''' + presentation + r'''
}
var checks = 0
func check(_ condition:Bool,_ label:String) {precondition(condition,label);checks += 1}
func rejected(_ name:String,_ location:String,_ comment:String) {
    let host = ClawNativeMenuInterface()
    do {_ = try host.createPlayer(name:name,location:location,email:comment);fatalError("accepted invalid field")}
    catch {check(host.resources.events.isEmpty,"validation must precede mutation")}
}
rejected("","L","");rejected("N","","")
rejected(String(repeating:"n",count:16),"L","")
rejected("N",String(repeating:"l",count:64),"")
rejected("N","L",String(repeating:"c",count:64))
do {
    let host = ClawNativeMenuInterface()
    let record = try host.createPlayer(name:String(repeating:"n",count:15),location:String(repeating:"l",count:63),email:String(repeating:"c",count:63))
    check(host.resources.events == ["create:"+String(repeating:"n",count:15),"select:\(record)","save"],"create/select/save order")
    check(host.resources.saved.first(where:{$0.id == record})?.email.count == 63,"comment capacity")
    host.resources.events = []
    try host.selectPlayer(1)
    check(host.resources.events == ["select:1"],"selection does not request save")
    host.finishPlayerDialog(cancelled:true)
    check(host.selectedPlayer == 1 && host.w(0x52545c) == 2,"cancel keeps selection")
}
for failCreate in [false,true] {
    let host = ClawNativeMenuInterface();host.resources.failCreate = failCreate;host.resources.failSave = true
    let ui = Presentation(host);ui.playerAction("new");ui.players?.name = "NEW";ui.players?.location = "L"
    ui.playerAction("create")
    check(ui.players?.page == 0 && ui.players?.error == nil,"create/save failure still closes child")
    check(host.resources.events.last == "save","creation failure still requests save")
    check(host.selectedPlayer == (failCreate ? 1:101),"creation failure preserves selection")
    check(host.resources.saved.isEmpty,"failed write not confused with persistence")
    check(host.w(0x52545c) == 1,"create closes successfully")
}
do {
    let host = ClawNativeMenuInterface(),ui:Presentation
    _ = try host.createPlayer(name:"NEW",location:"L",email:"")
    ui = Presentation(host);ui.playerAction("new");ui.players?.name = "NEW";ui.players?.location = "Other"
    host.resources.events = [];ui.playerAction("create")
    check(host.resources.events == ["create:NEW","save"],"duplicate still requests save and does not select")
    check(ui.players?.page == 0 && ui.players?.error == nil,"duplicate closes")
    check(host.playerChoices.last?.location == "L","duplicate preserves record")
}
for missingPlayer in [false,true] {
    let host = ClawNativeMenuInterface()
    let record = try host.createPlayer(name:"REMOVE",location:"L",email:"")
    if missingPlayer {host.playerChoices.removeAll{$0.name == "Player"}}
    host.resources.events = [];try host.removePlayer(record)
    let prefix = ["find:Player","select:\(missingPlayer ? 0:1)","remove:\(record)","save"]
    let suffix = missingPlayer ? ["find:Player","select:0","create:Player","select:102"]:[]
    check(host.resources.events == prefix+suffix,"remove/save/fallback repair order")
    check(host.playerChoices.count == 1 && host.playerChoices[0].name == "Player","fallback repaired")
    check(host.resources.saved.count == (missingPlayer ? 0:1),"fallback creation occurs after persisted bytes")
}
do {
    let host = ClawNativeMenuInterface();try host.removePlayer(1)
    check(host.resources.events.isEmpty,"reserved Player protected")
    let record = try host.createPlayer(name:"REMOVE",location:"L",email:"")
    try host.selectPlayer(1);host.resources.events = [];host.resources.failSave = true
    try host.removePlayer(record)
    check(host.resources.events == ["remove:\(record)","save"],"unselected removal ignores save failure")
    check(host.selectedPlayer == 1 && host.playerChoices.count == 1,"removal not rolled back")
}
do {
    let host = ClawNativeMenuInterface();_ = try host.createPlayer(name:"NEW",location:"L",email:"")
    let ui = Presentation(host);host.resources.events = [];ui.key(38)
    check(host.selectedPlayer == 1 && host.resources.events == ["select:1"],"arrow immediately selects")
    ui.key(27)
    check(ui.players == nil && host.selectedPlayer == 1 && host.w(0x52545c) == 2,"Escape keeps immediate selection")
    let other = Presentation(host);other.key(13)
    check(other.players == nil && host.w(0x52545c) == 1,"Return closes normally")
}
do {
    let host = ClawNativeMenuInterface();_ = try host.createPlayer(name:"NEW",location:"L",email:"")
    let ui = Presentation(host);ui.playerAction("remove");ui.key(78)
    check(ui.players?.page == 0 && host.playerChoices.count == 2 && host.w(0x52545c) == 2,"N cancels removal")
    ui.playerAction("remove");ui.key(89)
    check(ui.players?.page == 0 && host.playerChoices.count == 1 && host.w(0x52545c) == 1,"Y confirms removal")
    ui.playerAction("new")
    for _ in 0..<20 {ui.key(65)}
    ui.key(9);for _ in 0..<70 {ui.key(66)}
    ui.key(9);for _ in 0..<70 {ui.key(67)}
    check(ui.players?.name.count == 15 && ui.players?.location.count == 63 && ui.players?.email.count == 63,"keyboard field limits")
}
for legacyOnly in [false,true] {
    let host = ClawNativeMenuInterface()
    host.settings?.values = ["User Name":"INSTALL","User Location":"L","User Email":"OLD"]
    if !legacyOnly {host.settings?.values["User Comment"] = "COMMENT"}
    let player = host.importMetadata()
    check(host.playerChoices.first(where:{$0.id == player})?.email == (legacyOnly ? "":"COMMENT"),"metadata only reads Comment")
    check(host.settings?.text("User Email") == "OLD","Email untouched")
    check(host.resources.events.filter{$0.hasPrefix("read:")} == ["read:User Name","read:User Location","read:User Comment"],"metadata read keys")
    check(host.settings?.text("User Comment") == nil && host.settings?.text("User Name") == nil,"imported keys removed")
}
do {
    let host = ClawNativeMenuInterface();host.settings?.values = ["User Email":"OLD"]
    check(host.importMetadata() == 0 && host.resources.events.isEmpty,"old key alone is not import metadata")
    let record = try host.createPlayer(name:"EXISTING",location:"L",email:"keep")
    host.settings?.values = ["User Name":"EXISTING","User Location":"overwrite","User Comment":"overwrite"]
    check(host.importMetadata() == record && host.playerChoices.last?.email == "keep","existing metadata profile preserves text")
    host.startupSettings[0x525714] = host.resources.textToken("Player")
    host.settings?.values = ["User Name":"SHOULDNOTIMPORT","User Comment":"C"]
    host.resources.events = []
    check(host.importMetadata() == 1 && host.settings?.text("User Name") == "SHOULDNOTIMPORT","last User bypasses metadata import")
    check(!host.resources.events.contains(where:{$0.hasPrefix("read:")}),"valid last User avoids metadata reads")
}
do {
    setenv("CLAW_GAME_VERSION","1.0",1)
    defer {unsetenv("CLAW_GAME_VERSION")}
    let host = ClawNativeMenuInterface()
    host.settings?.values = ["User Name":"LEGACY","User Location":"L","User Email":"EMAIL","User Comment":"KEEP"]
    let record = host.importMetadata()
    check(host.playerChoices.first(where:{$0.id == record})?.email == "EMAIL","v1.0 imports Email")
    check(host.settings?.text("User Comment") == "KEEP","v1.0 leaves Comment untouched")
    check(host.resources.events.filter{$0.hasPrefix("read:")} == ["read:User Name","read:User Location","read:User Email"],"v1.0 metadata read keys")
    check(host.settings?.text("User Email") == nil,"v1.0 removes imported Email")
}
print("native profile join checks: \(checks)")
'''
    with tempfile.TemporaryDirectory(prefix='claw-profile-join-') as temporary:
        folder = Path(temporary)
        swift = folder / 'main.swift'
        swift.write_text(source)
        binary = folder / 'check'
        objects = []
        for name in ('V13ProfilesRuntime', 'V13ProfilesAdapter'):
            obj = folder / (name + '.o')
            subprocess.run(['clang++', '-std=c++17', '-O2', '-I', str(ROOT/'Sources'),
                            '-c', str(ROOT/'Sources'/(name+'.cpp')), '-o', str(obj)], check=True)
            objects.append(str(obj))
        subprocess.run(['xcrun', 'swiftc', str(swift), *objects, '-lc++', '-o', str(binary)], check=True)
        result = subprocess.run([str(binary)], check=True, text=True, capture_output=True)
    print(json.dumps({'check': 'v13_native_profile_join', 'status': 'pass',
                      'result': result.stdout.strip(),
                      'scope': 'Actual Swift methods with recording transport; no original comparison or live UI acceptance'}))


if __name__ == '__main__':
    main()
