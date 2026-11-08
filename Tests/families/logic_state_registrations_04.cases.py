"""Original registry inputs: real trie traversal, CString assignment and signed arrays."""
from clawparity.cases import Case

ENTRIES = (0x446780, 0x448970, 0x448f50, 0x4496a0, 0x449e70, 0x44c950,
           0x4544f0, 0x455720, 0x455c20, 0x456400, 0x456d30)
CLASSES = {0x446780:(0x527898,0x5278a0),0x4496a0:(0x527898,0x527b24),
           0x449e70:(0x52670c,0x527b98),0x44c950:(0x52670c,0x523a5c),
           0x4544f0:(0x523274,0x528460),0x456d30:(0x523714,0x528608)}
TABLES = (0x537788,0x5377b8,0x5377e8,0x537818,0x537848,0x537878,
          0x537980,0x5379d0,0x537a00,0x537a30,0x537a60,
          0x534bf8,0x534910,0x5349b8,0x537638,0x538428)
NAMES = ('LS_HOME LS_ROTATE LS_IDLE ES_IDLE ES_ERUPTING ES_THROWING LS_EXPLODING '
         'LS_FALLING LS_JUMP LS_FLIP3 ES_HOME ES_HIDE ES_DEFENSE ES_ATTACK '
         'ES_MOVINGATTACK ES_STRIKE ES_FALLING ES_NUDGE ES_LAUNCH LS_BOUNCE '
         'LS_THROWN LS_JUMPATCLAW LS_JUMPBACK LS_ADVANCE LS_FASTADVANCE LS_PACING '
         'LS_HITLOW LS_HITHIGH LS_JUMPOFFSPRINGBOARD LS_FIRING LS_VERTFIRING '
         'LS_DEAD LS_MOVINGLEFT LS_MOVINGRIGHT LS_LIFTED LS_PAUSE LS_DROPPED '
         'LS_MOVEBACK LS_MOVEAHEAD LS_BLOCKHIGH LS_BLOCKLOW LS_FLAILING LS_STARTUP').split()
EMPTY = 0x52e1c4


