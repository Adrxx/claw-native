"""Independent original-backed cases for downstream application helpers."""
from clawparity.cases import Case
from clawparity.fixtures import returns

def obj(env,*args,**kwargs):
    kwargs.setdefault('fill',0)
    return env.object(*args,**kwargs)


def cstring(env, text, name='string'):
    data = text if isinstance(text, bytes) else text.encode('ascii')
    p = obj(env,12 + len(data) + 1, name, words=[3, len(data), len(data)], data=b'')
    env.write(p + 12, data + b'\0')
    return p + 12


def physical(env):
    def interlocked(delta):
        def effect(e, call):
            p = call.arguments[0]
            v = (e.get(p) + delta) & 0xffffffff
            e.put(p, v)
            return v
        return effect
    env.override(0x5469ec, interlocked(1))
    env.override(0x5469e8, interlocked(-1))
    env.override(0x5469e4, lambda e,c: len(e.cstr(c.arguments[0])))
    env.override(0x546b10, lambda e,c: (e.write(c.arguments[0], e.cstr(c.arguments[1]) + b'\0'), c.arguments[0])[1])
    env.override(0x546d50, returns(0x12345678))
    env.override(0x546d54, returns(1))
    env.override(0x546d48, returns(1))
    def copy_n(e,c):
        dst,src,n=c.arguments
        if n:
            e.write(dst,e.cstr(src)[:n-1]+b'\0')
        return dst
    env.override(0x5469cc,copy_n)
    env.override(0x546ad0,returns(0))
    env.put(0x53c25c, 0)


def basic_display(code=0, null=False, shift=(0,0,0,0,0), color=0x1234):
    def setup(env):
        physical(env)
        app = obj(env,0x310, 'application')
        display = obj(env,0x60, 'display')
        log = obj(env,0x80, 'diagnostic-log')
        observer = obj(env,4, 'diagnostic-observer')
        table = obj(env,0x20, 'diagnostic-vtable')
        env.put(observer,table)
        def observe(e,c):
            i=e.get(log)
            e.put(log+4+i*8, *c.arguments)
            e.put(log,i+1)
            if null:
                e.put(app+0x30, display)
            return 0x4534
        env.put(table+0x1c,env.stub('report diagnostic', 'stdcall',2,observe))
        env.put(app+8,observer)
        env.put(app+0x30,0 if null else display)
        env.put(display+0x38,code)
        env.put(0x54135c,shift[0],shift[1],0,shift[2],shift[3],shift[4])
        env.put(0x543170,color)
        return {'app':app,'display':display}
    return setup


