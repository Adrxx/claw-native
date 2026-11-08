"""Original-driven cases for v1.3 cheat actions and acknowledgement helpers."""
from clawparity.cases import Case
DISPATCH=0x42A9B0
ACK=0x42C780
MODE=0x42C7A0
TEXT=0x4233E0
COMMANDS=(0x8043,0x8044,0x8045,0x8046,0x8047,0x8049,0x804A,0x804B,0x804C,0x804D,0x804E,0x804F,0x805B,0x8064,0x8065,0x8066,0x8068,0x806A,0x806C,0x806E,0x806F,0x8071,0x8072,0x8076,0x8077,0x8078,0x8079,0x807A,0x807B,0x8086,0x8087,0x8088,0x8089,0x808A,0x808B,0x808D,0x808E,0x808F,0x8091,0x8092,0x8093,*range(0x809C,0x80AB),*range(0x80AD,0x80B7))

def setup_case(v):
    def setup(env):
        sizes={'app':0x200,'state':0x400,'owner':0x100,'sound':0x100,'anim':0x100,'world':0x200,'app_vt':0x100,'state_vt':0x100,'log':0x10000,'text':0x40,'player':0x600,'logic':0x400,'stats':0x400,'window':0x20,'error':0x300,'error_vt':0x40,'music':0x80,'sequence':0x100,'sequence_vt':0x40,'renderer':0x100,'profile':0x200,'backend':0x20,'palette':0x1000,'graphics':0x80,'front':0x80,'front_vt':0x40,'active_map':0x100,'resource':0x100,'frames':0x10,'frame':0x80,'plane':0x200,'planes':0x10}
        t={name:env.object(size,name,fill=0) for name,size in sizes.items()}
        t['message']=env.object(128,'message',data=b'Original acknowledgement\0')
        sounds=[env.object(0x20,'sound resource %d'%i,fill=0) for i in range(3)]
        def record(env,call,payload=b''):
            count=env.get(t['log']); slot=t['log']+4+count*192
            env.put(slot,call.receiver,len(call.arguments),*call.arguments)
            if payload: env.write(slot+48,payload[:140])
            env.put(t['log'],count+1)
        def generic(env,call):
            record(env,call)
            return 1
        def state_id(env,call):
            record(env,call)
            if v.get('resolution') and env.calls_so_far(state_stub)>1:
                env.put(t['app']+0x30,0); env.put(0x5365d4,0)
            if v.get('clear_state'): env.put(t['app']+0x2c,0)
            return (2 if v.get('level_factory') else v.get('second_state',3)) if env.calls_so_far(state_stub)>1 else v.get('state',3)
        env.put(t['app_vt']+0xc,env.stub('application has state','thiscall',0,generic))
        state_stub=env.stub('game state id','thiscall',0,state_id)
        env.put(t['state_vt']+0x10,state_stub)
        env.put(t['state_vt'],env.stub('old state destroy','thiscall',1,generic))
        env.put(t['app']+0xa4,v.get('shutdown',1))
        for offset in (0x24,0x28): env.put(t['state_vt']+offset,env.stub('pause/resume %x'%offset,'thiscall',1,generic))
        env.put(t['error_vt']+0x1c,env.stub('error dialog','thiscall',2,generic))
        env.put(t['error'],t['error_vt'])
        env.put(t['app'],t['app_vt'])
        env.put(t['app']+4,t['window'],t['error'])
        env.put(t['window']+4,0x23456789)
        env.put(t['app']+0x14,v.get('music_enabled',1),v.get('adjacent_music',0))
        env.put(t['app']+0x2c,t['state'],t['owner'])
        env.put(t['app']+0x4c,0 if v.get('no_text') else t['text'],0 if v.get('no_music') else t['music'])
        env.put(t['app']+0x78,v.get('depth',32),v.get('width',320),200)
        env.put(t['state'],t['state_vt'])
        env.put(t['state']+0x2c,t['renderer'])
        env.put(t['owner']+0x10,t['anim'])
        env.put(t['owner']+4,t['graphics'])
        env.put(t['owner']+0x18,t['active_map'])
        env.put(t['graphics']+0x10,t['front'])
        env.put(t['front'],t['front_vt'])
        mode=v.get('resolution')
        env.put(t['front']+0x10,320 if mode=='first' else (800 if mode=='failure' else 640),200 if mode=='first' else (600 if mode=='failure' else 480),32)
        env.put(t['front_vt']+0x20,env.stub('set physical resolution','thiscall',3,lambda e,c:0))
        env.put(t['resource']+0x14,t['frames'])
        env.put(t['frames'],t['frame'])
        env.put(t['world']+0x38,t['planes'],1)
        env.put(t['planes'],t['plane'])
        env.put(t['plane']+8,v.get('plane_bits',0))
        env.write(t['plane']+0xb4,b'MONOLITH\0')
        env.put(t['owner']+0x24,t['world'],t['sound'])
        env.put(t['sound']+0x30,v.get('sound_disabled',0))
        env.put(t['player']+0x7c,t['logic'])
        env.put(t['player']+0x40,v.get('bits',0xA2))
        env.put(t['player']+0x128,17)
        env.put(t['logic']+0x14,t['stats'])
        env.put(t['stats']+0x70,11,22,33)
        env.put(t['music']+0x1c,0 if v.get('no_sequence') else t['sequence'])
        if v.get('music_lookup'):
            env.put(t['music']+0x20,0x55667788)
            env.put(t['music']+0x28,1)
        env.put(t['sequence'],t['sequence_vt'])
        env.put(t['sequence_vt']+0x18,env.stub('sequence initialized','thiscall',0,lambda e,c:v.get('ready',1)))
        env.put(t['sequence']+0x58,0x12345000)
        env.put(t['renderer']+0x10,t['palette'])
        env.put(t['palette']+0xc,t['palette']+0x100)
        env.put(t['sound']+0x1c,v.get('enum_count',3))
        env.put(t['profile']+0xb0,1931,v.get('custom_width',640),v.get('custom_height',480),983)
        env.put(0x5360a8,0 if v.get('no_profile') else t['profile'])
        env.put(0x5365d4,0 if v.get('no_player') else t['player'])
        env.put(0x535910,t['app'])
        env.put(0x53b0f8,1)
        env.put(0x532d34,v.get('powerup',0))
        env.put(0x532d30,v.get('powerup_time',123))
        for address in range(0x53592c,0x535960,4): env.put(address,v.get('bits',0xA2))
        env.put(0x535998,v.get('bits',0xA2))
        env.put(0x5359a0,v.get('bits',0xA2))
        env.put(0x53591c,sounds[v.get('cursor_index',0)] if v.get('cursor') else 0)
        env.put(0x53098c,v.get('audio_enabled',1)); env.put(0x530990,v.get('volume',73)); env.put(0x5aafdc,v.get('clock',1000))
        for item in sounds: env.put(item+0x10,t['backend'],v.get('last',900),v.get('interval',100))
        def lookup(env,call):
            key=env.cstr(call.arguments[0]); value=sounds[1] if call.receiver==t['sound']+0x10 and v.get('found',True) else 0
            keytext=key.decode('latin1') if isinstance(key,bytes) else key
            if v.get('monolith') and keytext=='GAME_MONOLITH': value=t['resource']
            if v.get('developer') and keytext=='GAME_DEVHEADS': value=t['resource']
            if value or not v.get('miss_preserves_out'): env.put(call.arguments[1],value)
            record(env,call,key if isinstance(key,bytes) else key.encode())
            return int(value!=0)
        def formatting(env,call):
            fmt=env.cstr(call.arguments[1])
            if isinstance(fmt,bytes): fmt=fmt.decode('latin1')
            arg=call.arguments[2]
            if '%s' in fmt:
                arg=env.cstr(arg)
                if isinstance(arg,bytes): arg=arg.decode('latin1')
            result=(fmt%arg).encode('latin1'); env.write(call.arguments[0],result+b'\0'); record(env,call,result)
            return len(result)
        def clear(env,call):
            record(env,call); env.put(call.receiver+0xc,0)
            return 0
        def add(env,call):
            payload=env.cstr(call.arguments[0])
            if not isinstance(payload,bytes): payload=payload.encode('latin1')
            record(env,call,payload); env.put(call.receiver+0xc,env.get(call.receiver+0xc)+1)
            if v.get('remove_sequence'): env.put(t['music']+0x1c,0)
            return v.get('list_result',0x87654321)
        env.override(0x4fc6b4,lookup); env.override(0x4a5b6e,formatting)
        env.override(0x4fb719,clear); env.override(0x4fb80b,add); env.override(0x4fb883,add); env.override(0x4fcd34,clear)
        env.override(0x4a595b,lambda e,c:v.get('rand',0))
        env.override(0x50c620,lambda e,c:v.get('sequence_status',4))
        def enumerate_map(env,call):
            position=env.get(call.arguments[0]); index=0 if position==0xffffffff else position
            count=v.get('enum_count',3)
            env.put(call.arguments[0],index+1 if index+1<count else 0)
            env.put(call.arguments[1],t['message'])
            env.put(call.arguments[2],sounds[index%3])
            record(env,call)
            return 0
        env.override(0x4fc525,enumerate_map)
        env.override(0x4fcda9,generic)
        env.override(0x4fbd2a,generic)
        env.override(0x4fcaea,lambda e,c:0)
        env.override(0x50c58c,lambda e,c:v.get('clock',1000))
        for address in (0x4b3da0,0x50c4cc,0x4bc4f0,0x4bc560,0x4bc5b0,0x50c61c): env.override(address,generic)
        return t
    return setup

