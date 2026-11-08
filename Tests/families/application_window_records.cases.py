"""Independent original cases for complete window-owner records and count aliasing."""
from clawparity.cases import Case

COUNTER=0x541340

def setup(count,fill,offset=0,alias=None):
    def build(env):
        if alias is None:
            backing=env.object(0x284,'complete window owner and canaries',fill=fill)
            receiver=backing+0x10+offset
        else:
            receiver=(COUNTER+alias)&0xffffffff
            env.write(receiver-16,bytes([fill])*0x274)
        env.put(COUNTER,count)
        return receiver
    return build

def cases(random_source):
    for f in (0x423300,0x4b8990):
        for count in (0,1,2,0x7fffffff,0x80000000,0xfffffffe,0xffffffff):
            for offset in (0,1,2,3):
                fill=random_source.randrange(1,256)
                yield Case(f'full record count{count:08x} alignment{offset}',f,setup(count,fill,offset),receiver=lambda t:t)
        for alias in (0,-4,-8,-12,-16,-0x240,-0x248,-0x24c,-0x250):
            yield Case(f'counter aliases store{alias}',f,setup(0x10203040,0xa6,alias=alias),receiver=lambda t:t)
        for i in range(12):
            count=random_source.getrandbits(32);fill=random_source.randrange(1,256)
            yield Case(f'random complete window owner{i}',f,setup(count,fill,random_source.randrange(4)),receiver=lambda t:t)
