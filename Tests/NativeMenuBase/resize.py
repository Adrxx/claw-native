"""Original/native resize join, including physical allocation failure.

The original runs every game instruction and its actual application error
virtual. Native uses canonical game owners and native shutdown transport.
"""
import json
from Tests.NativeMenuBase import trace as reference
from Tests.NativeMenuBase.native_join import NativeJoin, physical_events, WORK

BOUNDARIES = {0x4bb870:0, 0x42d590:4, 0x4b97c0:1, 0x4b98b0:1,
              0x4cf020:3, 0x4ca960:3, 0x4cb670:2, 0x4d6690:0,
              0x4bb8c0:1, 0x4c9bd0:0, 0x4bbd90:4, 0x4b90b0:2}


def state(host):
    app=host.application
    error=host.word(app+8)
    scene=host.word(app+0x30)
    world=host.word(scene+0x24)
    return dict(application=host.machine.mem_read(app+0x68,0x24).hex(),
                menu=host.machine.mem_read(host.menu,0x2c8).hex(),
                scene=host.machine.mem_read(scene,0x3c).hex(),
                camera=host.machine.mem_read(world+0xc8,0x18).hex(),
                error=host.machine.mem_read(error+0x244,0x10).hex())


def observe(host,address,receiver,args):
    if getattr(host,'watch_resize',False) and address in BOUNDARIES:
        host.resize_observations.append(dict(function=hex(address),receiver=hex(receiver),
                                            arguments=args,state=state(host)))


class OriginalResize(reference.MenuTrace):
    def hook(self,machine,address,size,user):
        if address in BOUNDARIES and getattr(self,'watch_resize',False):
            sp=machine.reg_read(reference.UC_X86_REG_ESP)
            observe(self,address,machine.reg_read(reference.UC_X86_REG_ECX),
                    [self.word(sp+4+4*i) for i in range(BOUNDARIES[address])])
        super().hook(machine,address,size,user)


class NativeResize(NativeJoin):
    def service(self,unused,pointer):
        q=pointer.contents
        observe(self,q.function,q.receiver,list(q.arguments[:q.count]))
        return super().service(unused,pointer)


def close(host):
    if isinstance(host,NativeJoin):host.close()
    else:
        for stream in host.files.values():stream.close()


def exercise(host):
    host.frame_count=0
    NativeJoin.execute(host)
    host.clock_step=100
    host.resize_observations=[]
    host.watch_resize=True
    error_receiver=host.word(host.application+8)
    assert host.word(host.word(error_receiver)+0x1c)==0x4b90b0
    rows=[]
    for name,address,args in [('unforced-same-size',0x42a000,(0,)),
                              ('forced-same-size',0x42a000,(1,)),
                              ('changed-size',0x42a060,(800,600)),
                              ('failed-resize',0x42a000,(1,)),
                              ('latched-error',0x429e10,(0x1234,0x5678))]:
        if name=='failed-resize':host.fail_primary_creation=True
        start=len(physical_events(host));boundary=len(host.resize_observations)
        result=host.run(address,host.application,args,phase=name)
        # reportDiagnostic is semantic void; its incidental EAX is not a result.
        row=dict(name=name,result=result if address!=0x429e10 else None,state=state(host),
                 boundaries=host.resize_observations[boundary:],
                 services=physical_events(host)[start:],
                 allocations=host.allocations.copy())
        rows.append(row)
        if name=='unforced-same-size':assert result==1 and not row['services'] and not row['boundaries']
        if name=='failed-resize':
            assert result==0 and not host.fail_primary_creation
            assert [host.word(error_receiver+i) for i in (0x244,0x248,0x24c,0x250)]==[0,1,0x8008,0x403]
            assert any(e.get('result')==0x8007000e for e in row['services'])
            assert [e['arguments'] for e in row['boundaries'] if e['function']=='0x4b90b0']==[[0x8008,0x403]]
            assert any(e['service']=='PostMessageA' for e in row['services'])
        if name=='latched-error':
            assert row['state']==rows[-2]['state'] and not row['services']
    return rows


def compare(library,entries):
    report=dict(status='blocked')
    original=OriginalResize();native=NativeResize(library,entries,frame_count=0)
    try:
        expected=exercise(original)
        (WORK/'resize-original.json').write_text(json.dumps(expected,indent=2)+'\n')
        actual=exercise(native)
        (WORK/'resize-native.json').write_text(json.dumps(actual,indent=2)+'\n')
        checks={a['name']:{key:a[key]==b[key] for key in ('result','state','boundaries','services','allocations')}
                for a,b in zip(expected,actual)}
        report['comparisons']=checks
        if not all(all(row.values()) for row in checks.values()):
            raise reference.Blocked('Resize comparison mismatch: '+str(checks))
        report['controls']=controls(library,entries)
        report['status']='compared'
        report['actual_error_virtual_target']='0x4b90b0'
        report['actual_error_receiver']=hex(original.word(original.application+8))
    except Exception as error:
        report['error']=str(error)
        report['native_calls']=list(native.native_calls)
        report['original_recent']=[hex(x) for x in original.recent]
    finally:
        close(original);close(native)
    (WORK/'resize.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('native_calls','original_recent')}))
    return 0 if report['status']=='compared' else 2


def controls(library,entries):
    results={}
    for name in ('missing-type','missing-resize-owner','missing-error-owner',
                 'missing-create-service','missing-close-service'):
        host=NativeResize(library,entries,frame_count=0)
        try:
            NativeJoin.execute(host);host.clock_step=100
            error=host.word(host.application+8)
            if name in ('missing-error-owner','missing-close-service'):
                assert host.run(0x42a060,host.application,(800,600),phase='control-prepare')==1
                host.fail_primary_creation=True
            if name=='missing-type':host.deny_owner=0x4c9bd0
            elif name=='missing-resize-owner':host.deny_owner=0x4d5720
            elif name=='missing-error-owner':host.deny_owner=0x4b90b0
            elif name=='missing-create-service':
                host.deny_platform=next(a for a,m in host.com_methods.items() if m==('IDirectDraw','CreateSurface'))
            else:host.deny_platform=next(a for a,(slot,_) in host.imports.items() if slot==0x546d50)
            try:
                if name in ('missing-resize-owner','missing-create-service'):
                    host.run(0x42a060,host.application,(800,600),phase=name)
                else:host.run(0x42a000,host.application,(1,),phase=name)
            except reference.Blocked as failure:
                if 'deliberately withheld' not in str(failure):raise
                assert host.word(error+0x24c)==0 and host.word(error+0x250)==0
                assert host.word(error+0x248)==(1 if name=='missing-close-service' else 0)
                results[name]=str(failure)
            else:raise reference.Blocked(f'{name} incorrectly completed')
        finally:close(host)
    return results
