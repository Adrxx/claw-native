"""Fresh retail/Swift resize and prior-state comparison on the shared menu heap."""
import json
from .initializer_compare import original_initializer, normalized, physical_effects
from .compare import WORK
from Tests.NativeMenuBase.trace import MenuTrace, UC_X86_REG_ECX, UC_X86_REG_ESP

EDGES={0x4cf020:3,0x4c9bd0:0,0x42abf0:0,0x4b90b0:2}
OFFSETS=(0x68,0x6c,0x78,0x7c,0x80,0x84,0x88)


def snapshot(h):
    app=h.app;scene=h.word(app+0x30);holder=h.word(scene+4)
    error=h.word(app+8);manager=h.word(scene+0x1c)
    return dict(application=[h.word(app+x) for x in OFFSETS],
                wrappers=[[h.word(h.word(holder+x)+y) for y in (16,20,24,28,32,36,40)] for x in (16,20,24)],
                sceneError=h.word(scene+0x38),managerError=h.word(manager+0x880),
                error=[h.word(error+x) for x in (0x244,0x248,0x24c,0x250)])


class Reference(MenuTrace):
    collecting=False
    fail_cooperative=False
    def com_fixture(self,address):
        if self.fail_cooperative and self.com_methods[address]==('IDirectDraw','SetCooperativeLevel'):
            self.fail_cooperative=False
            self.physical_events.append(dict(service='graphics-failure',function=0x6e110050,result=0x8007000e))
            self.returned(0x8007000e,12)
            return
        start=len(self.physical_events)
        super().com_fixture(address)
        if self.physical_events[start].get('result')==0x8007000e:
            self.physical_events[start]=dict(service='graphics-failure',function=0x6e120018,result=0x8007000e)

    def hook(self,machine,address,size,user):
        if self.collecting and address in EDGES:
            receiver=machine.reg_read(UC_X86_REG_ECX);sp=machine.reg_read(UC_X86_REG_ESP)
            role={self.app:'application',self.word(self.app+0x30):'scene',self.menu:'menu',self.word(self.app+8):'error'}.get(receiver,'unexpected')
            self.resize_edges.append(dict(function=address,receiver=role,arguments=[self.word(sp+4+4*i) for i in range(EDGES[address])],state=snapshot(self),serviceCount=sum(e["service"] not in {"CMapStringToPtr RemoveKey","CMemFile Attach","CArchive destructor"} for e in self.physical_events[self.profile_start:])))
        if self.collecting and address in (0x45b426,0x4d5587):self.branches.add(address)
        return super().hook(machine,address,size,user)


def main():
    witness=json.loads((WORK/'resize-swift.json').read_text())
    h,menu,_=original_initializer(Reference)
    try:
        h.menu=menu;h.app=h.word(menu+4);h.put(h.app+0x2c,menu)
        h.clock_step=100
        h.run(0x45b3f0,menu,(0,),phase='resize-enter')
        h.resize_edges=[];h.branches=set();h.collecting=True
        rows=[]
        profiles=[(f'prior-{i}',0x45b3f0,menu,(i,)) for i in range(2,14)]
        profiles += [('unforced',0x42a000,h.app,(0,)),('forced-same',0x42a000,h.app,(1,)),('changed',0x42a060,h.app,(800,600)),('restored',0x42a000,h.app,(1,)),('changed-again',0x42a060,h.app,(800,600)),('failed-resize',0x42a000,h.app,(1,)),('latched-error',0x429e10,h.app,(0x1234,0x5678))]
        primary=h.word(h.word(h.word(h.app+0x30)+4)+16)
        for code in (0,1001,1002,1003,1004,1005):
            profiles += [(f'graphics-{code}',0x4d5510,primary,(640,480,8)),(f'graphics-error-{code}',0x429e10,h.app,(0x8008,0x403))]
        for actual,(name,f,receiver,args) in zip(witness,profiles,strict=True):
            if name=='failed-resize':h.fail_primary_creation=True
            if name.startswith('graphics-') and not name.startswith('graphics-error-'):
                code=int(name.split('-')[1]);scene=h.word(h.app+0x30)
                h.put(h.word(scene+0x1c)+0x880,code);h.put(scene+0x38,0);h.fail_cooperative=True
                for off in (0x244,0x248,0x24c,0x250):h.put(h.word(h.app+8)+off,0)
            h.resize_edges=[];start=len(h.physical_events);h.profile_start=start
            result=h.run(f,receiver,args,phase=name)
            expected=dict(name=name,result=0 if f==0x429e10 else result,state=snapshot(h),edges=h.resize_edges,
                          effects=h.physical_events[start:],menu=list(h.machine.mem_read(menu,0x2c8)))
            rows.append(expected)
            (WORK/'resize-original.json').write_text(json.dumps(rows,indent=2)+'\n')
            assert actual['name']==name
            for key in ('result','state','edges'):
                assert actual[key]==expected[key],(name,key,actual[key],expected[key])
            a=normalized(actual['menu'],{},lambda off,v:off in actual['pointerOffsets'])
            b=normalized(expected['menu'],{},lambda off,v:any(t<=v<t+n for t,n in h.allocations.items()))
            assert a==b,(name,'menu',[(hex(i*4),x,y) for i,(x,y) in enumerate(zip(a,b)) if x!=y][:10])
            a=physical_effects(actual['effects'],native=True)
            b=physical_effects(expected['effects'])
            (WORK/'resize-effects.json').write_text(json.dumps(dict(name=name,native=a,original=b),indent=2)+'\n')
            assert a==b,(name,'effects',len(a),len(b),[(i,x,y) for i,(x,y) in enumerate(zip(a,b)) if x!=y][:3])
        assert {0x45b426,0x4d5587} <= h.branches
        cleanup=json.loads((WORK/'resize-cleanup.json').read_text())
        assert cleanup['fault']==cleanup['remaining']==cleanup['display']==0,cleanup
        controls=json.loads((WORK/'resize-controls.json').read_text())
        assert {(r['kind'],r['address']) for r in controls}=={
            ('owner',0x4cf020),('owner',0x4c9bd0),('owner',0x4d5720),('owner',0x4d5510),
            ('error-owner',0x4b90b0),('error-physical',0x546d50),('prior-owner',0x45b3f0),('prior-owner',0x4bbd90),
            ('physical',0x6e110054),('physical',0x6e120018),('physical',0x6e110030),
            ('resource',0),('cleanup-owner',0x429530)}
        assert all(r['rejected'] and r['files']==r['allocations']==0 for r in controls)
        result=dict(status='compared',profiles=len(rows),branches=[hex(a) for a in sorted(h.branches)],
                    ordered_services=True,publication_order=True,prior_states=list(range(2,14)),
                    retained_manager_errors=list(range(1001,1006)),physical_graphics_failure=True,
                    controls=len(controls),cleanup=True)
        (WORK/'resize-result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
    finally:
        for stream in h.files.values():stream.close()


if __name__=='__main__':main()
