#!/usr/bin/env python3
"""Complete original naming/registry bodies with real REZ directory profiles."""
import hashlib,json,random,struct
import image_registry_runtime_helpers as g

assets,order=g.readREZ();reports=[]
assert not any('CANDE' in p for p in order), 'Unexpected CANDE resource in pinned REZ'
for prefix,label,imagePrefix,aniPrefix in [('LEVEL','LEVEL1','LEVEL1/IMAGES/','LEVEL1/ANIS/'),('CLAW','CLAW','CLAW/IMAGES/','CLAW/ANIS/')]:
 if not any(p.startswith(imagePrefix)for p in order):
  assert label=='CLAW';imagePrefix='CLAW/IMAGES/';print('Available CLAW paths:',[p for p in order if p.startswith('CLAW/')][:4],flush=True)
 g.reset(13);g.write(g.PREFIX,prefix.encode()+b'\0');profile=g.rezTree(assets,order,imagePrefix,'IMAGES');tree=g.makeTree(*profile)
 result=g.compare(0x4cff40,g.CONTROLLER,[tree,g.PREFIX,g.SEPARATOR],label+'/images')
 roots={name.decode():g.words(slot)[0]for name,slot in g.maps[g.CONTROLLER+16].items()}
 mappings={}
 resourcePaths={}
 def paths(node,components=()):
  for child in g.directories[node][0]:paths(child,components+(g.text(g.words(child)[0]).decode(),))
  for ty in g.directories[node][1]:
   extension=g.words(ty)[0].to_bytes(4,'little').rstrip(b'\0')[::-1].decode()
   for file in g.types[ty]:resourcePaths[file]=imagePrefix+'/'.join(components+(g.text(g.words(file)[0]).decode()+'.'+extension,))
 paths(tree)
 assert len(g.resourceResults)==len(g.loadedImages)
 filenameIDs={resourcePaths[resource]:{'imageID':image[0],'payloadSHA256':hashValue,'transportWord16':assets[resourcePaths[resource]][1]}for(resource,length,hashValue),image in zip(g.resourceResults,g.loadedImages)}
 for name,t in roots.items():
  n=g.words(t+24)[0];slots=g.words(g.words(t+20)[0],n)
  mappings[name]={'minimum':g.words(t+100)[0],'maximum':g.words(t+104)[0],'storedName':g.text(t+36).decode(),'frames':{str(i):g.words(image+4)[0]for i,image in enumerate(slots)if image}}
 if label=='LEVEL1':
  assert mappings['LEVEL_SKULL']['frames']=={'0':0}
  assert 'LEVEL_CANDELABRASINGLE'not in roots
 before={k:dict(v)for k,v in g.maps.items()};g.compare(0x4cff40,g.CONTROLLER,[tree,g.PREFIX,g.SEPARATOR],label+'/images-retained-duplicate');assert g.maps==before
 # Restore/reload follows real root dispatch and retains the existing sparse IDs.
 g.compare(0x4d0120,g.CONTROLLER,[tree,g.PREFIX,g.SEPARATOR],label+'/images-retained-restore')
 for name in list(roots):g.write(g.PREFIX,name.encode()+b'\0');g.compare(0x4cf230,g.CONTROLLER,[g.PREFIX],label+'/remove/'+name,void=True)
 assert not g.maps[g.CONTROLLER+16]
 reports.append({'label':label,'domain':'images','sourcePrefix':imagePrefix,'result':result,'roots':mappings,'files':filenameIDs,'actualFiles':sum(1 for p in order if p.startswith(imagePrefix))})
 g.reset(21,ani=True);g.write(g.PREFIX,prefix.encode()+b'\0');tree=g.makeTree(*g.rezTree(assets,order,aniPrefix,'ANIS'))
 result=g.compare(0x4ce0d0,g.CONTROLLER,[tree,g.PREFIX,g.SEPARATOR],label+'/ANI')
 names={n.decode():g.words(s)[0]for n,s in g.maps[g.CONTROLLER+16].items()}
 if label=='LEVEL1':
  assert 'LEVEL_MANICLES_MANICAL'in names and 'LEVEL_MANICALS_MANICAL'not in names and 'LEVEL_MANICALS_M'not in names
  assert 'LEVEL_CANDELABRASINGLE'not in names
 for n,t in names.items():
  g.compare(0x4ce250,t,[1],label+'/ANI-delete/'+n)
 reports.append({'label':label,'domain':'ANI','sourcePrefix':aniPrefix,'result':result,'names':list(names),'actualFiles':sum(1 for p in order if p.startswith(aniPrefix))})
 print('PASS',label,'whole image/ANI registration, retained duplicates/restore and deletion',flush=True)
