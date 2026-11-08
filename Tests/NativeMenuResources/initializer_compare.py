"""Focused retail/Swift shared-heap menu initializer comparison (no frames)."""
import hashlib
import json
import struct
from collections import Counter
from .compare import WORK
from Tests.NativeMenuBase.trace import MenuTrace, UC_X86_REG_EAX, UC_X86_REG_ESP
from Tests.NativeMenuBase.native_join import interface_nodes


def original_initializer(reference_type=MenuTrace):
    class SharedHeapReference(reference_type):
        def hook(self, machine, address, size, user):
            if address == 0x45ace0:
                self.initializer_effect_start = len(self.physical_events)
            return super().hook(machine,address,size,user)

        def fixture(self,address):
            sp=self.machine.reg_read(UC_X86_REG_ESP)
            argument=self.word(sp+4)
            slot=self.imports.get(address,(address,''))[0]
            super().fixture(address)
            names={0x546ce4:'GetAsyncKeyState',0x546d9c:'SetCursorPos',
                   0x546c44:'GetSystemMetrics',0x546a24:'GetTickCount',0x546df0:'timeGetTime'}
            if slot in names:
                event=dict(service=names[slot])
                if slot==0x546d9c:event['position']=list(self.cursor)
                else:
                    event['result']=self.machine.reg_read(UC_X86_REG_EAX)
                    if slot==0x546ce4:event['key']=argument
                    if slot==0x546c44:event['index']=argument
                self.physical_events.append(event)

        def com_fixture(self,address):
            kind,method=self.com_methods[address]
            sp=self.machine.reg_read(UC_X86_REG_ESP)
            args=[self.word(sp+4*i) for i in range(1,9)]
            descriptor=bytes(self.machine.mem_read(args[1],108)) if method=='CreateSurface' else None
            start=len(self.physical_events)
            super().com_fixture(address)
            event=self.physical_events[start]
            if descriptor is not None:
                event.update(descriptor_sha256=hashlib.sha256(descriptor).hexdigest(),surface=self.word(args[2]))
            if kind=='IDirectDrawSurface' and method=='Lock':event['flags']=args[3]
            if kind=='IDirectSoundBuffer' and method=='Lock':event.update(offset=args[1],length=args[2])
            if kind=='IDirectSoundBuffer' and method=='Play':event['arguments']=args[1:4]
            if method=='WaitForVerticalBlank':event['flags']=args[1]
            if method=='SetColorKey':event.update(flags=args[1],range=[self.word(args[2]),self.word(args[2]+4)])
        def allocate(self, size):
            token=super().allocate(size)
            # Elect the actual Swift heap's zero-filled physical allocation
            # policy on both sides; no game-owned byte is copied from Swift.
            self.machine.mem_write(token,bytes(max(size,1)))
            return token
    original = SharedHeapReference()
    # Match the native MFC transport's immutable process-wide empty CString.
    original.empty_string = 0x52e1c4
    original.run(0x45acb0, 0, phase='menu-static-initialization')
    original.setup_version()
    application = original.allocate(0x134)
    original.run(0x4254a0, application, phase='application-construction')
    scene = original.allocate(0x3c)
    original.shared_scene = scene
    original.run(0x4ce960, scene, phase='scene-construction')
    assert original.run(0x4cea10, scene, (1, 640, 480, 8, 0), phase='scene-initialization') == 1
    original.setup_resources(application, scene)
    start = len(original.physical_events)
    original.run(0x428c40, application, (5, 1, 1, 0), phase='menu-initialization', boundary=0x429335)
    assert original.paused and original.machine.reg_read(UC_X86_REG_EAX) == 1
    menu = int(original.initializer_return['receiver'], 16)
    return original, menu, original.initializer_effect_start


