import Foundation
import CoreGraphics

func require(_ condition: @autoclosure () -> Bool, _ message: String) {
    if !condition() { fatalError(message) }
}
func word(_ value: Int) -> UInt32 { UInt32(truncatingIfNeeded: value) }
func rect(_ values: [Int]) -> ClawSpriteRect {
    ClawSpriteRect(left: word(values[0]), top: word(values[1]), right: word(values[2]), bottom: word(values[3]))
}
func command(_ source: [Int], _ destination: [Int], _ fx: Int, _ fy: Int) -> ClawSpriteDrawCommand {
    var c = ClawSpriteDrawCommand()
    c.kind = 3; c.source = rect(source); c.destination = rect(destination)
    c.flipX = word(fx); c.flipY = word(fy)
    return c
}
func pixels(_ draw: ClawSceneDraw) -> Data {
    draw.image.dataProvider!.data! as Data
}
func equal(_ old: ClawSceneDraw?, _ fast: ClawSceneDraw?, _ label: String) {
    require((old == nil) == (fast == nil), "nil mismatch: \(label)")
    guard let a = old, let b = fast else { return }
    require(a.rect == b.rect && a.mirrored == b.mirrored && a.z == b.z &&
        a.planeIndex == b.planeIndex && a.tileID == b.tileID, "draw metadata: \(label)")
    require(a.image.width == b.image.width && a.image.height == b.image.height &&
        a.image.bitsPerComponent == b.image.bitsPerComponent && a.image.bitsPerPixel == b.image.bitsPerPixel &&
        a.image.bytesPerRow == b.image.bytesPerRow && a.image.bitmapInfo == b.image.bitmapInfo &&
        a.image.shouldInterpolate == b.image.shouldInterpolate && a.image.renderingIntent == b.image.renderingIntent,
        "image metadata: \(label)")
    require(pixels(a) == pixels(b), "RGBA differs: \(label)")
}
let root = URL(fileURLWithPath: CommandLine.arguments[1])
let palette = try Data(contentsOf: root.appendingPathComponent("LEVEL1/PALETTES/MAIN.PAL"))
var calls = 0, nilResults = 0
var retained: [(ClawSceneDraw, Data)] = []
func compare(_ pid: ClawSprite, _ c: ClawSpriteDrawCommand, _ viewport: CGSize, _ label: String) {
    autoreleasepool {
        let old = ClawIndexedDrawing.draw(pid, command: c, viewport: viewport, z: -37)
        let fast = ClawFastIndexedDrawing.draw(pid, command: c, viewport: viewport, z: -37)
        equal(old, fast, label)
        calls += 1; if fast == nil { nilResults += 1 }
        if calls % 211 == 0, let draw = fast { retained.append((draw, pixels(draw))) }
    }
}
var assets: [ClawSprite] = []
for directory in ["IMAGES", "LEVEL1", "GAME"] {
    let enumerator = FileManager.default.enumerator(at: root.appendingPathComponent(directory),
        includingPropertiesForKeys: nil)!
    let urls = enumerator.compactMap { $0 as? URL }.filter { $0.pathExtension.uppercased() == "PID" }
        .sorted { $0.path < $1.path }
    for url in urls {
        let data = try Data(contentsOf: url)
        guard data[4] & 32 != 0, data[0] == 10, data[1] == 0, data[2] == 0, data[3] == 0 else { continue }
        let pid = try ClawSprite(pid: data, palette: palette)
        assets.append(pid)
        let w = pid.width, h = pid.height
        let cases = [[0, 0, w-1, h-1], [0, 0, w/2, h-1], [min(1,w-1), 0, w-1, h-1],
            [0, min(1,h-1), w-1, h-1], [w/3, h/3, max(w/3,w*2/3), max(h/3,h*2/3)]]
        for (i, source) in cases.enumerated() {
            for fx in 0...1 { for fy in 0...1 {
                compare(pid, command(source, [5,4,5+source[2]-source[0],4+source[3]-source[1]], fx, fy),
                    CGSize(width: w+29, height: h+12), "\(url.path):\(i):\(fx):\(fy)")
            }}
        }
        for fx in 0...1 { for fy in 0...1 {
            compare(pid, command(cases[0], [23,71,23+w-1,71+h-1], fx, fy),
                CGSize(width: 640, height: 480), "full viewport \(url.path):\(fx):\(fy)")
        }}
    }
}
require(assets.count == 261, "expected 261 supported CLAW/Level1 compressed assets")
print("PASS 261 actual compressed PIDs: five clipped source rectangles plus 640x480 viewport, all four flip paths", terminator: "\n")
func fixture(_ w: Int, _ h: Int, _ body: [UInt8]) throws -> ClawSprite {
    var bytes = Data()
    for value in [10,32,w,h,0,0,0,0] {
        var little = word(value).littleEndian
        withUnsafeBytes(of: &little) { bytes.append(contentsOf: $0) }
    }
    bytes.append(contentsOf: body)
    return try ClawSprite(pid: bytes, palette: palette)
}
let mixed = try fixture(7,4,[2,0,1,130,3,2,3,4, 135, 1,5,1,6,2,7,8,131, 7,9,10,11,12,13,14,15])
var randomState: UInt64 = 1997
func random(_ count: Int) -> Int {
    randomState = randomState &* 6364136223846793005 &+ 1442695040888963407
    return Int((randomState >> 32) % UInt64(count))
}
for number in 0..<150 {
    let w = random(31)+1, h = random(15)+1
    var body: [UInt8] = []
    for _ in 0..<h {
        var x = 0
        while x < w {
            let n = random(min(127,w-x))+1
            if random(3) == 0 { body.append(UInt8(128+n)) }
            else { body.append(UInt8(n)); for _ in 0..<n { body.append(UInt8(random(256))) } }
            x += n
        }
    }
    let pid = try fixture(w,h,body)
    let top = random(h), left = random(w)
    let source = [left,top,left+random(w-left),top+random(h-top)]
    let dx = random(10)-3, dy = random(3)+2
    for fx in 0...1 { for fy in 0...1 {
        compare(pid,command(source,[dx,dy,random(20)-10,dy+source[3]-top+random(3)-1],fx,fy),
            CGSize(width:w+19,height:h+12),"generated \(number)")
    }}
}
for top in 0..<4 { for bottom in top..<4 { for left in 0..<7 { for right in left..<7 {
    for fx in 0...1 { for fy in 0...1 {
        compare(mixed, command([left,top,right,bottom], [5,4,11,4+bottom-top], fx, fy),
            CGSize(width: 19, height: 13), "mixed exact source matrix")
    }}
}}}}
// Wrapped physical addresses expose the legacy right/left row spills. Odd
// viewport widths also expose stores into padding, which must stay invisible.
for width in 1...21 {
    for dx in [-3,-1,0,width-3,width-1,width,width+2] {
        for fx in 0...1 { for fy in 0...1 {
            compare(mixed, command([1,0,4,3], [dx,4,dx+3,7], fx, fy),
                CGSize(width: width, height: 13), "spill/padding \(width) \(dx) \(fx) \(fy)")
        }}
    }
}
// Establish that the fixture matrix actually exercises visible writes outside
// destination, padding stores and rejected physical addresses, rather than
// passing solely through an empty/no-op branch.
var visibleSpills = 0, paddingWrites = 0, acceptedSpillFixtures = 0
for width in 1...21 {
    let stride = (width+3) & ~3, capacity = stride*13
    for dx in [-3,-1,0,width-3,width-1,width,width+2] {
        for fx in 0...1 { for fy in 0...1 {
            var indices = [UInt8](repeating:0,count:capacity), coverage = indices
            var c = ClawPIDBlitCommand(destination:ClawPIDBlitRect(left:Int32(dx),top:4,right:Int32(dx+3),bottom:7),
                source:ClawPIDBlitRect(left:1,top:0,right:4,bottom:3),flipX:word(fx),flipY:word(fy),
                originalSourceRectAddress:0x01003000)
            let accepted = mixed.encodedPID.withUnsafeBytes { source in
                indices.withUnsafeMutableBufferPointer { pixels in coverage.withUnsafeMutableBufferPointer { mask in
                    claw_pid_blit8(source.bindMemory(to:UInt8.self).baseAddress,mixed.encodedPID.count,
                        &c,pixels.baseAddress,mask.baseAddress,capacity,stride,nil)
                }}
            }
            if accepted == 1 { acceptedSpillFixtures += 1 }
            for offset in 0..<capacity where coverage[offset] != 0 {
                let y = offset/stride, x = offset%stride
                if x >= width { paddingWrites += 1 }
                else if x < dx || x > dx+3 || y < 4 || y > 7 { visibleSpills += 1 }
            }
        }}
    }
}
require(visibleSpills > 0 && paddingWrites > 0 && acceptedSpillFixtures > 0,"spill coverage missing")
print("PASS directed fixtures exercise \(visibleSpills) visible spill writes and \(paddingWrites) padding writes")
let zero = try fixture(1,1,[1,0])
let literal = ClawFastIndexedDrawing.draw(zero, command: command([0,0,0,0],[1,1,1,1],0,0),
    viewport: CGSize(width: 7, height: 3), z: 0)!
