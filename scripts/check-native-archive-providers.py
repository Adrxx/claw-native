#!/usr/bin/env python3
"""Execute the app's native CArchive/CMemFile/CFile services on owned storage."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT),str(ROOT/'scripts')]


def original_contracts():
    from Tests.clawparity.program import claw
    from capstone import Cs,CS_ARCH_X86,CS_MODE_32
    from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_EIP,UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EAX
    program = claw()  # Enforces the v1.0 SHA-256 before reading bytes.
    ranges = [(0x4fd7fd,0x4fd901),(0x4fda33,0x4fdedd)]
    decoder = Cs(CS_ARCH_X86,CS_MODE_32)
    listing = []
    for start,end in ranges:
        section = next(s for s in program.sections if s.address <= start < s.address+len(s.data))
        listing += [f'{i.address:08x} {i.mnemonic} {i.op_str}' for i in decoder.disasm(section.data[start-section.address:end-section.address],start)]
    out = ROOT/'work/call-closure';out.mkdir(parents=True,exist_ok=True)
    (out/'archive-original.txt').write_text('\n'.join(listing)+'\n')
    uc = Uc(UC_ARCH_X86,UC_MODE_32)
    uc.mem_map(0x400000,0x180000)
    for s in program.sections:
        if s.data:uc.mem_write(s.address,s.data)
    uc.mem_map(0x1000000,0x100000)
    stack = 0x1080000;stop = 0x10ffff0;archive = 0x1010000;slot = 0x1011000;text = 0x1020000
    state = dict(output=bytearray(),input=b'',offset=0)
    def word(p):return int.from_bytes(uc.mem_read(p,4),'little')
    def hook(uc,address,size,user):
        sizes = {0x4a1637:1,0x4a165a:2,0x4a1681:4}
        esp = uc.reg_read(UC_X86_REG_ESP)
        if address in sizes:
            n = sizes[address];state['output'] += (word(esp+4)&((1<<(8*n))-1)).to_bytes(n,'little');pop=4
        elif address == 0x4fdcb3:
            state['output'] += uc.mem_read(word(esp+4),word(esp+8));pop=8
        elif address in (0x4a16d6,0x4a1709):
            n = 2 if address == 0x4a16d6 else 4;i = state['offset']
            uc.mem_write(word(esp+4),state['input'][i:i+n]);state['offset'] += n;pop=4
        else:return
        uc.reg_write(UC_X86_REG_EIP,word(esp));uc.reg_write(UC_X86_REG_ESP,esp+4+pop)
    uc.hook_add(UC_HOOK_CODE,hook)
    def run(target,args):
        uc.mem_write(stack,b''.join(v.to_bytes(4,'little') for v in [stop]+args))
        uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(UC_X86_REG_ECX,archive)
        uc.emu_start(target,stop,count=10000)
        assert uc.reg_read(UC_X86_REG_ESP)==stack+4+4*len(args)
        return uc.reg_read(UC_X86_REG_EAX)
    strings=[];counts=[]
    for n in (0,1,254,255,256,65533,65534,65535,65536):
        payload = bytes((i*37+128)&255 for i in range(n))
        uc.mem_write(text-12,(1).to_bytes(4,'little')+n.to_bytes(4,'little')*2)
        uc.mem_write(text,payload+b'\0');uc.mem_write(slot,text.to_bytes(4,'little'))
        state['output']=bytearray();assert run(0x4fd7fd,[archive,slot])==archive
        prefix = bytes([n]) if n<255 else b'\xff'+n.to_bytes(2,'little') if n<65534 else b'\xff\xff\xff'+n.to_bytes(4,'little')
        assert state['output']==prefix+payload
        strings.append(dict(length=n,prefix=prefix.hex(),sha256=hashlib.sha256(state['output']).hexdigest()))
    for n in (0,1,65534,65535,65536,0x7fffffff,0xffffffff):
        state['output']=bytearray();run(0x4fde7f,[n])
        expected = n.to_bytes(2,'little') if n<65535 else b'\xff\xff'+n.to_bytes(4,'little')
        assert state['output']==expected
        state.update(input=expected,offset=0);assert run(0x4fdead,[])==n
        assert state['offset']==len(expected)
        counts.append(dict(value=n,encoded=expected.hex()))
    return dict(strings=strings,counts=counts,contract='Hash-checked original CString store, WriteCount and ReadCount executed under Unicorn; only byte I/O helpers replaced.')


SWIFT_FIXTURE = r'''
final class ClawTokenHeap {
    var blocks:[UInt32:(UnsafeMutablePointer<UInt8>,UInt32)] = [:]
    var next:UInt32 = 0x60000000
    func allocate(_ n:UInt32)->UInt32 {
        let token = next;next += ((n+4095)/4096+1)*4096
        let p = UnsafeMutablePointer<UInt8>.allocate(capacity:Int(max(n,1)));p.initialize(repeating:0,count:Int(max(n,1)))
        blocks[token] = (p,n);return token
    }
    func release(_ t:UInt32) {if let block = blocks.removeValue(forKey:t) {block.0.deallocate()}}
    func lookupBytes(_ t:UInt32,count:UInt32)->UnsafeMutablePointer<UInt8>? {
        guard t != 0,UInt64(t)+UInt64(count) <= UInt32.max else {return nil}
        for (base,(p,n)) in blocks where t >= base && UInt64(t)+UInt64(count) <= UInt64(base)+UInt64(n) {return p.advanced(by:Int(t-base))}
        return nil
    }
    func lookup(_ t:UInt32,words:UInt32)->UnsafeMutablePointer<UInt32>? {lookupBytes(t,count:words*4).map{UnsafeMutableRawPointer($0).assumingMemoryBound(to:UInt32.self)}}
    deinit {for (_,block) in blocks {block.0.deallocate()}}
}
let heap = ClawTokenHeap()
func w(_ t:UInt32)->UInt32 {UnsafeRawPointer(heap.lookupBytes(t,count:4)!).loadUnaligned(as:UInt32.self)}
func put(_ t:UInt32,_ v:UInt32) {var v=v;withUnsafeBytes(of:&v){heap.lookupBytes(t,count:4)!.update(from:$0.baseAddress!.assumingMemoryBound(to:UInt8.self),count:4)}}
func data(_ t:UInt32,_ n:UInt32)->Data {n == 0 ? Data():Data(bytes:heap.lookupBytes(t,count:n)!,count:Int(n))}
func token(_ d:Data)->UInt32 {let t=heap.allocate(UInt32(d.count));d.copyBytes(to:heap.lookupBytes(t,count:UInt32(d.count))!,count:d.count);return t}
func string(_ d:Data)->UInt32 {let t=heap.allocate(UInt32(d.count)+13);put(t,1);put(t+4,UInt32(d.count));put(t+8,UInt32(d.count));d.copyBytes(to:heap.lookupBytes(t+12,count:UInt32(d.count)+1)!,count:d.count);return t+12}
let directory = FileManager.default.temporaryDirectory.appendingPathComponent("claw-native-archive-"+UUID().uuidString)
try FileManager.default.createDirectory(at:directory,withIntermediateDirectories:true)
defer {try? FileManager.default.removeItem(at:directory)}
let files = ClawNativeSaveFiles(directory:directory)
let owner = ClawNativeArchiveServices(bytes:{heap.lookupBytes($0,count:$1)},allocate:{heap.allocate($0)},release:{heap.release($0)},fileService:{files.service($0,$1,$2,heap:heap)},empty:0x52e1c4,makeString:string)
var checks=0
func ok(_ v:Bool,_ label:String) {if !v {FileHandle.standardError.write(Data(("FAIL: "+label+"\n").utf8));exit(1)};checks += 1}
func call(_ f:UInt32,_ r:UInt32,_ a:[UInt32]=[])->UInt32 {guard let v=owner.service(f,r,a) else {fatalError("Rejected \(String(f,radix:16)) \(a)")};return v}
func memfile()->UInt32 {let f=heap.allocate(40);ok(call(0x4ff5f9,f,[128])==f,"CMemFile construct");return f}
func archive(_ f:UInt32,_ mode:UInt32,_ size:UInt32=128,_ supplied:UInt32=0)->UInt32 {let r=heap.allocate(68);ok(call(0x4fda33,r,[f,mode,size,supplied])==r,"archive construct");return r}
func close(_ r:UInt32) {ok(call(0x4fdb0f,r)==0,"archive close")}
func attached(_ d:Data)->UInt32 {let f=memfile(),p=token(d);ok(call(0x4ff645,f,[p,UInt32(d.count),0])==0,"attach");return f}
var stringRows:[[String:Any]]=[]
for n in [0,1,254,255,256,65533,65534,65535,65536] {
    let d=Data((0..<n).map{UInt8(truncatingIfNeeded:$0*37+128)}),f=memfile(),r=archive(f,0),slot=heap.allocate(4)
    put(slot,string(d));ok(call(0x4fd7fd,0,[r,slot])==r,"CString store return")
    close(r)
    let encoded=data(w(f+32),w(f+28)),prefix=n<255 ? Data([UInt8(n)]):n<65534 ? Data([255,UInt8(truncatingIfNeeded:n),UInt8(truncatingIfNeeded:n>>8)]):Data([255,255,255,UInt8(truncatingIfNeeded:n),UInt8(truncatingIfNeeded:n>>8),UInt8(truncatingIfNeeded:n>>16),UInt8(truncatingIfNeeded:n>>24)])
    ok(encoded==prefix+d,"ANSI string bytes")
    let load=archive(attached(encoded),1),out=heap.allocate(4)
    ok(call(0x4fd877,0,[load,out])==load,"CString load return")
    ok(w(w(out)-8)==n && data(w(out),UInt32(n))==d,"binary ANSI round trip")
    close(load);stringRows.append(["length":n,"prefix":prefix.map{String(format:"%02x",$0)}.joined()])
}
for n:UInt32 in [0,1,65534,65535,65536,0x7fffffff,0xffffffff] {
    let f=memfile(),r=archive(f,0)
    ok(call(0x4fde7f,r,[n])==0,"WriteCount");close(r)
    let value=data(w(f+32),w(f+28)),load=archive(attached(value),1)
    ok(call(0x4fdead,load)==n,"ReadCount");close(load)
}
// Buffer boundaries, direct I/O, partial EOF, zero I/O and unread seek-back.
for n in [0,1,127,128,129,255,256,257,513,2049] {
    let payload=Data((0..<n).map{UInt8(truncatingIfNeeded:$0)}),p=token(payload),f=memfile(),r=archive(f,0)
    ok(call(0x4fdcb3,r,[p,UInt32(n)])==0,"write")
    ok(w(f+28)+w(r+36)-w(r+44)==n,"store cursors")
    ok(call(0x4fdd43,r)==0,"flush");ok(data(w(f+32),w(f+28))==payload,"flushed bytes");close(r)
    let load=archive(attached(payload),1),dest=heap.allocate(UInt32(n)+4)
    ok(call(0x4fdba5,load,[dest,UInt32(n)+3])==n,"partial EOF byte count")
    ok(data(dest,UInt32(n))==payload,"read bytes");close(load)
}
let fillFile=attached(Data((0..<300).map{UInt8(truncatingIfNeeded:$0)})),fillArchive=archive(fillFile,1)
ok(call(0x4fddbd,fillArchive,[4])==0 && w(fillFile+20)==128,"fill reads ahead")
put(fillArchive+36,w(fillArchive+36)+126)
ok(call(0x4fddbd,fillArchive,[4])==0,"compact fill")
ok(data(w(fillArchive+36),6)==Data([126,127,128,129,130,131]),"preserve unread")
ok(w(fillFile+20)==254,"refill cursor")
ok(call(0x4fdd43,fillArchive)==0 && w(fillFile+20)==126,"load flush rewinds unread")
close(fillArchive)
// CFile bridge uses the production scoped file owner, including real seeks.
let physical=heap.allocate(16);put(physical,0x510844);put(physical+4,.max);put(physical+12,0x52e1c4)
let path=token(Data(Array("C:\\CLAW\\ARCHIVE.BIN".utf8)+[0]))
ok(files.service(0x4f7448,physical,[path,0x1002,0],heap:heap)==1,"CFile open")
let output=archive(physical,0),payload=Data((0..<513).map{UInt8(truncatingIfNeeded:$0*13)}),source=token(payload)
ok(call(0x4fdcb3,output,[source,513])==0,"physical archive write");close(output)
ok(files.service(0x4f75f5,physical,[0,0],heap:heap)==0,"physical seek")
let input=archive(physical,1),dest=heap.allocate(600)
ok(call(0x4fdba5,input,[dest,7])==7 && data(dest,7)==payload.prefix(7),"physical read")
close(input)
ok(files.service(0x4f75f5,physical,[0,1],heap:heap)==7,"physical unread rewind")
ok(files.service(0x4f766e,physical,[],heap:heap)==0,"physical close")
// Supplied buffers are borrowed and survive archive destruction.
let supplied=heap.allocate(128),borrowFile=memfile(),borrow=archive(borrowFile,0,128,supplied)
ok(call(0x4fdcb3,borrow,[source,3])==0,"borrowed buffer write");close(borrow)
ok(heap.lookupBytes(supplied,count:128) != nil,"borrowed lifetime")
let aliasFile=memfile(),aliasStore=archive(aliasFile,0),aliasData=Data(repeating:0xab,count:512)
ok(call(0x4fdcb3,aliasStore,[token(aliasData),512])==0,"initial alias bytes");close(aliasStore)
let aliasAppend=archive(aliasFile,0)
ok(call(0x4fdcb3,aliasAppend,[w(aliasFile+32),512])==0,"self-buffer growth write");close(aliasAppend)
ok(data(w(aliasFile+32),w(aliasFile+28))==aliasData+aliasData,"growth preserves aliased source")
let shortFill=archive(attached(Data([1,2])),1)
ok(owner.service(0x4fddbd,shortFill,[3])==nil,"truncated fill")
ok(owner.service(0x4fddbd,shortFill,[129])==nil,"over-capacity fill");close(shortFill)
// Reject truncated serialized values and every missing/corrupt storage owner.
for truncated in [Data(),Data([255]),Data([255,255]),Data([255,255,255,1,0]),Data([4,65,66]),Data([255,254,255])] {
    let f=attached(truncated),r=archive(f,1),out=heap.allocate(4)
    ok(owner.service(0x4fd877,0,[r,out])==nil,"truncated/Unicode string refused");close(r)
}
for truncated in [Data(),Data([1]),Data([255,255]),Data([255,255,1,2,3])] {
    let r=archive(attached(truncated),1)
    ok(owner.service(0x4fdead,r,[])==nil,"truncated count refused");close(r)
}
let rejectFile=memfile(),reject=archive(rejectFile,0)
for (f,a) in [(UInt32(0x4fdcb3),[UInt32(0xdeadbeef),1]),(0x4fdba5,[dest,1]),(0x4fddbd,[1]),(0x4fdd43,[1]),(0x4fde7f,[]),(0x4fdead,[1])] {
    ok(owner.service(f,reject,a)==nil,"invalid mode/storage/ABI")
}
ok(owner.service(0x4fdcb3,reject,[source,0x800001])==nil,"bounded I/O")
ok(owner.service(0x4fdcb3,0xdeadbeef,[source,1])==nil,"unowned archive")
ok(owner.service(0x4fda33,heap.allocate(68),[0xdeadbeef,0,128,0])==nil,"unowned file")
ok(owner.service(0x4fda33,heap.allocate(68),[memfile(),0,128,0xdeadbeef])==nil,"unowned supplied buffer")
ok(owner.service(0x4fda33,heap.allocate(68),[memfile(),8,128,0])==nil,"invalid mode")
ok(owner.service(0x4fd7fd,0,[reject,0xdeadbeef])==nil,"unowned CString")
ok(owner.service(0x4fda33,heap.allocate(68),[rejectFile,0,128,0])==nil,"one archive per file")
ok(owner.service(0x4ff682,rejectFile,[])==nil,"active file lifetime")
let saved=w(reject+44);put(reject+44,0xdeadbeef)
ok(owner.service(0x4fdd43,reject,[])==nil,"corrupt buffer")
put(reject+44,saved);close(reject)
ok(owner.service(0x4fdd43,reject,[])==nil,"retired archive")
let emptyFile=memfile(),before=heap.blocks.count,owned=archive(emptyFile,0)
close(owned);ok(heap.blocks.count==before+1,"owned archive buffer released")
ok(call(0x4ff682,emptyFile)==0,"CMemFile destroy")
let noflushFile=memfile(),noflush=archive(noflushFile,2)
ok(call(0x4fdcb3,noflush,[source,3])==0,"no-flush write");close(noflush)
ok(w(noflushFile+28)==0,"no-flush destructor")
let report:[String:Any] = ["checks":checks,"strings":stringRows,"physical_file_reads":files.reads,"physical_file_writes":files.writes,"production_execution":true]
FileHandle.standardOutput.write(try JSONSerialization.data(withJSONObject:report,options:[.sortedKeys]))
'''


def main():
    spec=importlib.util.spec_from_file_location('closure',ROOT/'scripts/check-call-closure.py')
    closure=importlib.util.module_from_spec(spec);spec.loader.exec_module(closure)
    source=ROOT/'Sources/ClawNativeMenuInterface.swift'
    with closure.heavy_lock():
        closure.wait_load()
        production=source.read_text()
        classes='import Foundation\n'+closure.body(production,'final class ClawNativeSaveFiles {')+'\n'+closure.body(production,'final class ClawNativeArchiveServices {')
        assert 'archiveServices.service(q.function,r,a)' in closure.body(production,'    private func service(_ q:ClawCall)')
        key=hashlib.sha256((classes+SWIFT_FIXTURE).encode()).hexdigest()[:24]
        folder=ROOT/'work/build/native-archive-providers'/key;folder.mkdir(parents=True,exist_ok=True)
        swift=folder/'main.swift';swift.write_text(classes+'\n'+SWIFT_FIXTURE)
        binary=folder/'check'
        if not binary.exists():subprocess.run(['xcrun','swiftc','-O',str(swift),'-o',str(binary)],check=True)
        result=json.loads(subprocess.check_output([str(binary)],text=True))
        contracts=original_contracts()
    assert result['strings']==[dict(length=r['length'],prefix=r['prefix']) for r in contracts['strings']]
    report=dict(check='native-archive-providers',status='pass',production=result,original=contracts,
                inputs={str(source.relative_to(ROOT)):hashlib.sha256(production.encode()).hexdigest(),'scripts/check-native-archive-providers.py':closure.digest(Path(__file__))},
                domain='Owned archive and file ledgers; 8 MiB buffer/I/O limit; ANSI bytes; modes 0..7; Unicode strings refused. Production services extracted verbatim with bounded heap callbacks, including the real scoped CFile owner.')
    out=ROOT/'work/call-closure/native-archive-providers.json'
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='pass',checks=result['checks'],evidence=str(out.relative_to(ROOT)))))


if __name__=='__main__':main()
