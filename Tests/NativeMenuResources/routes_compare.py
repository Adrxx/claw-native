"""Fresh retail branches versus the actual initialized Swift menu host."""
import hashlib
import json
import re
from .compare import WORK
from .initializer_compare import original_initializer, physical_effects, normalized
from Tests.NativeMenuBase.trace import MenuTrace, UC_X86_REG_ESP, UC_X86_REG_ECX


class RoutesReference(MenuTrace):
    diagnostic_active = False
    movie = 0

    def com_fixture(self, address):
        kind, method = self.com_methods[address]
        if getattr(self, 'fail_flip', False) and method == 'Flip':
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            self.flip_request = [0,3,self.word(sp+8),self.word(sp+12)]
            self.physical_events.append(dict(service='IDirectDrawSurface::Flip',object=hex(self.word(sp+4)),flags=self.word(sp+12),result=0x88760064))
            self.returned(0x88760064,12)
            return
        return super().com_fixture(address)

    def hook(self, machine, address, size, user):
        if address == 0x4bd260:self.diagnostic_frame = machine.reg_read(UC_X86_REG_ESP)
        if self.diagnostic_active and address == 0x4bc110:
            self.route_effects.append(dict(kind='display-sink', arguments=[self.word(machine.reg_read(UC_X86_REG_ESP)+4)],text='', caption=''))
        if address == 0x4bd83f:
            self.diagnostic_jump_reached = True
        return super().hook(machine, address, size, user)

    def fixture(self, address):
        sp = self.machine.reg_read(UC_X86_REG_ESP)
        arg = lambda i: self.word(sp+4*i)
        receiver = self.machine.reg_read(UC_X86_REG_ECX)
        slot = self.imports.get(address, (address, ''))[0]
        if self.diagnostic_active:
            if slot == 0x546ca4:
                assert arg(1) == 0x30
                self.route_effects.append(dict(kind='beep', arguments=[arg(1)],text='', caption=''))
                self.returned(1, 4)
                return
            if slot == 0x546d48:
                assert arg(1) == 0 and arg(4) == 0x30
                self.route_effects.append(dict(kind='dialog',arguments=[arg(i) for i in range(1,5)],text=self.bytestring(arg(2)).decode('cp1252'),caption=self.bytestring(arg(3)).decode('cp1252')))
                self.returned(1, 16)
                return
            if address == 0x4a3920:
                destination = arg(1)
                count = 2+len(re.findall(rb'%[dis]',self.bytestring(arg(2))))
                arguments = [arg(i) for i in range(1,count+1)]
                super().fixture(address)
                self.route_effects.append(dict(kind='format',arguments=arguments,text=self.bytestring(destination).decode('cp1252'),caption=''))
                return
        if self.imports.get(address, (0, ''))[1].split('!')[-1] == 'PeekMessageA' and getattr(self, 'route_input', False):
            output, window, minimum, maximum, remove = [arg(i) for i in range(1,6)]
            assert window == 1 and minimum == maximum and remove == 1
            self.physical_events.append(dict(service='PeekMessageA',window=window,minimum=minimum,maximum=maximum,remove=remove,queued=len(self.messages)))
            index = next((i for i,e in enumerate(self.messages) if e[0] == window and (minimum == 0 or minimum == e[1])),None)
            if index is not None:
                event = self.messages.pop(index)
                for i,value in enumerate(event[:3]+[0,0,0,0]):self.put(output+4*i,value)
            self.returned(int(index is not None),20)
            return
        if self.movie and (address == 0x4f766e or address == 0x4f5915 and receiver == self.movie+0x138):
            args = [] if address == 0x4f766e else [arg(1),arg(2)]
            self.route_effects.append(dict(service=f'{address:x}',offset=receiver-self.movie,arguments=args))
            if address == 0x4f766e:
                assert receiver == self.movie+0x124
                for offset,value in [(4,0xffffffff),(8,0),(12,0x52e1c4)]:self.put(receiver+offset,value)
                self.returned(0)
                return
        return super().fixture(address)


