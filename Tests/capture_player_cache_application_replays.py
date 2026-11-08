import sys,gzip,ctypes as C,struct,hashlib
sys.path.insert(0,'Tests');import player_cache_application_helpers as h
h.pack=lambda *v:struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
corpus=[];replays=[];original=h.appDependency

def raw():return bytes(h.heap)+bytes(h.image[h.GS-h.IS:h.GS-h.IS+h.GN])
def patches(a,b):return [(i,y)for i,(x,y)in enumerate(zip(struct.unpack('<'+'I'*(len(a)//4),a),struct.unpack('<'+'I'*(len(b)//4),b)))if x!=y]
@h.AppDependency
def capture(c,q,u):
 e=q.contents;before=raw();buffers=[C.string_at(e.buffers[i],e.sizes[i])for i in range(e.buffersCount)];v=original(c,q,u);replays.append((e.function,e.receiver,tuple(e.arguments[:e.count]),e.name or b'',e.mask,hashlib.sha256(before).digest(),v,patches(before,raw()),buffers,[C.string_at(e.buffers[i],e.sizes[i])for i in range(e.buffersCount)]));return v
h.appDependency=capture

def run(f,t,args=(),span=False):
 replays.clear();before=raw();v=h.compareApp(f,t,args,'capture',span);corpus.append((f,t,args,span,v,before,raw(),list(replays)))
for prior,legacy in[(b'Player',b''),(b'',b''),(b'',b'Ada'),(b'Unknown',b'Player'),(b'',b'N'*31),(b'',b'N'*32)]:
 h.prepare();h.files={};h.putBytes(h.PRIORNAME,prior+b'\0');h.registry={0x52560c:legacy,0x5255fc:b'Location',0x5255f0:b'Email'};run(0x426546,h.APP,[h.PRIORNAME],True)
for f,args in[(0x42bf90,[h.RECORDS]),(0x430ac0,[h.RECORDS]),(0x42bbb0,[]),(0x42bbd0,[]),(0x42bbe0,[]),(0x42bbf0,[]),(0x42bb00,[0x525f30,0x49b730])]:
 for v in(0,1):
  h.prepare(1+v);h.dialogResult=v;h.putBytes(h.RECORDS+20,b'Player\0');run(f,h.INPUT if f==0x430ac0 else h.APP,args)
for f,args in[(0x49c090,[h.CONTROL,h.RECORDS,0]),(0x49c090,[h.CONTROL,h.RECORDS,1]),(0x49b050,[h.DIALOG]),(0x49b0c0,[h.CONTROL]),(0x49b730,[h.DIALOG,0x110,0,0]),(0x49b730,[h.DIALOG,0x111,1,0]),(0x49b730,[h.DIALOG,0x111,0x20000,h.CONTROL])]:
 h.prepare(2);h.putBytes(h.RECORDS+20,b'Player\0');h.putBytes(h.RECORDS+0x3000+20,b'Ada\0');h.listNames=[b'Player',b'Ada'];h.listIndex=1;run(f,h.M if f==0x49c090 else 0,args)
h.prepare(1);h.put(h.APP+100,[0]);h.putBytes(h.RECORDS+20,b'Player\0');run(0x49b050,0,[h.DIALOG])
h.prepare();h.globalSeed=bytes(h.image[h.GS-h.IS:h.GS-h.IS+h.GN]);h.files={}
for name in(b'Player',b'Ada'):
 h.putBytes(h.DATA,name+b'\0');h.compare(0x49bdb0,h.M,[h.DATA,0,0,4 if name==b'Ada'else 0],'source-saved-fixture')
h.compare(0x49bbc0,h.M,label='source-saved-writer');blob=h.files[b'CLAW.USR']
for name in(b'Player',b'Ada'):
 h.prepare();h.files={b'C:\\CLAW\\CLAW.USR':blob};h.putBytes(h.PRIORNAME,name+b'\0');run(0x426546,h.APP,[h.PRIORNAME],True)
with gzip.open(h.WORK/'sanitizer-replay.bin.gz','wb',compresslevel=1)as out:
 out.write(b'PCAP'+struct.pack('<4I',h.IS,len(h.image),h.SIZE,len(corpus))+bytes(h.image))
 for f,t,a,span,v,before,after,ee in corpus:
  out.write(h.pack(f,t,len(a),*list(a)+[0]*(5-len(a)),int(span),v,len(ee))+before)
  for ef,et,ea,name,mask,digest,value,pp,buffers,outputs in ee:
   out.write(h.pack(ef,et,len(ea),*list(ea)+[0]*(40-len(ea)),mask,value,len(name),len(pp),len(buffers))+digest+name)
   for p in pp:out.write(h.pack(*p))
   for b,v in zip(buffers,outputs):out.write(h.pack(len(b))+b+v)
  out.write(after)
print('PASS capture',h.calls,h.eventCount)
