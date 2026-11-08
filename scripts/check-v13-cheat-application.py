"""Check the app's quit/state-15 composition and source-owner handoffs."""
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/v13/application-native';OUT.mkdir(parents=True,exist_ok=True)
s=(ROOT/'Sources/ClawNativeMenuInterface.swift').read_text()
method=s[s.index('    private func v13ApplicationCommand('):s.index('    var v13CheatEvidence:')].replace('private func','func')
source='''import Foundation
final class Resources {
    var calls:[(UInt32,[UInt32])]=[]
    var state:UInt32=3,transition:UInt32=0
    func invoke(_ f:UInt32,_ r:UInt32,_ a:[UInt32]=[])->UInt32 {
        calls.append((f,a))
        if f==0x7000{return state}
        if f==0x428c40{return transition}
        return 1
    }
}
final class Owner {
    let resources=Resources()
    var memory:[UInt32:UInt32]=[0x102c:0x2000,0x2000:0x3000,0x3010:0x7000,0x109c:1,0x58010020:9999]
    func w(_ p:UInt32)->UInt32 {memory[p] ?? 0}
    func put(_ p:UInt32,_ v:UInt32){memory[p]=v}
'''+method+'''
}
var checked=0
for counter:UInt32 in [9999,1,0] {
 for state:UInt32 in [2,3,4,5] {
  for command:UInt32 in [0x8006,0x800f] {
   let o=Owner();o.put(0x58010020,counter);o.resources.state=state
   let result=o.v13ApplicationCommand(command,application:0x1000)
   if command==0x800f && (state==3 || state==4) {
    precondition(result==nil && o.w(0x58010020)==counter && o.resources.calls.count==1)
   } else if counter>0 {
    precondition(result==nil && o.w(0x58010020)==counter-1 && o.resources.calls.count==1)
   } else {
    precondition(result==1 && o.w(0x58010020)==0)
    precondition(o.resources.calls.map{$0.0}==(state==3 ? [0x7000,0x46bcf0,0x42abb0]:[0x7000,0x42abb0]))
   }
   checked+=1
  }
 }
}
for transition:UInt32 in [0,1] {
 let o=Owner();o.resources.transition=transition
 precondition(o.v13ApplicationCommand(0x80ac,application:0x1000)==1)
 precondition(o.resources.calls[0].0==0x428c40 && o.resources.calls[0].1==[15,1,0,0])
 if transition==0 {precondition(o.resources.calls[1].0==0x429e10 && o.resources.calls[1].1==[0x8005,0x44a])}
 else {precondition(o.resources.calls.count==1)}
 checked+=1
}
let normal=Owner();normal.put(0x109c,0)
precondition(normal.v13ApplicationCommand(0x8006,application:0x1000)==nil && normal.resources.calls.isEmpty)
print("{\\"status\\":\\"pass\\",\\"check\\":\\"v13-application-native\\",\\"cases\\":\\(checked+1)}")
'''
(OUT/'check.swift').write_text(source)
load=float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1]);assert load<16,load
subprocess.run(['xcrun','swiftc','-O',str(OUT/'check.swift'),'-o',str(OUT/'check')],check=True)
result=json.loads(subprocess.check_output([str(OUT/'check')],text=True))
(OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
