"""Original-only inputs for resource-backed debug cheats."""
from clawparity.cases import Case

TOPS = (0x42C2D0, 0x42C460, 0x42C6F0, 0x42C7D0, 0x42C8E0)
DEV_NAMES = (0x526140,0x526124,0x526108,0x5260EC,0x5260D0,0x5260B0,0x526094,0x526074,
             0x526058,0x52603C,0x526020,0x526000,0x525FE4,0x525FC4,0x525FA8,0x525F88)


def obj(env,*args,**kwargs):
    kwargs.setdefault("fill",0)
    return env.object(*args,**kwargs)


def physical(env):
    def increment(e,c):
        p=c.arguments[0]; v=(e.get(p)+1)&0xffffffff; e.put(p,v); return v
    def decrement(e,c):
        p=c.arguments[0]; v=(e.get(p)-1)&0xffffffff; e.put(p,v); return v
    def copyrect(e,c):
        e.write(c.arguments[0],e.read(c.arguments[1],16)); return 1
    env.override(0x5469EC,increment)
    env.override(0x5469E8,decrement)
    env.override(0x546D58,copyrect)
    env.override(0x5469E4,lambda e,c:len(e.cstr(c.arguments[0])))


def cstring(env,text):
    data=(text if isinstance(text,bytes) else text.encode('ascii'))+b'\0'
    p=obj(env,len(data)+12,'cstring')
    env.put(p,7,len(data)-1,len(data)-1)
    env.write(p+12,data)
    return p+12


def table(env, entries, count=None):
    """One bucket deliberately exercises real collision chains and enumeration."""
    m=obj(env,32,'map'); bucket=obj(env,4,'bucket'); head=0
    for key,value in reversed(entries):
        n=obj(env,16,'association'); env.put(n,head,0,cstring(env,key),value); head=n
    env.put(bucket,head)
    env.put(m+4,bucket,1,len(entries) if count is None else count)
    return m


def surface(env, width=3, height=4, effect=None, live=True, result=0, journal=None):
    s=obj(env,160,'frame'); env.put(s+0x10,width,height)
    env.put(s+0x30,effect or 0)
    if live:
        w=obj(env,160,'surface'); iface=obj(env,4,'DDraw interface')
        vt=obj(env,32,'surface vtable'); dd=obj(env,32,'DDraw vtable')
        env.put(s+0x2C,w); env.put(w,vt); env.put(w+8,iface); env.put(iface,dd)
        def blt(e,c):
            if journal:
                i=e.get(journal); e.put(journal,i+1)
                e.put(journal+4+i*32,c.receiver,*c.arguments, e.get(s+0x30))
            # The second copy may report lost; restore=false returns it unchanged.
            return result if c.arguments[2] else 0
        env.put(dd+0x14,env.stub('IDirectDrawSurface::Blt','stdcall',6,blt))
        env.put(vt+0x1C,env.stub('surface restore','thiscall',0,lambda e,c:0))
    return s


def resource(env, frames, lo=0, hi=None):
    r=obj(env,128,'resource'); a=obj(env,max(4,len(frames)*4),'frames',words=frames)
    env.put(r+0x14,a); env.put(r+0x64,lo,len(frames)-1 if hi is None else hi)
    return r


def manager(env, objects=(), count=None):
    m=obj(env,128,'overlay manager'); arr=obj(env,max(64,4*(len(objects)+8)),'overlays',words=list(objects))
    env.put(m+0x10,0,0,63,47)
    env.put(m+0x38,arr,len(objects) if count is None else count,16)
    env.put(m+0x5C,0x11223344,0x55667788)
    return m


