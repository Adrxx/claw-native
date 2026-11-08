import sys,gzip,ctypes as C,struct,hashlib
sys.path.insert(0,'tests');import player_menu_management_helpers as h
pack=lambda *v:struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
corpus=[];replays=[];original=h.menuDependency

def raw():return bytes(h.heap)+bytes(h.image[h.GS-h.IS:h.GS-h.IS+h.GN])
def canonicalRaw():return h.canonical()+bytes(h.image[h.GS-h.IS:h.GS-h.IS+h.GN])
def patches(a,b):return [(i,y)for i,(x,y)in enumerate(zip(struct.unpack('<'+'I'*(len(a)//4),a),struct.unpack('<'+'I'*(len(b)//4),b)))if x!=y]
@h.MenuDependency
def capture(c,q,u):
 e=q.contents;before=raw();buffers=[C.string_at(e.buffers[i],e.sizes[i])for i in range(e.buffersCount)];digest=hashlib.sha256(canonicalRaw()).digest();v=original(c,q,u);replays.append((e.function,e.receiver,tuple(e.arguments[:e.count]),e.name or b'',e.mask,digest,v,patches(before,raw()),buffers,[C.string_at(e.buffers[i],e.sizes[i])for i in range(e.buffersCount)]));return v
h.menuDependency=capture

def run(f,t,args=(),meaningful=True):
 replays.clear();before=raw();allocations=[(token,size,int(h.live.get(token,False)))for token,size in h.allocationSpans.items()];v=h.compareMenu(f,t,args,'capture',meaningful);corpus.append((f,t,args,meaningful,v,before,canonicalRaw(),list(replays),allocations))
for flags in(0,4):
 h.prepare();h.put(h.RECORDS+4,[flags]);run(0x49b160,0,[h.DIALOG,0x110,0,0])
for f in(0x49b160,0x49b630):
 for command in(1,2):
  h.prepare();h.controlLists[h.CONTROL]=[b'Ada',b'Lin'];h.controlIndices[h.CONTROL]=0;run(f,0,[h.DIALOG,0x111,command,0])
for index in(0,1,2,7,14):
 for f,control in((0x49b3a0,h.CONTROL),(0x49b470,h.CONTROL2)):
  h.prepare();h.controlIndices[control]=index;run(f,0,[h.DIALOG,control],False)
for value in(0,59999,60000,3723000,36000000,360000000):
 h.prepare();run(0x49c860,0,[h.TIME_CELL,value])
for result in(0,1):
 h.prepare();h.transitionResult=result;run(0x426e30,h.APP,[0,0x8090,6])
h.prepare();run(0x49b630,0,[h.DIALOG,0x110,0,0]);h.controlIndices[h.CONTROL]=0;run(0x49b630,0,[h.DIALOG,0x111,2,0]);run(0x49b630,0,[h.DIALOG,0x111,1,0])
h.prepare();h.put(h.APP+100,[h.RECORDS+0x3000]);run(0x49b160,0,[h.DIALOG,0x110,0,0]);h.put(h.APP+100,[h.RECORDS+0x6000]);h.controlIndices[h.CONTROL]=2;run(0x49b160,0,[h.DIALOG,0x111,0x10000,h.CONTROL]);run(0x49b160,0,[h.DIALOG,0x111,2,0])
h.prepare(0);h.globalSeed=bytes(h.image[h.GS-h.IS:h.GS-h.IS+h.GN]);h.files={}
for name in(b'Player',b'Ada',b'Lin'):
 h.putBytes(h.DATA,name+b'\0');h.compare(0x49bdb0,h.M,[h.DATA,0,0,4 if name==b'Ada'else 0],'source-created-fixture')
h.compare(0x49bbc0,h.M,label='source-encrypted-fixture')
blob=h.files[b'CLAW.USR'];h.prepare(0);h.files={b'C:\\CLAW\\CLAW.USR':blob};h.globalSeed=bytes(h.image[h.GS-h.IS:h.GS-h.IS+h.GN]);h.compare(0x49b840,h.M,[0x525618],'source-retained-reader-fixture')
h.put(h.APP+100,[h.get(h.get(h.M+4)[0]+8)[0]]);run(0x49b630,0,[h.DIALOG,0x110,0,0]);h.controlIndices[h.CONTROL]=0;run(0x49b630,0,[h.DIALOG,0x111,2,0]);run(0x49b630,0,[h.DIALOG,0x111,1,0]);h.put(h.APP+100,[h.get(0x53ebe0)[0]]);run(0x49b160,0,[h.DIALOG,0x110,0,0]);run(0x49b160,0,[h.DIALOG,0x111,1,0])
with gzip.open(h.WORK/'sanitizer-replay.bin.gz','wb',compresslevel=1)as out:
 out.write(b'PMMG'+pack(h.IS,len(h.image),h.SIZE,len(corpus))+bytes(h.image))
 for f,t,a,meaningful,v,before,after,ee,allocations in corpus:
  out.write(pack(f,t,len(a),*list(a)+[0]*(5-len(a)),int(meaningful),v,len(ee),len(allocations))+before)
  for token,size,alive in allocations:out.write(pack(token,size,alive))
  for ef,et,ea,name,mask,digest,value,pp,buffers,outputs in ee:
   out.write(pack(ef,et,len(ea),*list(ea)+[0]*(40-len(ea)),mask,value,len(name),len(pp),len(buffers))+digest+name)
   for p in pp:out.write(pack(*p))
   for b,v in zip(buffers,outputs):out.write(pack(len(b))+b+v)
  out.write(after)
print('PASS capture',len(corpus),sum(len(v[7])for v in corpus))
