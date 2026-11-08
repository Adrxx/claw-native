import interface_file_helpers as h

def menu(seed=0,name='CLAW.IFC'):
 length=h.fresh(seed,name);h.compare(0x4dcc40,h.MENU,[640,480],'constructor');h.compare(0x4dcdf0,h.MENU,[h.GRAPHICS,h.DATA,length,0x710000,0,0,0],name)

def tree(node):
 yield node
 for i in range(h.get(node+32)):yield from tree(h.get(h.get(node+28)+4*i))

menu()
nodes=list(tree(h.MENU+72));assert len(nodes)==133
assert len(h.nativeNames)==1064 and h.nativeNames==h.sourceNames
h.compare(0x4dd0c0,h.MENU,[],'current page')
for node in nodes:
 h.compare(0x4df480,node,[],'children')
 h.compare(0x4df200,h.MENU+72,[h.get(node+80)],'find ID')
 if not h.get(node+32):continue
 h.compare(0x4dcf10,h.MENU,[node,1],'show centered',void=True)
 for index in range(h.get(h.MENU+16)):
  h.compare(0x4dcf10,h.MENU,[node,1],"restore page",void=True)
  h.put(h.MENU+36,[0])
  h.compare(0x4dd490,h.MENU,[index],'select',void=True)
  widget=h.get(h.get(h.MENU+12)+4*index)
  h.compare(0x4dd520,h.MENU,[widget],'select pointer',void=True)
  h.compare(0x4ded40,widget,[h.SCRATCH+16],'rectangle')
  h.compare(0x4dda50,h.MENU,[],'previous',void=True)
  h.compare(0x4ddb40,h.MENU,[],'next',void=True)
  h.compare(0x4ddac0,h.MENU,[],'timed previous',void=True)
  h.now=1000;h.compare(0x4ddbc0,h.MENU,[],'press',void=True)
  h.now=1300;h.compare(0x4ddce0,h.MENU,[],'strict300',void=True);assert h.get(h.MENU+36)==1
  h.now=1301;h.compare(0x4ddce0,h.MENU,[],'release301',void=True);assert h.get(h.MENU+36)==0,(hex(node),index,h.get(h.MENU+28),h.get(h.MENU+44),h.get(h.MENU+36),h.get(h.get(h.get(h.MENU+12)+4*h.get(h.MENU+28))+104))
  h.now=1701;h.compare(0x4ddce0,h.MENU,[],'strict400',void=True)
  h.now=1702;h.compare(0x4ddce0,h.MENU,[],'blink401',void=True)
  h.compare(0x4dd270,h.MENU,[h.IMAGE],'draw widgets',void=True)
 h.put(h.MENU+32,[1]);h.compare(0x4ddb40,h.MENU,[],'skip disabled next',void=True);h.compare(0x4dda50,h.MENU,[],'skip disabled previous',void=True)
 h.put(h.MENU+32,[0])
h.compare(0x4dce90,h.MENU,[],'depart',void=True);h.compare(0x4dce90,h.MENU,[],'repeat depart',void=True);h.compare(0x4dccb0,h.MENU,[],'destruction',void=True)
print('PASS',h.calls,h.snapshots)

menu(1,'CLAWWITHLOBBY.IFC');assert len(list(tree(h.MENU+72)))==138;print('LOBBY nodes',len(list(tree(h.MENU+72))))
h.compare(0x4dccb0,h.MENU,[],'lobby destruction',void=True)
menu(2)
nodes=list(tree(h.MENU+72))
for node in nodes:
 h.compare(0x4dd020,h.MENU,[h.get(node+80)],'find wrapper')
 # Direct copy-constructor profile: retained output refs are compared, rather
 # than asserting that construction releases an older output value.
 h.compare(0x4df460,node,[h.SCRATCH+16],'copy description')
 h.compare(0x4dceb0,h.MENU,[h.get(node+80),0],'disable choice',void=True)
 h.compare(0x4dceb0,h.MENU,[h.get(node+80),1],'enable choice',void=True)
 if not h.get(node+32):continue
 h.compare(0x4dcf10,h.MENU,[node,1],'page',void=True)
 for axis in(0,1,2):
  for first,last in((0,640),(480,0),(-30,-900),(0x7fffffff,0x80000000)):
   h.compare(0x4dd800,h.MENU,[axis,first&0xffffffff,last&0xffffffff],'distribution',void=True)
 h.compare(0x4dd030,h.MENU,[],'back parent page',void=True)