def control(env, entries=(), stage='ready', mode=3, overlays=None, sound='blocked', map_count=None):
    physical(env)
    c=obj(env,128,'controller'); state=obj(env,4,'state'); vt=obj(env,20,'state-vtable')
    env.put(state,vt)
    env.put(vt+16,env.stub('state kind','thiscall',0,lambda e,call:mode))
    env.put(c+0x2C,0 if stage=='no-state' else state)
    messages=obj(env,32,'message list'); env.put(messages+0x18,2); env.put(c+0x4C,messages)
    if stage!='no-world':
        g=obj(env,64,'world'); registry=obj(env,64,'registry')
        mp=table(env,entries,map_count)
        env.write(registry+16,env.read(mp,32))
        env.put(g+16,registry); env.put(g+0x24,overlays or manager(env))
        audio=obj(env,64,'audio registry'); sm=table(env,[])
        env.write(audio+16,env.read(sm,32)); env.put(audio+0x30,1 if sound=='blocked' else 0)
        if sound in ('no-device','play'):
            snd=obj(env,32,'sound resource'); player=obj(env,32,'sound player'); driver=obj(env,128,'sound driver')
            env.put(snd+16,player); env.put(player+16,driver)
            sm=table(env,[('GAME_MINORCHEAT',snd)]); env.write(audio+16,env.read(sm,32))
        env.put(0x532C0C,1 if sound=='play' else 0)
        env.put(0x532C10,0x62738495)
        env.put(g+0x28,audio); env.put(c+0x30,g)
    return c


def entry(label,fn,setup,args=()):
    return Case(label,fn,setup,receiver=lambda t:t['self'] if isinstance(t,dict) else t,arguments=args)


def toggle_setup(fn, variant, mode=1, rand=99, sound='blocked', flags=0, geometry=None, current=0, mutate_current=False):
    def setup(env):
        effect=obj(env,40,'effect',fill=0x53); env.put(effect+0x14,mode,0xBACDEF01,0x23456789)
        frame=surface(env,effect=effect if variant!='no-effect' else None,live=False)
        r=resource(env,[0]*current+[0 if variant=='no-frame' else frame],current,current)
        key='GAME_MONOLITH' if fn==0x42C2D0 else ('GAME_DEVHEADS' if fn==0x42C460 else 'CLAW')
        entries=[] if variant=='missing' else [(key,r)]
        overlay=obj(env,344,'existing overlay',fill=0x67); env.put(overlay+8,flags)
        env.write(overlay+0xB4,b'MONOLITH\0')
        mgr=manager(env,[overlay] if variant=='existing' else [])
        c=control(env,entries,overlays=mgr,sound=sound)
        env.put(0x537260,0xA1B2C3D4)
        env.override(0x4A3050,lambda e,call:rand&0xffffffff)
        if fn==0x42C2D0 and variant=='new':
            # Mutate allocation-time flags and geometry in surviving state only;
            # all constructor and virtual initialization bodies still execute.
            from clawparity.fixtures import allocate
            base=allocate(); record=obj(env,8,'overlay allocations')
            def alloc(e,call):
                p=base(e,call); n=e.get(record); e.put(record,n+1)
                if n==0:
                    e.put(record+4,p)
                    if mutate_current:e.put(r+0x64,1)
                if n==3 and geometry is not None:e.put(e.get(record+4)+0x28,*geometry)
                return p
            env.override(0x4F63EC,alloc)
        return c
    return setup


