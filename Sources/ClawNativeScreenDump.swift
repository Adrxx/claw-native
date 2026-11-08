import Foundation

/// Native replacement for the eight-bit DirectDraw BMP output. The original
/// writes a 14-byte file header, BITMAPINFOHEADER, 256 BGR entries and bottom-up
/// rows. Its game display widths are multiples of four.
enum ClawNativeScreenDump {
    static func bitmap(pixels:Data,width:UInt32,height:UInt32,stride:UInt32,rgb:Data)->Data? {
        guard width > 0,width <= 16384,width % 4 == 0,height > 0,height <= 16384,
              stride >= width,pixels.count == Int(stride)*Int(height),rgb.count == 768 else {return nil}
        var result = Data()
        func word(_ value:UInt16) {var v = value.littleEndian;withUnsafeBytes(of:&v){result.append(contentsOf:$0)}}
        func dword(_ value:UInt32) {var v = value.littleEndian;withUnsafeBytes(of:&v){result.append(contentsOf:$0)}}
        word(0x4d42);dword(1078+width*height);word(0);word(0);dword(1078)
        dword(40);dword(width);dword(height);word(1);word(8)
        for _ in 0..<6 {dword(0)}
        for i in 0..<256 {result.append(contentsOf:[rgb[i*3+2],rgb[i*3+1],rgb[i*3],0])}
        for y in (0..<Int(height)).reversed() {
            result.append(pixels[y*Int(stride)..<y*Int(stride)+Int(width)])
        }
        return result
    }
}
