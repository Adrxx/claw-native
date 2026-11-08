// Real pointer input for one audit-owned window, in original 640 x 480 coordinates.
import AppKit
import CoreGraphics
let args = CommandLine.arguments
guard args.count == 4, let pid = pid_t(args[1]), let x = Double(args[2]), let y = Double(args[3]),
      let app = NSRunningApplication(processIdentifier:pid) else {exit(2)}
app.activate(options:[])
usleep(200000)
guard NSWorkspace.shared.frontmostApplication?.processIdentifier == pid else {exit(3)}
let windows = CGWindowListCopyWindowInfo([.optionOnScreenOnly,.excludeDesktopElements],0) as! [[String:Any]]
let boxes = windows.filter {($0[kCGWindowOwnerPID as String] as? Int) == Int(pid) && ($0[kCGWindowLayer as String] as? Int) == 0}
    .compactMap {($0[kCGWindowBounds as String] as? NSDictionary).flatMap {CGRect(dictionaryRepresentation:$0)}}
guard let box = boxes.filter({$0.height > 100}).max(by:{$0.width*$0.height < $1.width*$1.height}) else {exit(4)}
let scale = min(box.width/640,(box.height-28)/480)
let point = CGPoint(x:box.midX+(x-320)*scale,y:box.minY+28+(box.height-28)/2+(y-240)*scale)
let source = CGEventSource(stateID:.hidSystemState)
for type in [CGEventType.mouseMoved,.leftMouseDown,.leftMouseUp] {
    guard NSWorkspace.shared.frontmostApplication?.processIdentifier == pid else {exit(5)}
    let event = CGEvent(mouseEventSource:source,mouseType:type,mouseCursorPosition:point,mouseButton:.left)!
    event.setIntegerValueField(.mouseEventClickState,value:1)
    event.post(tap:.cghidEventTap)
    usleep(100000)
}