def main():
    native = json.loads((WORK/'routes-swift.json').read_text())
    assert [(r['selector'],r['limit']) for r in native['rows'] if r['kind']=='input'] == [(0x100,1),(0x100,64),(0x201,64),(0,64),(0,0),(0,0xffffffff)]
    assert [(r['flags'],r['error']) for r in native['rows'] if r['kind']=='diagnostic'] == [(flags,error) for flags in [[1,1,1,0],[0,0,0,0],[0,0,1,0],[0,0,0,1],[1,0,0,0],[0,1,0,0]] for error in [0x88760064,0x88760230,0x80004005,0x12345678]]
    assert [(r['mode'],r['fx'],r['fy'],r['render']) for r in native['rows'] if r['kind']=='raw'] == [(mode,fx,fy,render) for mode in [1,2,4,8,22,50,0,3,0xffffffff] for fx in [0,1] for fy in [0,1] for render in [0,1]]
    assert [(r['profile'],r['entry']) for r in native['rows'] if r['kind']=='movie'] == [(0,0x4efd00),(0,0x4efd00),(0,0x4efcd0),(0,0x4efcd0),(1,0x4efcd0),(1,0x4efcd0)]
    original, menu, _ = original_initializer(RoutesReference)
    original.instruction_limit = 300_000_000
    original.route_effects = []
    original.diagnostic_jump_reached = False
    application = original.word(menu+4)
    original.put(application+0x2c,menu)
    original.run(0x45b3f0,menu,(0,),phase='route-menu-entry')
    original.messages = [[1,0x100,1,1],[1,0x201,2,1],[1,0x101,4,0],[2,0x100,8,1]]
    original.route_input = True
    expected = []
    movie = pid = 0
    movie_profile = -1
    reached = set()
    native_pointers, original_pointers, cleanup_allocations = {}, {}, {}
    def diagnostic_effects(events,frame):
        return [{**e,'arguments':[f'stack{v-frame:+d}' if frame-0x400<=v<=frame else v for v in e['arguments']]} for e in events]
    try:
        for row in native['rows']:
            kind = row['kind']
            if kind == 'input':
                start = len(original.physical_events)
                original.run(0x4b8910,original.word(application+4),(row['selector'],row['limit']),phase='route-input')
                assert row['pending'] == original.messages, ('input-state',row)
                assert row['held'] == 3
                assert row['effects'] == original.physical_events[start:], ('input-effects',row,original.physical_events[start:])
            elif kind == 'diagnostic':
                original.route_effects = []
                original.diagnostic_active = True
                for i,v in enumerate(row['flags']):original.put(0x54139c+i*4,v)
                original.run(0x4bd260,0,(0x532500,75,row['error']),phase='route-diagnostic')
                original.diagnostic_active = False
                actual = diagnostic_effects(row['effects'],row['frame'])
                wanted = diagnostic_effects(original.route_effects,original.diagnostic_frame)
                assert actual == wanted, ('diagnostic',row['flags'],hex(row['error']),actual,wanted)
            elif kind == 'movie':
                if movie_profile != row['profile']:
                    movie_profile = row['profile']
                    movie = original.allocate(0x14c);array = original.allocate(16);original.movie = movie
                    for i,v in enumerate([1,int(movie_profile==0),1]):original.put(movie+i*4,v)
                    for i,v in enumerate([0x510844,77,1,0x52e1c4,9,0x5108fc,array,4,4,0]):original.put(movie+0x124+i*4,v)
                original.route_effects = []
                result = original.run(row['entry'],movie,phase='route-movie')
                if row['entry'] == 0x4efd00:assert result == row['result']
                observed = [original.word(movie+off) for off in (0,4,8,0x128,0x12c,0x134,0x13c,0x140,0x144)]
                # The live array identity differs; only its presence is semantic.
                actual = list(row['state']);actual[6] = bool(actual[6]);observed[6] = bool(observed[6])
                assert actual == observed, ('movie-state',actual,observed)
                assert row['effects'] == original.route_effects
            elif kind == 'raw':
                if not pid:
                    pid = original.allocate(40);stream = original.allocate(128);rects = original.allocate(32)
                    table = original.allocate(12);table_data = original.allocate(65536)
                    payload = bytes(v for y in range(5) for v in [2,10+y,20+y,130,4,30+y,40+y,50+y,60+y])
                    original.machine.mem_write(stream,payload)
                    for i,v in enumerate([0,3,table_data]):original.put(table+4*i,v)
                    holder = original.word(original.word(menu+12)+4)
                    surface = original.word(original.word(holder+20)+44)
                mode = row['mode']
                original.machine.mem_write(table_data,bytes((i if mode == 50 else (i>>8)^i)&255 for i in range(65536)))
                for i,v in enumerate([row['render'],8,5,stream,len(payload),mode,52,table,0,1]):original.put(pid+i*4,v)
                for i,v in enumerate([1,1,6,4,3,2,10,6]):original.put(rects+i*4,v)
                original.put(0x02008000-56,0x01003000)
                start = len(original.physical_events)
                result = original.run(0x4bffa0,pid,(rects+16,surface,rects,row['fx'],row['fy']),phase='route-raw')
                physical = original.com_objects[original.word(surface+8)]
                digest = hashlib.sha256(original.machine.mem_read(physical['pixels'],physical['pitch']*physical['height'])).hexdigest()
                assert result == row['result'] and digest == row['pixels'], ('raw',mode,row['fx'],row['fy'],row['render'],result,digest,row['pixels'])
                assert row['scratch'] == list(original.machine.mem_read(0x542bb0,129))
                assert row['rects'] == [original.word(rects+i*4) for i in range(8)]
                assert physical_effects(row['effects'],native=True) == physical_effects(original.physical_events[start:]), ('raw-effects',row)
                selected = (0x4c0cc0 if row['fy'] else 0x4c0450) if row['fx'] else (0x4c0920 if row['fy'] else 0x4c00b0)
                if mode != 1:selected = (0x4c4c20 if row['fy'] else 0x4c25b0) if row['fx'] else (0x4c3800 if row['fy'] else 0x4c1190)
                assert selected in row['calls']
                assert 'route-raw' in original.phases.get(selected,set())
                reached.add(selected)
            elif kind == 'flip-diagnostic':
                original.fail_flip = original.diagnostic_active = True
                original.route_effects = []
                for i,v in enumerate([1,1,1,0]):original.put(0x54139c+i*4,v)
                holder = original.word(original.word(menu+12)+4)
                primary = original.word(original.word(holder+16)+44)
                result = original.run(0x4b98b0,primary,(0,),phase='route-flip-diagnostic')
                original.fail_flip = original.diagnostic_active = False
                assert row['request'] == original.flip_request and row['result'] == result
                assert diagnostic_effects(row['effects'],row['frame']) == diagnostic_effects(original.route_effects,original.diagnostic_frame)
                assert 'route-flip-diagnostic' in original.phases[0x4bd260]
            elif kind.startswith('cleanup-'):
                if kind == 'cleanup-before':
                    # Native delivery consumed the other window after the input
                    # witnesses; no synthetic game input is dispatched.
                    original.messages = []
                    assert original.run(0x428b60,application,phase='route-post-branch-frame') == 1
                    cleanup_allocations = original.allocations.copy()
                else:
                    original.run(0x45b050,menu,phase=kind)
                    assert original.word(0x537b58) == 0
                a = normalized(row['state'],native_pointers,lambda off,v:off in row['pointerOffsets'])
                b = normalized(original.machine.mem_read(menu,0x2c8),original_pointers,lambda off,v:any(base<=v<base+size for base,size in cleanup_allocations.items()))
                assert a == b, (kind,[(hex(i*4),x,y) for i,(x,y) in enumerate(zip(a,b)) if x!=y][:12])
                assert row['active'] == bool(original.word(0x537b58))
            else:raise AssertionError(kind)
            expected.append(dict(kind=kind,compared=True))
        assert len(native['rows']) == 112 and len(reached) == 8 and original.diagnostic_jump_reached
        assert [r['kind'] for r in native['rows'][-4:]] == ['flip-diagnostic','cleanup-before','cleanup-state','cleanup-repeat']
        controls = {(r['kind'],r['address']) for r in native['controls']}
        assert controls == ({('owner',x) for x in [0x4bd260,0x4b8910,0x4efd00,0x4efcd0,0x4bc110]} |
            {('physical',x) for x in [0x546ca4,0x546d48,0x4a3920,0x4f766e,0x4f5915]} |
            {('movie-binding',0x4f766e),('diagnostic-resource',0x4bd260),('input-window',0x4b8910)} |
            {('raw-owner',x) for x in [0x4c00b0,0x4c0450,0x4c0920,0x4c0cc0,0x4c1190,0x4c25b0,0x4c3800,0x4c4c20,0x4b9730]} |
            {('raw-physical',0x6e120064),('raw-physical',0x6e120080),('raw-resource',0x4c1190)})
        assert len(native['controls']) == 25 and all(r['rejected'] for r in native['controls'])
        assert native['cleanup'] and native['sharedHeap']
        result=dict(status='compared',routes=len(expected),raw=72,diagnostic=24,input=6,movie=6,
                    diagnostic_jump='0x4bd83f',selected=[hex(x) for x in sorted(reached)],controls=25,cleanup=True)
        (WORK/'routes-result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
    finally:
        for stream in original.files.values():stream.close()


if __name__ == '__main__':main()
