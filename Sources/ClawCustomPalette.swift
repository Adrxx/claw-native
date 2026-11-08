import Foundation

/// Read-only package palettes and Lua value operations. No host pointers enter Lua.
struct ClawCustomPalette {
    let main:Data?
    let mainColorCount:Int
    let tables:[String:Data]
    init(_ package:ClawCustomAssets) throws {
        var main:Data?,mainColorCount = 0
        // The release scans all three accepted names; a stable lexical scan
        // makes packages containing multiple MAIN variants deterministic.
        for name in ["MAIN.ACT","MAIN.PAL","MAIN.TXT"] {
            if let data = try package.data("PALETTES/"+name) {
                main = try Self.decode(data,name:name,base:main)
                let count = name.hasSuffix(".TXT") ? String(decoding:data,as:UTF8.self).split(separator:"\n",omittingEmptySubsequences:false).prefix(256).prefix(while:{$0.range(of:"#[0-9a-fA-F]{6}",options:.regularExpression) != nil}).count:256
                mainColorCount = max(mainColorCount,count)
            }
        }
        self.main = main
        self.mainColorCount = mainColorCount
        var tables:[String:Data] = [:]
        for path in package.files.keys.sorted() where path.hasPrefix("PALETTES/") && path.hasSuffix(".CLT") && path.split(separator:"/").count == 2 {
            let data = try package.data(path)!
            tables[URL(fileURLWithPath:path).deletingPathExtension().lastPathComponent] = try Self.decodeTable(data)
        }
        self.tables = tables
    }
    static func decodeTable(_ data:Data) throws -> Data {
        guard data.count >= 65540,Array(data.prefix(4)) == [0,0,1,0] else {throw AssetError.invalid("Invalid color lookup table")}
        return Data(data[4..<65540])
    }
    static func decode(_ data:Data,name:String,base:Data? = nil) throws -> Data {
        if name.uppercased().hasSuffix(".TXT") {
            var rgb = base ?? Data(repeating:0,count:768)
            let lines = String(decoding:data,as:UTF8.self).split(separator:"\n",omittingEmptySubsequences:false)
            for (i,line) in lines.prefix(256).enumerated() {
                guard let range = line.range(of:"#[0-9a-fA-F]{6}",options:.regularExpression) else {break}
                let hex = String(line[range].dropFirst())
                for c in 0..<3 {let a = hex.index(hex.startIndex,offsetBy:c*2);rgb[i*3+c] = UInt8(hex[a..<hex.index(a,offsetBy:2)],radix:16)!}
            }
            return rgb
        }
        guard ["PAL","ACT"].contains(URL(fileURLWithPath:name).pathExtension.uppercased()),data.count >= 768 else {throw AssetError.invalid("Truncated or unsupported palette: \(name)")}
        return Data(data.prefix(768))
    }