def cases(random_source):
    for fn in TOPS:
        for stage,mode in [('no-state',3),('ready',0),('ready',2),('ready',4),('no-world',3)]:
            yield entry(f'{fn:x} precondition {stage} {mode}',fn,lambda e,s=stage,m=mode:control(e,stage=s,mode=m))
        yield entry(f'{fn:x} missing resource',fn,toggle_setup(fn,'missing'))
    for fn in (0x42C2D0,0x42C6F0,0x42C7D0):
        yield entry(f'{fn:x} null current frame',fn,toggle_setup(fn,'no-frame'))
    for fn in (0x42C6F0,0x42C7D0):
        yield entry(f'{fn:x} null effect',fn,toggle_setup(fn,'no-effect'))
        for mode in (0,1,2,3,4,0x80000000):
            for sound in ('blocked','missing','no-device','play'):
                yield entry(f'{fn:x} mode {mode} sound {sound}',fn,toggle_setup(fn,'normal',mode,sound=sound))
    for value in (0,1,255,256,257,-1,-255,-256,-257,-2147483648,2147483647):
        yield entry(f'shadow random signed remainder {value}',0x42C7D0,toggle_setup(0x42C7D0,'normal',rand=value))
    for flags in (0,1,2,3,0x80000000,0xFFFFFFFD,0xFFFFFFFF):
        yield entry(f'monolith existing flags {flags:x}',0x42C2D0,toggle_setup(0x42C2D0,'existing',flags=flags))
    yield entry('monolith constructs checkerboard',0x42C2D0,toggle_setup(0x42C2D0,'new'))
    for geometry in ((0,2),(-1,2),(2,0),(2,-1),(3,2),(2,3)):
        yield entry(f'monolith allocator revises dimensions {geometry}',0x42C2D0,toggle_setup(0x42C2D0,'new',geometry=geometry))
    for current in (1,3,7):
        for change in (False,True):
            yield entry(f'monolith captured resource index {current} mutate{change}',0x42C2D0,toggle_setup(0x42C2D0,'new',geometry=(3,2),current=current,mutate_current=change))
    for lo,hi,pattern in [(2,1,()),(0,0,('effect',)),(0,3,('null','plain','effect','effect')),(1,3,('effect','plain','effect','null'))]:
        for value in (0,0xFFFFFFFF,0x12345678,random_source.getrandbits(32)):
            def setup(e,lo=lo,hi=hi,pattern=pattern):
                fs=[]
                for kind in pattern:
                    eff=obj(e,40,'effect',fill=0xB7) if kind=='effect' else None
                    fs.append(0 if kind=='null' else surface(e,effect=eff,live=False))
                return resource(e,fs,lo,hi)
            yield entry(f'effect range {lo}..{hi} {value:x}',0x4CE800,setup,(value,))
    def aliased(e):
        r=resource(e,[] ,0,1); f=surface(e,effect=r+0x4C,live=False)
        a=obj(e,8,'aliased frames',words=[f,f]); e.put(r+0x14,a); return r
    yield entry('effect aliases resource lower bound on first store',0x4CE800,aliased,(10,))
    for names,query,count in [((),'',-1),((),'',0),(('A',),'A',None),(('Alpha','Beta','alpha'),'ALPHA',None),(('A','B','C'),'C',None),(('A','B'),'none',None),(('','X'),'',None)]:
        def setup(e,names=names,query=query,count=count):
            os=[]
            for name in names:
                o=obj(e,344,'named overlay',fill=0x49); e.write(o+0xB4,name.encode()+b'\0'); os.append(o)
            return {'self':manager(e,os,count),'query':cstring(e,query)}
        yield entry(f'overlay search {names} {query} count{count}',0x4CBB00,setup,(lambda t:t['query'],))
    for reason in ('null-source','source-effect','no-target-surface','target-effect','width','height','copy','lost'):
        def setup(e,reason=reason):
            j=obj(e,1028,'DDraw call journal'); eff=obj(e,40,'effect')
            dst=surface(e,effect=eff if reason=='target-effect' else None,live=reason!='no-target-surface',result=0x887601C2 if reason=='lost' else 0,journal=j)
            src=surface(e,width=7 if reason=='width' else 3,height=8 if reason=='height' else 4,effect=eff if reason=='source-effect' else None)
            return {'self':dst,'src':0 if reason=='null-source' else src}
        yield entry(f'copy frame {reason}',0x4D2710,setup,(lambda t:t['src'],))
    for variant in ('null-resource','null-name','missing','null-destination','below','above','null-source','copy'):
        def setup(e,v=variant):
            j=obj(e,2048,'copy journal')
            dst=surface(e,journal=j); src=surface(e)
            dest=resource(e,[0 if v=='null-destination' else dst])
            source=resource(e,[src,0 if v=='null-source' else src,src],1,2)
            c=control(e,[] if v=='missing' else [('TARGET',dest)])
            return {'self':c,'r':0 if v=='null-resource' else source,'name':0 if v=='null-name' else cstring(e,'TARGET'),'index':0 if v=='below' else (3 if v=='above' else 1)}
        yield entry(f'replace frame {variant}',0x42C5C0,setup,(lambda t:t['r'],lambda t:t['name'],lambda t:t['index']))
    for missing in (True,False):
        def setup(e,missing=missing):
            j=obj(e,4096,'devhead journal')
            sources=[surface(e) for _ in range(3)]; dev=resource(e,sources)
            entries=[('GAME_DEVHEADS',dev)]
            for i,address in enumerate(DEV_NAMES):
                if missing and i%3==0: continue
                dst=surface(e,journal=j); entries.append((e.cstr(address),resource(e,[dst])))
            return control(e,entries)
        yield entry(f'devheads all sixteen replacements missing{missing}',0x42C460,setup)
    for pattern in ((),('player',),('null',),('no-frame',),('no-effect',),('mode1',),('mode2',),('mode1','mode2'),('mode2','mode1'),('mode1','null','player')):
        for sound in ('blocked','missing','no-device','play'):
            def setup(e,pattern=pattern,sound=sound):
                p=resource(e,[surface(e,live=False)]); entries=[('CLAW',p)]
                for i,kind in enumerate(pattern):
                    if kind=='player': r=p
                    elif kind=='null': r=0
                    else:
                        eff=obj(e,40,'enumerated effect',fill=0x45); e.put(eff+0x14,2 if kind=='mode2' else 1)
                        f=0 if kind=='no-frame' else surface(e,effect=None if kind=='no-effect' else eff,live=False)
                        r=resource(e,[f])
                    entries.append((f'ITEM_{i}',r))
                return control(e,entries,sound=sound,map_count=0 if not pattern else None)
            yield entry(f'haunted enumeration {pattern} sound {sound}',0x42C8E0,setup)
    for width,height,flag in ((1,1,0),(2,3,0),(3,2,1),(4,1,0),(1,4,1)):
        def setup(e,w=width,h=height,flag=flag):
            physical(e); m=manager(e); name=cstring(e,'direct overlay')
            from clawparity.fixtures import allocate
            alloc=allocate(); record=obj(e,8,'allocation record')
            def allocation(e,c):
                p=alloc(e,c)
                n=e.get(record);e.put(record,n+1)
                if n==0:e.put(record+4,p)
                if n==2 and flag:e.put(e.get(record+4)+8,1)
                return p
            e.override(0x4F63EC,allocation)
            return {'self':m,'name':name}
        yield entry(f'create overlay {width}x{height} flags{flag}',0x4CB880,setup,(width,height,7,9,13,17,lambda t:t['name']))

    for change in ('source','destination','both'):
        def setup(e,change=change):
            j=obj(e,1028,'reread journal'); dst=surface(e,journal=j); src=surface(e)
            alternate_source=surface(e); alternate_destination=surface(e,journal=j)
            wrapper=e.get(dst+0x2C); iface=e.get(wrapper+8); vt=e.get(iface)
            def clear_and_change(e,c):
                i=e.get(j);e.put(j,i+1);e.put(j+4+i*32,*c.arguments,0,0)
                if change in ('source','both'):e.put(src+0x2C,e.get(alternate_source+0x2C))
                if change in ('destination','both'):e.put(dst+0x2C,e.get(alternate_destination+0x2C))
                return 0
            e.put(vt+0x14,e.stub('Blt changes image surfaces','stdcall',6,clear_and_change))
            return {'self':dst,'source':src}
        yield entry(f'copy rereads {change} after clear',0x4D2710,setup,(lambda t:t['source'],))
    def upper_alias(e):
        r=resource(e,[],0,2);f=surface(e,effect=r+0x50,live=False)
        a=obj(e,12,'upper alias frames',words=[f,f,f]);e.put(r+0x14,a);return r
    yield entry('effect aliases resource upper bound',0x4CE800,upper_alias,(0,))