(g.WORK/'original-resource-mappings.json').write_text(json.dumps(reports,indent=2)+'\n')

# First numeric substring, empty and signed-looking names; full decimal wrap.
fileNames=['SKULL','FRAME001','RIGHT5','A12B34','A-9','A+8','001X99','A4294967296','EMPTY','0000000','z\x7f7tail']
for seed in range(80):
 g.reset(seed);children=[('GROUP',[],[(n,0x504944,b'opaque-image-'+n.encode(),10000000+i)for i,n in enumerate(fileNames)])]
 tree=g.makeTree('IMAGES',children);g.compare(0x4cff40,g.CONTROLLER,[tree,g.PREFIX,g.SEPARATOR],f'first-numeric/{seed}')
 root=g.words(g.maps[g.CONTROLLER+16][b'LEVEL_GROUP'])[0];table=g.words(root+20)[0]

# Raw-root/create wrappers, formats, duplicate rejection and typed failures.
for iteration in range(24):
 g.reset(iteration);root=g.rootProfile();tree=g.makeTree('FILES',[],[('FRAME003',0x504944,b'rawPID',10000000),('FRAME011',0x504944,b'rawPID',10000001)]);file=g.types[g.directories[tree][1][0]][0]
 if iteration%4==0:g.imageFailures={3}
 if iteration%5==0:g.missingPayloads={file}
 g.compare(0x4ce320,root,[file,3,1],f'root-create/{iteration}')
 g.compare(0x4ce320,root,[file,3,1],f'root-duplicate/{iteration}')
 g.compare(0x4ce770,root,[file,3,1],f'root-reload/{iteration}')
 g.compare(0x4ce5e0,root,[tree],f'root-enumerate/{iteration}')
 g.compare(0x4ce670,root,[tree],f'root-restore/{iteration}')
 g.compare(0x4ce2d0,root,[],f'root-clear/{iteration}',void=True)
 g.compare(0x4d02f0,root,[1],f'root-delete/{iteration}')

for fn in (0x4cfaa0,0x4cfba0,0x4cfca0,0x4cfdb0,0x4cfee0,0x4cfec0,0x4cff00,0x4cff20,0x4ce480,0x4ce530):
 g.reset(fn);root=g.rootProfile();g.write(g.RAW,b'rawDATA-and-guards');resource=g.makeTree('FILE',[],[('FRAME004',0x504944,b'rawDATA',4)]);file=g.types[g.directories[resource][1][0]][0]
 if fn==0x4cfaa0:args=[file,g.PREFIX,4,1]
 elif fn==0x4cfba0:args=[file,g.PREFIX,4,1]
 elif fn in(0x4cfca0,0x4cfdb0):args=[g.RAW,4,g.PREFIX,7,1]
 elif fn in(0x4cfee0,0x4cfec0):args=[file,root,4,1]
 elif fn in(0x4cff00,0x4cff20):args=[g.RAW,4,root,7,1]
 else:args=[g.RAW,4,7,1]
 g.compare(fn,g.CONTROLLER if fn<0x4d0000 and fn>=0x4cf000 else root,args,f'wrapper/{fn:x}',void=fn in(0x4cfee0,0x4cfec0,0x4cff00,0x4cff20))

