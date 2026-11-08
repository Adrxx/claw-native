import Foundation
import Darwin

func check(_ value: Bool, _ message: String) {
    if !value { fatalError(message) }
}
final class Fixture {
    let heap = ClawTokenHeap()
    lazy var provider = ClawNativeMovieStateServices(heap: heap, closeFile: { [unowned self] file in
        if self.badClose { throw ClawNativeMovieStateServices.Failure.close }
        try file.close()
    })
    let outer: UInt32
    var movie: UInt32 { outer + 0x534 }
    let app: UInt32
    let array: UInt32
    let file: FileHandle
    let fd: Int32
    let hostPointer = UnsafeMutablePointer<ClawHost>.allocate(capacity: 1)
    var host: ClawHost {
        get { hostPointer.pointee }
        set { hostPointer.pointee = newValue }
    }
    deinit { hostPointer.deinitialize(count: 1); hostPointer.deallocate() }
    var events: [(UInt32, UInt32, [UInt32], [UInt32])] = []
    var allCalls: [UInt32] = []
    var missing: UInt32 = 0
    var badClose = false
    var badReset = false
    var bindOwner = true
    var seed: [UInt32] = []
    var prepared = false
    var w: UnsafeMutablePointer<UInt32> { heap.lookup(movie, words: 0x14c / 4)! }

