import gzip,json,struct
import palette_fade_helpers as h
#Whole menu/Story blocking fades. The first elapsed value is source10ms.
for seed in range(8):
 for duration in(0,1,10,750,1000):
  for start,count in((0,256),(32,64),(0,0)):
   h.fresh(seed);h.capture=seed==0 and start==0 and count==256;h.clocks=[1000,1000,1010,1010,1025,1333,1749,1750,1999,2000]if duration==1000 else[1000,1000,1010,1010,1025,1333,1749,1750]if duration==750 else[1000]
   h.compare(0x4bbd90,[start,count,h.TARGET,duration],'menu/story blocking table fade',void=True)
   assert h.created and h.created[-1][0]in h.freed
print('PASS blocking source timelines',h.calls,h.snapshots,flush=True)
#Retained source-configured scheduled table/packed-RGB histories.
for seed in range(8):
 for duration in(750,1000):
  for table in(False,True):
   h.fresh(seed);h.capture=seed==0;h.put(h.BACKEND+20,[h.TARGET if table else 0]);h.put(h.BACKEND+28,[0x00e08020]);h.put(h.BACKEND+32,[duration,1000,0,0,256,1])
   for elapsed in(0,1,1,10,125,duration//2,duration-1,duration,duration+1):
    h.clocks=[1000+elapsed];h.compare(0x4bbb70,[],'retained scheduled tick')
   assert h.get(h.BACKEND+52)==[0]and h.get(h.BACKEND+20)==[0]
   h.compare(0x4bbd20,[],'repeated cancel',void=True)
print('PASS scheduled retained timelines',h.calls,h.snapshots,flush=True)
for table in(False,True):
 for hr in(0,1,0x80004005):
  h.fresh();h.capture=True;h.hrGet=h.hrSet=h.hrWait=hr;h.clocks=[1000,1250,1750];h.compare(0x4bbd90,[0,256,h.TARGET,750],'device-error blocking fade',void=True)
  h.put(h.BACKEND+20,[h.TARGET if table else 0]);h.put(h.BACKEND+28,[0x0040f080]);h.put(h.BACKEND+32,[1000,1000,0,0,256,1]);h.clocks=[1250];h.compare(0x4bbb70,[],'device-error tick');h.compare(0x4bbd20,[],'device-error finalize',void=True)
#Cancellation applies final target immediately even before elapsed duration.
for active in(False,True):
 for table in(False,True):
  h.fresh();h.capture=True;h.put(h.BACKEND+20,[h.TARGET if table else 0]);h.put(h.BACKEND+28,[0x0070a030]);h.put(h.BACKEND+52,[int(active)]);h.compare(0x4bbd20,[],'cancel final target',void=True)
#Synchronous callbacks may replace valid backing/interface and cooperative aliases.
for where in('clock','get','set','wait'):
 h.fresh();h.capture=True;h.clocks=[1000,1250,1750]
 def mutate(f,index):
  if(where=='clock'and f==0x546df0 and index==2)or(where=='get'and f==0x700010)or(where=='set'and f in(0x700018,0x700118)and index==1):h.put(h.BACKEND+12,[h.ALT]);h.put(h.BACKEND+4,[h.PAL2]);h.put(0x541374,[0])
  if where=='wait'and f==0x700058:h.put(h.BACKEND+4,[h.PAL2])
 h.mutation=mutate;h.compare(0x4bbd90,[0,256,h.TARGET,750],'live callback aliases',void=True)
#UInt32 source time subtraction across a normal clock wrap.
h.fresh();h.capture=True;h.clocks=[0xfffffff0,0xfffffff5,250,800];h.compare(0x4bbd90,[0,256,h.TARGET,750],'source clock wrap',void=True)
for present in(False,True):
 for holder in(False,True):
  h.fresh();h.capture=True;h.put(h.BACKEND+16,[h.BACKUP if present else 0]);h.put(0x541374,[h.HOLDER if holder else 0]);h.compare(0x4bb8c0,[7],'backup apply',void=True)
print('VERIFIED',h.calls,'whole calls',h.snapshots,'ordered full snapshots',flush=True)
p=lambda *v:struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
with gzip.open(h.WORK/'sanitizer-replay.bin.gz','wb')as out:
 out.write(b'PFAD'+p(h.SIZE,h.IMAGE_START,h.IMAGE_SIZE,len(h.corpus),len(h.OBJECTS)))
 for token,n in h.OBJECTS:out.write(p(token,n))
 for f,t,a,value,meaningful,before,expected,created,events in h.corpus:
  out.write(p(f,t,len(a),value,meaningful,len(created),len(events))+p(*a)+before)
  for token,n in created:out.write(p(token,n))
  for ef,et,a,ev,buffers,outputs,digest,changes in events:
   out.write(p(ef,et,len(a),ev,len(buffers),len(changes))+p(*a)+digest)
   for b,v in zip(buffers,outputs):out.write(p(len(b))+b+v)
   for i,v in changes:out.write(p(i,v))
  out.write(expected)
report={'whole_calls':h.calls,'ordered_full_snapshots':h.snapshots,'sanitizer_calls':len(h.corpus),'sanitizer_callback_snapshots':sum(len(x[-1])for x in h.corpus),'source_sha256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263','scope':'ordinary blocking/scheduled/cancel/backup palette source bodies; physical device remains declared'}
(h.WORK/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('CORPUS',report['sanitizer_calls'],report['sanitizer_callback_snapshots'],flush=True)