# Namespace alternatives, truncation, first-byte/case retention and empty input.
for prefix in ('','level','LEVEL_X','A'*100):
 g.reset(len(prefix));g.write(g.PREFIX,prefix.encode()+b'\0');g.write(g.SEPARATOR,b'::\0');tree=g.makeTree('IMAGES',[('a2',[],[('A12B99',0x504944,b'data',10000000)]),('EMPTY',[],[])])
 g.compare(0x4cff40,g.CONTROLLER,[tree,g.PREFIX,g.SEPARATOR],f'namespace/{prefix}')
for name in ('','A','A'*63,'B'*64,'X'*200):
 g.reset(len(name));root=g.rootProfile();g.write(g.PREFIX,name.encode()+b'\0');g.compare(0x4d0380,root,[g.PREFIX],f'truncated-root-name/{len(name)}');assert g.read(root+99,1)==b'\0'
for missing in (False,True):
 g.reset();tree=g.makeTree('FILES',[('PICTURES',[],[('PIC001',0x504944,b'data',10000000)])]);g.write(g.PREFIX,b'MISSING\0'if missing else b'PICTURES\0');g.compare(0x4cf1f0,g.CONTROLLER,[tree,g.PREFIX],'default-group-loader')
for missingParent,idValue in((False,0),(False,0xffffffff),(True,0)):
 g.reset();g.put(g.CONTROLLER+4,[idValue]);g.put(g.CONTROLLER+12,[0 if missingParent else g.SCENE]);g.compare(0x4cf080,g.CONTROLLER,[],'metadata-initialization-probe')
for fn in (0x4cff40,0x4ce0d0):
 g.reset(fn,ani=fn==0x4ce0d0);tree=g.makeTree('EMPTY');g.allocationFailures=[256];assert g.compare(fn,g.CONTROLLER,[tree,g.PREFIX,g.SEPARATOR],f'name-buffer-null/{fn:x}')==0
g.reset();tree=g.makeTree('IMAGES',[],[('FRAME003',0x504944,b'data',10000000)]);g.allocationFailures=[108];g.failure(0x4cff40,g.CONTROLLER,[tree,g.PREFIX,g.SEPARATOR],'unsafe-root-allocation-null')
g.reset();root=g.rootProfile();tree=g.makeTree('IMAGES',[],[('FRAME003',0x504944,b'data',10000000)]);file=g.types[g.directories[tree][1][0]][0];g.allocationFailures=[52];g.failure(0x4ce320,root,[file,3,1],'unsafe-image-allocation-null')

# ANI raw-header edge profiles, existing sequences and empty named events.
for flags,count,path in ((0,0,b''),(0xffffffff,0,b'path'),(0,1,b''),(9,2,b'name')):
 g.reset(flags,ani=True);seq=g.treeAlloc(32);g.put(seq,[0x513a58,0,0x5108fc,0,0,0,0,0]);data=bytearray(32);struct.pack_into('<4I',data,4,0,flags,count,len(path));data.extend(path)
 for i in range(count):data.extend(struct.pack('<H9h',2,1,0,0,0,20,3,4,5,6)+b'\0')
 g.write(g.RAW,bytes(data));g.compare(0x4d6070,seq,[g.SCENE,g.RAW,0x100],f'ANI-edge/{flags}/{count}/{path}');g.compare(0x4ce250,seq,[1],'ANI-edge-delete')
for length in(0,52):
 g.reset(71,ani=True);resource=g.makeTree('ANIS',[],[('NULL',0x414e49,assets['GAME/ANIS/NULL.ANI'][0],10000000)]);file=g.types[g.directories[resource][1][0]][0]
 if not length:g.missingPayloads={file}
 g.compare(0x4cdff0,g.CONTROLLER,[g.PREFIX,file],f'ANI-payload/{length}')

