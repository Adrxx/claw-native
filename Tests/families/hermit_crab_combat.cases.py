"""Original-backed hermit crab combat inputs."""
import struct
from clawparity.cases import Case

def signed(x):
    return x - 0x100000000 if x & 0x80000000 else x

def setup_case(v):
    def setup(env):
        def new(*args, **kwargs):
            kwargs.setdefault('fill', 0)
            return env.object(*args, **kwargs)
        crab = new(0x440, 'crab', fill=0x93)
        actor = new(0x1c0, 'collision', fill=0x57)
        physics = new(0x1c0, 'physics', fill=0x35)
        anim = crab+0x100 if v.get('alias_animation',False) else new(0x1c0, 'animation', fill=0x79)
        state = new(0x24, 'state', fill=0x29)
        player = new(0x150, 'player', fill=0x49)
        hit = new(0x150, 'contact', fill=0x65)
        table = new(0x64, 'combat vtable')
        log = new(0x2000, 'callback observations')
        env.put(crab, table)
        env.put(crab + 0xc, actor, state)
        env.put(crab + 0x128, physics, anim)
        env.put(state + 0x1c, 7)
        env.put(crab + 0x24, 0x15467)
        for off, number in ((0x40,17.25),(0x50,v.get('velocity',-23.5)),(0x58,31.75),(0x60,-42.25),(0x68,v.get('position',101.5)),(0x80,v.get('lower',-1000.)),(0x98,v.get('upper',1000.))):
            env.write(crab+off,struct.pack('<d',number))
        env.put(crab+0x118,v.get('previous',19))
        env.put(crab+0x120,v.get('collision_flags',0))
        env.put(crab+0x138,0xfffffff9,11,29,43)
        env.put(crab+0x210,0xffffffed,17,31,47)
        env.put(crab+0x220,2,5,23,37)
        env.put(crab+0x184,v.get('mode',0))
        env.put(crab+0x18c,v.get('direction',3))
        env.put(crab+0x280,v.get('target',100))
        env.put(crab+0x410,0,5000,v.get('start',900),v.get('duration',200),v.get('launch_start',900),v.get('launch_duration',200),v.get('launch',0),v.get('pending',0),hit if v.get('repeated',False) else 0)
        env.put(0x537210,v.get('clock',1000))
        env.put(0x5430c4,0)
        env.put(0x537e88,player)
        env.put(player+0x4c,v.get('player_x',100))
        env.put(player+0x128,*((0,0,20,20) if v.get('intersect',True) else (100,100,110,110)))
        env.put(actor+0x4c,v.get('actor_x',100),20)
        env.put(actor+0x64,9)
        env.put(actor+0x74,hit)
        env.put(actor+0xcc,v.get('actor_mode',8))
        env.put(actor+0x100,v.get('damage',0))
        env.put(hit+8,0x489)
        env.put(hit+0x4c,v.get('hit_x',101))
        env.put(hit+0xd0,v.get('kind',0x1000000))
        env.put(anim+0x40,0x40|v.get('facing',0))
        env.put(anim+0x4c,123,234)
        env.put(anim+0x64,6)
        env.put(anim+0x118,-7,8,19)
        env.put(anim+0x128,-11,13,29)
        env.put(anim+0x138,-17,23,37,41)
        env.put(anim+0x16c,v.get('animation_id',203))
        env.put(anim+0x190,0)
        env.put(anim+0x19c,v.get('active',0))
        env.put(anim+0x1a4,v.get('completed',0))
        for index,off in enumerate((0x308,0x310,0x32c,0x408)):
            frames=new(0x18,'sequence'); frame=new(0x30,'frame')
            entries=new(4,'frame pointers',words=[frame])
            env.put(frames+0xc,entries,1)
            env.put(frame+0x1c,0x90+index)
            env.put(crab+off,frames)
        # Original Patricia lookup, with distinct nonzero identifiers.
        names=[b'ES_ATTACK',b'ES_LAUNCH',b'ES_STRIKE',b'ES_MOVINGATTACK',b'ES_FALLING',b'ES_NUDGE',b'ES_HIDE']
        def bit(key,index): return ((key+b'\0')[index//8]>>(index%8))&1
        leaves=[]
        for index,name in enumerate(names):
            key=new(len(name)+1,'state key',data=name+b'\0')
            leaf=new(0x14,'state leaf')
            env.put(leaf+8,0xffffffff,key,20+index)
            leaves.append((name,leaf))
        def trie(items,start=0):
            if len(items)==1: return items[0][1]
            index=start
            while len({bit(name,index) for name,_ in items})==1: index+=1
            node=new(0x14,'state branch')
            env.put(node,trie([p for p in items if not bit(p[0],index)],index+1),trie([p for p in items if bit(p[0],index)],index+1),index)
            return node
        env.put(0x537668+0x18,trie(leaves))
        state_name=b'LS_DEAD\0' if v.get('dead',False) else b'ES_ATTACK\0'
        name=new(len(state_name),'current state name',data=state_name)
        current=new(4,'state names',words=[name])
        env.put(0x537698+8,7,7,current,0,4,0,0)
        scene=new(0x70,'scene'); owner=new(0x28,'actor owner')
        grid=new(0x94,'tile grid'); cells=new(4,'cells'); rows=new(4,'rows')
        tiles=new(4,'tiles'); tile=new(4,'tile'); tile_vtable=new(0x24,'tile vtable')
        env.put(scene+0x5c,grid); env.put(scene+0x4c,tiles)
        env.put(grid+0x20,cells,rows); env.put(grid+0x30,1024,1024); env.put(grid+0x8c,10,10)
        env.put(tiles,tile); env.put(tile,tile_vtable); env.put(owner+0x24,scene)
        env.put(physics+0xc,owner); env.put(physics+0x50,20); env.put(physics+0x124,10)
        env.put(physics+0x118,0x80000000)
        def record(tag):
            def effect(e,call):
                count=e.get(log); at=log+4+count*0x80
                e.put(at,tag,call.receiver,*call.arguments)
                e.write(at+0x20,e.read(crab+0x24,4)); e.write(at+0x24,e.read(crab+0x50,0x20))
                e.write(at+0x44,e.read(actor+0x138,16))
                e.put(at+0x54,e.get(state+0x1c),e.get(anim+0x190)); e.put(log,count+1)
                return v.get('callback_result',0x1234)
            return effect
        for slot,argc in ((0x18,0),(0x44,0),(0x58,0),(0x5c,1)):
            env.put(table+slot,env.stub('combat slot '+hex(slot),'thiscall',argc,record(slot)))
        def tile_query(e,call):
            record(0x4207f0)(e,call)
            if v.get('mutate_tile',False) and e.get(log)==1:
                e.put(crab+0x18c,2 if v.get('direction',3)==3 else 3)
                e.put(anim+0x40,e.get(anim+0x40)^2)
                e.put(state+0x1c,39)
                e.put(crab+0x308,e.get(crab+0x408))
                e.put(crab+0x138,0xffffffe5,59,71,83)
            return v.get('ground',1) if signed(call.arguments[1])>=31 else v.get('upper_tile',0)
        env.put(tile_vtable+0x20,env.stub('tile collision','thiscall',2,tile_query))
        sound=new(0x14,'sound handle'); sound_object=new(0x40,'sound object'); backend=new(0x7c,'sound backend')
        env.put(sound+0x10,sound_object); env.put(sound_object+0x10,backend)
        if v.get('active_sound',False):
            channel=new(0x38,'sound channel'); interface=new(4,'sound interface'); methods=new(0x48,'sound methods')
            env.put(backend+0x78,1)
            env.put(sound_object+0x30,channel+4,channel+4)
            env.put(sound_object+0x18,22050,23,17)
            env.put(channel+0xc,interface,backend,0x41,22050)
            env.put(channel+0x30,1)
            env.put(interface,methods)
            for slot,argc in ((0x24,2),(0x30,4),(0x3c,2),(0x40,2),(0x44,2)):
                def sound_effect(e,call,slot=slot):
                    record(0x5000+slot)(e,call)
                    if slot==0x24: e.put(call.arguments[1],0)
                    return 0
                env.put(methods+slot,env.stub('sound method '+hex(slot),'stdcall',argc,sound_effect))
        for off in (0x3a0,0x400,0x404): env.put(crab+off,sound if v.get('sound',False) else 0)
        env.put(0x532c0c,v.get('audio',0)); env.put(0x532c10,71)
        env.put(0x538418,1); env.put(0x52a190,1)
        env.override(0x4a3050,lambda e,c:v.get('rand',0)&0xffffffff)
        def intersect(e,call):
            dest,a,b=call.arguments
            a=struct.unpack('<4i',e.read(a,16)); b=struct.unpack('<4i',e.read(b,16))
            rect=(max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3]))
            ok=rect[0]<rect[2] and rect[1]<rect[3]
            e.write(dest,struct.pack('<4i',*(rect if ok else (0,0,0,0))))
            return int(ok)
        # The scene's real name map and object factory construct the bomb.
        world=new(0x28,'world'); world_owner=new(0x28,'world owner')
        manager=new(0x30,'object manager'); registry=new(0x30,'object registry')
        definition=new(0x14,'bomb definition'); entry=new(0x10,'bomb map entry')
        bucket=new(4,'bomb map bucket',words=[entry])
        key=new(9,'bomb key',data=b'CrabBomb\0')
        free_node=new(0xc,'object list free node')
        ballistic=new(0x200,'bomb ballistic state')
        env.put(crab+0x130,world); env.put(world+0xc,world_owner)
        env.put(world_owner+8,manager); env.put(manager+0xc,world_owner)
        env.put(world_owner+0x14,registry); env.put(world_owner+0x24,scene)
        env.put(registry+0x14,bucket,1)
        env.put(entry+8,key,definition)
        env.put(manager+0x20,free_node)
        if v.get('real_damage',False):
            goodie_key=new(15,'goodie key',data=b'BouncingGoodie\0')
            goodie_entry=new(0x10,'goodie map entry')
            env.put(entry,goodie_entry); env.put(goodie_entry+8,goodie_key,definition)
            env.put(actor+0xc,world_owner)
            resource=new(0x6c,'damage animation resource')
            image=new(4,'damage frame pointers')
            env.put(resource+0x14,image)
            env.put(0x52a190,2); env.put(0x537ec8+4,resource)
            env.put(0x53721c,0)
        for off,number in ((0x38,1.),(0x48,3.),(0x68,12.),(0x70,23.),(0x78,34.)):
            env.write(ballistic+off,struct.pack('<d',number))
        def initialize_bomb(e,call):
            record(0xb04b)(e,call)
            bomb=call.arguments[0]
            logic=e.get(bomb+0x6c)
            e.put(logic+0x18,ballistic)
            return 0x4321
        env.put(definition+0x10,env.stub('bomb initializer','cdecl',1,initialize_bomb))
        env.override(0x546ce0,intersect)
        return crab
    return setup

