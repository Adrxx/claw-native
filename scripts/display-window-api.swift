// Task-local native window API probe. Only the explicit test PID is touched.
import AppKit
import ApplicationServices
let args=CommandLine.arguments
let pid=pid_t(args[1])!
guard let app=NSRunningApplication(processIdentifier:pid) else {fatalError("missing test app")}
let target=AXUIElementCreateApplication(pid)
func windows()->[AXUIElement] {
 var value:CFTypeRef?
 guard AXUIElementCopyAttributeValue(target,kAXWindowsAttribute as CFString,&value) == .success else {return []}
 return value as? [AXUIElement] ?? []
}
func mini(_ window:AXUIElement)->Bool {
 var value:CFTypeRef?;AXUIElementCopyAttributeValue(window,kAXMinimizedAttribute as CFString,&value)
 return value as? Bool ?? false
}
switch args[2] {
case "hide":app.hide()
case "show":app.unhide();app.activate(options:[])
case "minimize":
 guard AXIsProcessTrusted(),let w=windows().first else {fatalError("window Accessibility unavailable")}
 guard AXUIElementSetAttributeValue(w,kAXMinimizedAttribute as CFString,kCFBooleanTrue) == .success else {fatalError("minimize failed")}
case "restore":
 guard AXIsProcessTrusted(),let w=windows().first else {fatalError("window Accessibility unavailable")}
 guard AXUIElementSetAttributeValue(w,kAXMinimizedAttribute as CFString,kCFBooleanFalse) == .success else {fatalError("restore failed")}
 app.activate(options:[])
case "snapshot":break
default:fatalError("unknown action")
}
RunLoop.current.run(until:Date().addingTimeInterval(0.25))
let result:[String:Any] = ["pid":pid,"active":app.isActive,"hidden":app.isHidden,"minimized":windows().map{mini($0)},"trusted":AXIsProcessTrusted()]
print(String(data:try! JSONSerialization.data(withJSONObject:result,options:[.sortedKeys]),encoding:.utf8)!)
