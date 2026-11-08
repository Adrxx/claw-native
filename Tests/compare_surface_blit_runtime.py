import gzip,json,struct
import surface_blit_helpers as h
#Raw and synchronous rectangle forms retain the same source byte effects.
for seed in range(20):
 for flags in(0,0x800,0x8000,0x8800,0x20800):
  for mask in(0,1,4,5):
   h.fresh(seed);h.capture=seed==0 and flags in(0,0x8800);h.put(h.FX+4,[0x10 if flags&0x20000 else 0]);h.compare(0x4b9ce0,[h.DR,h.SRC,h.SR,flags,h.FX],mask,'indexed/menu rectangle')
  h.fresh(seed);h.capture=False;h.compare(0x4b9d80,[2,3,h.SRC,h.SR,flags],8 if seed&1 else 0,'indexed fast copy')
 #The original permits null rectangles and a null source for successful fills.
 h.fresh(seed);h.capture=seed==0;h.compare(0x4b9ce0,[0,h.SRC,0,0x800,0],label='whole surface rectangles');h.compare(0x4b9ce0,[h.DR,0,0,0x400,0],label='source-null fill')
print('PASS ordinary indexed/menu rectangles',h.calls,h.snapshots,flush=True)
for seed in range(8):
 for f in(0x4b9ce0,0x4b9d80):
  a=[h.DR,h.SRC,h.SR,0x8800,h.FX]if f==0x4b9ce0 else[2,3,h.SRC,h.SR,0x800]
  mask=5 if f==0x4b9ce0 else 8
  for first,second,restore,callback in((1,0,1,True),(0x80004005,0,1,True),(0x887601c2,0,1,True),(0x887601c2,1,1,True),(0x887601c2,0x887601c2,1,True),(0x887601c2,0,0,True),(0x887601c2,0,1,False)):
   h.fresh(seed);h.capture=seed==0;h.sequence=[first,second];h.restoreValue=restore
   if not callback:h.put(h.DST+180,[0])
   h.compare(f,a,mask,'device/restore return')
  h.fresh(seed);h.capture=seed==0;h.sequence=[0x887601c2,0];h.mutate=True;h.compare(f,a,mask,'restore replaces interfaces and live rectangles')
print('PASS error/restore/retry ordering',h.calls,h.snapshots,flush=True)
for seed in range(8):
 for key in(0,1,254,255,0xffffffff):
  for hr in(0,1,0x80004005):
   h.fresh(seed);h.capture=seed==0 and key in(0,0xffffffff) and hr in(0,0x80004005);h.sequence=[hr];h.compare(0x4b9990,[key],label='key convenience',void=True)
   assert h.get(h.DST+184)==[int(key!=0xffffffff)]
   h.put(h.PAIR,[key,key]);h.compare(0x4b9950,[8,h.PAIR],2 if seed&1 else 0,'physical key wrapper')
for callback,restore in((0,0),(0x7000b4,0),(0x7000b4,1),(0x7000b4,0xffffffff)):
 h.fresh();h.capture=True;h.put(h.DST+180,[callback]);h.restoreValue=restore;assert h.compare(0x4b9e60,[],label='frozen PCX restore')==int(bool(callback and restore))
print('VERIFIED',h.calls,'whole calls',h.snapshots,'ordered full snapshots',flush=True)
p=lambda *v:struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
with gzip.open(h.WORK/'sanitizer-replay.bin.gz','wb')as out:
 out.write(b'SBLT'+p(h.SIZE,h.IMAGE_START,h.IMAGE_SIZE,len(h.corpus),len(h.OBJECTS)))
 for token,n in h.OBJECTS:out.write(p(token,n))
 for f,t,words,count,mask,label,value,meaningful,before,expected,events,originalArgs in h.corpus:
  out.write(p(f,t,count,mask,value,meaningful,len(events))+p(*words)+before)
  for ef,et,a,em,ev,buffers,outputs,digest,changes in events:
   out.write(p(ef,et,len(a),em,ev,len(buffers),len(changes))+p(*a)+digest)
   for b,v in zip(buffers,outputs):out.write(p(len(b))+b+v)
   for i,v in changes:out.write(p(i,v))
  out.write(expected)
report={'original_sha256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263','whole_calls':h.calls,'ordered_full_snapshots':h.snapshots,'sanitizer_calls':len(h.corpus),'sanitizer_callback_snapshots':sum(len(x[-2])for x in h.corpus),'physical_scope':'declared endpoint byte writes, HRESULTs and restore callback; no physical DD raster acceptance'}
(h.WORK/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('CORPUS',report['sanitizer_calls'],report['sanitizer_callback_snapshots'],flush=True)