require(Array(pixels(literal)) == [palette[0],palette[1],palette[2],255], "literal zero must be opaque")
let empty = try fixture(7,4,[135,135,135,135])
for fx in 0...1 { for fy in 0...1 {
    compare(empty, command([0,0,6,3],[0,1,6,4],fx,fy), CGSize(width:11,height:9), "all transparent")
}}
for source in [[-1,0,6,3],[0,0,7,3],[0,-1,6,3],[0,4,6,4],[0,2,6,1],[1,2,1,2],[0,0,-1,-1],[9,2,6,1]] {
    for fx in 0...1 { for fy in 0...1 {
        compare(mixed, command(source,[5,4,11,7],fx,fy), CGSize(width:19,height:13), "rejected/inverted")
    }}
}
for viewport in [CGSize.zero, CGSize(width:0.9,height:3), CGSize(width:8193,height:3),
    CGSize(width:-1,height:3), CGSize(width:19.75,height:13.5)] {
    compare(mixed, command([0,0,6,3],[5,4,11,7],0,0), viewport, "viewport boundary")
}
require(ClawFastIndexedDrawing.draw(mixed, command: command([0,0,6,3],[5,4,11,7],0,0),
    viewport: CGSize(width: CGFloat.nan, height: 3), z:0) == nil, "finite extension")
