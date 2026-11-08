import sys,gzip,struct,ctypes as C,hashlib
sys.path.insert(0,'Tests');import player_menu_management_helpers as h
pack=lambda *v:struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
# Importing this focused runner establishes the test-only facade probe and
# verifies six unchanged-original profiles before capturing the same profiles.
import compare_player_menu_assignment_tail as target
corpus=[];replays=[];original=h.menuDependency
raw=lambda:bytes(h.heap)+bytes(h.image[h.GS-h.IS:h.GS-h.IS+h.GN])
canonical=lambda:h.canonical()+bytes(h.image[h.GS-h.IS:h.GS-h.IS+h.GN])
def patches(a,b):return[(i,y)for i,(x,y)in enumerate(zip(struct.unpack('<'+'I'*(len(a)//4),a),struct.unpack('<'+'I'*(len(b)//4),b)))if x!=y]
@h.MenuDependency
def capture(c,q,u):
 e=q.contents;before=raw();digest=hashlib.sha256(canonical()).digest();value=original(c,q,u);replays.append((e.function,e.receiver,tuple(e.arguments[:e.count]),e.name or b'',e.mask,digest,value,patches(before,raw()),[],[]));return value
h.menuDependency=capture
for value,cookie in[(v,False)for v in(b'USERREMOVECONFIRM',b'USERNEW',b'EDITPLAYERS',b'Ada Cove',b'Lin Coast')]+[(b'USERREMOVECONFIRM',True)]:
 h.prepare();h.strings.bytes=h.loadBytes;h.lc.save.lookupBytes=h.loadBytes
 if cookie:
  h.mc.scene.context=C.addressof(target.outerCookie);h.mc.scene.lookup=target.outerWords;h.strings.bytes=h.ByteLookup();h.lc.save.scene.context=C.addressof(target.saveCookie);h.lc.save.lookupBytes=target.saveBytes
 h.put(h.TIME_CELL,[h.ctx.emptyStringToken]);h.putBytes(h.DATA,value+b'\0');before=raw();replays.clear();result=h.compareMenu(0x4f66cc,h.TIME_CELL,[h.DATA],'capture-title-tail');corpus.append((result,before,canonical(),list(replays),cookie))
with gzip.open(h.WORK/'assignment-tail-replay.bin.gz','wb',compresslevel=1)as out:
 out.write(b'PMMG'+pack(h.IS,len(h.image),h.SIZE,len(corpus))+bytes(h.image))
 for result,before,after,ee,cookie in corpus:
  out.write(pack(0x4f66cc,h.TIME_CELL,1,h.DATA,0,0,0,0,3 if cookie else 1,result,len(ee),0)+before)
  for f,t,a,name,mask,digest,v,pp,buffers,outputs in ee:
   out.write(pack(f,t,len(a),*list(a)+[0]*(40-len(a)),mask,v,len(name),len(pp),0)+digest+name)
   for pair in pp:out.write(pack(*pair))
  out.write(after)
print('PASS capture',len(corpus),sum(len(v[3])for v in corpus))
