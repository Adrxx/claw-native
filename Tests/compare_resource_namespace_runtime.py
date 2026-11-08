import resource_namespace_helpers as h
import random,json
TAG=int.from_bytes(b'DIP\0','little')
h.reset();tree=(b'',[(b'STATES',[(b'BOOTY',[],[(b'FRAME001',TAG,1)]),(b'CREDITS',[],[(b'TITLE',TAG,0)])],[]),(b'LEVEL1',[(b'IMAGES',[],[(b'SKULL',TAG,0)])],[])],[]);root=h.buildTree(tree);h.put(h.CONTROL+36,[root])
for path in [b'STATES_BOOTY',b'STATES/CREDITS',b'\\STATES\\BOOTY',b'states_booty',b'STATES___BOOTY/',b'STATES',b'//STATES_BOOTY',b'',b'_',b'/',b'NOPE',b'LEVEL1_IMAGES']:
 h.text(h.PATH,path);h.compare(0x4b7f20,h.CONTROL,[h.PATH],str(path));h.compare(0x4b7cd0,root,[h.PATH],str(path))
for path in [b'STATES_BOOTY_FRAME001',b'STATES/CREDITS/TITLE',b'\\STATES\\BOOTY\\FRAME001',b'LEVEL1_IMAGES_SKULL',b'STATES_BOOTY',b'FRAME001',b'A/FRAME001',b'//FRAME001',b'STATES_BOOTY_',b'',b'/']:
 h.text(h.PATH,path);h.compare(0x4b7dc0,root,[h.PATH,TAG],str(path));h.compare(0x4b7f00,h.CONTROL,[h.PATH,TAG],str(path))
rng=random.Random(0x4b7cd0)
for i in range(500):
 h.text(h.PATH,bytes(rng.choice(b'ABz09_/@[]\\\x80\xff')for _ in range(rng.randrange(1,45))));h.compare(0x4b7cd0,root,[h.PATH],f'randompath{i}');h.compare(0x4b7dc0,root,[h.PATH,TAG],f'randomfile{i}')
h.capture=True
for i in range(12):
 h.reset(i);r=h.buildTree((b'',[(b'BOOTY',[],[(b'Alpha',TAG,1),(b'aLPHA',TAG,2),(b'Gamma',TAG,3)])],[]));h.put(h.CONTROL+36,[r]);h.text(h.PATH,b'booty_ALPHA');h.compare(0x4b7f00,h.CONTROL,[h.PATH,TAG],f'capture{i}')
h.capture=False
h.reset();tree,entries=h.rezTree();root=h.buildTree(tree);h.put(h.CONTROL+36,[root]);print('real tree',len(h.folderPaths),len(h.leaves),'bytes',h.cursor-h.BASE,flush=True)
for path,t in h.folderPaths.items():
 if not path:continue
 p=b'_'.join(path)
 h.text(h.PATH,p);value=h.compare(0x4b7f20,h.CONTROL,[h.PATH],str(path))
 if value!=t:print("source unaddressable flattened folder",path,hex(value),hex(t),flush=True)
for path,t in list(h.leafPaths.items()):
 if len(path)<2 or path[0]not in(b'STATES',b'LEVEL1',b'GAME',b'CLAW'):continue
 p=b'_'.join(path[:-1]);h.text(h.PATH,p);h.compare(0x4b7f00,h.CONTROL,[h.PATH,path[-1]],str(path))
print('PASS',h.calls,'whole calls',h.snapshots,'snapshots',len(h.m.executed),'instrumented addresses')
# Whole direct lookup + source iterator wrappers over every retail directory/type.
for t,children in h.folders.items():
 first=h.compare(0x4b68e0,t,[],f'firstfolder{t}');seen=[]
 while first:
  assert first not in seen;seen.append(first);first=h.compare(0x4b6900,t,[first],f'nextfolder{first}')
 assert set(seen)==set(children)
 for child in children:
  nt=h.get(child);assert h.compare(0x4b68c0,t,[nt],f'directfolder{child}')==child
 first=h.compare(0x4b6920,t,[],f'firsttype{t}');seen=[]
 while first:
  assert first not in seen;seen.append(first);first=h.compare(0x4b6940,t,[first],f'nexttype{first}')
 for ty in seen:
  first=h.compare(0x4b6960,t,[ty],f'firstfile{ty}');files=[]
  while first:
   assert first not in files;files.append(first);first=h.compare(0x4b6980,t,[first],f'nextfile{first}')
  assert set(files)==set(h.types[ty])
print('retail enum passed',h.calls,flush=True)
# CRT locale path is explicit; complete callee snapshots preserve raw aliases.
for locale in(0,1):
 h.reset(locale);r=h.buildTree((b'',[(b'STATES',[(b'BOOTY',[],[(b'Alpha',TAG,1),(b'aLPHA',TAG,2),(b'Gamma',TAG,3)])],[])],[]));h.put(h.CONTROL+36,[r]);h.put(0x540e88,[locale])
 for value in [b'STATES_BOOTY_ALPHA',b'states_booty_gamma',b'STATES_BOOTY_MISSING']:
  h.text(h.PATH,value);h.compare(0x4b7f00,h.CONTROL,[h.PATH,TAG],f'locale{locale}{value}')
 for folder in h.folders:
  for ty in h.types:
   for file in h.types[ty]:
    nt=h.get(file);h.compare(0x4b7f80,ty+36,[nt,0],f'sensitive{file}');h.compare(0x4b7f80,ty+36,[nt,1],f'insensitive{file}')
 for f in(0x4b7f50,0x4b8140):
  for s in(b'',b'Alpha',b'abc\x80\xff',b'Z'*288):h.text(h.PATH,s);h.compare(f,0,[h.PATH],f'hash{f}{s[:8]}')
 for f in(0x4b8060,0x4b80d0):
  for v in(0,1,9,19,0x7fffffff,0xffffffff):h.compare(f,0,[v],f'taghash{f}{v}')
 for f,args in[(0x4b7540,[]),(0x4b68c0,[0]),(0x4b7f80,[0,1]),(0x4b8170,[0,1])]:h.compare(f,h.CONTROL,args,f'null{f}')
