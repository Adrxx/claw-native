"""Independent original-only resource construction cases."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import release

NEW = 0x4F63EC
DELETE = 0x4F6428


def text(env, value, name='name'):
    return env.object(len(value) + 1, name, data=value + b'\0')


def table(env, address, count, name='buckets'):
    base = env.object(count * 16 + 4, name, fill=0x6D)
    env.put(base, count)
    env.put(address, count, base + 4)
    for i in range(count):
        env.put(base + 4 + i * 16 + 8, 0, 0)
    return base + 4


def link(env, header, node, index, payload):
    bucket = env.get(header + 4) + index * 16 + 8
    previous = env.get(bucket)
    env.put(node + 4, previous, 0, header, index, payload)
    if previous:
        env.put(previous + 4, node + 4)
    else:
        env.put(bucket + 4, node + 4)
    env.put(bucket, node + 4)


def directory(env, name=None):
    obj = env.object(0x4C, 'directory', fill=0x93)
    root = env.object(0x40, 'root', fill=0)
    env.put(obj, text(env, name) if name is not None else 0)
    env.put(obj + 0x18, root, 0, 0)
    env.put(obj + 0x24, 0x513574)
    env.put(obj + 0x38, obj)
    table(env, obj + 0x3C, 5)
    table(env, obj + 0x44, 9)
    return obj, root


def group(env, key=27):
    obj = env.object(0x2C, 'group', fill=0x74)
    env.put(obj, key, 0x513570)
    env.put(obj + 0x18, obj)
    table(env, obj + 0x1C, 19)
    table(env, obj + 0x24, 19)
    return obj


def resource(env, name=b'RESource', key=71):
    obj = env.object(0x60, 'resource', fill=0)
    env.put(obj, text(env, name), key, 27)
    env.put(obj + 0x0C, text(env, b'secondary'))
    env.put(obj + 0x18, env.object(17, 'resource-bytes', fill=0x27))
    env.put(obj + 0x20, env.object(23, 'resource-aux', fill=0x52))
    env.put(obj + 0x30, 0x51356C)
    env.put(obj + 0x44, obj)
    env.put(obj + 0x48, 0x513568)
    env.put(obj + 0x5C, obj)
    return obj


def allocator(env, fail_at=0, effect=None):
    def alloc(e, call):
        n = e.calls_so_far(NEW)
        if effect:
            effect(e, n)
        if n == fail_at:
            return 0
        return e.object(call.arguments[0], 'allocation', fill=0xAB)
    env.override(NEW, alloc)


def clock(env, year=2001, cached=False, dst=0):
    local = struct.pack('<8H', year, 7, 2, 17, 13, 29, 41, 987)
    system = struct.pack('<8H', year, 7, 2, 17, 19, 29, 41, 123)
    zone = bytearray(172)
    struct.pack_into('<i', zone, 0, 360)
    struct.pack_into('<H', zone, 70, 3)
    struct.pack_into('<i', zone, 168, -60)
    def output(data, result=0):
        def effect(e, call):
            e.write(call.arguments[0], data)
            return result
        return effect
    env.override(0x546A34, output(local))
    env.override(0x5469B4, output(system))
    env.override(0x546A3C, output(bytes(zone), 2 if dst else 0))
    env.put(0x5410B8, 1)
    env.put(0x531430, 6 * 3600, 1, 0)
    env.put(0x540B68, dst)
    env.write(0x540B70, system if cached else bytes(16))
    env.put(0x540E88, 0)


def case(label, address, setup, argc=0):
    return Case(label, address, setup, receiver=lambda t: t['obj'],
                arguments=tuple((lambda t, i=i: t['args'][i]) for i in range(argc)))


def cases(random_source):
    # Constructors retain padding, use exact array sizes, and survive individual failures.
    for count in (0, 1, 2, 5, 19, 31):
        for fail in (0, 1):
            def setup(e, count=count, fail=fail):
                obj = e.object(8, 'header', fill=0xB7)
                allocator(e, fail)
                return dict(obj=obj, args=(count,))
            yield case(f'table count {count} fail {fail}', 0x4D53A0, setup, 1)
    for count in (0xFFFFFFFF, 0x10000000, 0x80000000):
        def setup(e, count=count):
            obj=e.object(8, 'header', fill=0x49); allocator(e, 1)
            return dict(obj=obj, args=(count,))
        yield case(f'table unsigned size {count:x} fails', 0x4D53A0, setup, 1)
    for fail in (0, 1, 2):
        key=random_source.getrandbits(32)
        def setup(e, fail=fail, key=key):
            obj=e.object(0x2C, 'group-target', fill=0x57); allocator(e, fail)
            return dict(obj=obj, args=(key,))
        yield case(f'group constructor allocation {fail}', 0x4B64B0, setup, 1)
    for length in (0, 1, 2, 3, 4, 7, 8, 19, 37):
        value=bytes(random_source.randrange(1, 256) for _ in range(length))
        for fail in (0, 1, 2, 3):
            words=tuple(random_source.getrandbits(32) for _ in range(5))
            def setup(e, value=value, words=words, fail=fail):
                obj=e.object(0x4C, 'directory-target', fill=0xC7)
                name=text(e,value); allocator(e,fail)
                return dict(obj=obj,args=(words[0],words[1],name,*words[2:]))
            yield case(f'directory constructor len {length} fail {fail}',0x4B6600,setup,6)
    def bucket(e):
        return dict(obj=e.object(16,'bucket',fill=0xD7))
    yield case('bucket preserves first two words',0x4D5410,bucket)
    for null in (False,True):
        def setup(e,null=null):
            obj=e.object(8,'header',fill=0x64)
            if null: e.put(obj,19,0)
            else:
                table(e,obj,3)
                e.put(obj,0xFFFFFFFF) # destruction uses allocation prefix, not header count
            return dict(obj=obj)
        yield case(f'array destruction null {null}',0x4D5420,setup)

    # Hash wrappers vary unsigned keys and byte lengths including null strings.
    for address in (0x4B7F40,0x4B8050,0x4B80C0,0x4B8130):
        values=(0,1,5,9,18,19,20,0x80000001,0xFFFFFFFF,random_source.getrandbits(32))
        for n,value in enumerate(values):
            def setup(e,address=address,value=value,n=n):
                obj=e.object(24,'hash-node',fill=0x47)
                payload=e.object(16,'payload',fill=0x91)
                if address in (0x4B7F40,0x4B8130):
                    value2=0 if n==0 else text(e,bytes([0xE9,0x41,0x7F])*(n*3))
                else: value2=value
                e.put(payload,value2)
                e.put(payload+4,value)
                e.put(obj+20,payload)
                return dict(obj=obj)
            yield case(f'hash {address:x} variant {n}',address,setup)
    for cached in (False,True):
        for year in (1969,1970,2001,2038,2039):
            for dst in (0,1):
                def setup(e,cached=cached,year=year,dst=dst):
                    clock(e,year,cached,dst); return dict(obj=0)
                yield case(f'clock year {year} cached {cached} dst {dst}',0x4B7CC0,setup)

    # Lookup chains include a hit at each position, miss, empty, and defensive link four.
    for target in (0,19,38,57,76):
        for terminal in (0,4):
            def setup(e,target=target,terminal=terminal):
                obj=e.object(8,'numeric-table'); table(e,obj,19)
                for key in (0,19,38):
                    p=e.object(12,'lookup-payload',words=[0x9856,key,0x8127])
                    node=e.object(24,'lookup-node',fill=0x37)
                    link(e,obj,node,0,p)
                    if key==0: e.put(node+4,terminal)
                return dict(obj=obj,args=(target,))
            yield case(f'lookup {target} terminal {terminal}',0x4B8070,setup,1)
    def empty(e):
        obj=e.object(8,'empty-table'); table(e,obj,19)
        return dict(obj=obj,args=(2,))
    yield case('lookup empty bucket',0x4B8070,empty,1)

    # Virtual hash observes pre-publication state and can relocate the bucket array.
    for replace in (False,True):
        for index in (0,2,6):
            for occupied in (False,True):
                def setup(e,replace=replace,index=index,occupied=occupied):
                    obj=e.object(8,'insert-table'); table(e,obj,7)
                    replacement=e.object(8,'replacement-table'); table(e,replacement,7)
                    active=replacement if replace else obj
                    if occupied:
                        for _ in range(3):
                            old=e.object(24,'old-node',fill=0x53)
                            link(e,active,old,index,0xDDAA9988)
                    node=e.object(24,'new-node',fill=0xE3)
                    log=e.object(32,'callback-observation')
                    vt=e.object(4,'callback-vtable')
                    def hashed(env,call):
                        env.put(log,call.receiver,env.get(node+4),env.get(node+8),env.get(node+12),env.get(node+16),env.get(obj+4))
                        if replace: env.put(obj+4,env.get(replacement+4))
                        return index
                    e.put(vt,e.stub('hash-node','thiscall',0,hashed)); e.put(node,vt)
                    return dict(obj=obj,args=(node,))
                yield case(f'insert replace {replace} bucket {index} occupied {occupied}',0x4D5450,setup,1)
    for position in range(3):
        def setup(e,position=position):
            obj=e.object(8,'remove-table'); table(e,obj,7)
            nodes=[]
            for _ in range(3):
                node=e.object(24,'remove-node',fill=0x82); nodes.append(node)
                link(e,obj,node,3,0x12345678)
            return dict(obj=obj,args=(nodes[position],))
        yield case(f'unlink chain position {position}',0x4D5490,setup,1)

    # Factory paths: duplicate versus allocation failure versus publication/capacity updates.
    for mode in ('new','existing','fail','inner-first-fail','inner-second-fail'):
        key=random_source.getrandbits(32)
        def setup(e,mode=mode,key=key):
            obj,_=directory(e)
            if mode=='existing':
                g=group(e,key); link(e,obj+0x44,g+4,key%9,g)
            allocator(e,{'fail':1,'inner-first-fail':2,'inner-second-fail':3}.get(mode,0))
            return dict(obj=obj,args=(key,))
        yield case(f'group factory {mode}',0x4B7170,setup,1)
    for address in (0x4B69A0,0x4B6A60):
        for capacity in (0,7,8,0x80000000,0xFFFFFFFF):
            for mode in ('new','duplicate','fail','reload-root'):
                def setup(e,address=address,capacity=capacity,mode=mode):
                    clock(e)
                    obj,root=directory(e)
                    name=text(e,b'AbCdEfGh'); field=0x38 if address==0x4B69A0 else 0x3C
                    e.put(root+field,capacity)
                    other=e.object(0x40,'replacement-root',fill=0x29); e.put(other+field,capacity)
                    if address==0x4B6A60:
                        g=group(e,27); link(e,obj+0x44,g+4,0,g)
                        if mode=='duplicate':
                            p=resource(e,b'aBcDeFgH',52); link(e,g+0x24,p+0x30,8%19,p)
                        args=(71,name,27)
                    else:
                        if mode=='duplicate':
                            child,_=directory(e,b'aBcDeFgH'); link(e,obj+0x3C,child+0x24,8%5,child)
                        args=(name,)
                    def effect(env,n):
                        if mode=='reload-root' and n==1: env.put(obj+0x18,other)
                    allocator(e,1 if mode=='fail' else 0,effect)
                    return dict(obj=obj,args=args)
                yield case(f'factory {address:x} cap {capacity:x} {mode}',address,setup,1 if address==0x4B69A0 else 3)
    def numeric_duplicate(e):
        clock(e); obj,_=directory(e); g=group(e,27); link(e,obj+0x44,g+4,0,g)
        p=resource(e,b'other',71); link(e,g+0x1C,p+0x48,71%19,p)
        return dict(obj=obj,args=(71,text(e,b'fresh'),27))
    yield case('resource duplicate numeric',0x4B6A60,numeric_duplicate,3)

    # Destructors traverse both embedded tables with distinct allocations and null payloads.
    for address in (0x4B6530,0x4B66D0):
        for populated in (False,True):
            for nullable in (False,True):
                def setup(e,address=address,populated=populated,nullable=nullable):
                    if address==0x4B6530:
                        obj=group(e)
                        if populated:
                            for i in range(3):
                                p=resource(e,bytes([65+i])* (4+i),19*i)
                                link(e,obj+0x1C,p+0x48,0,p)
                                link(e,obj+0x24,p+0x30,i if i==2 else 0,p)
                            if nullable:
                                node=e.object(24,'null-resource-node',fill=0x37)
                                link(e,obj+0x24,node,0,0)
                    else:
                        obj,_=directory(e,None if nullable else b'directory-name')
                        if not nullable: e.put(obj+0x20,e.object(13,'directory-aux',fill=0x25))
                        if populated:
                            for i in range(3):
                                g=group(e,i*9); link(e,obj+0x44,g+4,0,g)
                                p=resource(e,bytes([75+i])*7,i)
                                link(e,g+0x1C,p+0x48,i%19,p); link(e,g+0x24,p+0x30,7,p)
                                child,_=directory(e,bytes([90-i])*5)
                                link(e,obj+0x3C,child+0x24,0,child)
                            if nullable:
                                for h in (obj+0x3C,obj+0x44):
                                    node=e.object(24,'null-child-node',fill=0x37); link(e,h,node,0,0)
                    return dict(obj=obj)
                yield case(f'destroy {address:x} populated {populated} nullable {nullable}',address,setup)

    # Allocation effects install real virtual callbacks after constructor vtable setup.
    # Observations survive, so publication and reload mistakes become comparisons.
    for address in (0x4B69A0,0x4B6A60):
        def setup(e,address=address):
            clock(e); obj,root=directory(e)
            alternate=e.object(0x40,'post-insert-root',fill=0)
            name=text(e,b'AbCdEfGh')
            log=e.object(0x80,'publication-log',fill=0)
            field=0x38 if address==0x4B69A0 else 0x3C
            e.put(root+field,0); e.put(alternate+field,3)
            if address==0x4B6A60:
                g=group(e,27); link(e,obj+0x44,g+4,0,g)
                args=(71,name,27)
            else: args=(name,)
            def observed_hash(env,call):
                node=call.receiver
                count=env.get(log+4)
                env.put(log+4,count+1)
                env.put(log+8+count*32,node,env.get(node+12),env.get(node+16),env.get(node+20),env.get(obj+0x18))
                # Mutate only on last insertion: numeric precedes string for resources.
                if address==0x4B69A0 or count==1:
                    env.put(obj+0x18,alternate)
                    env.write(name,b'ABC\0')
                return (71%19 if count==0 else 8%19) if address==0x4B6A60 else 8%5
            vt=e.object(4,'observed-vtable')
            e.put(vt,e.stub('factory-publication-hash','thiscall',0,observed_hash))
            def alloc(env,call):
                n=env.calls_so_far(NEW)
                result=env.object(call.arguments[0],'allocation',fill=0xAB)
                if n==1: env.put(log,result)
                # Directory has two nested bucket allocations before the name.
                if n==(4 if address==0x4B69A0 else 2):
                    target=env.get(log)
                    if address==0x4B69A0: env.put(target+0x24,vt)
                    else:
                        env.put(target+0x30,vt); env.put(target+0x48,vt)
                return result
            e.override(NEW,alloc)
            return dict(obj=obj,args=args)
        yield case(f'factory {address:x} hash publication order root and length reload',address,setup,1 if address==0x4B69A0 else 3)
