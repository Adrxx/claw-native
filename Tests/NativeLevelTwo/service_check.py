"""Bounded controls for Level 2 physical-service adapters; no guest execution."""
from Tests.NativeLevels.storage import EventLog
import hashlib,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from Tests.NativeLevelTwo.trace import LevelTwoTrace,Blocked,end_trace
class Memory:
    def __init__(self):self.data=bytearray(0x5000)
    def mem_read(self,a,n):return self.data[a:a+n]
    def mem_write(self,a,b):self.data[a:a+len(b)]=b
    def reg_read(self,r):return 0x1000

def main():
    x=object.__new__(LevelTwoTrace);x.machine=Memory();x.com_methods={7:('IDirectDrawSurface','Blt')}
    x.phase='provider-control';x.milliseconds=0;x.physical_events=EventLog()
    x.imports={};x.startup_paper=False
    x.platform_call=lambda *a:None
    returns=[];x.returned=lambda *a:returns.append(a)
    x.com_objects={1:dict(kind='IDirectDrawSurface',references=1,lost=False,locked=False,width=3,height=2,pitch=3,pixels=0x2000),
     2:dict(kind='IDirectDrawSurface',references=1,lost=False,locked=False,width=3,height=2,pitch=3,pixels=0x2100,color_key=(0,0))}
    x.machine.mem_write(0x1000,struct.pack('<7I',0,1,0,2,0,0x8800,0x3000))
    x.machine.mem_write(0x2100,bytes(range(6)))
    for fx,expected in [(0,[9,1,2,3,4,5]),(2,[2,1,9,5,4,3]),(4,[3,4,5,9,1,2]),(6,[5,4,3,2,1,9])]:
     x.machine.mem_write(0x2000,b'\x09'*6);x.machine.mem_write(0x3000,struct.pack('<2I',100,fx))
     x.com_fixture(7);assert list(x.machine.mem_read(0x2000,6))==expected
     assert returns[-1]==(0,24)
    x.machine.mem_write(0x3004,struct.pack('<I',1))
    try:x.com_fixture(7)
    except Blocked:pass
    else:raise AssertionError('Unsupported effect accepted')
    x.machine.mem_write(0x3004,struct.pack('<I',2));x.com_objects[2]['lost']=True
    try:x.com_fixture(7)
    except Blocked:pass
    else:raise AssertionError('Lost surface accepted')
    # Byte comparisons include equality, prefix ordering and unsigned high bytes.
    word=x.word
    x.word=lambda a: 0 if a==0x540e00 else word(a)
    x.machine.mem_write(0x1000,struct.pack('<3I',0,0x2200,0x2300))
    for left,right,expected in [(b'abc',b'abc',0),(b'a',b'ab',-1),(b'ab',b'a',1),(b'\xff',b'\x7f',1),(b'',b'a',-1)]:
     x.machine.mem_write(0x2200,left+b'\0');x.machine.mem_write(0x2300,right+b'\0')
     x.fixture(0x4a3810);assert returns[-1]==(expected,)
    x.word=lambda a:1 if a==0x540e00 else word(a)
    try:x.fixture(0x4a3810)
    except Blocked:pass
    else:raise AssertionError('Unsupported code page accepted')
    r=dict(status='pass',controls=12,tracer_sha256=hashlib.sha256(Path('Tests/NativeLevelTwo/trace.py').read_bytes()).hexdigest())
    Path('work/level-two-map/service-check.json').write_text(json.dumps(r)+'\n');print(json.dumps(r))

if __name__=='__main__':
    main()
