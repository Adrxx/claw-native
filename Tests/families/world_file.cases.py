"""Original-backed world file, descriptor and camera wrapper cases."""
import struct
import zlib
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns

NEW = 0x4F63EC
COPY = 0x546D58


def plane(env, flags=1):
    p = env.object(0x158, 'plane', fill=0)
    env.put(p + 8, flags)
    env.put(p + 0x10, 0x41A40000, 0x41780000, 0x3F400000, 0x3FA00000)
    env.put(p + 0x30, 4096, 3072)
    env.put(p + 0x70, 11, 9, 5, 4)
    return p


def world(env, count=0):
    w = env.object(0xE0, 'world', fill=0xA5)
    vt = env.object(0x48, 'world vtable')
    env.put(w, vt)
    env.put(w + 0x20, 0x5108FC, 0, 0, 0, 0)
    env.put(w + 0x34, 0x5108FC, 0, 0, 0, 0)
    env.put(w + 0x48, 0x5108FC, 0, 0, 0, 0)
    ps = [plane(env, f) for f in (1, 0, 1)]
    table = env.object(12, 'plane table', words=ps)
    env.put(w + 0x38, table, count, 3)
    env.put(w + 0x5C, ps[0], 0)
    env.put(w + 0x10, 0x80000000, 3, 17, 23)
    log = env.object(96, 'callback observations')
    def reset(e, call):
        e.put(log, call.receiver, e.get(w + 0x10), e.get(w + 0x3C))
        return 0xABCD
    env.put(vt + 0x44, env.stub('world reset', 'thiscall', 0, reset))
    def copy(e, call):
        dst, src = call.arguments
        e.write(dst, e.read(src, 16))
        return 1
    env.override(COPY, copy)
    return dict(w=w, vt=vt, ps=ps, table=table, log=log)


def raw_setup(kind='plain', flags=1, count=0, tiles=None, nplanes=0, compressed=False):
    def setup(env):
        t = world(env, count)
        env.put(t['ps'][0] + 8, flags)
        h = env.object(0x1400, 'world bytes', fill=0)
        env.put(h, 0x2F0)
        env.put(h + 8, 2 if compressed else 0x51)
        env.write(h + 0x10, b'Distinct world name!\0')
        env.put(h + 0x2D0, 37, 29)
        env.put(h + 0x2DC, nplanes, 0x400, 0, 0, 0xA1B2C3D4)
        for i in range(nplanes):
            ph = h + 0x400 + i * 0xA0
            env.put(ph, 0xA0 if kind != 'badplane' else 0x9F)
            env.put(ph + 8, 1 if i == 0 else 0)
            env.write(ph + 0x10, f'plane{i}'.encode() + b'\0')
            env.put(ph + 0x58, 32, 24, 1, 1, 3, 5, 100, 75)
            env.put(ph + 0x84, 0x900 + 4 * i)
            env.put(h + 0x900 + 4 * i, 0xCA00 + i)
        if tiles is not None:
            env.put(h + 0x2E4, 0xA00)
            env.put(h + 0xA08, len(tiles))
            pos = h + 0xA20
            for tile in tiles:
                env.put(pos, tile, 0x88, 2, 3, 0xCAFEBABE, 0x12345678, 0xABCDEF, 7, 8, 9)
                pos += {1:20, 2:40, 3:22}.get(tile, 40)
        if kind == 'header': env.put(h, 0x5F5)
        if kind in ('tile-null', 'tile-overflow'):
            env.put(h + 0x2E4, ((0 if kind == 'tile-null' else 0xFFFFFFE0) - h) & 0xFFFFFFFF)
        if compressed:
            payload = env.read(h + 0x2F0, 0xB00)
            packed = zlib.compress(payload)
            env.write(h + 0x2F0, packed)
            env.put(h + 0x2E8, len(payload))
            if kind == 'decodefail': env.write(h + 0x2F0, b'bad stream')
            if kind == 'allocfail': env.override(NEW, allocate(fail=True))
        t['src'] = h
        return t
    return setup