    init(initialized: UInt32, a: UInt32, b: UInt32) throws {
        hostPointer.initialize(to: ClawHost())
        outer = heap.allocate(bytes: 0x86a8)
        app = heap.allocate(bytes: 0x200)
        array = heap.allocate(bytes: 12)
        file = try FileHandle(forReadingFrom: URL(fileURLWithPath: "/dev/null"))
        fd = file.fileDescriptor
        seed = [initialized, a, b]
        let vt = heap.store(token: 0x510844, words: 22)
        vt[21] = 0x4f766e
        let ap = heap.lookup(app, words: 0x200 / 4)!
        ap[0x9c / 4] = 1
        let scene = heap.allocate(bytes: 40), holder = heap.allocate(bytes: 28)
        let target = heap.allocate(bytes: 48), palette = heap.allocate(bytes: 4)
        ap[48 / 4] = scene
        heap.lookup(scene, words: 10)![1] = holder
        heap.lookup(scene, words: 10)![7] = palette
        heap.lookup(holder, words: 7)![4] = target // Null target +44 selects cleanMovie.
        // Exact source constructor metadata needed by the cleanup owner.
        prepareWords()
        host.user = Unmanaged.passUnretained(self).toOpaque()
        host.bytes = { user, token, count in
            guard let user else { return nil }
            return Unmanaged<Fixture>.fromOpaque(user).takeUnretainedValue().heap.lookupBytes(token, count: count)
        }
        host.call = { user, call in
            guard let user, let call else { return 0 }
            return Unmanaged<Fixture>.fromOpaque(user).takeUnretainedValue().call(call.pointee)
        }
    }
    func prepareWords() {
        w[0] = seed[0]; w[1] = seed[1]; w[2] = seed[2]
        w[0x124 / 4] = 0x510844; w[0x128 / 4] = 0x70000001
        w[0x12c / 4] = 1; w[0x130 / 4] = 0x52e1c4
        w[0x134 / 4] = 0xabcdef01
        w[0x138 / 4] = 0x5107e0; w[0x13c / 4] = array
        w[0x140 / 4] = 2; w[0x144 / 4] = 3; w[0x148 / 4] = 17
    }
    func prepare() throws {
        guard !prepared else { return }
        prepared = true
        prepareWords()
        if bindOwner { try provider.bind(movie: movie, file: file, array: array, arrayBytes: 12) }
        if badReset { heap.free(array) }
    }
    func call(_ call: ClawCall) -> UInt32 {
        allCalls.append(call.function)
        let args = withUnsafeBytes(of: call.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(call.argumentCount))) }
        if call.function == 0x4f766e || call.function == 0x4f5915 {
            events.append((call.function, call.receiver, args, [w[0], w[1], w[2], w[0x134 / 4]]))
            if missing == call.function { host.fault = UInt32(CLAW_FAULT_HOST); return 0 }
            do { return try provider.service(call.function, receiver: call.receiver, arguments: args) }
            catch { host.fault = UInt32(CLAW_FAULT_HOST); return 0 }
        }
        switch call.function {
        case 0x48c190: return 1 // Finite caller prefix service.
        case 0x4f0120:
            do { try prepare() } catch { host.fault = UInt32(CLAW_FAULT_HOST) }
            return 0
        case 0x4f72c9, 0x4f57c5, 0x4a3b10, 0x4a3040,
             0x4f57f8, 0x4f7369: return 0 // Unrelated constructor/destructor physical boundary.
        default: fatalError("unexpected dependency \(String(call.function, radix: 16))")
        }
    }
    func run(_ kind: Int, stop: Bool = false) throws -> (UInt32, UInt32) {
        if kind == 0 { try prepare() }
        var result: UInt32 = 0xcccccccc
        let done: UInt32
        // Use a pointer to stored host memory: service callbacks publish the same fault.
        done = { (h: UnsafeMutablePointer<ClawHost>) in
            if kind == 0 {
                return claw_movie_state_cleanup_entry(stop ? 0x4efd00 : 0x4efcd0, movie, nil, 0, h, &result)
            }
            return movie_test_caller(kind == 1 ? 0 : 1, kind == 1 ? outer : app, outer, h, &result)
        }(hostPointer)
        return (done, result)
    }
}
var checks = 0
for kind in 0...2 {
    for initialized: UInt32 in [0, 7] {
        for a: UInt32 in [0, 0x80000000] {
            for b: UInt32 in [0, 3] {
                let f = try Fixture(initialized: initialized, a: a, b: b)
                let (done, _) = try f.run(kind)
                check(done == 1 && f.host.fault == 0, "cleanup completed")
                let active = initialized != 0 && (a != 0 || b != 0)
                check(f.events.map { $0.0 } == (initialized == 0 ? [] : active ? [0x4f766e, 0x4f5915] : [0x4f5915]), "service order")
                if active {
                    let e = f.events[0]
                    check(e.1 == f.movie + 0x124 && e.2.isEmpty && e.3 == [initialized, a, b, 0xabcdef01], "close before game stores")
                    check(f.w[1] == 0 && f.w[2] == 0 && f.w[0x134 / 4] == 0, "active cleared")
                    check(fcntl(f.fd, F_GETFD) == -1 && errno == EBADF, "actual native descriptor closed")
                } else {
                    check(f.w[1] == a && f.w[2] == b && f.w[0x134 / 4] == 0xabcdef01, "false stop preserves fields")
                }
                if initialized != 0 {
                    let e = f.events.last!
                    check(e.1 == f.movie + 0x138 && e.2 == [0, .max], "array receiver and arguments")
                    check(e.3[0] == initialized && e.3[1] == 0 && e.3[2] == 0, "reset before initialized clear")
                    check(f.heap.lookup(f.array, words: 1) == nil && f.w[0x13c / 4] == 0 && f.w[0x140 / 4] == 0 && f.w[0x144 / 4] == 0, "native array freed and reset")
                }
                check(f.w[0] == 0 && f.w[0x148 / 4] == 17, "initialized clear and growth preserved")
                let count = f.events.count
                // Repeating the cleanup entry does not reconstruct or reopen a movie.
                check(try f.run(0).0 == 1, "repeat completed")
                check(f.events.count == count, "repeat has no physical effects")
                checks += 1
            }
        }
    }
}
for initialized: UInt32 in [0, 5] {
    for a: UInt32 in [0, 9] {
        for b: UInt32 in [0, 1] {
            let f = try Fixture(initialized: initialized, a: a, b: b)
            let (done, result) = try f.run(0, stop: true)
            check(done == 1 && result == (initialized != 0 && (a != 0 || b != 0) ? 1 : 0), "exact boolean contract")
            check(f.w[0] == initialized && f.heap.lookup(f.array, words: 1) != nil, "stop does not reset initialized or array")
            check(try f.run(0, stop: true).1 == 0, "repeated stop is false")
            checks += 1
        }
    }
}
for kind in 0...2 {
    for failure in 0...4 {
        let f = try Fixture(initialized: 2, a: 3, b: 4)
        if failure == 0 { f.bindOwner = false }
        if failure == 1 { f.badClose = true }
        if failure == 2 { f.badReset = true }
        if failure == 3 { f.missing = 0x4f766e }
        if failure == 4 { f.missing = 0x4f5915 }
        let (done, result) = try f.run(kind)
        check(done == 0 && f.host.fault != 0 && result == 0xcccccccc, "fault is not returned game value kind=\(kind) failure=\(failure) done=\(done) fault=\(f.host.fault) result=\(result)")
        check(f.w[0] == 2, "failure retains initialized")
        let afterClose = failure == 2 || failure == 4
        check(f.w[1] == (afterClose ? 0 : 3) && f.w[2] == (afterClose ? 0 : 4), "failure game-store prefix")
        check(f.events.map { $0.0 } == (afterClose ? [0x4f766e, 0x4f5915] : [0x4f766e]), "failure call prefix")
        check(!f.allCalls.contains(0x4f57f8) && !f.allCalls.contains(0x4f7369), "caller stops before later destructors")
        if failure == 1 { check(f.w[0x128 / 4] == .max && f.w[0x12c / 4] == 0, "close failure retains platform mutations") }
        checks += 1
    }
}
// Missing array owner with false stop still faults, without initialized clear.
let inactive = try Fixture(initialized: 1, a: 0, b: 0)
inactive.bindOwner = false
check(try inactive.run(0).0 == 0 && inactive.w[0] == 1 && inactive.events.map { $0.0 } == [0x4f5915], "false stop still requires array owner")
checks += 1
// The shipping Swift entry uses its own canonical host and semantic APIs.
for active in [false, true] {
    let f = try Fixture(initialized: 1, a: active ? 2 : 0, b: 0)
    try f.prepare()
    check(try f.provider.stop(movie: f.movie) == active, "native stop API boolean")
    try f.provider.cleanup(movie: f.movie)
    try f.provider.cleanup(movie: f.movie)
    check(f.w[0] == 0 && f.w[0x13c / 4] == 0, "native cleanup API void")
    if active { try f.provider.retire(movie: f.movie) }
    checks += 1
}
// Constructor-empty native resources: no handle and no array allocation.
do {
    let f = try Fixture(initialized: 1, a: 1, b: 0)
    f.w[0x128 / 4] = .max
    f.w[0x13c / 4] = 0
    try f.provider.bind(movie: f.movie, file: nil, array: 0, arrayBytes: 0)
    try f.provider.cleanup(movie: f.movie)
    check(f.w[0] == 0 && f.w[1] == 0 && f.w[0x148 / 4] == 17, "empty physical resources")
    try f.provider.retire(movie: f.movie)
    checks += 1
}
func rejects(_ body: () throws -> Void) -> Bool {
    do { try body(); return false } catch { return true }
}
do {
    let f = try Fixture(initialized: 1, a: 1, b: 1)
    try f.prepare()
    check(rejects { _ = try f.provider.service(0x4f5915, receiver: f.movie + 0x138, arguments: [0, 0]) }, "reject grow mutation")
    check(rejects { _ = try f.provider.service(0x4f766e, receiver: f.movie + 0x128, arguments: []) }, "reject wrong receiver")
    check(rejects { _ = try f.provider.service(0x4f766e, receiver: f.movie + 0x124, arguments: [1]) }, "reject close arity")
    check(rejects { _ = try f.provider.service(0x4f766f, receiver: f.movie + 0x124, arguments: []) }, "reject unknown service")
    check(rejects { try f.provider.retire(movie: f.movie) }, "reject premature retirement")
    f.w[0x128 / 4] += 1
    check(rejects { try f.provider.cleanup(movie: f.movie) }, "reject replaced handle token")
    check(f.w[0] == 1 && f.w[1] == 1, "invalid ownership stops stores")
    checks += 6
}
// Reuse of an allocation address does not inherit a prior movie's ownership.
do {
    let f = try Fixture(initialized: 1, a: 1, b: 1)
    try f.prepare()
    f.heap.free(f.outer)
    _ = f.heap.store(token: f.outer, words: 0x86a8 / 4)
    f.prepareWords()
    check(rejects { try f.provider.cleanup(movie: f.movie) }, "reject replaced containing allocation")
    check(f.w[0] == 1 && f.w[1] == 1, "stale owner stops stores")
    checks += 1
}
// Two movies share the provider but never the underlying file/array ownership.
do {
    let f = try Fixture(initialized: 1, a: 1, b: 1)
    try f.prepare()
    let second = f.heap.allocate(bytes: 0x14c)
    let words = f.heap.lookup(second, words: 0x14c / 4)!
    words.update(from: f.w, count: 0x14c / 4)
    check(rejects { try f.provider.bind(movie: second, file: f.file, array: f.array, arrayBytes: 12) }, "reject shared physical ownership")
    let secondFile = try FileHandle(forReadingFrom: URL(fileURLWithPath: "/dev/null"))
    let secondFD = secondFile.fileDescriptor
    let data = f.heap.allocate(bytes: 12)
    words[0x13c / 4] = data
    try f.provider.bind(movie: second, file: secondFile, array: data, arrayBytes: 12)
    try f.provider.cleanup(movie: f.movie)
    check(words[0] == 1 && words[1] == 1 && f.heap.lookup(data, words: 1) != nil && fcntl(secondFD, F_GETFD) >= 0, "other movie untouched")
    try f.provider.cleanup(movie: second)
    check(words[0] == 0 && f.heap.lookup(data, words: 1) == nil, "second movie cleans independently")
    checks += 2
}
print("{\"command\":\"native-movie-state-join\",\"status\":\"pass\",\"profiles\":\(checks),\"callers\":[\"canonical\",\"application 0x42b520\",\"booty 0x42b140\"],\"playback_acceptance\":false}")
