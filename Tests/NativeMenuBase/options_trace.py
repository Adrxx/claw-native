"""Trace the actual posted Controls command through the original state factory."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from unicorn import UcError
from unicorn.x86_const import UC_X86_REG_EIP, UC_X86_REG_ESP, UC_X86_REG_ECX
from Tests.NativeMenuBase import input_trace
from Tests.NativeMenuBase.trace import Blocked, ROOT
from Tests.clawparity.program import claw

class OptionsTrace(input_trace.InputTrace):
    dialog_request_output = None

    def extra_witness(self, application):
        state = self.word(application+0x2c)
        mode = self.run(self.word(self.word(state)+0x10),state,phase='observe-state') if state else 0
        return dict(state_id=mode,state_vtable=self.word(state) if state else 0)

    def resource(self, kind, name):
        section = next(section for section in claw().sections if section.name == '.rsrc')
        data = section.data
        def entries(offset):
            named, ids = struct.unpack_from('<HH', data, offset+12)
            for index in range(named+ids):
                key, child = struct.unpack_from('<II', data, offset+16+8*index)
                if key & 0x80000000:
                    at = key & 0x7fffffff
                    count, = struct.unpack_from('<H',data,at)
                    key = data[at+2:at+2+2*count].decode('utf-16le')
                yield key, child
        directory = 0
        for key in (kind,name):
            found = next((child for candidate,child in entries(directory) if candidate == key),None)
            if found is None:
                return 0
            if not found & 0x80000000:
                raise Blocked('Invalid resource directory')
            directory = found & 0x7fffffff
        languages = list(entries(directory))
        if len(languages) != 1 or languages[0][1] & 0x80000000:
            raise Blocked('Unelected resource language')
        return section.address + languages[0][1]

    def fixture(self, address):
        if address == 0x4f7ad2:
            # Native CDialog storage; construction has no window side effect.
            receiver = self.machine.reg_read(UC_X86_REG_ECX)
            self.platform_call(address, 'MFC CDialog constructor')
            self.machine.mem_write(receiver, bytes(0x5c))
            self.put(receiver, 0x510d3c)
            self.put(receiver+4, 1)
            self.put(receiver+0x14, 1)
            self.returned(receiver)
            return
        if address == 0x4fb7d8:
            # The native host has no MFC thread/main-window wrapper.
            self.platform_call(address, 'MFC thread wrapper query')
            self.returned(0)
            return
        if address == 0x4f7b4e:
            # Do not invent geometry or force dialog creation to fail: this
            # physical boundary needs a successful Win32 measurement first.
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            template = self.word(sp+4)
            resource = self.resource(5, 'CONFIGCONTROLS')
            size = self.word(resource+4)
            data = bytes(self.machine.mem_read(template, size))
            request = dict(service='MFC CDialog CreateIndirect',
                           resource='CONFIGCONTROLS', resource_kind=5,
                           executable_sha256=claw().sha256,
                           template_sha256=hashlib.sha256(data).hexdigest(),
                           template_size=size,
                           required=['GetWindowRect', 'GetSystemMetrics(4,7,8)',
                                     'SystemParametersInfoA(SPI_GETNONCLIENTMETRICS)'],
                           status='blocked', scope='Physical measurement only; game geometry remains original')
            if self.dialog_request_output is not None:
                (self.dialog_request_output/'configcontrols.bin').write_bytes(data)
                (self.dialog_request_output/'dialog-measurement-request.json').write_text(json.dumps(request,indent=2)+'\n')
            raise Blocked('CONFIGCONTROLS requires a measured successful Win32 dialog creation and geometry; see dialog-measurement-request.json')
        if address in self.imports:
            api = self.imports[address][1].split('!')[-1]
            if api in ('FindResourceA','LoadResource','LockResource','SizeofResource','FreeResource'):
                sp = self.machine.reg_read(UC_X86_REG_ESP)
                arg = lambda index: self.word(sp+4*index)
                if api == 'FindResourceA':
                    name = arg(2) if arg(2) < 0x10000 else self.bytestring(arg(2)).decode('ascii')
                    kind = arg(3) if arg(3) < 0x10000 else self.bytestring(arg(3)).decode('ascii')
                    result = self.resource(kind,name)
                    pop = 12
                    self.physical_events.append(dict(service=api,name=name,kind=kind,found=bool(result)))
                elif api in ('LoadResource','SizeofResource'):
                    result = self.word(arg(2)+(4 if api == 'SizeofResource' else 0))
                    if api == 'LoadResource':
                        result += claw().base
                    pop = 8
                else:
                    result = arg(1) if api == 'LockResource' else 0
                    pop = 4
                self.platform_call(address,self.imports[address][1])
                self.returned(result,pop)
                return
        if address in (0x4f6974,0x4f69c3):
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            receiver = self.machine.reg_read(UC_X86_REG_ECX)
            buffer = self.word(receiver)
            size = self.word(sp+4)
            self.platform_call(address, 'MFC CString buffer access')
            if address == 0x4f6974:
                value = self.bytestring(buffer)
                capacity = max(size,len(value))
                if capacity > 0x100000:
                    raise Blocked('Unbounded CString buffer')
                buffer = self.allocate(12+capacity+1)+12
                for offset,word in ((-12,1),(-8,len(value)),(-4,capacity)):
                    self.put(buffer+offset,word)
                self.machine.mem_write(buffer,value+b'\0')
                self.put(receiver,buffer)
            else:
                if size == 0xffffffff:
                    size = len(self.bytestring(buffer))
                if size > self.word(buffer-4):
                    raise Blocked('CString release length exceeds capacity')
                self.put(buffer-8,size)
                self.machine.mem_write(buffer+size,b'\0')
            self.returned(buffer if address == 0x4f6974 else 0,4)
            return
        if address == 0x4f684d:
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            dest,left,right = [self.word(sp+4*i) for i in range(1,4)]
            self.platform_call(address, 'MFC CString concatenation')
            value = (self.bytestring(left) if left else b'') + self.bytestring(self.word(right))
            self.put(dest,self.cstring(value))
            self.returned(dest,12)
            return
        if address == 0x4f5e89:
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            receiver = self.machine.reg_read(UC_X86_REG_ECX)
            self.platform_call(address, 'MFC pointer map constructor')
            for offset,value in enumerate((0x510264,0,17,0,0,0,self.word(sp+4))):
                self.put(receiver+4*offset,value)
            self.maps[receiver] = {}
            self.returned(receiver,4)
            return
        if address == 0x4fcf35:
            receiver = self.machine.reg_read(UC_X86_REG_ECX)
            self.platform_call(address, 'MFC CCmdTarget constructor')
            for offset,value in enumerate((0x510444,0,0,0)):
                self.put(receiver+4*offset,value)
            self.returned(receiver)
            return
        if address in self.imports and self.imports[address][1].endswith('!SystemParametersInfoA'):
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            args = tuple(self.word(sp+4*i) for i in range(1,5))
            if args[0] != 0x29 or args[1] != 0 or args[3] != 0 or self.word(args[2]) != 0x154:
                raise Blocked('Unelected SystemParametersInfo request')
            self.platform_call(address, self.imports[address][1])
            self.physical_events.append(dict(service='SystemParametersInfoA',action=0x29,result=0,scope='unavailable nonclient metrics'))
            self.returned(0,16)
            return
        if address in self.imports and self.imports[address][1].endswith('!PostMessageA'):
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            args = tuple(self.word(sp + 4 * i) for i in range(1, 5))
            if args != (1, 0x111, 0x8090, 0):
                return super().fixture(address)
            self.platform_call(address, self.imports[address][1])
            self.messages.append(args)
            self.physical_events.append(dict(service='PostMessageA',window=args[0],message=args[1],wparam=args[2],lparam=args[3]))
            self.returned(1,16)
            return
        return super().fixture(address)

    def dispatch_messages(self, application):
        while self.messages:
            window,message,wparam,lparam = self.messages.pop(0)
            if (window,message,wparam,lparam) != (1,0x111,0x8090,0):
                raise Blocked('Unelected window command')
            self.run(0x426e30,application,(0,wparam,lparam),phase='controls-window-command')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'work/menu-options')
    args = parser.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to((ROOT/'work').resolve()):
        parser.error('Original-derived evidence must remain under work/')
    out.mkdir(parents=True, exist_ok=True)
    events = []
    for frame, x, y, label in [(9,320,342,'options'),(25,320,277,'controls')]:
        events.extend([dict(frame=frame,message=513,x=x,y=y,label=label),
                       dict(frame=frame+1,message=514,x=x,y=y)])
    for frame, label in [(41,'escape-controls'),(57,'escape-options')]:
        events.extend([dict(frame=frame,message=256,key=27,label=label),
                       dict(frame=frame+1,message=257,key=27)])
    (out/'events.json').write_text(json.dumps(events,indent=2)+'\n')
    input_trace.EVENTS = events
    trace = OptionsTrace(out)
    trace.dialog_request_output = out
    try:
        trace.execute()
    except (Blocked,UcError) as error:
        trace.stop = dict(address=hex(trace.machine.reg_read(UC_X86_REG_EIP)),reason=str(error),phase=trace.phase)
    finally:
        for stream in trace.files.values():
            stream.close()
    report = trace.report()
    baseline = json.loads((ROOT/'work/menu-input/original.json').read_text())
    for key in ('game_functions','platform_calls','platform_imports'):
        known = {row['address'] for row in baseline[key]}
        report['new_'+key] = [row for row in report[key] if row['address'] not in known]
    report.update(status='pass' if trace.stop is None and len(trace.presentations)==61 else 'blocked',
                  events=events,input_witnesses=trace.input_witnesses)
    (out/'original-command.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:report[key] for key in ('status','stop','counts')}))
    return 0 if report['status']=='pass' else 2

if __name__ == '__main__':
    raise SystemExit(main())