def physical_effects(events,native=False):
    """Compare external physical effects; storage layout is checked separately.

    CRT/MFC allocation, strings and containers are native implementation details.
    All reached COM methods, input/clock/random services, archive reads and MIDI
    services are retained in one ordered stream, with identities renamed only.
    """
    midi={'allocate':'_AIL_allocate_sequence_handle@4','initialize':'_AIL_init_sequence@12',
          '546e7c':'_AIL_sequence_status@4','546e78':'_AIL_end_sequence@4',
          '546e84':'_AIL_stop_sequence@4','546e88':'_AIL_set_sequence_loop_count@8'}
    fields={
        'DirectDrawCreate':('object','output'),
        'graphics-failure':('function','result'),
        'IDirectDraw::SetDisplayMode':('object','mode'),
        'IDirectDraw::GetDisplayMode':('object',),
        'IDirectDrawSurface::GetAttachedSurface':('object',),
        'IDirectDrawSurface::BltFill':('object','flags','fill_color'),
        'PostMessageA':('window','message','wparam','lparam'),
        'IDirectDraw::CreateSurface':('object','surface','descriptor_sha256'),
        'IDirectDrawSurface::GetSurfaceDesc':('object',),
        'IDirectDrawSurface::SetColorKey':('object','flags','range'),
        'IDirectDrawSurface::IsLost':('object',),
        'IDirectDrawSurface::Release':('object',),
        'IDirectDrawSurface::BltFast':('object','source','rectangle','destination','flags','pixels_sha256'),
        'IDirectDrawSurface::Blt':('object','source','source_rectangle','destination_rectangle','flags'),
        'IDirectDrawSurface::Flip':('object','flags','pixels_sha256'),
        'IDirectDrawSurface::GetDC':('object','dc'),
        'IDirectDrawSurface::ReleaseDC':('object','dc','pixels_sha256'),
        'SetBkMode':('dc','previous','value'),
        'SetTextColor':('dc','previous','value'),
        'DrawTextA':('dc','text','rectangle','flags','palette_index','pixels_sha256'),
        'IDirectDrawSurface::Lock':('object','flags'),
        'IDirectDrawSurface::Unlock':('object','pixels_sha256'),
        'IDirectDraw::CreatePalette':('object','palette','entries_sha256'),
        'IDirectDraw::WaitForVerticalBlank':('object','flags'),
        'IDirectDrawSurface::SetPalette':('object','palette'),
        'IDirectDrawPalette::GetEntries':('object','start','count','entries_sha256'),
        'IDirectDrawPalette::SetEntries':('object','start','count','entries_sha256'),
        'IDirectSound::CreateSoundBuffer':('buffer','length','format_sha256'),
        'IDirectSoundBuffer::Lock':('object','offset','length'),
        'IDirectSoundBuffer::Unlock':('object','pcm_sha256'),
        'IDirectSoundBuffer::GetVolume':('object',),
        'IDirectSoundBuffer::GetStatus':('object',),
        'IDirectSoundBuffer::Play':('object','arguments'),
        'IDirectSoundBuffer::GetPan':('object',),
        'IDirectSoundBuffer::GetFrequency':('object',),
        'IDirectSoundBuffer::SetVolume':('object','value'),
        'IDirectSoundBuffer::SetPan':('object','value'),
        'IDirectSoundBuffer::SetFrequency':('object','value'),
        'IDirectSoundBuffer::Stop':('object','value'),
        'CRT fread':('offset','requested','bytes','sha256'),
        'CRT rand':('state','result'),
        'CRT atexit':('callback',),
        'GetCursorPos':('position',),'ShowCursor':('show','count'),
        'SetCursorPos':('position',),'GetAsyncKeyState':('key','result'),
        'GetSystemMetrics':('index','result'),
        'PeekMessageA':('window','minimum','maximum','remove','queued'),
        'GetTickCount':('result',),'timeGetTime':('result',),
        '_AIL_allocate_sequence_handle@4':(),
        '_AIL_init_sequence@12':('bytes','events','duration_ticks','sha256'),
        '_AIL_sequence_status@4':('status',),'_AIL_end_sequence@4':('status',),
        '_AIL_stop_sequence@4':('status',),'_AIL_set_sequence_loop_count@8':('status',),
    }
    pointers={};result=[]
    for raw in events:
        e=dict(raw);name=e['service']
        if native:
            name={'read':'CRT fread',**midi}.get(name,name)
            if 'ticks' in e:e['duration_ticks']=e['ticks']
        if name=='IDirectDrawSurface::Blt' and 'fill_color' in e:name='IDirectDrawSurface::BltFill'
        if name not in fields:
            assert not native and name in {'CMapStringToPtr RemoveKey','CMemFile Attach','CArchive destructor'},name
            continue
        if name=='IDirectSound::CreateSoundBuffer' and not native:
            e['format_sha256']=hashlib.sha256(bytes.fromhex(e['format'])).hexdigest()
        if not native and name.startswith('IDirectSoundBuffer::Set'):
            e['value']=e[name.split('::Set')[1].lower()] & 0xffffffff
        if name=='IDirectSoundBuffer::Stop':e['value']=0
        row={'service':name}
        for key in fields[name]:
            value=e[key]
            if isinstance(value,tuple):value=list(value)
            if key in ('object','surface','palette','buffer','source','dc','output'):
                if isinstance(value,str):value=int(value,16)
                value=pointers.setdefault(value,f'object-{len(pointers)}')
            row[key]=value
        result.append(row)
    return result