def packet_setup(kind=0, player_mode=3, fields=None, flags=None, lookup_fail=False, resource_mode=0, name=b'Raven', filename=b'', file_ok=False, send_status=0):
    fields={} if fields is None else fields
    flags={} if flags is None else flags
    def setup(env):
        physical(env)
        game=obj(env,0xc40,'multiplayer-state')
        app=obj(env,0x300,'application')
        window=obj(env,0x20,'window')
        state=obj(env,0x40,'state')
        resources=obj(env,0x80,'resources')
        config=obj(env,0x180,'config')
        manager=obj(env,0x20,'multiplayer-manager')
        dp=obj(env,4,'directplay')
        table=obj(env,0x80,'directplay-vtable')
        player=obj(env,0x30,'remote-player')
        actor_link=obj(env,0x30,'player-actor-link')
        actor=obj(env,0x140,'actor',fill=0x67)
        sender=obj(env,8,'local-player',words=[0x1234,0x2634])
        log=obj(env,0x600,'callback-observations')
        packet=obj(env,0x80,'packet',fill=0xa9)
        env.put(game+4,app)
        env.put(game+0xc,state)
        env.put(app+4,window)
        env.put(window+4,0x76543210)
        env.put(app+0x30,0 if kind==0x31 else state)
        env.put(state+0x28,resources)
        env.put(state+0x24,config)
        env.put(resources+0x30,1 if resource_mode==0 else 0)
        env.put(resources+0x14,0,17,0,0,0,0)
        env.put(game+0x780,manager,sender)
        env.put(manager+0x18,dp)
        env.put(dp,table)
        env.put(player+4,0x3344)
        env.put(player+8,cstring(env,name))
        env.put(player+0x14,actor_link if player_mode>=2 else 0)
        env.put(actor_link,actor if player_mode>=3 else 0)
        env.put(actor_link+0x24,1)
        env.put(game+0xc08,0,obj(env,16,'scores-array'),4,4,0)
        env.put(game+0xbe4,cstring(env,b'Old end message'))
        chat=obj(env,0x30,'chat')
        env.put(chat+0x18,10)
        env.put(app+0x4c,chat)
        env.put(0x537e88,actor)
        env.put(app+0xc0,cstring(env,filename))
        env.put(config+0xac,0x9482)
        env.put(0x532c0c,1 if resource_mode==3 else 0)
        if resource_mode>=2:
            sound_manager=obj(env,0x80,'sound-manager')
            sound=obj(env,0x40,'sound-sample')
            sound_resource=obj(env,0x20,'sound-resource')
            env.put(sound_resource+0x10,sound)
            env.put(sound+0x10,sound_manager)
            if resource_mode==3:
                env.put(sound_manager+0x78,1)
                voice=obj(env,0x34,'playing-sound-voice')
                buffer=obj(env,4,'directsound-buffer')
                methods=obj(env,0x48,'directsound-methods')
                sound_log=obj(env,0x200,'sound-operation-log')
                env.put(buffer,methods)
                env.put(voice+0xc,buffer,sound_manager,0x5321,22050)
                env.put(voice+0x30,1)
                env.put(sound+0x18,22050,0x1243,0x3789)
                env.put(sound+0x30,voice+4,voice+4)
                def sound_effect(tag):
                    def effect(e,c):
                        n=e.get(sound_log)
                        e.put(sound_log+4+n*24,tag,len(c.arguments),*c.arguments)
                        e.put(sound_log,n+1)
                        if tag==0x24:
                            e.put(c.arguments[1],0)
                        return 0
                    return effect
                for slot,argc in ((0x24,2),(0x30,4),(0x3c,2),(0x40,2),(0x44,2)):
                    env.put(methods+slot,env.stub(f'DirectSound method{slot:x}','stdcall',argc,sound_effect(slot)))
            buckets=obj(env,17*4,'sound-map-buckets')
            env.put(resources+0x14,buckets,17)
            for key in (b'GAME_CATNMAG',b'GAME_NEWMESSAGE'):
                h=0
                for byte in key: h=(h*33+byte)&0xffffffff
                i=h%17
                key_string=cstring(env,key)
                node=obj(env,16,'sound-map-node',words=[env.get(buckets+i*4),0,key_string,sound_resource])
                env.put(buckets+i*4,node)
        def read_file(e,c):
            data=bytearray(0x5f4)
            data[:4]=(0x5f4).to_bytes(4,'little')
            data[0x2ec:0x2f0]=(0x9482).to_bytes(4,'little')
            size=c.arguments[2]
            e.write(c.arguments[1],bytes(data[:size]))
            e.put(c.arguments[3],size)
            return 1
        env.override(0x546b00,returns(0x1234 if file_ok else 0xffffffff))
        env.override(0x546afc,read_file)
        env.override(0x546a04,returns(1))
        for offset,value in flags.items(): env.put(game+offset,value)
        for offset,value in fields.items(): env.put(packet+offset,value)
        env.put(packet,kind)
        if kind==0x3f0: env.write(packet+8,b'hello\0')
        def lookup(e,c):
            n=e.get(log)
            e.put(log+4+n*16,c.arguments[1],c.arguments[4],e.get(c.arguments[3]),0x55667788)
            e.put(log,n+1)
            e.put(c.arguments[2],player if player_mode else 0)
            return 0x80004005 if lookup_fail else 0
        def send(e,c):
            p=log+0x300
            e.put(p,*c.arguments)
            if c.arguments[4] and c.arguments[5]:
                e.write(p+0x30,e.read(c.arguments[4],min(c.arguments[5],0x40)))
            return send_status
        env.put(table+0x50,env.stub('DirectPlay lookup','stdcall',5,lookup))
        env.put(table+0x68,env.stub('DirectPlay send','stdcall',6,send))
        return dict(game=game,app=app,manager=manager,player=player,packet=packet,actor=actor,log=log,resources=resources)
    return setup