# Every typed image wrapper uses the original type selection before transport.
for ty in (0x424d50,0x504358,0x524944,0x504944,0x414e49,0):
 for missing in (False,True):
  g.reset(ty);root=g.rootProfile();tree=g.makeTree('FILES',[],[('F004',ty,b'full-raw-image',41)]);file=g.types[g.directories[tree][1][0]][0]
  if missing:g.missingPayloads={file}
  image=g.treeAlloc(52);g.put(image,[0x513a70,4,0,g.SCENE]);g.compare(0x4d2380,image,[file,0],f'typed-wrapper/{ty:x}/{missing}')
# Source restore failure must propagate FFFFFFFF, including a retained sparse root.
g.reset();root=g.rootProfile();tree=g.makeTree('FILES',[],[('F003',0x504944,b'raw',9)]);g.compare(0x4ce5e0,root,[tree],'restore-setup');g.imageFailures={3};assert g.compare(0x4ce670,root,[tree],'restore-existing-failure')==0xffffffff
# Safe sequence allocation failure, and typed wrapper rejects non-ANI before flag write.
g.reset(33,ani=True);tree=g.makeTree('ANIS',[],[('NULL',0x414e49,assets['GAME/ANIS/NULL.ANI'][0],2)]);file=g.types[g.directories[tree][1][0]][0];g.allocationFailures=[32];assert g.compare(0x4cdff0,g.CONTROLLER,[g.PREFIX,file],'ANI-sequence-allocation-null')==0
g.reset(37,ani=True);tree=g.makeTree('FILES',[],[('WRONG',0x504944,b'opaque',2)]);file=g.types[g.directories[tree][1][0]][0];seq=g.treeAlloc(32);assert g.compare(0x4d61b0,seq,[g.SCENE,file,0xdeadbeef],'ANI-wrong-type')==0
# Seeded record/name leaves produce a callback-free, whole-heap sanitizer corpus.
for seed in range(96):
 g.reset(seed+1000);actor=g.treeAlloc(112);name=('p'+str(seed)+'_'+'X'*(seed%80)).encode();g.write(g.PREFIX+1,name+b'\0');g.compare(0x4d0380,actor,[g.PREFIX+1],f'leaf-name/{seed}')
 raw=bytearray(random.Random(seed).randbytes(20));flags=seed%2;struct.pack_into('<H',raw,0,flags);g.write(g.RAW+1,bytes(raw));record=g.treeAlloc(48);g.compare(0x4d76e0,record,[0,g.RAW+1],f'leaf-record/{seed}')
 g.compare(0x4d6260,record,[0],f'leaf-record-destructor/{seed}')
# Native diagnostics are intentionally distinct from original gameplay returns.
g.reset();bad=g.Args();bad.count=5;result=g.U(0x1234);assert g.lib.claw_image_registry_entry(0x4d0380,g.CONTROLLER,bad,g.C.byref(g.ctx),g.C.byref(result))==0 and g.ctx.fault==2 and result.value==0x1234
g.ctx.fault=0;assert g.lib.claw_image_registry_entry(0xffffffff,g.CONTROLLER,bad,g.C.byref(g.ctx),g.C.byref(result))==0 and g.ctx.fault==0 and result.value==0x1234
g.replayWriter.close();(g.WORK/'sanitizer-replay.bin.gz').write_bytes(g.replay.getvalue())

report={'completeOriginalCalls':g.calls,'orderedFullHeapEvents':g.eventCount,'persistentRawHeapBytes':g.SIZE,'sanitizerWholeHeapReplayCalls':g.replayCases,'originalInstructionAddresses':len([x for x in g.m.executed if x<0x1000000 and x not in g.ADAPTED_ENTRIES]),'unsafeOriginalPrefixesBeforeNullDereference':g.contextFaults,'originalResourceProfiles':reports,'explicitServices':['directory/type/leaf traversal and payload residency','generic name-map lookup/value-slot/remove','physical image initialization4d2410 and image deletion4ce8e0','CRT physical allocation/free'],'frozenComposition':['CArray','AnimationEngine record decoder']}
(g.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='originalResourceProfiles'}),flush=True)