h.compare(0x4df270,h.MENU+72,[17],'actual recursive argument alias',void=True)
h.compare(0x4dd0d0,h.MENU,[300],'restore recursive interval',void=True)
h.compare(0x4dccb0,h.MENU,[],'destroy second menu',void=True)
print('PASS extended',h.calls,h.snapshots)

menu(3);h.capture=True
h.compare(0x4dcf00,h.MENU,[],'root show',void=True)
for index in range(h.get(h.MENU+16)):
 h.compare(0x4dd490,h.MENU,[index],'mouse prepare',void=True);w=h.get(h.get(h.MENU+12)+4*index);h.compare(0x4ded40,w,[h.SCRATCH+16],'mouse rect');rect=[h.get(h.SCRATCH+16+4*i)for i in range(4)];h.cursorPoint=(rect[0]+1,rect[1]+1);h.put(h.MENU+36,[0]);h.now+=500;h.compare(0x4ddc30,h.MENU,[],'source mouse press',void=True)
 h.now+=301;h.compare(0x4ddce0,h.MENU,[],'mouse timed activation',void=True);h.compare(0x4dcf00,h.MENU,[],'root again',void=True)
h.cursorPoint=(-9999,-9999);h.compare(0x4ddc30,h.MENU,[],'mouse miss',void=True)
h.put(h.MENU+36,[0]);h.put(h.MENU+32,[1]);h.compare(0x4dceb0,h.MENU,[10001,0],'source disabled',void=True);h.cursorPoint=(305,100);h.compare(0x4ddc30,h.MENU,[],'disabled mouse',void=True)
h.now=0xfffffffe;h.compare(0x4ddbc0,h.MENU,[],'wrap press',void=True);h.now=299;h.compare(0x4ddce0,h.MENU,[],'wrap elapsed301',void=True)
for node in list(tree(h.MENU+72))[:10]:
 w=node+60
 for index in(-1,0,7,8):h.compare(0x4de4d0,w,[h.IMAGE,index&0xffffffff],'image replacement',void=True)
 h.compare(0x4ded20,w,[h.SCRATCH+16],'get position',void=True)
h.compare(0x4dd270,h.MENU,[0],'null draw',void=True)
h.compare(0x4dccb0,h.MENU,[],'captured destructor',void=True);h.capture=False

# Synthetic archives are produced with the original encoding observed above;
# the oracle still executes its own byte/CString/CArchive/tree bodies.
import struct,random

def encoded(s):return (bytes([len(s)])if len(s)<255 else b'\xff'+struct.pack('<H',len(s))if len(s)<65534 else b'\xff\xff\xff'+struct.pack('<I',len(s)))+s

def nodebytes(name=b'node',images=None,children=(),count=None):
 images=images or[b'1_main_a',b'',b'',b'2_main_a',b'',b'',b'',b'']
 return struct.pack('<I',17)+encoded(name)+b''.join(encoded(s)for s in images)+struct.pack('<Ih',10000,len(children)if count is None else count)+b''.join(struct.pack('<I',0)+x for x in children)

for seed in range(12):
 h.fresh(seed);data=nodebytes(bytes([65+seed])*((seed%4)*4096+seed),children=[nodebytes(b'child')for _ in range(seed%5)])
 token=h.BASE+0x300000;h.write(token,data);h.compare(0x4dcc40,h.MENU,[640,480],'synthetic ctor');h.compare(0x4dcdf0,h.MENU,[h.GRAPHICS,token,len(data),0x710000,0,0,0],'synthetic IFC');h.compare(0x4dccb0,h.MENU,[],'synthetic destruction',void=True)
for fail in(1,8,9,32):
 length=h.fresh(10+fail);h.compare(0x4dcc40,h.MENU,[640,480],'failed-image ctor');h.resolverFailAt=fail;h.compare(0x4dcdf0,h.MENU,[h.GRAPHICS,h.DATA,length,0x710000,0,0,0],'resolver null result');h.compare(0x4dccb0,h.MENU,[],'failed-image source cleanup',void=True)
