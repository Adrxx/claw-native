#!/usr/bin/env python3
"""Verify Comment import and old-key behavior in isolated, muted app launches."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from real_input import Session,build_helper
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'work/save-load'))
import usr
OUT=ROOT/'work/v13-profile-import'
KEY=r'HKEY_LOCAL_MACHINE\Software\Monolith Productions\Claw\1.0'

def main():
    if float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1])>=16:
        raise SystemExit('Wait until load is below 16')
    app=ROOT/Path(os.environ.get('CLAW_DERIVED_DATA','work/MacCatalyst'))/'Build/Products/Release-maccatalyst/Claw.app'
    helper=build_helper(ROOT/'work/post-window-input')
    OUT.mkdir(parents=True,exist_ok=True)
    results=[]
    def run(name,values,selected,comment,seed=None):
        out=OUT/name
        if out.exists():shutil.rmtree(out)
        (out/'settings').mkdir(parents=True);(out/'saves').mkdir()
        if seed is not None:(out/'saves/CLAW.USR').write_bytes(seed)
        settings={k:{'type':1,'hex':(v.encode('ascii')+b'\0').hex()} for k,v in values.items()}
        path=out/'settings/registry.json';path.write_text(json.dumps({KEY:settings}))
        session=Session(out,fast=True,helper=helper)
        def live():return json.loads((out/'live.json').read_text())
        def tap(key):session.post('key',key);session.run(24)
        try:
            session.launch(app,{},['--no-paper-startup','--menu-live-check',str(out),'--settings-dir',str(out/'settings'),'--save-dir',str(out/'saves')])
            session.run(1)
            assert any(p['name']==selected and p['selected'] for p in live()['profiles']),live()
            # A real New Player confirmation requests persistence, allowing the
            # imported record to be checked in the actual CLAW.USR bytes.
            for code in [125,125,36,36,45,17,14,46,35,48,37,36]:tap(code)
            saved=(out/'saves/CLAW.USR').read_bytes();records=usr.decode(saved)
            record=next(r for r in records['records'] if r['name']==selected)
            assert records['valid'] and record['email']==comment,record
            stored=json.loads(path.read_text())[KEY]
            if 'User Email' in values:assert stored['User Email']==settings['User Email']
            if selected=='IMPORT' and values.get('User')!='IMPORT':
                assert all(k not in stored for k in ('User Name','User Location','User Comment'))
            if values.get('User')=='IMPORT':assert stored['User Comment']==settings['User Comment']
            results.append({'scenario':name,'selected':selected,'comment':record['email'],'input_transitions':session.transitions(),'retries':session.retries})
            return saved
        finally:session.close()
    seed=run('comment',{'User Name':'IMPORT','User Location':'PLACE','User Comment':'COMMENT','User Email':'IGNORED'},'IMPORT','COMMENT')
    run('email-only',{'User Email':'LEGACY'},'Player','')
    run('old-third-field',{'User Name':'LEGACY','User Location':'PLACE','User Email':'LEGACY'},'LEGACY','')
    # Reusing TEMP exercises duplicate creation: it still requests a save
    # and leaves the existing imported record and selection unchanged.
    run('existing-name',{'User Name':'IMPORT','User Location':'CHANGED','User Comment':'REPLACE'},'IMPORT','COMMENT',seed)
    run('stored-user-first',{'User':'IMPORT','User Name':'OTHER','User Location':'PLACE','User Comment':'PENDING'},'IMPORT','COMMENT',seed)
    result={'status':'pass','check':'v13_profile_import_app','scenarios':results}
    (OUT/'check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