def cases(random_source):
    for _ in range(4):
        values = [random_source.getrandbits(32) for _ in range(3)]
        yield Case('constructor distinct words ' + str(values), 0x4CACE0,
                   lambda e: {'w': e.object(0xE0, 'world', fill=0x79)},
                   receiver=lambda t:t['w'], arguments=tuple(values))
    for entry, words in ((0x4D5840,3),(0x4D5C30,8)):
        for alias in (None, -8, 0, 4, 12):
            vals = [random_source.getrandbits(32) for _ in range(24)]
            def setup(e, alias=alias, vals=vals):
                a=e.object(128,'pattern',words=vals)
                src=e.object(64,'source',words=list(reversed(vals[:16]))) if alias is None else a+32+alias
                return {'w':a+32,'src':src}
            yield Case(f'copy {entry:x} alias {alias}',entry,setup,receiver=lambda t:t['w'],arguments=(lambda t:t['src'],))
    for width,height in ((0,0),(3,4),(1,1),(1,0),(1,-1),(2,3),(4,4),(4,7),(8,8),(2,2)):
        for failure in (False,True):
            def setup(e,width=width,height=height,failure=failure):
                t={'w':e.object(24,'tile',fill=0x69),'src':e.object(512,'tile input',data=bytes(range(256))*2)}
                e.put(t['src']+8,width,height)
                if failure or height < 0:e.override(NEW,allocate(fail=True))
                return t
            yield Case(f'pixel tile {width}x{height} fail {failure}',0x4D5870,setup,receiver=lambda t:t['w'],arguments=(lambda t:t['src'],))
    def mutate_pixel(e):
        t={'w':e.object(24,'tile',fill=0x42),'src':e.object(64,'source',data=bytes(range(64)))}
        e.put(t['src']+8,4,4)
        def alloc(e,c):
            e.put(t['w']+0x10,7)
            return e.object(c.arguments[0],'pixels',fill=0x31)
        e.override(NEW,alloc)
        return t
    yield Case('pixel count read after allocator',0x4D5870,mutate_pixel,receiver=lambda t:t['w'],arguments=(lambda t:t['src'],))
    for kind in (None,0,1,2,3,4,0xFFFFFFFF):
        for dims in ((2,2),(3,4)) if kind==3 else ((2,3),):
            def setup(e,kind=kind,dims=dims):
                src=0 if kind is None else e.object(256,'descriptor',data=bytes(range(256)))
                if src:e.put(src,kind,0x98765432,*dims,0x11223344,0x55667788,0x99AABBCC,0xDDEEFF00,7,8)
                return {'src':src}
            yield Case(f'factory kind {kind} dims {dims}',0x4CB700,setup,arguments=(lambda t:t['src'],))
    for entry,size in ((0x4CDD10,0xE0),(0x4CDE70,24),(0x4D2210,0x158),(0x4D5330,16)):
        for flag in (0,1,2,0x100,0x103):
            for nested in (False,True):
                def setup(e,entry=entry,size=size,nested=nested):
                    w=e.object(size,'deleting object',fill=0)
                    if nested and entry==0x4CDE70:e.put(w+0x14,e.object(11,'payload',fill=0xD3))
                    if nested and entry==0x4D2210:e.put(w+0x20,e.object(12,'grid words'),e.object(20,'row words'))
                    return {'w':w}
                yield Case(f'destructor {entry:x} flag {flag} nested {nested}',entry,setup,receiver=lambda t:t['w'],arguments=(flag,))
    for entry in (0x4CB670,0x4CB960):
        for count in (-1,0,1,3):
            for variant in ('plain','sentinel','alias','mutate'):
                def setup(e,count=count,variant=variant):
                    t=world(e,count)
                    src=t['w']+0xC if variant=='alias' else e.object(16,'rectangle',words=[0x80000000 if variant=='sentinel' else 3,5,17,23])
                    t['src']=src
                    if variant=='mutate':
                        alternate=e.object(12,'alternate table',words=list(reversed(t['ps'])))
                        def copy(e,c):
                            e.write(c.arguments[0],e.read(c.arguments[1],16))
                            e.put(t['log']+16,c.arguments[0],c.arguments[1],e.get(t['w']+0x10),e.get(t['w']+0x3C))
                            e.put(t['w']+0x38,alternate,2)
                            return 1
                        e.override(COPY,copy)
                    return t
                args=(41,27) if entry==0x4CB670 else (lambda t:t['src'],)
                yield Case(f'viewport {entry:x} count {count} {variant}',entry,setup,receiver=lambda t:t['w'],arguments=args)
    for width,height in ((0,2),(-1,2),(1,0),(1,-1),(1,1),(0x7FFFFFFF,2)):
        yield Case(f'viewport size boundary {width} {height}',0x4CB670,lambda e:world(e,-1),receiver=lambda t:t['w'],arguments=(width,height))
    for state in ('null','nogrid','noworld','world'):
        def setup(e,state=state):
            t=world(e)
            p=t['ps'][0]
            if state=='null':e.put(t['w']+0x5C,0)
            if state in ('noworld','world'):
                context=e.object(40,'context',fill=0)
                e.put(p+0xC,context)
                e.put(p+0xB0,e.object(0x80,'spatial grid',fill=0))
                e.put(context+0x24,t['w'] if state=='world' else 0)
                e.put(t['w']+0xC8,41,29,83,57,19,13)
            return t
        yield Case('selected grid '+state,0x4CDCA0,setup,receiver=lambda t:t['w'])
    for result in (0,1,0xFFFFFFFF):
        for mode in ('mapped','cached','empty'):
            def setup(e,result=result,mode=mode):
                t=world(e)
                r=e.object(44,'resource',fill=0); archive=e.object(36,'archive',fill=0); data=e.object(32,'resource data',fill=0x37)
                e.put(r+0x24,archive)
                if mode=='mapped':e.put(archive+0x20,data)
                if mode=='cached':e.put(r+0x18,data)
                def parse(e,c):
                    e.put(t['log']+16,c.receiver,c.arguments[0],e.get(r+0x18),e.get(t['w']+8))
                    return result
                e.put(t['vt']+0x38,e.stub('resource parser','thiscall',1,parse))
                t['src']=r
                return t
            yield Case(f'resource {mode} parser {result}',0x4CB5A0,setup,receiver=lambda t:t['w'],arguments=(lambda t:t['src'],))
    for mode in ('openfail','allocfail','parsefail','success'):
        def setup(e,mode=mode):
            t=world(e); t['src']=e.object(16,'filename',data=b'world.wwd\0')
            e.override(0x4F72C9,lambda e,c:(e.put(c.receiver,0x11111111,0x22222222,0x33333333,0x44444444) or c.receiver))
            def record(e,c):
                e.put(t['log']+32,c.receiver,*[e.get(c.receiver+i) for i in range(0,16,4)])
                return 0
            e.override(0x4F7369,record)
            e.override(0x4F7448,returns(0 if mode=='openfail' else 1))
            e.override(0x4F774D,returns(48))
            def read(e,c):
                e.write(c.arguments[0],bytes(range(c.arguments[1])))
                e.put(c.receiver+4,0xABCD0123)
                return c.arguments[1]
            e.override(0x4F7570,read)
            def parse(e,c):
                e.put(t['log']+16,c.receiver,c.arguments[0],e.get(c.arguments[0]))
                return 0 if mode=='parsefail' else 0x80000000
            e.put(t['vt']+0x38,e.stub('file parser','thiscall',1,parse))
            if mode=='allocfail':e.override(NEW,allocate(fail=True))
            return t
        yield Case('file '+mode,0x4CB470,setup,receiver=lambda t:t['w'],arguments=(lambda t:t['src'],))
    for mode in ('nullsrc','nulldst','large','uncompressed','zero','capacity','invalid','exact','mismatch'):
        def setup(e,mode=mode):
            src=e.object(0x900,'compressed input',fill=0x39); dst=e.object(0x900,'decoded output',fill=0x71)
            data=b'abcd'*16; packed=zlib.compress(data)
            e.put(src,0x2F3); e.put(src+8,2); e.put(src+0x2E8,64)
            e.write(src+0x2F3,packed+bytes(64-len(packed)))
            capacity=0x600
            if mode=='nullsrc':src=0
            if mode=='nulldst':dst=0
            if mode=='large':e.put(src,0x5F5)
            if mode=='uncompressed':e.put(src+8,0)
            if mode=='zero':e.put(src+0x2E8,0)
            if mode=='capacity':e.put(src+0x2E8,0xF00);capacity=0
            if mode=='invalid':e.write(src+0x2F3,b'invalid!')
            if mode=='mismatch':e.put(src+0x2E8,65)
            def calloc(e,c):return e.object(max(1,c.arguments[0]*c.arguments[1]),'codec allocation',fill=0)
            e.override(0x4ADF50,calloc)
            return {'src':src,'dst':dst,'cap':capacity}
        yield Case('decompress '+mode,0x4CD660,setup,arguments=(lambda t:t['src'],lambda t:t['dst'],lambda t:t['cap']))
    for kind in ('plain','header','tile-null','tile-overflow','badplane'):
        yield Case('raw '+kind,0x4CB200,raw_setup(kind,nplanes=1 if kind=='badplane' else 0),receiver=lambda t:t['w'],arguments=(lambda t:t['src'],))
    for flags in (0,1):
        for count in (-1,0,1,3):
            yield Case(f'raw cameras flags {flags} count {count}',0x4CB200,raw_setup(flags=flags,count=count),receiver=lambda t:t['w'],arguments=(lambda t:t['src'],))
    for tiles in ([],[0],[1],[1,2],[3]):
        yield Case('raw tiles '+str(tiles),0x4CB200,raw_setup(tiles=tiles),receiver=lambda t:t['w'],arguments=(lambda t:t['src'],))
    for nplanes in (1,2):
        yield Case('raw planes '+str(nplanes),0x4CB200,raw_setup(nplanes=nplanes),receiver=lambda t:t['w'],arguments=(lambda t:t['src'],))
    for kind in ('plain','decodefail','allocfail','badplane','badtiles'):
        def setup(e,kind=kind):
            t=raw_setup(kind,compressed=True,nplanes=1 if kind=='badplane' else 0,tiles=[0] if kind=='badtiles' else None)(e)
            e.override(0x4ADF50,lambda e,c:e.object(max(1,c.arguments[0]*c.arguments[1]),'codec calloc',fill=0))
            return t
        yield Case('raw compressed '+kind,0x4CB200,setup,receiver=lambda t:t['w'],arguments=(lambda t:t['src'],))
    def factory_payload_failure(e):
        src=e.object(32,'descriptor',fill=0x65)
        e.put(src,3,0x12345678,2,2)
        e.override(NEW,allocate(fail_from_call=2))
        return {'src':src}
    yield Case('factory pixel payload allocation fails',0x4CB700,factory_payload_failure,arguments=(lambda t:t['src'],))
    for changed in ('planes','tiles'):
        def setup(e,changed=changed):
            t=raw_setup(nplanes=2 if changed=='planes' else 0,tiles=[1,2] if changed=='tiles' else None)(e)
            def allocation(e,c):
                if e.calls_so_far(c.function)==1:
                    e.put(t['src']+(0x2DC if changed=='planes' else 0xA08),1)
                return e.object(c.arguments[0],'allocation')
            e.override(NEW,allocation)
            return t
        yield Case('raw live '+changed+' count changes in allocation',0x4CB200,setup,receiver=lambda t:t['w'],arguments=(lambda t:t['src'],))
    def calloc_failure(e):
        t=raw_setup(compressed=True)(e)
        e.override(0x4ADF50,returns(0))
        return t
    yield Case('raw codec allocation failure',0x4CB200,calloc_failure,receiver=lambda t:t['w'],arguments=(lambda t:t['src'],))
