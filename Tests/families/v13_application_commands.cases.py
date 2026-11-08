"""Original-backed v1.3 application lifecycle comparisons."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, sequence, returns, halt
D,F,S,E,C=0x427d10,0x428d70,0x4498f0,0x46df80,0x42c380


def setup(state_id=2,live=True,shutdown=0,quit_flag=1,counter=9999,allocation=False,
          engine=True,window=True,profile=True,level=1,finished=0,cached=False,
          null_teardown=False,ticks=(100,4100),**opt):
    def make(env):
        objs={name:env.object(size,name,fill=0) for name,size in [('log',4096),('app',0x200),('state',0x1000),
              ('host',0x300),('wnd',0x100),('settings',0x100),('game',0x400),('resources',0x1000),
              ('sounds',0x100),('music',0x100),('keyboard',0x300),('user',0x3000),('scene',0x300),
              ('renderer',0x100),('backdesc',0x100),('network',0x100),('substate',0x100),('comholder',0x100),('surface',0x100),('com',0x100),('manager',0x100),('controller',0x100),
              ('actor',0x200),('directory',0x100),('dirconfig',0x100),('buckets',0x100),('resource-manager',0x100),('stack',0x100)]}
        a=objs['app']; st=objs['state']; g=objs['game']; w=objs['wnd']; h=objs['host']; log=objs['log']
        def record(tag,result=0):
            def effect(env,call):
                n=env.get(log); p=log+4+n*32
                env.put(p,tag,call.receiver,len(call.arguments),*(tuple(call.arguments)+(0,)*(4-len(call.arguments))))
                env.put(log,n+1)
                if tag==0x28 and null_teardown:env.put(a+0x2c,0)
                if tag==0x10 and opt.get('idseq'):
                    seq=opt['idseq'];return seq[min(env.calls_so_far(call.function),len(seq))-1]
                return result
            return effect
        def vt(obj,slots,name):
            table=env.object(0x100,name+'-vtable',fill=0);env.put(obj,table)
            for off,argc,result in slots:env.put(table+off,env.stub(name+hex(off),'thiscall',argc,record(off,result)))
        vt(st,[(0,1,0),(4,3,1),(0x10,0,state_id),(0x24,1,1),(0x28,1,1),(0x40,0,opt.get('slot40',0)),(0x4c,0,1),(0x50,1,1),(0x54,1,1),(0x5c,0,1)],'state')
        vt(h,[(0x1c,2,1)],'engine')
        vt(a,[(0xc,0,0)],'application')
        vt(objs['substate'],[(0x10,0,opt.get('substate',0))],'substate')
        env.put(st+0x154,objs['substate'])
        vt(objs['manager'],[(0x20,1,1)],'manager')
        vt(objs['renderer'],[(0x2c,2,1)],'renderer')
        cv=env.object(0x100,'COM-vtable',fill=0);env.put(objs['com'],cv)
        env.put(cv+0x14,env.stub('physical-blit','stdcall',6,record(0x14)))
        env.put(cv+0x28,env.stub('physical-device','stdcall',1,record(0x28)))
        env.put(cv+0x2c,env.stub('surface-flip','stdcall',3,record(0x2c)))
        env.put(objs['surface']+8,objs['com'])
        env.put(objs['scene']+0x60,0xffffffff)
        env.put(a+4,w if window else 0,h if engine else 0)
        env.put(a+0xc,opt.get('paused',0),opt.get('sound_on',0),opt.get('music_on',0))
        env.put(a+0x2c,st if live else 0,g if opt.get('game_present',True) else 0)
        env.put(a+0x34,objs['resource-manager'])
        env.put(objs['resource-manager']+0x44,objs['directory'])
        env.put(objs['directory']+0x18,objs['dirconfig'])
        env.put(objs['dirconfig']+0x68,1)
        env.put(objs['directory']+0x38,1,objs['buckets'])
        empty=env.object(16,'empty-CString',fill=0)
        env.put(empty,1,0,0)
        env.put(a+0xc4,empty+12)
        env.put(0x53b0f4,empty+12)
        env.put(a+0x38,env.object(16,'title',data=b'Claw\0'))
        env.put(a+0x4c,objs['controller'],objs['music'])
        env.put(a+0x5c,objs['controller']);env.put(a+0x64,objs['user'] if profile else 0)
        env.put(a+0x68,opt.get('sound_level',10))
        env.put(a+0x98,0x13579,quit_flag);env.put(a+0xa4,shutdown);env.put(a+0x154,7)
        env.put(a+0x160,objs['stack'],0)
        env.put(w+4,0x13572468);env.put(w+0x10,objs['settings'],objs['backdesc'],0x11223344)
        env.put(w+0x78,24);env.put(objs['settings']+0x2c,objs['surface'])
        env.put(objs['backdesc']+0x2c,objs['surface'])
        env.put(objs['settings']+0x10,640,480,32)
        env.put(objs['backdesc']+0x10,640,480,32)
        env.put(a+0x7c,640,480)
        env.put(g+0x18,objs['resources'])
        env.put(g+0x1c,objs['resources'])
        env.put(g+4,w,objs['manager'],objs['renderer']);env.put(g+0x14,objs['resources'])
        env.put(g+0x24,objs['scene'],objs['sounds']);env.put(objs['sounds']+0x30,opt.get('sound_disabled',0))
        env.put(objs['manager']+0xc,g);env.put(st+4,a);env.put(st+0xc,g);env.put(st+0x14,level)
        env.put(st+0x780,objs['network'])
        env.put(st+0x25c,finished);env.put(st+0x168,opt.get('exit_flag',0))
        env.put(objs['controller'],objs['resources'])
        env.put(objs['controller']+0xc,opt.get('controller_active',0));env.put(objs['music']+0x1c,0)
        env.put(objs['controller']+0x14,opt.get('actor_present',0));env.put(objs['actor']+0x7c,objs['controller'])
        env.put(objs['keyboard'],objs['keyboard'])
        env.put(0x535910,a,objs['keyboard'],objs['keyboard'])
        env.put(0x5365d4,objs['actor'] if opt.get('actor_global',False) else 0,st)
        env.put(0x535978,opt.get('developer',0));env.put(0x523580,counter);env.put(0x535928,opt.get('current_time',12345))
        if cached:env.put(a+0x164,1);env.put(objs['stack'],st)
        for i in range(16):
            env.put(objs['user']+0x187c+i*0xb0,1234567+i*1001)
            env.put(0x5357a4+i*4,7654321+i*1003);env.put(0x5357e0+i*4,0x10000101+i)
        env.override(0x4fcaea,lambda env,call:env.object(call.arguments[0],'allocation',fill=opt.get('allocator_fill',0xa5 if shutdown or opt.get('halt_clock') else 0)) if allocation else 0);env.override(0x50c58c,sequence(*ticks))
        def lookup(env,call):
            found=objs['resources'] if opt.get('sound_resource') else 0
            env.put(call.arguments[1],found);return int(bool(found))
        env.override(0x4fc6b4,lookup)
        def cstring(env,call):
            text=env.cstr(call.arguments[0]);raw=env.object(12+len(text)+1,'CString')
            env.put(raw,1,len(text),len(text));env.write(raw+12,text+b'\0');env.put(call.receiver,raw+12)
            return call.receiver
        env.override(0x4fce17,cstring);env.override(0x50c4d0,sequence(0xffffffff,0))
        for target in (0x50c4cc,0x50c4c4,0x4b9380,0x4fcd34,0x4fcda9,0x4fb719,0x4fb80b,0x4fb883,0x4fc3da,0x4fb8fa):
            env.override(target,returns(0))
        def resize(env,call):
            count=call.arguments[0]
            env.put(call.receiver+8,count)
            return 0
        env.override(0x4fbd2a,resize)
        def grow(env,call):
            index,value=call.arguments
            env.put(env.get(call.receiver+4)+index*4,value)
            env.put(call.receiver+8,index+1)
            return 0
        env.override(0x4fbe43,grow)
        for target in (0x50c008,0x50c000):env.override(target,returns(2))
        env.override(0x50c274,returns(0))
        env.override(0x50c184,returns(1))
        def atomic(delta):
            def effect(env,call):
                p=call.arguments[0];v=(env.get(p)+delta)&0xffffffff;env.put(p,v);return v
            return effect
        env.override(0x50c310,atomic(1));env.override(0x50c314,atomic(-1))
        def sprintf(env,call):
            fmt=env.cstr(call.arguments[1]);text=fmt.replace(b'%i',str(call.arguments[2]).encode())
            env.write(call.arguments[0],text+b'\0');return len(text)
        env.override(0x4a5b6e,sprintf)
        env.override(0x50c470,returns(0))
        env.override(0x50c42c,returns(0))
        env.override(0x4b3da0,returns(1))
        env.put(0x53098c,1)
        cursor_counter=env.object(4,'physical-cursor-display-count',words=[0xfffffffe])
        def cursor(env,call):
            delta=1 if call.arguments[0] else -1
            count=(env.get(cursor_counter)+delta)&0xffffffff
            env.put(cursor_counter,count)
            return count
        env.override(0x50c4d0,cursor)
        if opt.get('tree'):
            def directory(name,children=()):
                d=env.object(0x80,'directory-'+name,fill=0)
                namep=env.object(len(name)+1,'directory-name',data=name.encode()+b'\0')
                env.put(d,namep);env.put(d+0x18,objs['dirconfig'])
                table=env.object(16,'directory-buckets',fill=0);env.put(d+0x38,1,table)
                nodes=[env.object(0x18,'directory-node',fill=0) for child in children]
                if nodes:env.put(table+8,nodes[0]+4)
                for i,child in enumerate(children):
                    env.put(nodes[i]+0x14,child)
                    if i+1<len(nodes):env.put(nodes[i]+4,nodes[i+1]+4)
                return d
            leveldir=directory('LEVEL1');splash=directory('SPLASH');states=directory('STATES',(splash,));claw=directory('CLAW')
            root=directory('ROOT',(leveldir,states,claw));env.put(objs['resource-manager']+0x44,root)
            env.put(empty+4,1,1);env.write(empty+12,b'X\0')
            env.put(objs['sounds']+0x30,1)
            env.put(a+0x78,32)
        if opt.get('message'):
            descriptor=env.object(0x14,'message-descriptor',fill=0)
            opaque=env.object(16,'message-resource',fill=0)
            env.put(descriptor+0x10,0x494f30)
            env.put(g+0x10,objs['resources'])
            env.put(0x535840,100,200,740,680)
            def message_lookup(env,call):
                found=descriptor if env.cstr(call.arguments[0])==b'SingleFrameMessage' else 0
                env.put(call.arguments[1],found);return int(bool(found))
            env.override(0x4fc6b4,message_lookup)
            def map_slot(env,call):return env.object(4,'map-value',fill=0)
            def add_tail(env,call):
                node=env.object(12,'pointer-list-node',fill=0)
                previous=env.get(call.receiver+4)
                env.put(node,0,previous,call.arguments[0])
                if previous:env.put(previous,node)
                else:env.put(call.receiver,node)
                env.put(call.receiver+4,node,env.get(call.receiver+8)+1)
                return node
            env.override(0x4fc9cc,map_slot);env.override(0x4fbbcf,add_tail)
        if opt.get('halt_clock'):env.override(0x50c58c,halt())
        if opt.get('chat'):
            for i in range(7):env.write(objs['user']+0xe0+i*0x48,opt['chat']+b'\0')
        if opt.get('sound_instance'):env.put(objs['sounds']+0x2c,objs['resources'])
        if opt.get('crc'):
            env.put(w+0xc,objs['resources'])
            env.put(g+0x1c,objs['comholder']);env.put(objs['comholder'],objs['com'])
            env.put(0x535910,0);env.put(objs['sounds']+0x30,1)
        return objs
    return make


def case(label,fn,kw=None,args=(),receiver='app',expect='return'):
    return Case(label,fn,setup(**(kw or {})),receiver=(lambda t:t[receiver]) if receiver else 0,arguments=args,expect=expect)


def cases(random_source):
    for shut in (0,1,0x80000000):
        for host in (False,True):
            for wnd in (False,True):yield case(f'close {shut}/{host}/{wnd}',C,dict(shutdown=shut,engine=host,window=wnd))
    for live in (False,True):
        for shut in (0,1):
            for alloc in (False,True):yield case(f'80ac {live}/{shut}/{alloc}',D,dict(live=live,shutdown=shut,allocation=alloc),(0xabcdef,0x80ac,0x10203))
    for req in (0,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,0xffffffff):
        for live in (False,True):yield case(f'factory {req}/{live} no-memory',F,dict(live=live),(req,1,0,0x18293a4b))
    for state in (2,3,4,5):
        for count in (9999,1,0):
            for flag in (0,1):
                for cmd in (0x8006,0x800f):
                    if cmd==0x800f and state==3:continue
                    yield case(f'quit {cmd:x}/{state}/{count}/{flag}',D,dict(state_id=state,counter=count,quit_flag=flag),(1,cmd,0))
    for level in (0,1,2,3,14,15,16,0x7fffffff):
        for finished in (0,1):
            for cached in (False,True):yield case(f'stats {level}/{finished}/{cached}',S,dict(level=level,finished=finished,cached=cached,actor_global=True,actor_present=1,current_time=random_source.getrandbits(32)),receiver=None)
    for flag in (0,1,2,0xff):
        for start,now in ((100,100),(100,4099),(100,4100),(100,4101),(0xfffffff0,0xfffffff1),(0xfffff060,0),(0xfffffff0,0),(0xfffffff0,3983),(0xfffffff0,3984)):
            yield case(f'exit {flag}/{start:x}/{now:x}',E,dict(exit_flag=flag,ticks=(start,now)),receiver='state')
    for cmd in (0x8007,0x8009,0x800a,0x800e,0x801b,0x801c,0x8022,0x8026,0x802a,0x802b,0x802c,0x8035,0x8039,0x803a,0x803c,0x803d,0x8042,0x805c,0x8062,0x8063,0x8075,0x807c,0x807d,0x8082,0x8083,0x8084,0x8085,0x8095,0x80ff):
        yield case(f'dispatch guard {cmd:x}',D,dict(state_id=4 if cmd==0x8095 else 2),(1,cmd,9))

    commands=(0x8005,0x8007,0x8009,0x800a,0x800d,0x800e,0x801b,0x801c,0x8021,0x8022,0x8023,0x8024,0x8025,0x8026,0x8027,0x802a,0x802b,0x802c,0x8035,0x8036,0x8038,0x8039,0x803a,0x803c,0x803d,0x8041,0x8042,0x8050,0x8051,0x8052,0x8053,0x8054,0x8055,0x8056,0x8059,0x805c,0x8062,0x8063,0x8070,0x8075,0x807c,0x807d,0x807e,0x807f,0x8080,0x8082,0x8083,0x8084,0x8085,0x8090,0x8095,0x80ab,0x80ac)
    for state in (2,3,4,5):
        for cmd in commands:
            if cmd==0x8095 and state in (2,5):continue
            if cmd in (0x800d,0x8075,0x807e,0x807f) and state==3:continue
            yield case(f'dispatch matrix {cmd:x}/{state}',D,dict(state_id=state,actor_global=cmd in (0x803c,0x803d),sound_level=1 if cmd==0x801c else 10,game_present=cmd not in (0x802c,0x8041,0x8070),crc=cmd==0x8085),(1,cmd,9))
    for req in (2,3,4,5,8,9,10,11,12,13,14):
        yield case(f'factory {req} allocated',F,dict(live=True,allocation=True,quit_flag=0,halt_clock=req in (3,4,5,10,14)),(req,1,1,0x18293a4b),expect='halt' if req in (3,4,5,10,14) else 'return')
    for live in (False,True):
        yield case(f'factory developer {live}',F,dict(live=live,developer=1),(13,1,0,99))

    for cmd in range(0x8050,0x8057):
        for text in (b'A',b'four',b'seven!!'):
            yield case(f'chat {cmd:x}/{len(text)}',D,dict(state_id=4,chat=text),(1,cmd,0))

    for cmd in (0x8022,0x8026):
        yield case(f'dispatch sound lookup {cmd:x}',D,dict(sound_resource=True),(1,cmd,0))
    for sub in (0,2):
        yield case(f'dispatch state10 child{sub}',D,dict(state_id=10,substate=sub),(1,0x807c,0))
    yield case('dispatch sound off',D,dict(sound_on=1,sound_instance=True),(1,0x8009,0))
    yield case('dispatch music off',D,dict(state_id=3,music_on=1),(1,0x800a,0))
    yield case('dispatch reset live actor',D,dict(state_id=3,actor_global=True),(1,0x8063,0))
    yield case('dispatch controller live',D,dict(state_id=4,controller_active=1),(1,0x8083,0))
    yield case('quit state3 retains guarded helper',D,dict(state_id=3,idseq=(3,2)),(1,0x800f,0))

    yield case('factory14 authentic resource success',F,dict(allocation=True,live=False,tree=True),(14,1,0,0))
    yield case('exit authentic message',E,dict(allocation=True,message=True),receiver='state')

    for req in (2,3,4,5,8,9,10,11,12,13,14):
        fill=random_source.randrange(1,256)
        yield case(f'factory {req} nonzero constructor witness',F,dict(live=False,allocation=True,halt_clock=True,allocator_fill=fill),(req,0x76543210,0,0x1234abcd),expect='halt')
