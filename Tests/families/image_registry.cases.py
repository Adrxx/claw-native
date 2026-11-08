"""Original-backed image registry inputs; game callees retain their real bodies."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import allocate

NEW = 0x4F63EC


def services(env):
    env.override(0x546AC8, lambda e, c: 0)
    env.override(0x5469E4, lambda e, c: len(e.cstr(c.arguments[0])))
    def decrement(e, c):
        value = (e.get(c.arguments[0]) - 1) & 0xffffffff
        e.put(c.arguments[0], value)
        return value
    env.override(0x5469E8, decrement)


def string(env, data, name='string'):
    if isinstance(data, str):
        data = data.encode('ascii')
    return env.object((len(data) + 4) & ~3, name, data=data + b'\0')


def callback(env, label, argc, result=1, change=None):
    receipt = env.object(64, label + '-receipt')
    def effect(e, c):
        n = e.get(receipt)
        e.put(receipt, n + 1, c.receiver, *c.arguments)
        if change:
            change(e, c)
        return result
    return env.stub(label, 'thiscall', argc, effect)


def virtual(env, size, methods, fill=0xA7):
    obj = env.object(size, 'virtual-object', fill=fill)
    table = env.object(0x60, 'virtual-table')
    env.put(obj, table)
    for offset, argc, result, change in methods:
        env.put(table + offset, callback(env, f'virtual-{offset:x}', argc, result, change))
    return obj


def array(env, obj, offset, items, signed_count=None):
    data = env.object(max(4, 4 * len(items)), 'array-slots', words=items)
    env.put(obj + offset, 0x50E924, data, len(items) if signed_count is None else signed_count,
            len(items), 3)
    return data


def group(env, items=(), minimum=99999, maximum=0):
    obj = env.object(0x6c, 'image-group', fill=0xB3)
    env.put(obj, 0x513CF8, 0x13579, 0x2468, 0)
    array(env, obj, 0x10, list(items))
    env.put(obj + 0x64, minimum, maximum)
    return obj


def ani(env, items=(), name=None):
    obj = env.object(0x20, 'ani-sequence', fill=0xC9)
    env.put(obj, 0x513A58, 0x64738291)
    array(env, obj, 8, list(items))
    env.put(obj + 0x1c, string(env, name, 'sequence-name') if name is not None else 0)
    return obj


def map_at(env, obj, entries):
    buckets = env.object(4, 'map-bucket')
    env.put(obj, 0x50E924, buckets, 1, len(entries), 0, 0, 4)
    head = 0
    for key, value in entries:
        text = key.encode() if isinstance(key, str) else key
        chars = env.object(12 + len(text) + 1, 'CString', words=[1, len(text), len(text)])
        env.write(chars + 12, text + b'\0')
        assoc = env.object(16, 'map-association', words=[head, 0, chars + 12, value])
        head = assoc
    env.put(buckets, head)


def registry(env, entries=(), methods=()):
    obj = virtual(env, 0x40, methods)
    parent = env.object(0x2c, 'registry-parent')
    env.put(obj + 0xc, parent)
    map_at(env, obj + 0x10, entries)
    return obj


def hash_at(env, header, objects, node_offset):
    buckets = env.object(16, 'hash-bucket')
    env.put(header, 1, buckets)
    env.put(buckets + 8, objects[0] + node_offset + 4 if objects else 0)
    for i, obj in enumerate(objects):
        node = obj + node_offset
        env.put(node, 0, objects[i+1] + node_offset + 4 if i+1 < len(objects) else 0,
                0, header, 0, obj)


def directory(env, types=(), children=(), name='directory'):
    obj = env.object(0x60, name)
    env.put(obj, string(env, name))
    hash_at(env, obj + 0x3c, children, 0x24)
    hash_at(env, obj + 0x44, types, 4)
    return obj


def resource(env, kind, name='frame17', payload=b'', cached=False):
    obj = env.object(0x60, 'resource')
    tag = env.object(4, 'resource-type', words=[kind])
    owner = env.object(0x30, 'resource-owner')
    data = env.object(max(1, len(payload)), 'resource-bytes', data=payload)
    env.put(obj, string(env, name))
    env.put(obj + 8, tag)
    env.put(obj + 0x14, len(payload), data if cached and payload else 0)
    env.put(obj + 0x24, owner, 0x110)
    env.put(owner + 0xc, 0x110)
    env.put(owner + 0x20, 0 if cached or not payload else data)
    return obj


def type_node(env, resources, kind=0x504358):
    obj = env.object(0x30, 'type-node', words=[kind])
    hash_at(env, obj + 0x1c, resources, 0x48)
    return obj


def binary(env, name=b'', count=0, flags=0, record_words=None):
    if record_words is None:
        record_words = [0x35, 0x8000, 0x7fff, 0xffff, 3, 0x83ab, 0x1345, 0xf001, 0x67ab, 0xcdef]
    records = b''.join(struct.pack('<10H', *record_words) for _ in range(max(0, count)))
    raw = bytearray(0x20)
    struct.pack_into('<III', raw, 8, flags, count & 0xffffffff, len(name))
    return env.object(len(raw) + len(name) + len(records) + 32, 'ANI-bytes', data=bytes(raw)+name+records)


def case(label, function, setup, argc=0):
    return Case(label, function, setup, receiver=lambda t: t['self'],
                arguments=tuple((lambda t, i=i: t['args'][i]) for i in range(argc)))


def cases(random_source):
    for function, shape in [(0x4ce250,'ani'), (0x4ce270,'ani'), (0x4ce2d0,'group'),
                            (0x4d02f0,'group'), (0x4d0310,'group'), (0x4d6210,'ani'),
                            (0x4d6260,'record'), (0x4d6280,'record')]:
        for count in (0, 1, 3):
            for flag in (0, 1, 0x102):
                if function in (0x4ce270,0x4ce2d0,0x4d0310,0x4d6210,0x4d6280) and flag:
                    continue
                def setup(e, shape=shape, count=count, flag=flag):
                    services(e)
                    items = [e.object(0x30, 'record', fill=0x6d, words=[0x513DF8]) if i != 1 else 0 for i in range(count)]
                    obj = ani(e, items, 'different-name' if count else None) if shape=='ani' else group(e, items)
                    if shape=='record':
                        obj = e.object(0x30,'record',fill=0xD3)
                    return {'self':obj,'args':[flag]}
                yield case(f'cleanup {function:x} count {count} flag {flag}',function,setup,
                           1 if function in (0x4ce250,0x4d02f0,0x4d6260) else 0)
    for length in (0,1,3,62,63,64,95):
        text = bytes(random_source.randrange(33,127) for _ in range(length))
        def setup(e,text=text):
            return {'self':group(e),'args':[string(e,text)]}
        yield case(f'name length {length}',0x4d0380,setup,1)
    for optional in (False, True):
        for parent_mode in ('null','miss','hit'):
            words = [random_source.randrange(0x10000) for _ in range(10)]
            words[0] = words[0] | 2 if optional else words[0] & ~2
            def setup(e,words=words,parent_mode=parent_mode):
                services(e)
                target=e.object(0x30,'record-output',fill=0x9d)
                src=e.object(40,'record-source',data=struct.pack('<10H',*words)+b'needle\0')
                linked=e.object(8,'lookup-value',fill=0x3a)
                parent=0 if parent_mode=='null' else registry(e,[('needle',linked)] if parent_mode=='hit' else [])
                return {'self':target,'args':[parent,src]}
            yield case(f'record optional {optional} parent {parent_mode}',0x4d76e0,setup,2)
    for count in (-1,0,1,3):
        for name in (b'',b'q',b'odd name'):
            flags=random_source.getrandbits(32)
            def setup(e,count=count,name=name,flags=flags):
                services(e)
                return {'self':ani(e),'args':[0,binary(e,name,count,0x1340),flags]}
            yield case(f'ANI parse count {count} name {len(name)}',0x4d6070,setup,3)
    for kind in (0,0x424d50,0x504358,0x504944,0x524944,0xffffffff):
        for cached in (False,True):
            for payload in (b'',b'opaque\x83\xff'):
                def setup(e,kind=kind,cached=cached,payload=payload):
                    obj=virtual(e,0x34,[(0x28,4,0x81928374,None)])
                    return {'self':obj,'args':[resource(e,kind,payload=payload,cached=cached),0x43217865]}
                yield case(f'image load {kind:x} cache {cached} bytes {len(payload)}',0x4d2380,setup,2)
    for kind in (0,0x414e49):
        for cached in (False,True):
            for loaded in (False,True):
                def setup(e,kind=kind,cached=cached,loaded=loaded):
                    services(e)
                    raw=bytearray(0x20)
                    struct.pack_into('<I',raw,8,0x1230)
                    res=resource(e,kind,payload=bytes(raw) if loaded else b'',cached=cached)
                    return {'self':ani(e),'args':[0,res,0xA1938625]}
                yield case(f'ANI resource type {kind:x} cached {cached} loaded {loaded}',0x4d61b0,setup,3)
    for function in (0x4ce320,0x4ce480,0x4ce530):
        def setup(e,function=function):
            obj=group(e,[0,e.object(4,'occupied')],0,1)
            return {'self':obj,'args':[0,1,0] if function==0x4ce320 else [0,0,1,0]}
        yield case(f'create occupied {function:x}',function,setup,3 if function==0x4ce320 else 4)
    for selected in (-1,0,1,2,3):
        for result in (0,1,0xffffffff):
            def setup(e,selected=selected,result=result):
                img=virtual(e,0x34,[(0x34,2,result,None)])
                return {'self':group(e,[0,img,0],1,2),'args':[0x1638,selected,0xfedcba98]}
            yield case(f'update index {selected} result {result:x}',0x4ce770,setup,3)
    for function,slot,argc,objarg in [(0x4cfec0,0x34,4,1),(0x4cfee0,0x38,4,1),
                                      (0x4cff00,0x30,5,2),(0x4cff20,0x2c,5,2)]:
        for _ in range(3):
            values=[random_source.getrandbits(32) for _ in range(argc)]
            def setup(e,values=values,slot=slot,argc=argc,objarg=objarg):
                args=list(values)
                args[objarg]=virtual(e,0x6c,[(slot,argc-1,0x87549321,None)])
                return args
            yield Case(f'forward {function:x} {values[0]:x}',function,setup,
                       arguments=tuple((lambda t,i=i:t[i]) for i in range(argc)))
    for function,slot,argc in [(0x4cfaa0,0x38,4),(0x4cfba0,0x34,4),(0x4cfca0,0x30,5),(0x4cfdb0,0x2c,5)]:
        values=[random_source.getrandbits(32) for _ in range(argc)]
        def setup(e,slot=slot,argc=argc,values=values):
            services(e)
            obj=virtual(e,0x6c,[(slot,argc-1,0xDE718234,None)])
            reg=registry(e,[('group-key',obj)])
            args=list(values)
            args[1 if argc==4 else 2]=string(e,'group-key')
            return {'self':reg,'args':args}
        yield case(f'existing group {function:x}',function,setup,argc)
    for function in (0x4ce5e0,0x4ce670,0x4ce0d0,0x4cff40,0x4d0120):
        for prefix in (None,'','prefix'):
            def setup(e,function=function,prefix=prefix):
                services(e)
                obj=group(e) if function in (0x4ce5e0,0x4ce670) else registry(e,methods=[(0x54,1,1,None)])
                d=directory(e)
                args=[d] if function in (0x4ce5e0,0x4ce670) else [d,0 if prefix is None else string(e,prefix),string(e,'/')]
                return {'self':obj,'args':args}
            yield case(f'empty directory {function:x} prefix {prefix}',function,setup,
                       1 if function in (0x4ce5e0,0x4ce670) else 3)
    for fail in (False,True):
        def setup(e,fail=fail):
            services(e)
            reg=registry(e)
            if fail:e.override(NEW,allocate(fail=True))
            return {'self':reg,'args':[string(e,'ani-key'),resource(e,0)]}
        yield case(f'create ANI fail {fail}',0x4cdff0,setup,2)
    for present in (False,True):
        def setup(e,present=present):
            services(e)
            obj=virtual(e,0x20,[(4,1,0,None)])
            return {'self':registry(e,[('remove',obj)] if present else []),'args':[string(e,'remove')]}
        yield case(f'remove key present {present}',0x4cf230,setup,1)
    def lookup_missing(e):
        obj=registry(e)
        parent=e.get(obj+0xc)
        envdir=directory(e)
        e.put(parent+0x24,0)
        return {'self':obj,'args':[parent,0]}
    yield case('directory lookup null path',0x4cf1f0,lookup_missing,2)
    for function in (0x4ce5e0,0x4ce670):
        for result in (0,1,0x80000001):
            for occupied in (0,2,5):
                def setup(e,function=function,result=result,occupied=occupied):
                    names=(b'',b'abc',b'\x80-z009tail',b'7',b':X31')
                    kinds=(0x504358,0x424d50,0x524944,0x504944,0x999999)
                    resources=[resource(e,k,n) for k,n in zip(kinds,names)]
                    nodes=[type_node(e,resources[:3]),type_node(e,[]),type_node(e,resources[3:])]
                    d=directory(e,nodes)
                    obj=group(e,[0,0x1111,0,0x2222,0],1,3)
                    e.put(obj+0x18,occupied)
                    table=e.object(0x60,'group-interface')
                    e.put(obj,table)
                    def change(e,c):
                        e.put(obj+0x64,4,4)
                    slot=0x38 if function==0x4ce5e0 else 0x40
                    e.put(table+slot,callback(e,'enumerate-resource',3,result,change))
                    return {'self':obj,'args':[d]}
                yield case(f'enumerate {function:x} result {result:x} count {occupied}',function,setup,1)
    for function in (0x4cff40,0x4d0120):
        for prefix in (None,'','folder'):
            for child_result in (0,3,0xffffffff):
                for group_count in (0,2):
                    def setup(e,function=function,prefix=prefix,child_result=child_result,group_count=group_count):
                        services(e)
                        child1=directory(e,name='first')
                        child2=directory(e,name='second-long')
                        d=directory(e,children=[child1,child2])
                        obj=group(e)
                        e.put(obj+0x18,0 if group_count else 2)
                        table=e.object(0x60,'existing-group-table')
                        e.put(obj,table)
                        def reloaded(e,c):
                            e.put(obj+0x18,group_count)
                        e.put(table+0x28,callback(e,'group-populate',1,1,reloaded))
                        e.put(table+0x3c,callback(e,'group-reload',1,child_result,reloaded))
                        reg=registry(e,[('folder',obj)],[(0x48,3,child_result,None),(0x4c,3,child_result,None),(0x54,1,1,None)])
                        return {'self':reg,'args':[d,0 if prefix is None else string(e,prefix),string(e,'/')]}
                    yield case(f'tree {function:x} prefix {prefix} child {child_result:x} size {group_count}',function,setup,3)
    for prefix in (None,'','folder'):
        for loaded in (False,True):
            def setup(e,prefix=prefix,loaded=loaded):
                services(e)
                raw=bytearray(32)
                resources=[resource(e,0x414e49,'one',bytes(raw) if loaded else b''),resource(e,0,'skip')]
                t=type_node(e,resources)
                child=directory(e,[type_node(e,[resource(e,0x414e49,'nested',bytes(raw))])],name='child')
                d=directory(e,[t,type_node(e,[])],[child])
                return {'self':registry(e),'args':[d,0 if prefix is None else string(e,prefix),string(e,'/')]}
            yield case(f'ANI tree prefix {prefix} loaded {loaded}',0x4ce0d0,setup,3)
    for cached in (False,True):
        def setup(e,cached=cached):
            services(e)
            raw=bytes(32)
            return {'self':registry(e),'args':[string(e,'fresh-key'),resource(e,0x414e49,payload=raw,cached=cached)]}
        yield case(f'new sequence inserted cached {cached}',0x4cdff0,setup,2)
    for function in (0x4ce0d0,0x4cff40):
        def setup(e):
            e.override(NEW,allocate(fail=True))
            return {'self':registry(e),'args':[directory(e),0,string(e,'/')]}
        yield case(f'path allocation failure {function:x}',function,setup,3)
    for function in (0x4ce320,0x4ce480):
        for size,index in ((0,0),(3,1),(2,5)):
            def setup(e,function=function,size=size,index=index):
                services(e)
                obj=group(e,[0]*size)
                args=[resource(e,0),index,0x19283746] if function==0x4ce320 else [e.object(32,'invalid-image'),0,index,0x19283746]
                return {'self':obj,'args':args}
            yield case(f'new image rejected {function:x} size {size} index {index}',function,setup,3 if function==0x4ce320 else 4)
    for function in (0x4cfaa0,0x4cfca0):
        def setup(e,function=function):
            services(e)
            args=[resource(e,0),string(e,'fresh-group'),1,0x19283746] if function==0x4cfaa0 else [e.object(32,'invalid-image'),0,string(e,'fresh-group'),1,0x19283746]
            return {'self':registry(e),'args':args}
        yield case(f'new group insertion {function:x}',function,setup,4 if function==0x4cfaa0 else 5)
    for function in (0x4ce2d0,0x4d6210):
        for shrink in (False,True):
            def setup(e,function=function,shrink=shrink):
                offset=0x18 if function==0x4ce2d0 else 0x10
                obj=group(e) if function==0x4ce2d0 else ani(e,name='released-last')
                def change(e,c):
                    e.put(obj+offset,1 if shrink else 3)
                first=virtual(e,0x30,[(4,1,0,change)])
                last=virtual(e,0x30,[(4,1,0,None)])
                array(e,obj,0x10 if function==0x4ce2d0 else 8,[first,0,last])
                if not shrink:e.put(obj+offset,1)
                return {'self':obj,'args':[]}
            yield case(f'cleanup reload {function:x} shrink {shrink}',function,setup)
    for function in (0x4d6070,):
        for shrink_name in (False,True):
            def setup(e,shrink_name=shrink_name):
                obj=ani(e)
                source=binary(e,b'abcdef',0)
                def alloc(e,c):
                    out=e.object(c.arguments[0],'allocation',fill=0xA3)
                    if c.arguments[0]==8:
                        e.put(source+0x10,0 if shrink_name else 3)
                    return out
                e.override(NEW,alloc)
                return {'self':obj,'args':[0,source,0x91824635]}
            yield case(f'name length reloaded after allocation shrink {shrink_name}',function,setup,3)
    for found in (False,True):
        def setup(e,found=found):
            services(e)
            reg=registry(e,methods=[(0x48,3,0x91827364,None)])
            parent=e.get(reg+0xc)
            d=directory(e,children=[directory(e,name='')])
            buckets=e.object(5*16,'lookup-hash-buckets',fill=0)
            e.put(buckets+8,e.get(e.get(d+0x40)+8))
            e.put(d+0x3c,5,buckets)
            e.put(parent+0x24,d)
            return {'self':reg,'args':[parent,string(e,'' if found else 'absent')]}
        yield case(f'directory dispatch found {found}',0x4cf1f0,setup,2)
    for function in (0x4ce530,0x4cfdb0):
        for size,index,minimum,maximum in ((0,0,99999,0),(3,1,0,2),(2,5,99999,0)):
            def setup(e,function=function,size=size,index=index,minimum=minimum,maximum=maximum):
                services(e)
                manager=display(e)
                parent=e.object(0x30,'image-parent')
                e.put(parent+0x1c,manager)
                obj=group(e,[0]*size,minimum,maximum)
                e.put(obj+0xc,parent)
                if function==0x4ce530:
                    return {'self':obj,'args':[7,3,index,0]}
                reg=registry(e)
                e.put(reg+0xc,parent)
                return {'self':reg,'args':[7,3,string(e,'blank-group'),index,0]}
            yield case(f'blank image {function:x} size {size} index {index}',function,setup,4 if function==0x4ce530 else 5)


    for function in (0x4ce320,0x4ce480):
        for size,index,minimum,maximum in ((0,0,99999,0),(3,1,0,2),(2,5,99999,0)):
            def setup(e,function=function,size=size,index=index,minimum=minimum,maximum=maximum):
                services(e)
                manager=display(e)
                parent=e.object(0x30,'image-parent')
                e.put(parent+0x1c,manager)
                obj=group(e,[0]*size,minimum,maximum)
                e.put(obj+0xc,parent)
                raw=bitmap()
                data=e.object(len(raw),'BMP-file',data=raw)
                args=[resource(e,0x424d50,payload=raw),index,0] if function==0x4ce320 else [data,1,index,len(raw)]
                return {'self':obj,'args':args}
            yield case(f'BMP image {function:x} size {size} index {index}',function,setup,3 if function==0x4ce320 else 4)
    for success in (False,True):
        def setup(e,success=success):
            manager=display(e)
            if not success:
                e.put(manager,0)
            parent=e.object(0x30,'image-parent')
            e.put(parent+0x1c,manager)
            obj=group(e)
            e.put(obj+0xc,parent)
            return {'self':obj,'args':[7,3,0,0]}
        yield case(f'blank physical creation succeeds {success}',0x4ce530,setup,4)


    for function in (0x4d2380,0x4d61b0):
        def setup(e,function=function):
            services(e)
            obj=virtual(e,0x34,[(0x28,4,1,None)]) if function==0x4d2380 else ani(e)
            res=resource(e,0x424d50 if function==0x4d2380 else 0x414e49,payload=b'allocate-this',cached=True)
            e.put(res+0x18,0)
            e.override(NEW,allocate(fail=True))
            return {'self':obj,'args':[res,0x1243] if function==0x4d2380 else [0,res,0x12345678]}
        yield case(f'resource allocation failure {function:x}',function,setup,2 if function==0x4d2380 else 3)
    for initial in (0,1):
        def setup(e,initial=initial):
            services(e)
            obj=ani(e,[e.object(0x30,'existing-record',fill=0x83)] if initial else [])
            linked=e.object(12,'linked-image',fill=0x73)
            parent=registry(e,[('frame-a',linked)])
            raw=bytearray(32)
            struct.pack_into('<III',raw,8,0x8140,3,3)
            raw+=b'ANI'
            for i, text in enumerate((b'frame-a',b'missing',b'')):
                raw+=struct.pack('<10H',0x1202+i*4,0x8000+i,0x7fff-i,0xffff-i,7+i,0x8312+i,0x1435+i,0xf001+i,0x6abc+i,0xcaef+i)
                raw+=text+b'\0'
            source=e.object(len(raw)+4,'ANI-variable-records',data=raw)
            return {'self':obj,'args':[parent,source,0x1381]}
        yield case(f'ANI variable names append after {initial}',0x4d6070,setup,3)
    for cached in (False,True):
        def setup(e,cached=cached):
            res=resource(e,0x504944,payload=b'contents-to-release',cached=cached)
            replacement=e.object(9,'late-cache',fill=0x6a)
            def mutate(e,c):
                e.put(res+0x18,replacement)
                e.put(res+0x14,7)
            obj=virtual(e,0x34,[(0x28,4,0xF1986243,mutate)])
            return {'self':obj,'args':[res,0x87126354]}
        yield case(f'loader callback mutates cache {cached}',0x4d2380,setup,2)


    def new_file_group(e):
        services(e)
        reg=registry(e)
        parent=e.get(reg+0xc)
        e.put(parent+0x1c,display(e))
        return {'self':reg,'args':[string(e,'missing-bitmap'),string(e,'new-file-group'),2,0]}
    yield case('new file group missing embedded bitmap',0x4cfba0,new_file_group,4)


    for function in (0x4ce320,0x4ce480,0x4ce530):
        def setup(e,function=function):
            services(e)
            obj=group(e,[0,0,0],99999,0)
            def change(e,c):
                e.put(obj+0x64,0,8)
                slots=e.object(12,'replacement-array',words=[0,0,0])
                e.put(obj+0x14,slots,3,3)
            manager=display(e,create_change=change)
            parent=e.object(0x30,'image-parent')
            e.put(parent+0x1c,manager)
            e.put(obj+0xc,parent)
            raw=bitmap()
            data=e.object(len(raw),'BMP-file',data=raw)
            args=([resource(e,0x424d50,payload=raw),1,0] if function==0x4ce320 else
                  [data,1,1,len(raw)] if function==0x4ce480 else [7,3,1,0])
            return {'self':obj,'args':args}
        yield case(f'creation reloads array and bounds {function:x}',function,setup,3 if function==0x4ce320 else 4)


def display(env, width=7, height=3, depth=24, create_change=None):
    """Physical DirectDraw storage; all surface construction remains original."""
    manager=env.object(0x900,'display-manager')
    interface=env.object(4,'DirectDraw')
    table=env.object(0x80,'DirectDraw-table')
    surface=env.object(4,'DirectDrawSurface')
    stable=env.object(0x90,'DirectDrawSurface-table')
    pixels=env.object(4096,'physical-pixels',fill=0xDA)
    receipt=env.object(0x100,'physical-display-receipt')
    env.put(manager,interface)
    env.put(manager+0x474,depth)
    env.put(manager+0x3b8,0x50e924,0,0,0,0,0,4)
    env.put(interface,table)
    env.put(surface,stable)
    def create(e,c):
        e.put(receipt,*c.arguments)
        e.write(receipt+0x20,e.read(c.arguments[1],0x6c))
        e.put(c.arguments[2],surface)
        if create_change:
            create_change(e,c)
        return 0
    def describe(e,c):
        desc=c.arguments[1]
        e.put(desc,0x6c,7,height,width,width*4)
        e.put(desc+0x48,0x20)
        e.put(desc+0x54,depth)
        return 0
    def lock(e,c):
        desc=c.arguments[2]
        e.put(desc,0x6c,7,height,width,width*4)
        e.put(desc+0x54,depth)
        e.put(desc+0x24,pixels)
        return 0
    env.put(table+0x18,env.stub('IDirectDraw::CreateSurface','stdcall',4,create))
    env.put(stable+0x58,env.stub('IDirectDrawSurface::GetSurfaceDesc','stdcall',2,describe))
    env.put(stable+0x64,env.stub('IDirectDrawSurface::Lock','stdcall',5,lock))
    env.put(stable+0x80,env.stub('IDirectDrawSurface::Unlock','stdcall',2,lambda e,c:0))
    env.put(stable+0x74,env.stub('IDirectDrawSurface::SetColorKey','stdcall',3,lambda e,c:0))
    env.put(stable+8,env.stub('IDirectDrawSurface::Release','stdcall',1,lambda e,c:1))
    env.put(0x543170,0xffffffff)
    return manager


def bitmap():
    raw=bytearray(54+24*3)
    raw[:2]=b'BM'
    struct.pack_into('<I',raw,2,len(raw))
    struct.pack_into('<I',raw,10,54)
    struct.pack_into('<IiiHH',raw,14,40,7,3,1,24)
    struct.pack_into('<I',raw,34,72)
    for i in range(54,len(raw)):
        raw[i]=(i*37+13)&255
    return bytes(raw)
