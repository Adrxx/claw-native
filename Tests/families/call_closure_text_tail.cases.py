"""Original-backed font measurements and clipped 16-bit mask drawing."""
from clawparity.cases import Case

INC, DEC, INTERSECT = 0x5469ec, 0x5469e8, 0x546ce0

def signed(n):
    return n if n < 0x80000000 else n-0x100000000

def setup_text(text=b'\x01\x02\x03', null_font=False, widths=(3,4,2,5), heights=(2,4,3,5),
               color=0x9462d7, shifts=(11,5,3,2,3), lock_null=False, pitch=48,
               color_after=None, refs=4, count=4, observe_stack=False, observe_measure=False, observe_extra_word=True, masks=(0,255,1,127,254,63)):
    def setup(env):
        painter=env.object(16,'painter',fill=0x9b)
        font=env.object(32,'font',fill=0x73)
        table=env.object(1024,'glyph pointers',fill=0)
        extent=env.object(2048,'glyph extents',fill=0)
        stride=max(1,max(widths))*16
        maskbase=env.object(stride*256,'glyph masks',data=bytes(masks[(i+j)%len(masks)] for j in range(256) for i in range(stride)))
        for ch in range(256):
            w=widths[ch%len(widths)];h=heights[ch%len(heights)]
            mask=maskbase+ch*stride
            env.put(table+ch*4,mask)
            env.put(extent+ch*8,w,h)
        env.put(font,0xaabbccdd,count,table,extent)
        env.put(painter,0 if null_font else font,color)
        textbase=env.object(12+len(text)+1,'cstring',fill=0)
        env.put(textbase,refs,len(text),len(text)+1)
        env.write(textbase+12,text+b'\0')
        out=env.object(16,'extent result',fill=0xbd)
        pixels=env.object(4096,'surface pixels',data=bytes((i*73+29)&255 for i in range(4096)))
        surface=env.object(188,'surface',fill=0)
        com=env.object(4,'COM');vt=env.object(132,'COM methods',fill=0)
        env.put(surface+8,com)
        env.put(surface+0x14,16,20,pitch)
        env.put(surface+0x30,0 if lock_null else pixels)
        env.put(com,vt)
        events=env.object(128,'physical observations',fill=0)
        def lock(e,c):
            e.put(events,c.arguments[0],c.arguments[1],c.arguments[2],c.arguments[3],c.arguments[4])
            e.put(surface+0x30,0 if lock_null else pixels)
            e.put(surface+0x1c,pitch)
            if color_after is not None:e.put(painter+4,color_after)
            return 0
        def unlock(e,c):
            e.put(events+24,c.arguments[0],c.arguments[1],e.get(painter+4))
            if observe_stack:
                entry=e.get(events+40)
                e.write(events+64,e.read(entry-0x8c,8))
                e.write(events+112,e.read(entry+12,16))
            return 0x87654321
        env.put(vt+0x64,env.stub('Lock','stdcall',5,lock))
        env.put(vt+0x80,env.stub('Unlock','stdcall',2,unlock))
        def inc(e,c):
            v=(e.get(c.arguments[0])+1)&0xffffffff;e.put(c.arguments[0],v);return v
        def dec(e,c):
            if observe_measure:e.write(events+64,e.read(0x2008000-0x24,24))
            v=(e.get(c.arguments[0])-1)&0xffffffff;e.put(c.arguments[0],v);return v
        def intersect(e,c):
            dst,a,b=c.arguments
            if observe_stack:
                entry=a-12
                e.put(events+40,entry)
                if observe_extra_word:e.put(events+48,e.get(entry+40))
                e.write(events+80,e.read(b,16))
                e.write(events+96,e.read(a,16))
            aa=[signed(e.get(a+i*4)) for i in range(4)]
            bb=[signed(e.get(b+i*4)) for i in range(4)]
            r=[max(aa[0],bb[0]),max(aa[1],bb[1]),min(aa[2],bb[2]),min(aa[3],bb[3])]
            ok=r[0]<r[2] and r[1]<r[3]
            e.put(dst,*(r if ok else [0,0,0,0]))
            return int(ok)
        env.override(INC,inc);env.override(DEC,dec);env.override(INTERSECT,intersect)
        for addr,value in zip((0x54135c,0x541360,0x541368,0x54136c,0x541370),shifts):env.put(addr,value)
        return dict(painter=painter,font=font,table=table,extent=extent,text=textbase+12,out=out,surface=surface,pixels=pixels)
    return setup

def t(k):return lambda x:x[k]

