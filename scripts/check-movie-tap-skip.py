"""Execute the app's iPad/Catalyst touch handlers without a simulator.

Only UIKit event objects and the playback endpoint are stand-ins. The actual
key handler decides skip flags/result, and the actual touch methods route a
whole gesture, including releases after a transition. Real movie/state behavior
is checked separately by check-movie-skip.py and check-movie-flows.py.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'work/movie-tap-skip'
OUT.mkdir(parents=True, exist_ok=True)
app = (ROOT / 'App/ClawApp.swift').read_text()


def method(signature):
    start = app.index(signature)
    brace = app.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (app[end] == '{') - (app[end] == '}')
        end += 1
    return app[start:end]


key = method('    func key(_ key: UInt32,')
touches = '\n'.join(method('        override func ' + name + '(')
                    for name in ['touchesBegan', 'touchesMoved', 'touchesEnded', 'touchesCancelled'])
# Compile both production conditional branches on the host, without UIKit.
touches = touches.replace('targetEnvironment(macCatalyst)', 'TEST_CATALYST')
source = r'''
import Foundation
class UIEvent {}
class UITouch: Hashable {
    let point: CGPoint
    init(_ x: Double, _ y: Double) { point = CGPoint(x:x,y:y) }
    func location(in view: UIView) -> CGPoint { point }
    static func == (a: UITouch,b: UITouch) -> Bool { a === b }
    func hash(into h: inout Hasher) { h.combine(ObjectIdentifier(self)) }
}
class UIView {
    func becomeFirstResponder() {}
    func touchesBegan(_ t: Set<UITouch>, with e: UIEvent?) {}
    func touchesMoved(_ t: Set<UITouch>, with e: UIEvent?) {}
    func touchesEnded(_ t: Set<UITouch>, with e: UIEvent?) {}
    func touchesCancelled(_ t: Set<UITouch>, with e: UIEvent?) {}
}
enum Message: String { case primaryDown, primaryUp, mouseMove }
class Playback {
    var movieID: UInt32? = nil
    var skips = 0
    func skip() { skips += 1 }
}
class Queue { func menuKey(_ k: UInt32, down: Bool, repeatKey: Bool) { preconditionFailure("key leaked") } }
class Base { var windowInput: Queue? = Queue() }
class Owner { var base = Base() }
class Menu {
    var movieActive = true, movieFlags: UInt32 = 1, movieSkipResult: UInt32 = 99
    let moviePlayback = Playback()
    var movieStarted = 0.0, movieRecords: [[String:Any]] = []
    var players: Int? = nil, owner: Owner? = Owner()
    var accepted = true
    func acceptInput(_ e: [String:Any], fromScript: Bool) -> Bool { accepted }
    func observeInput(_ e: [String:Any]) {}
    func playersKey(_ k: UInt32,down: Bool,fromScript: Bool) -> Bool { false }
    func controlsKey(_ k: UInt32,down: Bool,repeatKey: Bool) -> Bool { false }
    var live: [Bool] = []
    func liveInputArrived(_ k: UInt32,down: Bool) { live.append(down) }
''' + key + r'''
}
class Input: UIView {
    let menu: Menu
    var movieTouches: Set<UITouch> = []
    var sent: [Message] = []
    init(_ menu: Menu) { self.menu = menu }
    func send(_ m: Message, at p: CGPoint) { sent.append(m) }
''' + touches + r'''
}
var cases = 0
for movie: UInt32 in 1...10 {
 for flags: UInt32 in [0,1,0x100,0x101] {
  // Interior and every margin: touch-to-key routing does not clip to 4:3.
  for point in [(0.0,0.0),(1365,0),(0,1023),(1365,1023),(683,512)] {
   let tapMenu = Menu(), keyMenu = Menu()
   for m in [tapMenu,keyMenu] { m.movieFlags=flags; m.moviePlayback.movieID=movie }
   let input=Input(tapMenu), touch=UITouch(point.0,point.1)
   input.touchesBegan([touch],with:nil)
   #if TEST_CATALYST
   precondition(input.sent == [.primaryDown] && tapMenu.moviePlayback.skips == 0)
   input.touchesMoved([touch],with:nil); input.touchesEnded([touch],with:nil)
   precondition(input.sent == [.primaryDown,.mouseMove,.primaryUp])
   #else
   keyMenu.key(0,down:true)
   precondition(tapMenu.moviePlayback.skips == keyMenu.moviePlayback.skips)
   precondition(tapMenu.movieSkipResult == keyMenu.movieSkipResult)
   precondition(tapMenu.moviePlayback.skips == (flags & 1 != 0 ? 1 : 0))
   // Playback may have already advanced to another movie or to the menu.
   tapMenu.movieActive=false
   input.touchesMoved([touch],with:nil)
   input.touchesEnded([touch],with:nil)
   precondition(input.sent.isEmpty && input.movieTouches.isEmpty)
   precondition(tapMenu.live == [true])
   // Normal touch input resumes immediately after lifting the skip finger.
   input.touchesBegan([touch],with:nil); input.touchesEnded([touch],with:nil)
   precondition(input.sent == [.primaryDown,.primaryUp])
   #endif
   cases += 1
  }
 }
}
#if !TEST_CATALYST
for cancelled in [false,true] {
 let menu=Menu(), input=Input(menu), a=UITouch(0,0), b=UITouch(100,100)
 menu.moviePlayback.movieID=2
 input.touchesBegan([a],with:nil)
 // Another finger in the same gesture must not skip the next queued movie.
 menu.moviePlayback.movieID=3
 input.touchesBegan([b],with:nil)
 input.touchesEnded([a],with:nil)
 if cancelled { input.touchesCancelled([b],with:nil) }
 else { input.touchesEnded([b],with:nil) }
 precondition(menu.moviePlayback.skips == 1 && input.sent.isEmpty && input.movieTouches.isEmpty)
 input.touchesBegan([a],with:nil)
 precondition(menu.moviePlayback.skips == 2)
 cases += 1
}
let denied=Menu(); denied.accepted=false
let deniedInput=Input(denied)
deniedInput.touchesBegan([UITouch(0,0)],with:nil)
precondition(denied.moviePlayback.skips == 0)
cases += 1
#endif
print("checked \(cases)")
'''
# Ensure the storage under test is present and the input overlay covers the
# complete window independently of the aspect-fitted movie, with no Skip button.
assert 'private var movieTouches: Set<UITouch> = []' in app
view = app[app.index('struct ClawMainMenuView:'):app.index('// Native modal surfaces')]
assert 'allowsSkipping: false' in view and '.ignoresSafeArea()' in view
assert view.index('ClawMenuInputView(menu: menu)') > view.index('.aspectRatio(4.0 / 3.0')
(OUT / 'check.swift').write_text(source)
load = float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1])
assert load < 16, f'wait for load below 16: {load}'
results = {}
for name, flags in [('ipad', []), ('catalyst', ['-DTEST_CATALYST'])]:
    binary = OUT / name
    subprocess.run(['xcrun','swiftc','-O',*flags,str(OUT/'check.swift'),'-o',str(binary)],check=True)
    results[name] = subprocess.check_output([str(binary)],text=True).strip()
result = dict(check='movie-tap-skip',status='pass',branches=results,
              movie_ids=list(range(1,11)),simulator=False)
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