def setup_case(entry, seed, hits=False, inherited=False, grow=None, fail=False,
               negative=False, class_text=None, original=False, occupied=False, counter_changes=False):
    def setup(env):
        env.put(0x52e1cc, EMPTY)
        env.put(EMPTY-12, 0xffffffff, 0, 0, 0)
        env.put(0x52f2b0, 0x52f2b0)
        env.put(0x540fe8, 0)
        env.put(0x544d18, 0)
        error = env.object(24, 'quiet-error-handler', words=[0,seed,0,4,0,0])
        env.put(0x52712c, 2000 if original else 7)
        env.put(0x537668, 1,error,0,0,0,0,0,0,0,0,0)
        # Each array has separate live storage and a separate observable fallback.
        for ordinal, table in enumerate((0x537698,)+TABLES):
            stride = 4 if table == 0x537698 else 4 + 4*(ordinal % 3)
            low, high = (-64,64) if negative else (1,96)
            if grow == 'above': low,high = 1,3
            if grow == 'below': low,high = 48,64
            if original: low,high = 2000,1999
            count = high-low+1
            data = env.object(max(1,count*stride), f'array-{table:x}')
            for i in range(count):
                for j in range(stride//4):
                    value = EMPTY if table == 0x537698 else (seed+ordinal*0x10403+i*0x101+j*0x1000001)&0xffffffff
                    if occupied and table == 0x537698:
                        text = bytes(((seed+i+k)%26+65 for k in range(5)))
                        header=env.object(45, f'old-name-{i}', words=[1,5,32])
                        env.write(header+12,text+b'\0'+bytes(27))
                        value=header+12
                    env.put(data+i*stride+j*4,value)
            fallback = env.object(16, f'fallback-{table:x}', words=[EMPTY if table==0x537698 else seed^table,seed,seed^0x12345678,seed^0x87654321])
            env.put(table, 1,error,low,high,data,fallback,stride,data,0xabc00000+ordinal)
        if not inherited and entry in CLASSES:
            parent,child = CLASSES[entry]
            env.write(child,env.cstr(parent)+b'\0')
        if class_text is not None:
            parent,child=CLASSES[entry]
            env.write(parent,class_text[0]+b'\0')
            env.write(child,class_text[1]+b'\0')
        if hits:
            # A compressed binary radix tree. Terminal records have bit 0,
            # so traversal stops on their back edge and compares the real key.
            items=[]
            for i,name in enumerate(NAMES):
                key=name.encode()+b'\0'
                string=env.object(len(key),'existing-key',data=key)
                leaf=env.object(20,'trie-terminal',words=[0,0,0,string,(-i-2 if negative else i+7)&0xffffffff])
                items.append((key,leaf))
            def tree(group,bit=0):
                if len(group)==1:return group[0][1]
                while True:
                    groups=[[],[]]
                    for key,leaf in group:
                        value=(key[bit//8]>>(bit%8))&1 if bit//8<len(key) else 0
                        groups[value].append((key,leaf))
                    if groups[0] and groups[1]:break
                    bit+=1
                left=tree(groups[0],bit+1); right=tree(groups[1],bit+1)
                return env.object(20,'trie-branch',words=[left,right,bit,group[0][1],0])
            env.put(0x537668+0x18,tree(items))
            env.put(0x537668+0x14,len(items))
        env.override(0x5469e4, lambda env,call: len(env.cstr(call.arguments[0])))
        def heap_alloc(env,call):
            return env.object(call.arguments[2], 'crt-heap-allocation')
        env.override(0x546960,heap_alloc)
        if counter_changes:
            def allocate_and_change_counter(env,call):
                allocation=env.object(call.arguments[0], 'new-with-counter-change')
                if env.calls_so_far(0x4f63ec)==1:
                    env.put(0x52712c,env.get(0x52712c)+5)
                return allocation
            env.override(0x4f63ec,allocate_and_change_counter)
        def realloc(env,call):
            old,size=call.arguments[2:4]
            if fail:return 0
            # CRT realloc is called only for an array owned by this setup.
            old_size=0
            for table in (0x537698,)+TABLES:
                if env.get(table+0x10)==old:
                    old_size=(env.get(table+0xc)-env.get(table+8)+1)*env.get(table+0x18)
                    break
            new=env.object(size,'grown-array')
            if old_size:env.write(new,env.read(old,min(old_size,size)))
            env.release(old)
            return new
        env.override(0x546928,realloc)
    return setup


def cases(random_source):
    for entry in ENTRIES:
        for inherited in (False,True):
            for hits in (False,True):
                seed=random_source.getrandbits(32)|1
                yield Case(f'{entry:x} inherited={inherited} hits={hits}',entry,
                           setup_case(entry,seed,hits,inherited))
        for growth in ('above','below'):
            for hits in (False,True):
                for fail in (False,):
                    seed=random_source.getrandbits(32)|1
                    yield Case(f'{entry:x} {growth} hits={hits} failure={fail}',entry,
                               setup_case(entry,seed,hits,grow=growth,fail=fail))
        yield Case(f'{entry:x} signed negative existing IDs',entry,
                   setup_case(entry,random_source.getrandbits(32)|1,hits=True,negative=True))
        yield Case(f'{entry:x} original bootstrap empty range',entry,
                   setup_case(entry,random_source.getrandbits(32)|1,original=True))
        yield Case(f'{entry:x} counter changes during dictionary allocation',entry,
                   setup_case(entry,random_source.getrandbits(32)|1,counter_changes=True))
        yield Case(f'{entry:x} distinct existing CString contents',entry,
                   setup_case(entry,random_source.getrandbits(32)|1,occupied=True))
        if entry in CLASSES:
            for left,right in ((b'',b''),(b'Ab',b'Ab'),(b'A',b'A'),(b'\x80Q',b'\x7fQ'),(b'Ax',b'Ay')):
                yield Case(f'{entry:x} compare {left!r} {right!r}',entry,
                           setup_case(entry,random_source.getrandbits(32)|1,hits=True,class_text=(left,right)))