def cases(random_source):
    def case(entry,label,argument=None,**values):
        return Case(label,entry,setup_case(values),receiver=lambda t:t,arguments=() if argument is None else (argument,))
    for entry in (0x44b130,0x44b2b0,0x44b780,0x44bc50): yield case(entry,'direct '+hex(entry))
    for launch,start,duration,clock in ((0,900,200,1000),(1,900,101,1000),(1,900,100,1000),(1,0xfffffff0,31,15),(1,0,0xffffffff,0x80000000)):
        yield case(0x44b130,'launch timer',launch=launch,launch_start=start,launch_duration=duration,clock=clock)
    for mode in (-1,0,1,2,3,4,5,0x7fffffff):
        for overlap in (False,True): yield case(0x44b200,'attack choice',mode=mode,intersect=overlap)
    for aid in (203,204,205):
        for completed,active in ((0,0),(0,1),(1,0),(1,1)):
            for face in (0,2): yield case(0x44b300,'strike rectangle',animation_id=aid,completed=completed,active=active,facing=face)
    for entry in (0x44b300,0x44b6a0,0x44b9e0):
        for duration in (99,100,101,0xffffffff):
            for sound,audio in ((False,1),(True,0),(True,1)): yield case(entry,'sound timer',duration=duration,sound=sound,audio=audio,animation_id=203 if entry==0x44b300 else 801)
    for direction in (2,3,7):
        for ground in (0,1,2,3,4):
            for upper in (0,1):
                for facing in (0,2): yield case(0x44b480,'terrain and turn',317,direction=direction,ground=ground,upper_tile=upper,facing=facing)
    for direction in (2,3):
        for bound in (-1000.,60.,140.,1000.,float('nan')):
            for number in (0,40,-40,0x7fffffff,0x80000000): yield case(0x44b480,'move numeric boundary',0x80000000,direction=direction,lower=bound,upper=bound,rand=number)
    for argument in (0,1,2,0xffffffff):
        for bound in (-1000.,80.,120.,1000.,float('nan')):
            for number in (0,20,-20,0x7fffffff,0x80000000): yield case(0x44b860,'nudge numeric boundary',argument,lower=bound,upper=bound,rand=number)
    for entry in (0x44b6a0,0x44b960):
        for velocity in (-1.,0.,1.,float('nan')):
            for position in (99.,100.,101.,float('nan')): yield case(entry,'motion stop',velocity=velocity,position=position,previous=100)
        yield case(entry,'collision stop',velocity=1.,position=99.,collision_flags=0x10000)
    for mode in (0,1,8,0xffffffff): yield case(0x44b7e0,'fall landing',actor_mode=mode)
    for dead in (False,True):
        for repeated in (False,True):
            for kind in (0x1000000,0x2000000,0x20):
                for aid in (800,801,802,803): yield case(0x44b9e0,'contact response',dead=dead,repeated=repeated,kind=kind,animation_id=aid,hit_x=99)
    for damage in (-1,0,1,0x7fffffff): yield case(0x44b9e0,'contact damage',animation_id=803,damage=damage)
    for aid in (201,202):
        for completed,active in ((0,0),(0,1),(1,0),(1,1)): yield case(0x44bb40,'launch inactive',animation_id=aid,completed=completed,active=active,pending=0)
    for direction in (2,3):
        for completed,active in ((0,0),(0,1),(1,1)):
            for sound,audio in ((False,1),(True,0),(True,1)):
                yield case(0x44bb40,'real bomb launch',animation_id=201,completed=completed,active=active,pending=1,direction=direction,sound=sound,audio=audio)
    for direction in (2,3):
        for ground in (1,2,3):
            yield case(0x44b480,'tile callback changes reloaded fields',419,direction=direction,ground=ground,mutate_tile=True)
    for mode in (0,1,9,0xffffffff):
        yield case(0x44b780,'falling publishes mode eight',actor_mode=mode)
    for velocity in (-23.512345,0.123456789,1.23456789e200):
        for launch in (0,1):
            yield case(0x44b130,'clear distinct velocity words',velocity=velocity,launch=launch)
    for entry in (0x44b300,0x44b6a0,0x44b9e0,0x44bb40):
        yield case(entry,'sound reaches live physical callbacks',animation_id=201 if entry==0x44bb40 else (801 if entry==0x44b9e0 else 203),pending=1,duration=99,sound=True,audio=1,active_sound=True)
    for facing in (0,2):
        yield case(0x44b480,'shared rectangle and facing backing',431,direction=2,alias_animation=True,facing=facing)
    yield case(0x44b9e0,'positive damage constructs actual goodie',animation_id=803,damage=1,real_damage=True)
    for _ in range(20): yield case(0x44b960,'random motion',velocity=random_source.uniform(-400,400),position=random_source.uniform(-1000,1000),target=random_source.randrange(-500,500),previous=random_source.randrange(-500,500))