def cases(random_source):
    for i in range(12):
        value=random_source.getrandbits(32)
        for function,arg in ((0x4df6c0,()),(0x4df6d0,(value,)),(0x4df6e0,(value,))):
            yield Case(f'initialize-set {function:x} {i}',function,setup_text(),receiver=t('painter'),arguments=arg)
    for char in (0,1,2,3,127,128,255,256,257,0x1234ff,0xffffffff):
        yield Case(f'glyph slot {char:x}',0x4dfee0,setup_text(),receiver=t('font'),arguments=(char,))
        yield Case(f'glyph extent {char:x}',0x4dff00,setup_text(),receiver=t('font'),arguments=(t('out'),char))
    for count in (-1,0,1,2,4,8):
        for heights in ((-9,-1,-2,-3),(0,0,0,0),(3,9,9,2),(9,3,2,1)):
            yield Case(f'max height {count} {heights}',0x4dff30,setup_text(count=count,heights=heights),receiver=t('font'))
    for text in (b'',b'\x01',b'\x01\x02\x03',b'\xff\x80\x00\x7f',b'\x03\x02\x01\x01'):
        for null in (False,True):
            for heights in ((3,3,3,3),(5,1,9,2),(-3,-4,-5,-6)):
                yield Case(f'measure {text!r} {null} {heights}',0x4dfde0,setup_text(text=text,null_font=null,heights=heights),receiver=t('painter'),arguments=(t('out'),t('text')))
    for refs in (1,2,5):
        yield Case(f'measure reference lifetime {refs}',0x4dfde0,setup_text(refs=refs),receiver=t('painter'),arguments=(t('out'),t('text')))
    for null in (False,True):
        for y in (0,11,12,16,17):
            for aa in (0,1):
                yield Case(f'draw whole {null} y{y} aa{aa}',0x4df6f0,setup_text(null_font=null),receiver=t('painter'),arguments=(t('text'),t('surface'),2,y,aa))
    rects=((0,0,11,5),(0,0,99,99),(1,0,8,4),(4,1,9,3),(0,1,2,3),(5,0,11,4),
           (11,0,15,5),(0,5,11,8),(-3,-3,8,4),(0,0,0,0),(0,0,1,1),(3,0,4,2),
           (0,0,10,5),(2,0,7,4))
    for i,rect in enumerate(rects):
        for aa in (0,1):
            for mode in range(3):
                color=random_source.getrandbits(32)
                shifts=((11,5,3,2,3),(10,5,3,3,3),(8,4,4,4,4))[mode]
                yield Case(f'clipped {i} aa{aa} mode{mode}',0x4df7d0,setup_text(color=color,shifts=shifts),receiver=t('painter'),arguments=(t('text'),t('surface'),*rect,2,1,aa))
    for text in (b'',b'\x01',b'\x03\x02\x01',b'\xff\x7f'):
        for aa in (0,1):
            for lock_null in (False,True):
                yield Case(f'clipped text {text!r} aa{aa} null{lock_null}',0x4df7d0,setup_text(text=text,lock_null=lock_null),receiver=t('painter'),arguments=(t('text'),t('surface'),0,0,99,99,1,1,aa))
    for aa in (0,1):
        yield Case(f'null font clipped {aa}',0x4df7d0,setup_text(null_font=True),receiver=t('painter'),arguments=(t('text'),t('surface'),0,0,99,99,1,1,aa))
        yield Case(f'lock changes color {aa}',0x4df7d0,setup_text(color_after=0x1234ef),receiver=t('painter'),arguments=(t('text'),t('surface'),0,0,99,99,1,1,aa))

    for widths in ((0,4,0,5),(1,0,2,3)):
        for aa in (0,1):
            yield Case(f'zero-width interior glyph {widths} aa{aa}',0x4df7d0,setup_text(widths=widths),receiver=t('painter'),arguments=(t('text'),t('surface'),0,0,99,99,1,1,aa))

    for text,widths,heights in ((b'\x01\x02\x03',(3,4,2,5),(2,7,3,5)),
                                (b'\x03\x01\x02',(2,3,5,4),(6,2,4,8))):
        for left,right in ((0,99),(4,99),(0,4),(4,6),(6,11),(3,4),(4,9)):
            for aa in (0,1):
                noise=bytes(random_source.randrange(1,256) for _ in range(2048))
                yield Case(f'observed stack and exact glyph boundary {text!r} {left}:{right} aa{aa}',
                    0x4df7d0,setup_text(text=text,widths=widths,heights=heights,observe_stack=True),
                    receiver=t('painter'),arguments=(t('text'),t('surface'),left,0,right,99,2,1,aa),
                    initial_stack=((-2048,noise),))

    for text in (b'\x01\x02',b'\x03\x02\x01'):
        noise=bytes(random_source.randrange(1,256) for _ in range(2048))
        yield Case(f'measure equality scratch witness {text!r}',0x4dfde0,
            setup_text(text=text,heights=(3,3,3,3),observe_measure=True),receiver=t('painter'),
            arguments=(t('out'),t('text')),initial_stack=((-2048,noise),))
    for aa in (0,1):
        noise=bytes(random_source.randrange(1,256) for _ in range(2048))
        # Child+40 is parent-0x30, the incoming EDI saved at original4df70a.
        # Ordinary ABI cases do not elect that register as an observable input.
        yield Case(f'whole-text child frame witness aa{aa}',0x4df6f0,
            setup_text(heights=(3,3,3,3),observe_stack=True,observe_extra_word=False),receiver=t('painter'),
            arguments=(t('text'),t('surface'),2,1,aa),initial_stack=((-2048,noise),))