# Safe overlapping leaf/folder locals, long direct leaves, parser's64-byte limit.
for length in(31,32,33,64,255,287):
 h.reset(length);leaf=b'X'*length;r=h.buildTree((b'',[(b'ROOT',[],[(leaf,TAG,1)])],[(leaf,TAG,2)]));h.put(h.CONTROL+36,[r]);h.text(h.PATH,b'/'+leaf);h.compare(0x4b7dc0,r,[h.PATH,TAG],f'longdirect{length}');h.text(h.PATH,b'ROOT/'+leaf);h.compare(0x4b7dc0,r,[h.PATH,TAG],f'overlap{length}')
print('FINAL PASS',h.calls,'whole calls',h.snapshots,'full snapshots',len(h.m.executed),'instrumented addresses',flush=True)
# Source direct scalar/hash/iterator entries, wraparound bucket arithmetic.
h.capture=True
h.reset(77);r=h.buildTree((b'',[(b'A',[],[(b'Alpha',TAG,1),(b'Bravo',TAG,2)]),(b'B',[],[])],[]));h.put(h.CONTROL+36,[r])
for t,children in h.folders.items():
 for child in children:
  h.compare(0x4b8170,t+60,[h.get(child),0],f'directsensitive{child}');h.compare(0x4b8170,t+60,[h.get(child),1],f'directfold{child}')
 for index in range(5):h.compare(0x4d54f0,t+60,[index],f'bucket{t}{index}')
 h.compare(0x4d54c0,t+60,[],f'rawfirst{t}')
 for child in children:h.compare(0x4d5350,child+36,[],f'rawnext{child}')
 for ty in h.types:
  h.compare(0x4b80e0,t+68,[TAG],f'rawtype{t}');h.compare(0x4b67f0,t,[0,TAG],f'nullfile{t}')
# Empty-string reads original input[-1]; both allowed and disallowed predecessor.
for predecessor in(0,ord('A'),ord('_'),0x80):
 h.text(h.PATH-4,bytes([1,2,3,predecessor]));h.text(h.PATH,b'');h.compare(0x4b7dc0,r,[h.PATH,TAG],f'emptyprecedent{predecessor}')
# Borrowed callback changes a matched node value: source returns re-read alias.
h.capture=False;h.put(0x540e88,[1]);h.text(h.PATH,b'A');bucket=h.get(r+64);node=h.get(bucket+8+16)-4;h.mutationToken=node+20;h.mutationValue=r;assert h.compare(0x4b7cd0,r,[h.PATH],'borrowed alias')==r;h.mutationToken=0
# Genuine unchecked pointer faults, prefix heap/order equality (not safe success).
unsafe=[]
for f,t,a in [(0x4b7cd0,r,[0]),(0x4b7f20,0,[h.PATH]),(0x4d54f0,0,[0])]:
 before=bytes(h.heap);bi=bytes(h.image);h.ctx.fault=0;h.events.clear();h.oevents.clear();args=(h.U*len(a))(*a);out=h.U();ok=h.lib.claw_resource_namespace_entry(f,t,args,len(a),h.C.byref(h.ctx),h.dep,None,h.C.byref(out));assert not ok and h.ctx.fault==1;expected=h.raw(True);h.m.u.mem_write(h.BASE,before);h.m.u.mem_write(h.iBase,bi)
 try:h.m.call(f,t,h.pack(*a));raise AssertionError('original fault expected')
 except h.UcError:pass
 assert h.raw(False)==expected and h.events==h.oevents;unsafe.append((hex(f),hex(h.m.u.reg_read(h.UC_X86_REG_EIP))))
# Native copy guards are separately labeled: original stack overwrite not emulated.
for f,value in[(0x4b7cd0,b'Z'*64),(0x4b7dc0,b'X/'+b'Z'*288),(0x4b7dc0,b'Z'*256+b'/Q')]:
 h.text(h.PATH,value);h.ctx.fault=0;args=(h.U*2)(h.PATH,TAG);out=h.U();ok=h.lib.claw_resource_namespace_entry(f,r,args,1 if f==0x4b7cd0 else 2,h.C.byref(h.ctx),h.dep,None,h.C.byref(out));assert not ok and h.ctx.fault==2
# Capture exact live object spans. Raw source strings require their containing
# final aligned word in this word-only SceneActorHost; CRT transport supplies it.
import gzip,struct
with gzip.open(h.WORK/'sanitizer-corpus.bin.gz','wb')as w:
 w.write(struct.pack('<I',len(h.replays)))
 for f,t,args,before,after,im,ret,objects in h.replays:
  objects.update({h.CONTROL:128,h.PATH-4:1028});w.write(struct.pack('<7I',f,t,len(args),*(args+[0]*2)[:2],ret,len(objects)));w.write(before);w.write(after);w.write(im)
  for token,size in objects.items():w.write(struct.pack('<2I',token,(size+3)&~3))
report={'wholeCalls':h.calls,'snapshots':h.snapshots,'unsafePrefixes':unsafe,'instrumentedAddresses':len(h.m.executed),'originalTextAddresses':len([v for v in h.m.executed if 0x401000<=v<0x50adb6]),'exactSizeReplays':len(h.replays),'sourceSafetyGuards':3}
(h.WORK/'report.json').write_text(json.dumps(report,indent=2));print('VERIFIED',report,flush=True)