    // Independently written value API matching the release's byte truncation,
    // inclusive ranges and its HSV-style saturation in the HSL conversion.
    static let lua = #"""
    local function byte(x) return math.floor(math.max(0,math.min(255,x))) end
    ImageFlag={NoDraw=0,Normal=1,Ghost=2,Shadow=3,ColorFill=5,Glitch=6,Chameleon=6,Blob=8}
    local methods={}
    local function color(v,old)
        old=old or {Red=0,Green=0,Blue=0,Alpha=0}
        if type(v)=='string' then local s=assert(v:match('#%x%x%x%x%x%x'),'Invalid color');v={tonumber(s:sub(2,3),16),tonumber(s:sub(4,5),16),tonumber(s:sub(6,7),16)} end
        assert(type(v)=='table','Invalid color')
        local values={Red=math.floor(v[1] or v.Red or old.Red)%256,Green=math.floor(v[2] or v.Green or old.Green)%256,Blue=math.floor(v[3] or v.Blue or old.Blue)%256,Alpha=math.floor(v[4] or v.Alpha or old.Alpha)%256}
        return setmetatable({}, {__index=values,__newindex=function(_,k,n) assert(values[k]~=nil,'Invalid color channel');values[k]=math.floor(n)%256 end,__tostring=function(c) return string.format('#%02x%02x%02x',c.Red,c.Green,c.Blue) end})
    end
    function CreatePalette()
        local colors={};for i=0,255 do colors[i]=color({}) end
        return setmetatable({}, {__index=function(_,k) return type(k)=='number' and colors[k] or methods[k] end,__newindex=function(_,k,v) assert(type(k)=='number' and k>=0 and k<=255 and k%1==0,'Palette index');colors[k]=color(v,colors[k]) end})
    end
    local function read(kind)
        local p=CreatePalette()
        for i=0,255 do local v=_paletteService('Read:'..kind..':'..i);p[i]={math.floor(v/65536)%256,math.floor(v/256)%256,v%256} end
        return p
    end
    function GetFirstPalette() return read('First') end
    function GetCurrentPalette() return read('Current') end
    function LoadPaletteFile(name) _paletteService('Load:'..name);return read('Loaded') end
    function methods:Copy() local p=CreatePalette();for i=0,255 do p[i]=self[i] end;return p end
    function methods:GetColor(i) return self[byte(i)] end
    function methods:SetColor(i,c) self[byte(i)]=c;return self end
    function methods:Set()
        for i=0,255 do local c=self[i];_paletteService('Write:'..i,c.Red*65536+c.Green*256+c.Blue) end
        _paletteService('Commit')
    end
    methods.Render=methods.Set
    local function each(p,lo,hi,f)
        for i=byte(lo or 0),byte(hi or 255) do p[i]=f(p[i]) end;return p
    end
    function methods:InvertColors(lo,hi) return each(self,lo,hi,function(c) return {255-c.Red,255-c.Green,255-c.Blue,c.Alpha} end) end
    local function channel(s) s=s:lower();return assert(({red='Red',green='Green',blue='Blue'})[s],'Invalid channel') end
    function methods:InvertChannel(ch,lo,hi) ch=channel(ch);return each(self,lo,hi,function(c) c[ch]=255-c[ch];return c end) end
    function methods:SwapChannels(a,b,lo,hi) a=channel(a);b=channel(b);return each(self,lo,hi,function(c) c[a],c[b]=c[b],c[a];return c end) end
    function methods:AdjustRGB(r,g,b,lo,hi) return each(self,lo,hi,function(c) return {byte(c.Red+r),byte(c.Green+g),byte(c.Blue+b),c.Alpha} end) end
    function methods:BlackAndWhite(lo,hi) return each(self,lo,hi,function(c) local n=byte(.3*c.Red+.59*c.Green+.11*c.Blue);return {n,n,n,c.Alpha} end) end
    function methods:AdjustHSL(h,s,l,lo,hi)
        return each(self,lo,hi,function(c)
            local r,g,b=c.Red/255,c.Green/255,c.Blue/255
            local low,high=math.min(r,g,b),math.max(r,g,b);local d=high-low
            local hue=0
            if d~=0 then if high==r then hue=(g-b)/d elseif high==g then hue=(b-r)/d+2 else hue=(r-g)/d+4 end end
            hue=((hue*60+h)%360)/360
            local sat=math.max(0,math.min(1,(high==0 and 0 or d/high)+s/100))
            local lum=math.max(0,math.min(1,(high+low)/2+l/100))
            if sat==0 then local v=byte(lum*255);return {v,v,v} end
            local q=lum<.5 and lum*(1+sat) or lum+sat-lum*sat;local p=2*lum-q
            local function ch(t) if t<0 then t=t+1 elseif t>1 then t=t-1 end;local v=p;if t<1/6 then v=p+(q-p)*6*t elseif t<.5 then v=q elseif t<2/3 then v=p+(q-p)*(2/3-t)*6 end;return byte(v*255) end
            return {ch(hue+1/3),ch(hue),ch(hue-1/3)}
        end)
    end
    function LoadCLT(file,name) return _paletteService('LoadCLT:'..(name or '')..':'..file) end
    local function imageKey(img)
        if type(img)=='string' then return 'Name:'..img end
        if img._imageObject then return 'Object:'..img._imageObject end
        if img._handle then return 'Object:'..img._handle end
        return 'Name:'..assert(img._imageName,'Invalid image')
    end
    function GetImage(name) return _planeImage(name) end
    function GetImgStr(img) return img._imageName or _legacyImageName(img) end
    function SetImgFlag(img,v) assert(v==1 or v==2 or v==3 or v==5 or v==6 or v==7 or v==8,'Invalid image flag');return _paletteService('Image:Flag:'..imageKey(img),v) end
    function SetImgColor(img,v) assert(v>=0 and v<=255,'Invalid color index');return _paletteService('Image:Color:'..imageKey(img),v) end
    function SetImgCLT(img,name) return _paletteService('Image:CLT:'..name:upper()..':'..imageKey(img)) end
    SetImgClt=SetImgCLT
    """#
}
