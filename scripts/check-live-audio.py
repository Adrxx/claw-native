"""Muted real-callback audio route; keeps physical speaker acceptance separate.

No deterministic flags: the actual CoreAudio callback advances buffers. Confirmed
window events operate both Audio pages, combat, walking and a timed power-up.
Evidence contains sample identities and bounded callback/status service histories.
"""
import argparse
import json
import os
import shutil
import math
import subprocess
import sys
from pathlib import Path
from real_input import Session, build_helper

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work/audio-live/check'
MAC = {'up':126,'down':125,'left':123,'right':124,'ret':36,'esc':53,'ctrl':59}
LETTERS = {'A':0,'D':2,'F':3,'H':4,'G':5,'V':9,'E':14,'R':15,'T':17,'O':31,'U':32,'I':34,'P':35,'L':37,'J':38,'K':40,'N':45,'M':46,'S':1}


def compare(marks):
    """Compare live callback facts with freshly executed original game code."""
    subprocess.run([sys.executable,'-m','Tests.NativeAudio.reference','--marks',str(WORK)],cwd=ROOT,check=True)
    ref=json.loads((ROOT/'work/audio-live/original-voices.json').read_text())
    def require(ok,message):
        if not ok:raise RuntimeError(message)
    voices={v['pcm_sha256']:v for v in ref['voices']}
    require(ref['defaults']==dict(music_driver=63,sound=80,effects=80),'original defaults changed')
    require(marks['audio']['audio_globals']==[1,80],'native effects defaults differ')
    require(any(e['service']=='546e6c' and e.get('volume')==63 for e in marks['audio']['music_events']['tail']),'native music default differs')
    events={e['index']:e for m in marks.values() for e in m['audio_lifetimes']['events']}
    ordered=[events[k] for k in sorted(events)]
    history={};plays={};completed=[];finished=set();ordered_plays=0;status_after_end=0
    rate=marks['expired']['audio_output']['sample_rate']
    for e in ordered:
        token=e['buffer'];trail=history.setdefault(token,[])
        if e['service']=='Play':
            finished.discard(token)
            require(e['pcm_sha256'] in voices,'unidentified original sample')
            if [x['service'] for x in trail[-3:]]==['SetVolume','SetPan','SetFrequency']:
                # Original 4b45f0 and 4b3dc0 both own this exact request order.
                original=voices[e['pcm_sha256']]['services']
                require([x['service'] for x in original[3:7]]==['SetVolume','SetPan','SetFrequency','Play'],'original request order changed')
                require(trail[-3]['arguments'][0] in ref['volume_table'],'volume outside original table')
                ordered_plays+=1
            frequency=next((x['arguments'][0] for x in reversed(trail) if x['service']=='SetFrequency'),voices[e['pcm_sha256']]['frequency'])
            plays[token]=(e,frequency)
        elif e['service']=='complete':
            require(token in plays,'completion without Play')
            play,frequency=plays.pop(token)
            frames=voices[e['pcm_sha256']]['sample_frames']-play.get('cursor',0)
            expected=math.ceil(frames*rate/frequency)
            actual=e['completion_frame']-play['render_frame']
            require(abs(actual-expected)<=1,f'callback completion {e["pcm_sha256"]}: {actual} vs {expected}')
            completed.append(e['pcm_sha256'])
            finished.add(token)
        elif e['service']=='Stop':plays.pop(token,None)
        elif e['service']=='GetStatus' and token in finished:
            require(e['value']==0,'completed buffer still reports playing');status_after_end+=1
        trail.append(e)
    for name,resource in [('menu','GAME/SOUNDS/CLICK.WAV'),('dialogue','LEVEL1/SOUNDS/TRIGGER/1007.WAV')]:
        require(any(resource in voices[d]['aliases'] for d in completed),name+' cue did not complete on live callback')
    combat_range=(marks['level']['audio_lifetimes']['count'],marks['combat-complete']['audio_lifetimes']['count'])
    require(any(combat_range[0]<e['index']<=combat_range[1] and e['service']=='complete' and
                any(a in ('CLAW/SOUNDS/UPPERCUT1.WAV','CLAW/SOUNDS/UPPERCUT2.WAV','CLAW/SOUNDS/SWORDSWISH.WAV')
                    for a in voices[e['pcm_sha256']]['aliases']) for e in ordered),'combat cue did not complete on live callback')
    require(ordered_plays>=10 and status_after_end>0,'missing play ordering or completion/reuse GetStatus')
    require(ref['ambient'],'no original spatial comparison')
    for row in ref['ambient']:
        require(all(row[k]==row['native_'+k] for k in ('volume','pan','playing')),'spatial callback differs: '+str(row))
    varied={(r['volume'],r['pan']) for r in ref['ambient'] if 'IDirectSoundBuffer::SetVolume' in r['services']}
    require(len(varied)>=3,'walking did not vary spatial attenuation')
    require(len({v for v,p in varied})>=2,'route never changed the spatial volume band')
    # Compare all AIL calls (including status results and sequence identity),
    # not just the final selected song. The native driver's clock is separate
    # from speaker synthesis, which remains detached while muted.
    api={'_AIL_sequence_status@4':'546e7c','_AIL_stop_sequence@4':'546e84','_AIL_end_sequence@4':'546e78',
         '_AIL_start_sequence@4':'546e90','_AIL_set_sequence_loop_count@8':'546e88','_AIL_resume_sequence@4':'546e80'}
    previous=marks['walk-complete']
    elapsed=[]
    for name in ('powerup','expired'):
        mark=marks[name];count=mark['music_events']['count']-previous['music_events']['count']
        tail=mark['music_events']['tail'][-count:] if count else []
        sha={e['handle']:e['sha256'] for e in mark['music_events']['tail'] if e['service']=='initialize'}
        got=[(e['service'],e['status'],sha.get(e['handle'])) for e in tail]
        expected=[(api[e['service']],e['status'],e['sha256']) for e in ref['music'][name]]
        require(got==expected,name+' music services differ: '+str(got))
        elapsed.append(tail[0]['clock_ms']);previous=mark
    require(29900<=elapsed[1]-elapsed[0]<=30200,'power-up did not expire at 30 s')
    require(marks['expired']['audio_output']['nonzero_frames']>marks['level']['audio_output']['nonzero_frames'],'no live pre-mute PCM')
    return dict(original_pcm_resources=len(voices),completed_cues=len(completed),ordered_plays=ordered_plays,
                completion_status_queries=status_after_end,spatial_comparisons=len(ref['ambient']),spatial_values=len(varied),
                attenuation_values=len({v for v,p in varied}),
                powerup_ms=elapsed[1]-elapsed[0],speaker_acceptance='not performed',offline_pcm='separate music-render check')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default=os.environ.get('CLAW_CONFIG','Release'))
    parser.add_argument('--compare-only',action='store_true',help='recheck retained live marks against the original')
    args = parser.parse_args()
    if args.compare_only:
        result=compare({p.stem:json.loads(p.read_text()) for p in WORK.glob('*.json') if 'audio_lifetimes' in json.loads(p.read_text())})
        print(json.dumps(dict(check='live-audio-comparison',status='pass',**result)));return 0
    shutil.rmtree(WORK,ignore_errors=True);WORK.mkdir(parents=True)
    helper = build_helper(ROOT/'work/audio-live/post-window-input')
    app = ROOT/f'{os.environ.get("CLAW_DERIVED_DATA","work/MacCatalyst")}/Build/Products/{args.config}-maccatalyst/Claw.app'
    s = Session(WORK,fast=False,helper=helper)
    result = dict(check='live-audio',status='fail',errors=[],marks=[])
    marks = {}
    def live():
        try:return json.loads((WORK/'live.json').read_text())
        except (OSError,ValueError):return {}
    def require(ok,message):
        if not ok:raise RuntimeError(message)
    def tap(key,n=1):
        for _ in range(n):s.post('key',MAC.get(key,LETTERS.get(key)));s.sleep(.16)
    def mark(name):
        m=s.mark(name);require(m is not None,'missing mark '+name)
        marks[name]=m;result['marks'].append(name)
        output=m.get('audio_output',{})
        require(output.get('enabled') and output.get('running'),'real callback disabled at '+name)
        require(output.get('muted') and output.get('mixer_volume')==0 and not output.get('music_attached'),'mute isolation '+name)
        return m
    def select(item):
        for _ in range(12):
            if live().get('menu_selected')==item:return
            tap('down')
        raise RuntimeError(f'cannot select {item}: {live().get("menu_selected")}')
    try:
        s.launch(app,{'CLAW_AUDIO_EVIDENCE':'1'},['--save-dir',str(WORK/'saves'),'--settings-dir',str(WORK/'settings'),'-ClawCheckDirectory',str(WORK)])
        require(s.wait(lambda:live().get('menu_selected')==10001,30),'main menu not ready')
        mark('menu');tap('down');mark('menu-cue');s.sleep(2);mark('menu-complete')
        select(10004);tap('ret');select(13004);tap('ret');mark('audio')
        for key,name in [('left','sv72'),('right','sv80'),('right','sv80-clamp'),('ret','sound-off'),('left','sound-off-left'),('ret','sound-on'),
                         ('down',None),('ret','voice-off'),('ret','voice-on'),('down',None),('ret','amb-off'),('ret','amb-on'),
                         ('down',None),('right','mv60'),('left','mv50'),('ret','music-off'),('right','music-off-right'),('ret','music-on')]:
            tap(key)
            if name:mark(name)
        tap('esc',2);select(10001);tap('ret',3)
        require(s.wait(lambda:live().get('state_vtable')=='0x50c264' and live().get('game_ms',0)>1800,60),'Level 1 did not start')
        mark('level');tap('ctrl');mark('combat');s.sleep(2);mark('combat-complete')
        s.post('press',124,'down')
        s.post('key',49)  # Jump while walking: sample multiple distance/volume bands, not just pan.
        for i in range(8):s.sleep(.06);mark(f'walk-{i}')
        s.sleep(3.5)
        s.post('press',124,'up');s.sleep(3);mark('walk-complete')
        for c in 'MPVADER':tap(c)
        mark('powerup');s.sleep(35);mark('expired')
        require('0x808e' in live().get('posted_commands',[]),'MPVADER not delivered')
        # Static source defaults and values are independently exercised by the
        # in-game checker; these observations cover the main-menu owner.
        for name,offset,value in [('audio',0x12c,80),('sv72',0x12c,72),('sv80',0x12c,80),('sv80-clamp',0x12c,80),
             ('sound-off',0x10,0),('sound-off-left',0x12c,80),('sound-on',0x10,1),('voice-off',0x118,0),('voice-on',0x118,1),
             ('amb-off',0x11c,0),('amb-on',0x11c,1),('music-off',0x14,0),('music-on',0x14,1)]:
            require(marks[name]['application_words'][offset//4]==value,f'{name}: application +{offset:x} != {value}')
        for name,value in [('mv60',76),('mv50',63)]:
            require(any(e.get('service')=='546e6c' and e.get('volume')==value for e in marks[name]['music_events']['tail']),name+' driver volume')
        require(marks['sound-off']['audio_output']['active_voices']==0,'Sound off left a live voice')
        require(marks['sound-off-left']['audio_output']['play_requests']==marks['sound-off']['audio_output']['play_requests'],'Sound off did not suppress requests')
        require(marks['music-off-right']['music_events']['count']==marks['music-off']['music_events']['count'],'Music off Right changed the driver')
        result['status']='pass'
    except Exception as error:
        result['errors'].append(str(error))
    finally:s.close()
    if not result['errors']:
        try:result['comparison']=compare(marks)
        except Exception as error:result['errors'].append(str(error));result['status']='fail'
    result['scope']='Real CoreAudio callback, muted final mixer; original request/lifetime/spatial/music service comparisons. Offline synth PCM and speaker acceptance are separate.'
    (WORK/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    return int(result['status']!='pass')


if __name__=='__main__':raise SystemExit(main())
