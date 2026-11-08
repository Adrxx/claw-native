"""Original-derived cases for player fade owners and their physical services."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns


# The specification narrowly exempts these source-reviewed intrinsic faults.
# No fixture replaces their game bodies and no case claims a normal return.
specification_problems = []
intrinsic_fault_domains = [
    "Factory allocation failure reaches 0x4ec0c6-0x4ec0c8, "
    "0x4ec323-0x4ec325, 0x4ec41b-0x4ec41d or 0x4ec523-0x4ec525, "
    "then calls 0x4ecb00 with ECX=0 and writes address 0x24. "
    "Current normal-return cases cannot represent this intrinsic fault outcome.",
    "Factory count UINT32_MAX reaches 0x4ec179-0x4ec194, releases/clears "
    "the list, then publishes at cleared_list + old_count*4 (0xfffffffc). "
    "This is an intrinsic invalid-memory outcome, not a valid empty-list return.",
    "Factory kind 3 with null init reaches 0x4ec54e-0x4ec596. "
    "Original default initializer 0x4ecc30 writes palette=0 and table=0; "
    "original 0x4ecd00 reads palette+0xc at 0x4ecd3b before the gradient "
    "builder. The owned failure tail is unreachable through a normal "
    "well-backed default init. The supplied-init success and real gradient "
    "allocation-failure branches are covered without replacing dependencies.",
]

def physical(env):
    # Use separate closures keyed by import, never retained Python counters.
    for a in (0x546a24,0x546df0):
        env.override(a, lambda e,c,a=a: e.calls_so_far(a)*7)
    env.override(0x5469e4,lambda e,c: len(e.cstr(c.arguments[0])))
    def atomic(delta):
        def effect(e,c):
            p=c.arguments[0]; n=(e.get(p)+delta)&0xffffffff; e.put(p,n); return n
        return effect
    env.override(0x5469e8,atomic(-1)); env.override(0x5469ec,atomic(1))
    def point(e,c):
        l,t,r,b=struct.unpack('<4i',e.read(c.arguments[0],16))
        x,y=(v if v<0x80000000 else v-0x100000000 for v in c.arguments[1:])
        return int(l<=x<r and t<=y<b)
    env.override(0x546cd4,point)
    env.override(0x4a3050,lambda e,c: (e.calls_so_far(0x4a3050)*137+53)&0x7fff)


def base(env,fill=0):
    physical(env)
    return {'o':env.object(0x2080,'fade',fill=fill)}


def surface(env,w=9,h=7,depth=8,seed=17):
    s=env.object(188,'surface',fill=0); p=env.object((w*4+11)*(h+4),'pixels',data=bytes((i*seed+31)&255 for i in range((w*4+11)*(h+4))))
    api=env.object(4,'DDraw'); vt=env.object(132,'DDraw vtable')
    env.put(s+8,api); env.put(api,vt)
    env.put(s+0x14,h,w,w*4+11); env.put(s+0x30,p); env.put(s+0xa4,depth); env.put(s+0xac,depth//8)
    for off,argc in ((8,1),(0x64,5),(0x80,2),(0x14,6),(0x2c,6)):
        env.put(vt+off,env.stub('DDraw method '+str(off),'stdcall',argc,returns(0)))
    return s,p


def render_setup(w,h,x,y,gradient,closing,old=0,depth=8):
    def setup(env):
        d=base(env); o=d['o']; s,p=surface(env,w,h,depth,17); t,q=surface(env,w,h,depth,29)
        lut=env.object(256*max(1,gradient)+256,'gradient bytes',data=bytes((i*19+7)&255 for i in range(256*max(1,gradient)+256)))
        owner=env.object(16,'gradient owner'); env.put(owner+8,lut)
        env.put(o+0x1c,owner); env.put(o+0x20,old); env.put(o+0x38,s,t,t if closing and gradient>0 else 0,0,closing,x,y,p,q,max(w,h)+2)
        env.put(o+0x2060,gradient,w,h)
        for row in range(h): env.put(o+0x60+row*4,0 if closing else x); env.put(o+0x1060+row*4,w if closing else x)
        d.update(p=p,q=q,lut=lut); return d
    return setup


def cases(random_source):
    for f in (0x4c61d0,0x4ebf80,0x4ec8d0,0x4ecb30,0x4ecbc0,0x4ed5e0):
        for fill in (0x5b,random_source.randrange(1,255)):
            yield Case(f'constructor {f:x} fill {fill}',f,lambda e,v=fill:base(e,v),receiver=lambda d:d['o'])
    for f,args in ((0x4ecb00,(0x12345678,0x897abcde)),(0x4ecb20,(0xa321cdf0,))):
        yield Case(f'setter {f:x}',f,lambda e:base(e,0x6d),receiver=lambda d:d['o'],arguments=args)
    for f in (0x4ec920,0x4ed620,0x4ed600):
        for owned in (0,1):
            def setup(e,owned=owned):
                d=base(e); e.put(d['o']+0x1c,0x345678); e.put(d['o']+0x30,owned); return d
            yield Case(f'destructor {f:x} own {owned}',f,setup,receiver=lambda d:d['o'],arguments=(0,) if f==0x4ed600 else ())
        if f==0x4ed600: yield Case('deleting destructor',f,base,receiver=lambda d:d['o'],arguments=(1,))
    for f in (0x42d420,0x42d440):
        for flags in (0,1):
            for present in (0,1):
                def setup(e,flags=flags,present=present):
                    d=base(e); p=e.object(0x30,'sound',fill=0); e.put(d['o']+0x14,flags); e.put(d['o']+0x50,p if present else 0); return d
                yield Case(f'sound {f:x} {flags} {present}',f,setup,receiver=lambda d:d['o'])
    for f in (0x4b8960,0x4ec990):
        for delay in (0,1,20,0xffffffff):
            yield Case(f'wait {f:x} {delay}',f,base,arguments=(delay,))
    for n in (-1,0,1,4):
        for flag in (0,1):
            def setup(e,n=n,flag=flag):
                d=base(e); o=d['o']; vt=e.object(24,'runner methods'); log=e.object(512,'callback log',fill=0)
                def record(e,c):
                    i=e.get(log); e.put(log, i+1); e.put(log+4+i*16,c.receiver,len(c.arguments),*(tuple(c.arguments)+(0,0))[:2]); return 0
                e.put(vt+4,e.stub('frame','thiscall',1,record)); e.put(vt+8,e.stub('extent','thiscall',0,returns(n&0xffffffff)))
                e.put(vt+12,e.stub('begin','thiscall',0,record)); e.put(vt+16,e.stub('end','thiscall',0,record)); e.put(o,vt)
                if flag:
                    manager=e.object(4,'presentation manager');child=e.object(4,'presentation child');methods=e.object(92,'presentation methods');e.put(manager,child);e.put(child,methods);e.put(methods+0x58,e.stub('Present','stdcall',3,record));e.put(o+0x2c,manager)
                return d
            yield Case(f'runner {n} notify {flag}',0x4ec9c0,setup,receiver=lambda d:d['o'],arguments=(21,0,flag))
    for count in (0,1,4):
        for selected in (-1,0,3):
            def setup(e,count=count,selected=selected):
                d=base(e); arr=e.object(20,'fade entries'); vals=[]
                for i in range(4):
                    p=e.object(8,'entry'); vt=e.object(4,'entry methods'); e.put(p,vt); e.put(vt,e.stub('destroy','thiscall',1,returns(0))); vals.append(p)
                e.put(arr,*vals); e.put(d['o']+0x14,arr,count,4); d['target']=vals[selected] if selected>=0 else 0; return d
            yield Case(f'remove count {count} item {selected}',0x4ec600,setup,receiver=lambda d:d['o'],arguments=(lambda d:d['target'],))
    for f in (0x48fae0,0x48fbe0):
        for missing in (0,1,2,3):
            def setup(e,missing=missing):
                d=base(e); o=d['o']; menu=e.object(32,'menu'); app=e.object(24,'app'); a=e.object(48,'front view'); b=e.object(48,'back view'); mgr=e.object(40,'manager',fill=0);
                e.put(o+0xc,menu,0 if missing==0 else mgr); e.put(menu+0x1c,0 if missing==1 else 1); e.put(menu+4,app); e.put(app+0x10,a,b); e.put(a+0x2c,0 if missing==2 else 0x123400); e.put(b+0x2c,0 if missing==3 else 0x567800)
                # Last missing-back path is only reached by the two-surface wrapper.
                if missing==3 and f==0x48fae0:e.put(o+0x10,0)
                return d
            yield Case(f'wrapper {f:x} missing {missing}',f,setup,receiver=lambda d:d['o'],arguments=(3,4,7,0))
    for gradient in (-1,0,1,3):
        for closing in (0,1):
            for w,h,x,y in ((9,7,4,3),(7,5,0,0),(7,5,6,4),(2,1,1,0)):
                for radius in (0,1,3,8):
                    yield Case(f'render {w} {h} {x} {y} g{gradient} c{closing} r{radius}',0x4ed800,render_setup(w,h,x,y,gradient,closing),receiver=lambda d:d['o'],arguments=(radius,))
    for g in (0,1,3):
        for y,row in ((0,0),(1,2),(4,3),(4,0),(1,6)):
            setup=render_setup(9,7,4,y,g,0)
            yield Case(f'gradient row g{g} y{y} row{row}',0x4ee170,setup,receiver=lambda d:d['o'],arguments=(row,25,5,lambda d:d['lut'],lambda d:d['p'],lambda d:d['q']))
    for x,y in ((0,0),(1,2),(8,0),(0,6),(8,6),(4,3),(-3,10)):
        yield Case(f'extent x{x} y{y}',0x4ee6b0,render_setup(9,7,x,y,0,0),receiver=lambda d:d['o'])
    for g,closing in ((0,0),(-1,1),(1,0)):
        yield Case(f'prepare skipped {g} {closing}',0x4ee820,render_setup(9,7,4,3,g,closing),receiver=lambda d:d['o'])
    yield Case('release absent scratch surface',0x4ee860,base,receiver=lambda d:d['o'])
    for gradient in (-1,0,1,3):
        for closing in (0,1):
            for mode in ('valid','default','missing_front','missing_back','outside','missing_palette','gradient_missing_both'):
                def setup(e,g=gradient,c=closing,mode=mode):
                    d=base(e); o=d['o']; s,p=surface(e); t,q=surface(e); init=e.object(36,'circle init'); lut=e.object(16,'LUT'); pixels=e.object(1024,'lookup pixels'); e.put(lut+8,pixels)
                    e.put(o+0x24,s,t); e.put(init,2,0 if mode in ('default','missing_front') else s,0 if mode=='default' else t,0,c,g,20 if mode=='outside' else 4,3,lut)
                    if mode=='missing_front':e.put(o+0x24,0)
                    if mode=='missing_back':e.put(init+8,0);e.put(o+0x28,0)
                    if mode=='gradient_missing_both':e.put(init+12,0);e.put(init+0x20,0)
                    if mode=='missing_palette':
                        pal=e.object(16,'palette',fill=0);rgb=e.object(1024,'RGB palette quads',data=bytes((i*29+11)&255 for i in range(1024)));e.put(pal+12,rgb);e.put(init+12,pal);e.put(init+0x20,0)
                    d['init']=init;return d
                yield Case(f'init g{gradient} c{closing} {mode}',0x4ed670,setup,receiver=lambda d:d['o'],arguments=(lambda d:d['init'],))
    for kind in range(4):
        for null in ((False,) if kind==3 else (False,True)):
            def setup(e,kind=kind,null=null):
                d=base(e); mgr=d['o']; s,p=surface(e,256 if kind==0 else 9); t,q=surface(e,256 if kind==0 else 9); e.put(mgr,s,t); init=e.object(48,'factory init'); e.put(init,kind+1,s,t,0,1,0,4,3,0); 
                if kind==3:
                    table=e.object(32,'radial prebuilt');e.put(init+0x14,table)
                d['init']=0 if null else init;return d
            yield Case(f'factory kind {kind} null {null}',0x4ec050,setup,receiver=lambda d:d['o'],arguments=(kind,lambda d:d['init']))
    for kind in (0,1,2,3,4,0xffffffff):
        for mode in ('success','mismatch','invalid'):
            for count,capacity,growth in ((0,0,0),(1,4,0),(4,4,0),(4,4,2),(4,4,1),(0,1,-1),(40,40,0),(8200,8200,0)) if mode=='success' and kind==1 else ((0,0,0),):
                def setup(e,k=kind,m=mode,n=count,cap=capacity,growth=growth):
                    d=base(e); o=d['o']; s,p=surface(e); t,q=surface(e); init=e.object(48,'factory init',fill=0); tab=e.object(32,'prebuilt gradient'); e.put(o,s,t); e.put(o+0x20,growth)
                    e.put(init,k+1,s,t,0,1,0,4,3,tab)
                    if k==0: e.put(init+0x10,2,3,0,0,0,0,0)
                    if k==2:e.put(init+0x10,50 if m=='success' else 101)
                    if k==3:e.put(init+0x14,tab)
                    if m=='mismatch':e.put(init,55)
                    if m=='invalid':e.put(init+4,0);e.put(o,0)
                    if cap:
                        arr=e.object(cap*4,'existing factory entries',data=struct.pack('<%dI'%cap,*[0x12340000+i*4 for i in range(cap)]));e.put(o+0x14,arr,n,cap)
                    d['init']=init;return d
                yield Case(f'factory extra {kind} {mode} {count} {capacity} {growth}',0x4ec050,setup,receiver=lambda d:d['o'],arguments=(kind,lambda d:d['init']))
    for f in (0x48fae0,0x48fbe0):
        for fast in (0,1):
            for valid in (False,True):
                def setup(e,fast=fast,valid=valid):
                    d=base(e);o=d['o'];scene=e.object(32,'scene',fill=0);app=e.object(24,'app',fill=0);a=e.object(48,'front link',fill=0);b=e.object(48,'back link',fill=0);mgr=e.object(40,'fader manager',fill=0);pause=e.object(84,'pause wrapper',fill=0);s,p=surface(e);t,q=surface(e)
                    e.put(o+4,pause);e.put(o+0xc,scene,mgr);e.put(scene+4,app);e.put(scene+0x1c,1);e.put(app+0x10,a,b);e.put(a+0x2c,s);e.put(b+0x2c,t);e.put(0x537238,fast)
                    if not valid:e.put(s+0x18,0)
                    return d
                yield Case(f'wrapper active {f:x} fast{fast} valid{valid}',f,setup,receiver=lambda d:d['o'],arguments=(1,1,21,0))
    def scratch(env):
        d=render_setup(9,7,4,3,2,1)(env); mgr=env.object(0x480,'surface manager',fill=0);api=env.object(4,'DirectDraw factory');methods=env.object(100,'factory methods',fill=0);env.put(api,methods);env.put(mgr,api);env.put(mgr+0x3d0,16)
        p=env.object(512,'scratch pixels',data=bytes((i*31+9)&255 for i in range(512)));child=env.object(4,'created surface');vt=env.object(132,'created surface methods',fill=0);env.put(child,vt)
        def create(e,c):e.put(c.arguments[2],child);return 0
        def describe(e,c):
            a=c.arguments[1];e.put(a+8,7,9,15);e.put(a+0x24,p);e.put(a+0x54,8);return 0
        env.put(methods+0x18,env.stub('CreateSurface','stdcall',4,create));env.put(vt+0x58,env.stub('GetSurfaceDesc','stdcall',2,describe));env.put(vt+0x14,env.stub('Blt','stdcall',6,returns(0)))
        env.put(d['o']+0x2c,mgr);return d
    yield Case('prepare positive closing scratch surface',0x4ee820,scratch,receiver=lambda d:d['o'])
    def scratch_release(e):
        d=base(e);mgr=e.object(0x400,'surface manager',fill=0);s,p=surface(e);node=e.object(12,'surface list node',fill=0);other=e.object(12,'other list node',fill=0)
        e.put(s,0x513690);e.put(s+4,node);e.put(node,other,0,s);e.put(other,0,node,0);e.put(mgr+0x3bc,node,other,2);e.put(d['o']+0x2c,mgr);e.put(d['o']+0x40,s);return d
    yield Case('release present scratch surface',0x4ee860,scratch_release,receiver=lambda d:d['o'])

    for kind in (0,1,2):
        def setup(e,kind=kind):
            d=base(e);s,p=surface(e,256);t,q=surface(e,256);e.put(d['o'],s if kind!=2 else 0,t);return d
        yield Case(f'factory null initializer {kind}',0x4ec050,setup,receiver=lambda d:d['o'],arguments=(kind,0))
    for closing in (0,1):
        for x in (12,20):
            yield Case(f'offright clipping {closing} {x}',0x4ed800,render_setup(9,7,x,3,0,closing),receiver=lambda d:d['o'],arguments=(3,))
    for f in (0x42d420,0x42d440):
        def setup(e):
            d=base(e);s=e.object(32,'sound controller',fill=0);child=e.object(4,'sound backend');vt=e.object(48,'sound methods',fill=0);log=e.object(16,'sound observed',fill=0);e.put(d['o']+0x14,1);e.put(d['o']+0x50,s);e.put(s+0x1c,child);e.put(child,vt)
            def record(e,c):e.put(log,c.receiver,len(c.arguments),c.arguments[0] if c.arguments else 0,0x654321);return 19
            e.put(vt+0x28,e.stub('pause physical audio','thiscall',0,record));e.put(vt+0x2c,e.stub('resume physical audio','thiscall',1,record));return d
        yield Case(f'physical audio callback {f:x}',f,setup,receiver=lambda d:d['o'])

    def failed_radial_gradient(e):
        d=base(e);s,p=surface(e);t,q=surface(e);e.put(d['o'],s,t);pal=e.object(16,'radial palette',fill=0);rgb=e.object(1024,'radial RGB quads',fill=31);e.put(pal+12,rgb);init=e.object(24,'radial init',fill=0);e.put(init,4,s,t,1,pal,0)
        def allocation(e,c):
            n=c.arguments[0]
            return 0 if n==12 else e.object(n,'allocation',fill=0)
        e.override(0x4f63ec,allocation);d['init']=init;return d
    yield Case('radial gradient allocation failure',0x4ec050,failed_radial_gradient,receiver=lambda d:d['o'],arguments=(3,lambda d:d['init']))
    def narrow_default(e):
        d=base(e);s,p=surface(e);t,q=surface(e);e.put(d['o'],s,t);return d
    yield Case('default square initializer rejects oversized step',0x4ec050,narrow_default,receiver=lambda d:d['o'],arguments=(0,0))
    def lock_changes_pitch(e):
        d=render_setup(9,7,4,3,1,0)(e);o=d['o'];s=e.get(o+0x38);api=e.get(s+8);vt=e.get(api)
        def lock(e,c):e.put(s+0x1c,19);e.put(o+0x4c,3);return 0
        e.put(vt+0x64,e.stub('Lock changes destination pitch and center','stdcall',5,lock));return d
    yield Case('render reloads pitch and center after lock',0x4ed800,lock_changes_pitch,receiver=lambda d:d['o'],arguments=(3,))

    # Exercise byte counts separately from indexed-byte gradient paths. All
    # previous row boundaries stay inside their backing pixel allocations.
    for depth in (8,16,24,32):
        for closing in (0,1):
            w=random_source.randrange(5,17);h=random_source.randrange(3,11)
            x=random_source.randrange(w);y=random_source.randrange(h)
            radius=random_source.randrange(2,7)
            yield Case(f'random raster depth{depth} c{closing} {w}x{h} r{radius}',
                       0x4ed800,render_setup(w,h,x,y,0,closing,old=radius-1,depth=depth),
                       receiver=lambda d:d['o'],arguments=(radius,))
    for closing in (0,1):
        for old in (2,4):
            yield Case(f'positive gradient previous frame {old} closing {closing}',
                       0x4ed800,render_setup(9,7,4,3,3,closing,old=old),
                       receiver=lambda d:d['o'],arguments=(4,))

    for selected in (0,1,3):
        def publication(e,selected=selected):
            d=base(e);o=d['o'];arr=e.object(16,'distinct fade entries')
            log=e.object(32,'remove publication observed',fill=0);vals=[]
            def destroy(e,c):
                e.put(log,c.receiver,c.arguments[0],e.get(o+0x18),e.get(o+0x14))
                e.write(log+16,e.read(e.get(o+0x14),16))
                return 0x97531
            for i in range(4):
                item=e.object(8,'fade entry',words=[0,0x12340000+i])
                vt=e.object(4,'fade destructor');e.put(item,vt)
                e.put(vt,e.stub('observe removal publication','thiscall',1,destroy));vals.append(item)
            e.put(arr,*vals);e.put(o+0x14,arr,4,4)
            d['target']=vals[selected];return d
        yield Case(f'remove publication order index {selected}',0x4ec600,publication,
                   receiver=lambda d:d['o'],arguments=(lambda d:d['target'],))