def dispatch(label,command,**options):
    if 0x809C<=command<=0x80A9: options['level_factory']=True
    return Case(label,DISPATCH,setup_case(options),receiver=lambda t:t['app'],arguments=(command,))

def cases(random_source):
    for command in COMMANDS:
        yield dispatch('action %04x no player'%command,command,no_player=True)
        yield dispatch('action %04x alternate bits'%command,command,bits=1,no_player=True,sound_disabled=1)
    for command in (0,0x8042,0x8048,0x80AC,0x80B7,0xFFFFFFFF,0xABCD8043): yield dispatch('selector %08x'%command,command,no_player=True)
    for state in (0,2,4,0xffffffff): yield dispatch('state guard %08x'%state,0x80B6,state=state)
    for command in (0x8044,0x8045,0x8046,0x806C,0x80B4):
        for bits in (0,4,0xFFFFFFFF): yield dispatch('live player %04x bits %x'%(command,bits),command,bits=bits)
    for command in (0x80AD,0x80B2,0x80B3,0x80B4,0x80B5,0x80B6):
        for extra in ({'found':False},{'audio_enabled':0},{'last':901},{'last':1001},{'clock':0,'last':0xFFFFFFF0,'interval':16},{'interval':0xFFFFFFFF},{'no_text':True}): yield dispatch('ack boundary %04x %s'%(command,extra),command,**extra)
    for command,powerup in ((0x805B,0x26BC),(0x808D,0x26B7),(0x808E,0x26BD),(0x8091,0x26BA),(0x8092,0x26B8),(0x8093,0x26B9)):
        for timer in (0,123,999990): yield dispatch('live powerup %04x timer %d'%(command,timer),command,powerup=powerup,powerup_time=timer)
    for command in COMMANDS:
        yield dispatch('random action %04x'%command,command,no_player=True,bits=random_source.getrandbits(32),volume=random_source.getrandbits(32),clock=random_source.getrandbits(32),last=0,interval=0)
    yield dispatch('state cleared by first query',0x808F,clear_state=True)
    yield dispatch('second state query is not gameplay',0x808F,second_state=2)
    for mode in ('first','fallback','failure'):
        yield dispatch('resolution '+mode,0x8076,width=641,resolution=mode,no_player=True)
    for bits in (0,2): yield dispatch('monolith existing plane %d'%bits,0x8086,monolith=True,plane_bits=bits)
    yield dispatch('developer resource available',0x8087,developer=True)
    for command in (0x8043,0x80B2,0x80B6):
        yield dispatch('map miss leaves initialized output %04x'%command,command,found=False,miss_preserves_out=True)
    yield dispatch('exhausted sound cursor resets to live first',0x80AE,cursor=True,cursor_index=2)
    for enabled,adjacent in ((1,0),(0,1),(7,0)):
        yield dispatch('monolith music enable independent %d %d'%(enabled,adjacent),0x8086,monolith=True,music_enabled=enabled,adjacent_music=adjacent,music_lookup=True)
    for width,height in ((0,480),(-1,480),(1,0),(1,-1),(1,2),(800,600),(0x7fffffff,1),(0x80000000,1),(1,0x80000000)):
        yield dispatch('custom dimensions %s %s'%(width,height),0x80AA,custom_width=width,custom_height=height)
    yield dispatch('no custom dimensions profile',0x80AA,no_profile=True)
    for command in range(0x809C,0x80AA): yield dispatch('level failure %04x'%command,command,shutdown=0)
    for command in (0x80AF,0x80B0,0x80B1):
        for extra in ({'music_enabled':0},{'no_music':True},{'no_sequence':True},{'ready':0},{'sequence_status':1},{'sequence_status':16},{'remove_sequence':True}): yield dispatch('music guards %04x %s'%(command,extra),command,**extra)
    for extra in ({'rand':0xffffffff},{'rand':1},{'rand':100},{'rand':101},{'rand':0x7fffffff},{'cursor':True},{'cursor':True,'enum_count':0},{'enum_count':0},{'audio_enabled':0},{'interval':101}): yield dispatch('sound cursor %s'%extra,0x80AE,**extra)
    for function in (ACK,MODE,TEXT):
        for options in ({},{'no_text':True}):
            args=(lambda t:t['message'],)
            if function==MODE: args+=(1,)
            if function==TEXT: args+=(4,)
            yield Case('direct helper %x %s'%(function,options),function,setup_case(options),receiver=(lambda t:t['text']) if function==TEXT else (lambda t:t['app']),arguments=args)
    for flag in (0,1,2,3,4,5,6,7,0xFF,0x100,0x101,0xffffff00,0xffffffff):
        for count in (0,7,8,0xffffffff):
            def direct(env,flag=flag,count=count):
                t=setup_case({})(env); env.put(t['text']+0xc,count)
                return t
            yield Case('text flags %x count %x'%(flag,count),TEXT,direct,receiver=lambda t:t['text'],arguments=(lambda t:t['message'],flag))
    yield Case('text null',TEXT,setup_case({}),receiver=lambda t:t['text'],arguments=(0,4))
    def empty(env):
        t=setup_case({})(env); env.write(t['message'],b'\0')
        return t
    yield Case('text empty',TEXT,empty,receiver=lambda t:t['text'],arguments=(lambda t:t['message'],4))
    for mode in (0,1,0xffffffff,random_source.getrandbits(32)): yield Case('mode flag %x'%mode,MODE,setup_case({}),receiver=lambda t:t['app'],arguments=(lambda t:t['message'],mode))
    # The application acknowledgement clears first even when the list is full.
    # Original 0x42c790 supplies flags 4; capacity rejection requires flags bit 1.
    def full_acknowledgement_list(env):
        t=setup_case({})(env)
        env.put(t['text']+0xc,8)
        return t
    yield Case('ack clears full list without capacity guard',ACK,full_acknowledgement_list,receiver=lambda t:t['app'],arguments=(lambda t:t['message'],))