def cases(random_source):
    for mode in ('no-table','empty','collision','found'):
        for key in (0,1,0x1234,0xffffffff):
            value=random_source.getrandbits(32)
            def popup(env,mode=mode,key=key,value=value):
                physical(env)
                app=obj(env,0x2a0,'popup')
                buckets=obj(env,17*4,'popup-buckets')
                node=obj(env,12,'popup-association',words=[0,key,value])
                other=obj(env,12,'popup-collision',words=[node if mode=='found' else 0,key^1,0x31321314])
                env.put(app+0x27c,0 if mode=='no-table' else buckets,17)
                if mode in ('collision','found'):
                    env.put(buckets+((key>>4)%17)*4,other)
                return dict(app=app)
            yield Case(f'popup {mode} key{key:x}',0x424db0,popup,receiver=lambda t:t['app'],arguments=(key,))
    for mode in (0,1,-1,0x789a):
        def archive(env,mode=mode):
            physical(env)
            app=obj(env,0x110,'application')
            out=obj(env,4,'returned-cstring')
            env.put(app+0xf8,cstring(env,b'CLAW.REZ'),cstring(env,b'CLAWDEMO.REZ'))
            env.put(app+0x104,mode)
            return dict(app=app,out=out)
        yield Case(f'archive mode {mode}',0x4268b0,archive,receiver=lambda t:t['app'],arguments=(lambda t:t['out'],))
    for code in (0,1,0x3ef,0x3f0,0x3f1,0x3f2,0x3f3,0x7d1,0x7d2,0x7d3,0x7d4,0xbb9,0xbba,0xbbb,0x80e9,0x80ea,0x80eb,0x80ec,0x80ed,0x80ee,0xffffffff):
        yield Case(f'display error {code:x}',0x42c0b0,basic_display(code),receiver=lambda t:t['app'],arguments=(0x3456789a,))
    yield Case('display installed by first error callback',0x42c0b0,basic_display(0x3f2,True),receiver=lambda t:t['app'],arguments=(0x12344567,))
    for depth in (0,7,8,16,24,32,0xffffffff):
        for absent in (False,True):
            yield Case(f'colorkey depth {depth} absent {absent}',0x42c640,basic_display(0,absent),receiver=lambda t:t['app'],arguments=(depth,))
    shifts=[(0,0,0,0,0),(11,5,3,2,3),(31,31,31,31,31),(32,33,34,35,36),(7,0,4,8,0),(16,23,1,31,5)]
    shifts += [tuple(random_source.getrandbits(32) for _ in range(5)) for _ in range(20)]
    for i,shift in enumerate(shifts):
        yield Case(f'colorkey packed shifts {i}',0x42c640,basic_display(shift=shift,color=random_source.getrandbits(32)),receiver=lambda t:t['app'],arguments=(16,))
    for recipient in (False,True):
        def send_case(env,recipient=recipient):
            t=packet_setup()(env)
            t['recipient']=t['player'] if recipient else 0
            return t
        yield Case(f'send recipient {recipient}',0x477790,send_case,receiver=lambda t:t['game'],arguments=(lambda t:t['recipient'],lambda t:t['packet'],0x84563729))
    yield Case('null packet',0x477a10,packet_setup(),receiver=lambda t:t['game'],arguments=(0x3544,0,0xdeadbeef))
    for kind in (0,1,2,3,4,5,6,0x30,0x31,0x32,0x100,0x101,0x102,0x3e7,0x3e8,0x3e9,0x3ea,0x3eb,0x3ec,0x3ed,0x3ee,0x3ef,0x3f0,0x3f1,0x3f2,0x3f3,0x3f4,0x3f5,0x3f6,0xffffffff):
        flags={0x790:1,0x78c:1,0xbcc:0}
        fields={4:0,8:0x44556677,12:0x89234567,16:0x31243}
        yield Case(f'packet basic {kind:x}',0x477a10,packet_setup(kind,fields=fields,flags=flags),receiver=lambda t:t['game'],arguments=(0x789a,lambda t:t['packet'],0x10203040))
    for kind in (0x3e9,0x3ec,0x3ed):
        for mode in (0,1,2,3):
            for bit in (0,2):
                yield Case(f'packet actor {kind:x} mode{mode} bit{bit}',0x477a10,packet_setup(kind,mode,fields={4:0x81724356,8:0x8000001f,12:0x346789ab,16:0x89000000|bit}),receiver=lambda t:t['game'],arguments=(0x789a,lambda t:t['packet'],0xfedcba98))
    for kind,fields,flags,mode in [
        (5,{4:1,8:0x7564},{},0),
        (0x3ea,{12:0x6745},{0x790:0},0),
        (0x3eb,{}, {0x78c:0,0xbcc:0},0),
        (0x3eb,{}, {0x78c:0,0xbcc:1,0x790:1,0x7b8:1},0),
        (0x3eb,{}, {0x78c:0,0xbcc:1,0x790:0,0x7b8:1},0),
        (0x3eb,{}, {0x78c:1,0xbcc:2},0),
        (0x3f3,{}, {0x79c:1},0),
        (0x3f3,{}, {0x79c:1},3),
        (0x3ec,{4:0x80912347,12:0x71234567,16:0x416},{0xbcc:2},3),
        (0x3f5,{12:0x9482},{0x258:1},3),
    ]:
        yield Case(f'packet alternate {kind:x} {fields} {flags} player{mode}',0x477a10,packet_setup(kind,mode,fields,flags),receiver=lambda t:t['game'],arguments=(0x9988,lambda t:t['packet'],0x0badcafe))

    for kind in (0x3eb,0x3f0):
        for resource_mode in (1,2,3):
            for finished in (0,1):
                flags={0x78c:finished,0xbcc:2}
                yield Case(f'sound packet {kind:x} map{resource_mode} finished{finished}',0x477a10,packet_setup(kind,flags=flags,resource_mode=resource_mode),receiver=lambda t:t['game'],arguments=(0x9988,lambda t:t['packet'],0x10304050))
    for mode in (0,1,2):
        for resource_mode in (1,2,3):
            flags={0x78c:0,0xbcc:1,0x790:0,0x7b8:1}
            yield Case(f'last level mode{mode} sound{resource_mode}',0x477a10,packet_setup(0x3eb,mode,flags=flags,resource_mode=resource_mode),receiver=lambda t:t['game'],arguments=(0x9988,lambda t:t['packet'],0x11223344))
    for filename in (b'',b'LEVEL.WWD'):
        for file_ok in (False,True):
            for equal in (False,True):
                fields={12:0x9482 if equal else 0x4521}
                def file_case(env,filename=filename,file_ok=file_ok,fields=fields):
                    t=packet_setup(0x3f5,fields=fields,flags={0x258:1},filename=filename,file_ok=file_ok)(env)
                    config=env.get(env.get(t['game']+0xc)+0x24)
                    env.put(config+0xac,0)
                    return t
                yield Case(f'checksum file {filename} ok{file_ok} equal{equal}',0x477a10,file_case,receiver=lambda t:t['game'],arguments=(0x9988,lambda t:t['packet'],0x55667788))
    for i in range(12):
        fields={4:random_source.getrandbits(32),8:random_source.getrandbits(32),12:random_source.getrandbits(32),16:random_source.getrandbits(32)}
        yield Case(f'packet position random {i}',0x477a10,packet_setup(0x3e9,fields=fields),receiver=lambda t:t['game'],arguments=(0x8ffffffe,lambda t:t['packet'],0x12345678))

    for stop in (0,1):
        yield Case(f'communication lost stop{stop}',0x477a10,packet_setup(0x31,flags={0x7ac:1,0x7bc:stop}),receiver=lambda t:t['game'],arguments=(0x9977,lambda t:t['packet'],0x12131415))
    yield Case('last level sends completion',0x477a10,packet_setup(0x3eb,flags={0x78c:0,0xbcc:1,0x790:1,0x7b8:0}),receiver=lambda t:t['game'],arguments=(0x9977,lambda t:t['packet'],0x21222324))

    for name in (b'',b'ABC',b'ABCD',b'ABCDEF'):
        yield Case(f'score record name length{len(name)}',0x477a10,packet_setup(0x3ec,fields={4:0x87123456,12:0x68234517,16:0x3216},flags={0xbcc:2},name=name),receiver=lambda t:t['game'],arguments=(0x4321,lambda t:t['packet'],0x21))
    for status in (1,0x80004005,0x88770005):
        yield Case(f'send failure {status:x}',0x477790,packet_setup(send_status=status),receiver=lambda t:t['game'],arguments=(lambda t:t['player'],lambda t:t['packet'],0x89234756))

    # Distinguish the game decisions from adjacent state words. Sound calls
    # enter unchanged playback policy and a real virtual physical buffer.
    for finished in (0,1):
        for mode in (0,1,2,3):
            for local in (0,1):
                for disabled in (0,1):
                    def observed_sound(env,finished=finished,mode=mode,local=local,disabled=disabled):
                        t=packet_setup(0x3eb,flags={0x78c:finished,0xbcc:mode,0x790:local,0x794:1-local,0x7b8:1},resource_mode=3)(env)
                        r=t['resources']
                        env.put(r+0x2c,0x7351 if not disabled else 0)
                        env.put(r+0x30,disabled,1-disabled)
                        return t
                    yield Case(f'observed end sound finished{finished} mode{mode} local{local} disabled{disabled}',0x477a10,observed_sound,receiver=lambda t:t['game'],arguments=(0x9988,lambda t:t['packet'],0x12345678))