def normalized(data, pointers, is_pointer):
    data = bytes(data)
    assert len(data) % 4 == 0
    words = list(struct.unpack('<'+'I'*(len(data)//4), data))
    for i, value in enumerate(words):
        if is_pointer(i*4,value):
            words[i] = pointers.setdefault(value, f'pointer-{len(pointers)}')
    return words


def native_routes(events):
    """Exact elected native packet routes, alongside the ordered effect proof."""
    packets={
        'IDirectDraw::CreateSurface':('6e120018',4),
        'IDirectDrawSurface::GetSurfaceDesc':('6e120058',2),
        'IDirectDrawSurface::Lock':('6e120064',5),
        'IDirectDrawSurface::Unlock':('6e120080',2),
        'IDirectDrawSurface::SetColorKey':('6e120074',3),
        'IDirectDrawSurface::IsLost':('6e120060',1),
        'IDirectDrawSurface::Release':('6e120008',1),
        'IDirectDrawSurface::BltFast':('6e12001c',6),
        'IDirectDraw::CreatePalette':('6e100014',5),
        'IDirectDrawSurface::SetPalette':('6e10027c',2),
        'GetCursorPos':('546cd0',1),'GetTickCount':('546a24',0),
        '_AIL_allocate_sequence_handle@4':('546e9c',1),
        '_AIL_init_sequence@12':('546e98',3),
        'CRT fread':('4a7260',4),
    }
    typed={
        'IDirectSound::CreateSoundBuffer':'ClawAudioResourceHost.createBuffer(context, device, formatBytes, byteCount, output)',
        'IDirectSoundBuffer::GetFrequency':'ClawAudioResourceHost.get(context, buffer, method=0x20, output)',
        'IDirectSoundBuffer::GetPan':'ClawAudioResourceHost.get(context, buffer, method=0x1c, output)',
        'IDirectSoundBuffer::GetVolume':'ClawAudioResourceHost.get(context, buffer, method=0x18, output)',
        'IDirectSoundBuffer::Lock':'ClawAudioPCMHost.lock(context, buffer, offset, byteCount, flags, regions)',
        'IDirectSoundBuffer::Unlock':'ClawAudioPCMHost.unlock(context, buffer, regions)',
        'PeekMessageA':'ClawNativeWindowInputQueue.drain via 0x4b8910 thiscall(message, maximum); receiver+4 reread per query',
    }
    rows=[]
    for service,count in sorted(Counter(e['service'] for e in events).items()):
        if service in packets:
            address,argc=packets[service]
            rows.append(dict(service=service,count=count,function='0x'+address,receiver=0,arguments=argc,
                             abi='32-bit physical packet; COM self is argument zero'))
        else:
            assert service in typed,service
            rows.append(dict(service=service,count=count,abi=typed[service]))
    return rows


def main():
    witness = json.loads((WORK/'initializer-swift.json').read_text())
    original, menu, start = original_initializer()
    try:
        state = list(original.machine.mem_read(menu, 0x2c8))
        pointers_native, pointers_original = {}, {}
        def original_pointer(offset,value):
            return any(base<=value<base+size for base,size in original.allocations.items())
        native = normalized(witness['state'], pointers_native,lambda off,v:off in witness['pointerOffsets'])
        reference = normalized(state, pointers_original,original_pointer)
        mismatches = [dict(offset=hex(i*4),native=a,original=b) for i,(a,b) in enumerate(zip(native,reference)) if a!=b]
        (WORK/'initializer-state-differences.json').write_text(json.dumps(mismatches,indent=2)+'\n')
        (WORK/'initializer-original-state.json').write_text(json.dumps(state)+'\n')
        assert not mismatches, json.dumps(mismatches[:20])
        tokens = [original.word(menu+off) for off in (0x258,0x25c,0x260,0x264,0x268,0x270,0x274,0x278)]
        tokens += [original.word(original.word(menu+0x26c)+4*i) for i in range(15)]
        actor_mismatches=[]
        for index,(token,actor) in enumerate(zip(tokens,witness['actors'])):
            assert len(actor['data']) == original.allocations[token]
            a=normalized(actor['data'],pointers_native,lambda off,v:off in actor['pointerOffsets'])
            b=normalized(original.machine.mem_read(token,len(actor['data'])),pointers_original,original_pointer)
            actor_mismatches += [dict(actor=index,offset=hex(i*4),native=x,original=y) for i,(x,y) in enumerate(zip(a,b)) if x!=y]
        (WORK/'initializer-actor-differences.json').write_text(json.dumps(actor_mismatches,indent=2)+'\n')
        assert not actor_mismatches,json.dumps(actor_mismatches[:20])
        world=original.word(original.shared_scene+0x24)
        assert normalized(witness['world'],pointers_native,lambda off,v:off in witness['worldPointerOffsets'])==normalized(original.machine.mem_read(world,0xe0),pointers_original,original_pointer)
        original.menu=menu
        nodes=[]
        for node in interface_nodes(original):
            selected=[]
            for surface in node['selected']:
                physical=original.com_objects[original.word(int(surface['surface'],16)+8)]
                pixels=original.machine.mem_read(physical['pixels'],physical['pitch']*physical['height'])
                selected.append(dict(width=physical['width'],height=physical['height'],sha256=hashlib.sha256(pixels).hexdigest()))
            nodes.append({**{k:node[k] for k in ('depth','id','name','children','images')},'selected':selected})
        assert nodes==witness['nodes']
        keys=('offset','requested','bytes','sha256')
        original_reads=[{k:e[k] for k in keys} for e in original.physical_events if e['service']=='CRT fread']
        native_reads=[{k:e[k] for k in keys} for e in witness['reads'] if e['service']=='read']
        assert native_reads==original_reads,(len(native_reads),len(original_reads),next(((i,a,b) for i,(a,b) in enumerate(zip(native_reads,original_reads)) if a!=b),None))
        (WORK/'initializer-original-physical.json').write_text(json.dumps(original.physical_events[start:],indent=2)+'\n')
        expected=physical_effects(original.physical_events[start:])
        observed=physical_effects(witness['physicalEffects'],native=True)
        (WORK/'initializer-original-effects.json').write_text(json.dumps(expected,indent=2)+'\n')
        (WORK/'initializer-native-effects.json').write_text(json.dumps(observed,indent=2)+'\n')
        differences=[dict(index=i,native=a,original=b) for i,(a,b) in enumerate(zip(observed,expected)) if a!=b]
        assert observed==expected,(len(observed),len(expected),differences[:3])
        cleanup=json.loads((WORK/'initializer-cleanup.json').read_text())
        assert all(cleanup[k]==0 for k in ('cleanupFault','resourceFault','cleanupRemaining','displayFault'))
        controls=json.loads((WORK/'initializer-controls.json').read_text())
        assert {(e['kind'],e['address']) for e in controls}=={
            ('owner','4cace0'),('owner','4ce0d0'),('owner','4dcdf0'),
            ('physical','4f1d90'),('physical','4a7260'),('physical','546e98'),
            ('physical','6e120018'),('physical','6e100014'),
            ('resource','0'),('cleanup-owner','429530')}
        assert all(e['rejected'] for e in controls)
        world=original.word(original.shared_scene+0x24)
        original.run(0x4cdd30,world,phase='world-cleanup')
        world_bytes=list(original.machine.mem_read(world,0xe0))
        differences=[dict(offset=hex(i),native=a,original=b) for i,(a,b) in enumerate(zip(cleanup['destroyedWorld'],world_bytes)) if a!=b]
        (WORK/'initializer-world-cleanup-differences.json').write_text(json.dumps(differences,indent=2)+'\n')
        assert not differences,differences
        result=dict(status='compared',initializer='0x45ace0',state_bytes=len(state),actors=len(tokens),nodes=len(nodes),image_selections=sum(len(n['selected']) for n in nodes),ordered_reads=len(native_reads),ordered_physical_effects=len(observed),controls=len(controls),world_state_bytes=0xe0,world_destructor_bytes=0xe0,frames=0)
        result['native_physical_routes']=native_routes(observed)
        (WORK/'initializer-result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
    finally:
        for stream in original.files.values():stream.close()


if __name__=='__main__':main()
