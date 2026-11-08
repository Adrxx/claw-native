"""Offline scheduling check for the app's actual tempo sequencer; no speakers."""
import json
import math
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/v13/tempo-native'
OUT.mkdir(parents=True,exist_ok=True)
s=(ROOT/'Sources/ClawNativeMenuMusic.swift').read_text()
sequencer=s[s.index('final class ClawMusicSequencer {'):s.index('/// The General MIDI synth:')]
source='''import Foundation
struct ClawXMIDISong {
    struct Message {var tick:Int;var status:UInt8;var data1:UInt8;var data2:UInt8}
    var messages:[Message];var ticks:Int
}
'''+sequencer+'''
let song=ClawXMIDISong(messages:(0...3).map{.init(tick:$0*120,status:0x90,data1:UInt8(60+$0),data2:100)},ticks:480)
var results:[[String:Any]]=[]
for (tempo,ms):(Double,UInt32) in [(150,2500),(75,2500),(100,1000)] {
    let sequencer=ClawMusicSequencer()
    sequencer.noteOnLog=[]
    sequencer.start(1,song:song,loops:1)
    sequencer.setTempo(1,percent:tempo,milliseconds:ms)
    for _ in 0..<80 {sequencer.render(frames:64,sampleRate:1000){_,_,_,_ in}}
    results.append(["tempo":tempo,"milliseconds":ms,"frames":sequencer.noteOnLog!.map{$0.frame}])
}
print(String(data:try! JSONSerialization.data(withJSONObject:results),encoding:.utf8)!)
'''
(OUT/'tempo.swift').write_text(source)
load=float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1]);assert load<16,load
subprocess.run(['xcrun','swiftc','-O',str(OUT/'tempo.swift'),'-o',str(OUT/'tempo')],check=True)
rows=json.loads(subprocess.check_output([str(OUT/'tempo')],text=True))
for row in rows:
    target=row['tempo']/100;duration=row['milliseconds']/1000
    def elapsed(t):
        r=min(t,duration)
        return r+(target-1)*r*r/(2*duration)+max(0,t-duration)*target
    expected=[]
    for tick in range(4):
        lo,hi=0,5.12
        for _ in range(60):
            mid=(lo+hi)/2
            if elapsed(mid)<tick:lo=mid
            else:hi=mid
        expected.append(math.ceil(hi*1000-1e-7))
    assert row['frames']==expected,(row,expected)
result={'status':'pass','check':'v13-tempo-offline','rows':rows,'note_ons':12,'speaker_output':False}
(OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
