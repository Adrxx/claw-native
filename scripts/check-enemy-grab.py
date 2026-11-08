#!/usr/bin/env python3
"""Enemy lift base calls: original call-site audit and real-key grab/throw in both profiles.

The opt-in app fixture places Claw next to an existing enemy; it never changes
an enemy or carry state. All gameplay actions use delivered window key events.
MPKFA keeps Claw alive during setup; MPSCULLY advances from Level 1 to Level 2.
"""
import argparse
import ctypes as C
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import time

from real_input import Session, build_helper

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'work/enemy-grab'


def tables():
    while float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1]) >= 16:
        time.sleep(10)
    spec = importlib.util.spec_from_file_location('transport_check', ROOT/'scripts/check-level-one-transports.py')
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    lib = shared.build()
    predicate = lib.claw_level_enemy_lift_base_ok
    predicate.argtypes = [C.POINTER(shared.Call), shared.U32, shared.U32]
    predicate.restype = shared.U32
    from Tests.clawparity.program import claw
    program = claw()
    sites = []
    for section in program.sections:
        if section.address >= program.text[1]:
            continue
        for offset in range(len(section.data)-4):
            if section.data[offset] == 0xe8 and section.address+offset+5+struct.unpack_from('<i',section.data,offset+1)[0] == 0x44df10:
                sites.append(section.address+offset)
    assert sites == [0x463358,0x463394,0x484238], sites
    def original_word(address):
        section = next(s for s in program.sections if s.address <= address < s.address+len(s.data))
        return struct.unpack_from('<I',section.data,address-section.address)[0]
    # Both original derived vtables override slot +0x88; neither contains
    # the shared base, explaining why the former membership guard rejects it.
    for table,caller in ((0x50ea0c,0x463310),(0x50f394,0x484210)):
        assert original_word(table+0x88)==caller
        assert 0x44df10 not in [original_word(table+i*4) for i in range(43)]
    checks = 0
    for caller in (0x463310,0x484210):
        q = shared.Call(function=0x44df10,receiver=0x61000000)
        assert predicate(C.byref(q),caller,caller) == 1
        assert predicate(C.byref(q),caller,0x44df10) == 0
        assert predicate(C.byref(q),0x497960,caller) == 0
        checks += 3
        for field in ('function','receiver','receiver2','count','source','compiler','callback_cpu',
                      'callback_activation','x87_count','x87_argument','x87_state','x87_operation','return_pc',
                      'transfer_version','transfer_kind','transfer_site','caller','disposition'):
            bad = shared.Call.from_buffer_copy(q)
            # Field names belong to the shared ABI, and must exist (no silent attributes).
            assert field in dict(shared.Call._fields_), field
            setattr(bad,field,0 if field in ('function','receiver') else 1)
            assert predicate(C.byref(bad),caller,caller) == 0, field
            checks += 1
    return dict(original_call_sites=[hex(s) for s in sites], predicate_checks=checks)


def play(profile):
    out = OUT/profile
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    session = Session(out,fast=True,helper=build_helper(ROOT/'work/cheat-codes/post-window-input'))
    derived = Path(os.environ.get('CLAW_DERIVED_DATA',ROOT/'work/MacCatalyst'))
    marks = []
    failed = False
    def read(name):
        try:
            return json.loads((out/name).read_text())
        except (OSError,ValueError):
            return {}
    def healthy():
        assert not session.failed(), read('real-speed.json').get('error','frame failed')
    def hold(key,seconds):
        session.post('press',key,'down')
        session.sleep(seconds)
        healthy()
        session.post('press',key,'up')
    def code(value):
        keys = {'M':46,'P':35,'S':1,'C':8,'U':32,'L':37,'Y':16,'K':40,'F':3,'A':0}
        for letter in value:
            session.post('key',keys[letter])
    def mark(name):
        value = session.mark(name)
        healthy()
        assert value, name
        marks.append(dict(name=name,player=value['player'],invoke_counts=value.get('invoke_counts',{})))
        return value['player']
    try:
        session.launch(derived/'Build/Products/Release-maccatalyst/Claw.app',
                       {'CLAW_LIVES_BOSS_PROFILE':f'claw-v{profile}','CLAW_GAME_VERSION':profile},
                       ['--save-dir',str(out/'saves'),'--menu-live-check',str(out),
                        '-ClawCheckDirectory',str(out),'--enemy-grab-check'])
        session.sleep(1)
        for _ in range(3):
            session.post('key',36)
            session.sleep(1)
        assert session.wait(lambda: read('live.json').get('level')==1,90), 'New Game not reached'
        code('MPKFA')
        for level in (1,2):
            for name,callback in (('officer',0x462350),('soldier',0x48a980)):
                label=f'level-{level}-{name}'
                # A live enemy can hit Claw during approach. Retry delivered
                # lift presses through that reaction; never force player state.
                for attempt in range(20):
                    session._command(f'grab-place {callback}')
                    session._gate_wait()
                    healthy()
                    # Let the ordinary collision step settle the one-pixel
                    # placement before delivering the edge-triggered lift key.
                    session.sleep(.17)
                    hold(6,.5)
                    carried=mark(label+f'-lift-{attempt}')
                    if carried['grab_check']['held']:
                        break
                    session.sleep(.2)
                grab=carried['grab_check']
                assert grab['held'] == grab['target'] != 0 and grab['held_callback']==callback, (label,'not carrying target',carried)
                before_throw=marks[-1]['invoke_counts']
                hold(124,.2)
                hold(59,.3)
                session.sleep(.5)
                thrown=mark(label+'-thrown')
                assert thrown['grab_check']['held']==0, (label,'not thrown',thrown)
                after_throw=marks[-1]['invoke_counts']
                for entry in ('41b280','44de30'):
                    assert after_throw.get(entry,0)>before_throw.get(entry,0), (label,'throw path not exercised',entry)
                assert carried['level']==level and thrown['level']==level
            if level==1:
                code('MPSCULLY')
                assert session.wait(lambda: read('live.json').get('state_vtable')=='0x50c0c4',90), 'results not reached'
                session.sleep(12)
                session.post('key',36)
                assert session.wait(lambda: read('live.json').get('level')==2 and read('live.json').get('state_vtable')=='0x50c264',90), 'Level 2 not reached'
        counts=read('live-state.json').get('transports',{})
        assert counts.get('enemy-lift-base-direct-463310',0)>=2, counts
        assert session.transitions().get('90:down',0)>=4 and session.transitions().get('17:down',0)>=4
        return dict(profile=profile,status='pass',marks=marks,transports=counts,input=session.input_state())
    except Exception as error:
        failed = True
        return dict(profile=profile,status='fail',error=str(error),marks=marks,runtime=read('real-speed.json'),state=read('live-state.json'))
    finally:
        session.close()
        # JSON retains the evidence. No per-attempt image accumulation.
        for path in out.glob('*.png'):
            if not failed or (path.name != 'frame-fail.png' and (not marks or path.stem != marks[-1]['name'])):
                path.unlink()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tables-only',action='store_true')
    parser.add_argument('--profile',choices=['1.0','1.3'])
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    result=dict(check='enemy-grab',status='fail')
    try:
        result['tables']=tables()
        if not args.tables_only:
            result['play']=[play(profile) for profile in ([args.profile] if args.profile else ['1.3','1.0'])]
            assert all(r['status']=='pass' for r in result['play']), [r.get('error') for r in result['play']]
        result['status']='pass'
    except Exception as error:
        result['error']=str(error)
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='play'}))
    return int(result['status']!='pass')


if __name__=='__main__':
    raise SystemExit(main())
