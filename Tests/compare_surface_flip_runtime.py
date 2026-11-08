import gzip,json,struct
import surface_flip_helpers as h
profiles=((0,0,1,True),(1,0,1,True),(0x80004005,0,1,True),(0x887601c2,0,1,True),(0x887601c2,1,1,True),(0x887601c2,0x887601c2,1,True),(0x887601c2,0,0,True),(0x887601c2,0,1,False))
for seed in range(10):
 for vt in(0x513588,0x513690,0x5136c0):
  for source in(0,h.SRC,h.DST):
   for first,second,restored,callback in profiles:
    h.fresh(seed,vt);h.capture=seed==0 and vt==0x5136c0;h.sequence=[first,second];h.restoreValue=restored
    if not callback:h.put(h.DST+180,[0])
    value=h.compare(source,'ordinary Flip/result/restore')
    assert value==(second if first==0x887601c2 and restored and callback else first)
print('PASS ordinary Flip profiles',h.calls,h.snapshots,flush=True)
for source in(0,h.SRC,h.DST):
 for where in('first','restore','diagnostic','privateRestore'):
  h.fresh();h.capture=True;h.sequence=[0x887601c2,0x80004005 if where=='diagnostic'else 0]
  def mutate(f,index):
   if(where=='first'and f==0x70002c and index==1)or(where in('restore','diagnostic','privateRestore')and f in(0x7000b4,0x7000e0)):
    h.put(h.DST+8,[h.DD2]);h.put(h.SRC+8,[h.SD2])
   if where=='privateRestore'and f==0x70002c and index==1:h.put(h.DST,[h.PRIVATE])
   if where=='diagnostic'and f==0x4bd260:h.put(h.DST+8,[h.DD])
  h.mutation=mutate;h.compare(source,'captured source/live destination alias')
  physical=[e for e in h.events if e[0]in(0x70002c,0x70012c)]
  assert physical[0][2][1]==physical[1][2][1]
  if where!='first' or source!=h.DST:assert physical[1][2][0]==h.DD2
print('PASS live alias ordering',h.calls,h.snapshots,flush=True)
#Repeated successful presentation reuses the retained original object graph.
for seed in range(8):
 for source in(0,h.SRC,h.DST):
  h.fresh(seed);h.capture=seed==0 and source==h.SRC
  for frame in range(4):assert h.compare(source,'retained presentation')==0
print('VERIFIED',h.calls,'whole calls',h.snapshots,'ordered full snapshots',flush=True)
p=lambda *v:struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
with gzip.open(h.WORK/'sanitizer-replay.bin.gz','wb')as out:
 out.write(b'SFLP'+p(h.SIZE,h.IMAGE_START,h.IMAGE_SIZE,len(h.corpus),len(h.OBJECTS)))
 for token,n in h.OBJECTS:out.write(p(token,n))
 for source,value,before,expected,events in h.corpus:
  out.write(p(source,value,len(events))+before)
  for f,t,a,v,digest,changes in events:
   out.write(p(f,t,len(a),v,len(changes))+p(*a)+digest)
   for i,v in changes:out.write(p(i,v))
  out.write(expected)
report={'whole_calls':h.calls,'ordered_full_snapshots':h.snapshots,'sanitizer_calls':len(h.corpus),'sanitizer_callback_snapshots':sum(len(x[-1])for x in h.corpus),'original_sha256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263','physical_scope':'declared presentation writes/HRESULTs and restore callbacks; no live display acceptance'}
(h.WORK/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('CORPUS',report['sanitizer_calls'],report['sanitizer_callback_snapshots'],flush=True)
