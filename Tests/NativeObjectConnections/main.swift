import Foundation
import Darwin
setbuf(stdout, nil)
// Usage: connection-tests DIRECTORY FAMILY. Only the selected family's
// comparison file is compiled with this runner; it defines runConnection.
let family = CommandLine.arguments[2]
guard let election = ClawNativeObjectConnections.elections.first(where: { $0.family == family }) else {
    FileHandle.standardError.write("Unelected object connection\n".data(using: .utf8)!); exit(2)
}
guard ClawNativeObjectConnections.resolve(election) != nil else {
    print("{\"command\": \"native-object-connection\", \"family\": \"\(family)\", \"status\": \"missing-implementation\", \"missing\": [\"@objc(\(election.adapter)) ClawNativeObjectAdapter subclass\"]}")
    exit(3)
}
let directory = URL(fileURLWithPath: CommandLine.arguments[1])
try runBridgeControls(directory)
try runConnection(directory)
print("Native \(family) scene comparison inputs and bridge controls generated")