for length in(0,1,3,4,10,500,4095,4096,14248):
 h.fresh(20);h.compare(0x4dcc40,h.MENU,[640,480],'EOF ctor');h.compare(0x4dcdf0,h.MENU,[h.GRAPHICS,h.DATA,length,0x710000,0,0,0],f'EOF span {length}',unsafe=True)
for fail in(1,2,3,4,5):
 length=h.fresh(21);h.compare(0x4dcc40,h.MENU,[640,480],'alloc-failure ctor');h.allocFailure=h.allocIndex+fail;h.compare(0x4dcdf0,h.MENU,[h.GRAPHICS,h.DATA,length,0x710000,0,0,0],f'allocator null {fail}',unsafe=fail!=5)
print('PASS FINAL',h.calls,h.snapshots,'instrumented',len(h.m.executed),'text',len([a for a in h.m.executed if 0x401000<=a<0x50adb6]))
length=h.fresh();h.compare(0x4dcc40,h.MENU,[640,480],'callerzero ctor');h.compare(0x4dcdf0,h.MENU,[h.GRAPHICS,h.DATA,length,0x710000,0,0,0],'callerzero menu');h.compare(0x4dd0d0,h.MENU,[0],'actual StateFive zero interval',void=True)
h.now=1000;h.compare(0x4ddbc0,h.MENU,[],'callerzero press',void=True);assert h.get(h.MENU+36)==1
h.compare(0x4ddce0,h.MENU,[],'callerzero same tick',void=True);assert h.get(h.MENU+36)==1
h.now=1001;h.compare(0x4ddce0,h.MENU,[],'callerzero next tick',void=True);assert h.get(h.MENU+36)==0
h.compare(0x4dccb0,h.MENU,[],'callerzero cleanup',void=True)
print('VERIFIED',h.calls,h.snapshots,'instrumented',len(h.m.executed),'text',len([a for a in h.m.executed if 0x401000<=a<0x50adb6]),flush=True)

rng=random.Random(0x4de4d0)
for seed in range(64):
 h.fresh(seed);node=h.BASE+0xa000;h.compare(0x4def70,node,[],'seeded node ctor');component=node+60
 array=h.BASE+0xb000;h.put(component+4,[array,8,8,0]);h.put(component+72,[h.GRAPHICS]);h.put(component+60,[0]);h.put(component+64,[h.IMAGE]);new=h.IMAGE+400;h.put(new+20,[rng.choice([1,0,-19,77,0x7fffffff])&0xffffffff,rng.choice([1,0,-3,50,0x80000000])&0xffffffff]);h.put(array,[h.IMAGE]*8)
 for index in(-1,0,3,7,8):
  h.compare(0x4de4d0,component,[new,index&0xffffffff],'distinct alias replacement',void=True)
  h.compare(0x4dec60,component,[rng.getrandbits(8)],'all flags selection',void=True)
  h.compare(0x4ded00,component,[rng.getrandbits(32),rng.getrandbits(32)],'wrapped position',void=True)
  h.compare(0x4ded40,component,[h.SCRATCH+16],'signed current-image rectangle')
  h.compare(0x4de790,component,[h.IMAGE],'source centered draw',void=True)
print('VERIFIED ALL',h.calls,h.snapshots,'instrumented',len(h.m.executed),'text',len([a for a in h.m.executed if 0x401000<=a<0x50adb6]),flush=True)

for seed in range(16):
 h.fresh(seed);component=h.BASE+0xa000;h.compare(0x4dde80,component,[],'component ctor');array=h.BASE+0xb000;mask=h.BASE+0xc000;h.put(component+4,[array,8,8,0]);h.put(component+56,[mask,1]);h.put(component+72,[h.GRAPHICS]);h.put(array,[h.IMAGE]*8);h.compare(0x4de450,component,[],'owned whole clear',void=True)
 releases=[event for event in h.events if event[0]==0x4bc4f0];assert len(releases)==1;h.compare(0x4ddf70,component,[],'component dtor after clear',void=True)
print('VERIFIED COMPLETE',h.calls,h.snapshots,'instrumented',len(h.m.executed),'text',len([a for a in h.m.executed if 0x401000<=a<0x50adb6]),flush=True)