for (draw, expected) in retained { require(pixels(draw) == expected, "retained provider lifetime") }
print("PASS \(calls) byte-complete old/new draws, \(nilResults) identical nil results, \(retained.count) retained images; literal zero, row spills, padding, all clips/flip paths")

if CommandLine.arguments.contains("--benchmark") {
    let iterations = 120
    let testAssets = Array(assets.prefix(24))
    func benchmark(_ fast: Bool) -> Double {
        var checksum = 0
        let begin = ProcessInfo.processInfo.systemUptime
        for i in 0..<iterations { autoreleasepool {
            let pid = testAssets[i % testAssets.count]
            let c = command([0,0,pid.width-1,pid.height-1], [27,53,27+pid.width-1,53+pid.height-1], i&1,(i>>1)&1)
            let viewport = CGSize(width:640,height:480)
            let draw = fast ? ClawFastIndexedDrawing.draw(pid,command:c,viewport:viewport,z:0)
                : ClawIndexedDrawing.draw(pid,command:c,viewport:viewport,z:0)
            checksum += draw?.image.width ?? 0
        }}
        require(checksum > 0, "benchmark outputs")
        return ProcessInfo.processInfo.systemUptime - begin
    }
    _ = benchmark(true)
    let old = benchmark(false), fast = benchmark(true)
    print(String(format:"BENCHMARK %d identical 640x480 draws: old %.6fs, fast %.6fs, speedup %.2fx",iterations,old,fast,old/fast))
}
