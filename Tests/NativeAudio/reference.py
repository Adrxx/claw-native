"""Focused original EXE audio service oracle, with native physical PCM storage.

Runs original voice/pool constructors, selection, controls, Play and GetStatus;
no game callee stand-ins. DirectSound and elapsed sample transport are supplied
by NativeMenuBase (outside the admission harness). Original PCM is kept local.
"""
import argparse
import hashlib
import io
import json
import math
import struct
import wave
from pathlib import Path
from unicorn.x86_const import UC_X86_REG_ESP
from Tests.NativeMenuBase.trace import MenuTrace, ROOT
from Tests.NativeObjectConnections.rez import entries, REZ_SHA256


class AudioTrace(MenuTrace):
    def com_fixture(self,address):
        kind,method=self.com_methods[address]
        sp=self.machine.reg_read(UC_X86_REG_ESP)
        obj=self.word(sp+4)
        super().com_fixture(address)
        event=self.physical_events[-1]
        event['clock_ms']=self.milliseconds
        if kind=='IDirectSoundBuffer' and method.startswith('Get'):
            event['value']=self.word(self.word(sp+8))
        if kind=='IDirectSoundBuffer' and method=='Play':
            event['arguments']=[self.word(sp+4*i) for i in (2,3,4)]
        if kind=='IDirectSoundBuffer' and method.startswith('Set'):
            event['value']=self.word(sp+8)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--marks',type=Path,default=ROOT/'work/audio-live/check')
    args=parser.parse_args()
    out=ROOT/'work/audio-live';out.mkdir(exist_ok=True)
    t=AudioTrace(instruction_limit=10_000_000)
    manager=t.allocate(128)
    t.run(0x4b4710,manager,phase='manager-constructor')
    assert t.run(0x4b47e0,manager,(1,1),phase='manager-start')==1
    # Read physical buffers actually reached by the app, then elect their WAV
    # payload by digest, independently of native resource names or addresses.
    digests=set()
    for path in args.marks.glob('*.json'):
        m=json.loads(path.read_text())
        digests.update(e['pcm_sha256'] for e in m.get('audio_lifetimes',{}).get('events',[]) if e.get('service')=='Play')
    wavs={};aliases={};music={}
    for name,payload in entries():
        if name in ('LEVEL1/MUSIC/PLAY0.XMI','GAME/MUSIC/POWERUP0.XMI'):music[name]=payload
        if not name.endswith('.WAV'):continue
        with wave.open(io.BytesIO(payload)) as w:
            raw=w.readframes(w.getnframes());digest=hashlib.sha256(raw).hexdigest()
            if digest in digests:
                aliases.setdefault(digest,[]).append(name)
                wavs[digest]=(name,raw,w.getnchannels(),w.getsampwidth(),w.getframerate())
    result=dict(executable_sha256=t.program.sha256,archive_sha256=REZ_SHA256,voices=[],status='pass')
    for digest,(path,raw,channels,width,rate) in sorted(wavs.items()):
        data=t.allocate(len(raw));t.machine.mem_write(data,raw)
        fmt=struct.pack('<HHIIHHH',1,channels,rate,rate*channels*width,channels*width,width*8,0)
        buffer=t.com_object('IDirectSoundBuffer',data=data,length=len(raw),format=fmt.hex(),volume=0,pan=0,
            frequency=rate,position=0,write_cursor=0,playing=False,locked=None)
        pool=t.allocate(56);t.run(0x4b4200,pool,(buffer,manager),phase='pool-constructor')
        begin=len(t.physical_events)
        assert t.run(0x4b45f0,pool,(80,0,0,0),phase='cue-play')==1
        voice=t.word(pool+0x30)-4
        assert t.run(0x4b3e70,voice,phase='cue-playing')==1
        duration=math.ceil(len(raw)/(channels*width)*1000/rate)
        t.advance_time(t.milliseconds+duration-1)
        before=t.run(0x4b3e70,voice,phase='cue-before-end')
        t.advance_time(t.milliseconds+1)
        after=t.run(0x4b3e70,voice,phase='cue-after-end')
        assert before==1 and after==0,(path,before,after)
        events=t.physical_events[begin:]
        services=[]
        for e in events:
            name=e.get('service','')
            if name.startswith('IDirectSoundBuffer::'):
                services.append(dict(service=name.split('::')[1],**{k:e[k] for k in ('value','arguments') if k in e}))
        result['voices'].append(dict(resource=path,aliases=aliases[digest],pcm_sha256=digest,
            sample_frames=len(raw)//(channels*width),frequency=rate,duration_ms=duration,services=services))
    assert result['voices'],'No live sample identities found in original assets'
    assert set(wavs)==digests,'An observed live cue has no original PCM identity'
    result['volume_table']=[t.word(0x541178+i*4) for i in range(101)]
    # Re-evaluate each live spatial object's inputs through its original
    # callback. Only addresses are rebound; every scalar comes from the mark.
    application=t.allocate(0x140);group=t.allocate(48)
    t.machine.mem_write(application,bytes(0x140));t.machine.mem_write(group,bytes(48))
    scene=t.allocate(48);t.machine.mem_write(scene,bytes(48))
    t.put(application+0x30,scene);t.put(scene+0x28,manager)
    controller=t.allocate(48);t.machine.mem_write(controller,bytes(48))
    t.put(controller+0x2c,manager);t.put(group,controller)
    t.put(0x5371fc,application);t.put(application+0x5c,group)
    result['ambient']=[]
    spatial_marks=[args.marks/'level.json',args.marks/'combat.json',*sorted(args.marks.glob('walk-*.json'))]
    for mark in spatial_marks:
        m=json.loads(mark.read_text())
        for row in m.get('ambient_objects',[]):
            if row['words'][0]!=0x50b01c:continue
            native=next(b for b in m['audio_lifetimes']['buffers'] if b['buffer']==row['buffer'])
            _,raw,channels,width,rate=wavs[native['pcm_sha256']]
            data=t.allocate(len(raw));t.machine.mem_write(data,raw)
            fmt=struct.pack('<HHIIHHH',1,channels,rate,rate*channels*width,channels*width,width*8,0)
            buffer=t.com_object('IDirectSoundBuffer',data=data,length=len(raw),format=fmt.hex(),volume=native['volume'],pan=native['pan'],
                frequency=rate,position=0,write_cursor=0,playing=native['playing'],looping=True,locked=None)
            voice=t.allocate(56);t.run(0x4b3cb0,voice,(buffer,manager),phase='spatial-voice')
            obj=t.allocate(72)
            for i,v in enumerate(row['words']):t.put(obj+4*i,v)
            t.put(obj+4,voice);t.put(application+0x10,m['application_words'][4]);t.put(group+0x24,m['ambient_group'][9])
            p=m['player'];listener=m['ambient_group'][10:12];begin=len(t.physical_events)
            t.run(0x402ac0,obj,(*listener,0),phase='spatial-live-inputs')
            physical=t.com_objects[buffer]
            result['ambient'].append(dict(mark=mark.stem,object=row['object'],x=p['x'],y=p['y'],
                volume=physical['volume'],pan=physical['pan'],playing=physical['playing'],
                services=[e['service'] for e in t.physical_events[begin:]],
                native_volume=native['volume'],native_pan=native['pan'],native_playing=native['playing']))
    # Execute the music branch of the actual power-up handler. The boundary
    # precedes unrelated player/animation changes, rather than stubbing them.
    t.setup_music(application);music_manager=t.word(application+0x50)
    t.setup_volumes(application)
    result['defaults']=dict(music_driver=t.midi_master_volume,sound=t.word(application+0x12c),effects=t.word(0x532c10))
    for name,key in [('LEVEL1/MUSIC/PLAY0.XMI',b'LEVEL'),('GAME/MUSIC/POWERUP0.XMI',b'POWERUP')]:
        payload=music[name];data=t.allocate(len(payload));t.machine.mem_write(data,payload)
        assert t.run(0x4b53f0,music_manager,(data,len(payload),t.cstring(key)),phase='music-register')
    assert t.run(0x4b54f0,music_manager,(t.cstring(b'LEVEL'),0),phase='level-music')
    t.put(application+0x14,1);t.put(0x53c9c0,0);t.put(0x534eac,0)
    result['music']={}
    for name,args_ in [('powerup',(0,0,0,0x26bc,30000)),('expired',(0,0,0,0,0))]:
        begin=len(t.physical_events)
        t.run(0x41f990,0,args_,phase=name,boundary=0x41fa94)
        assert t.paused
        result['music'][name]=[e for e in t.physical_events[begin:] if e['service'].startswith('_AIL_')]
        assert result['music'][name], 'Music branch did not reach its physical services'
        for event in result['music'][name]:event['sha256']=t.sequences[int(event['sequence'],16)]['sha256']
    (out/'original-voices.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='pass',voices=len(result['voices']),executable_sha256=t.program.sha256)))


if __name__=='__main__':main()
