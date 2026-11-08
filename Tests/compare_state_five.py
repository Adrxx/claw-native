"""Retail State5 whole-source controller and resolver differential proof."""
import state_five_helpers as h
import json,hashlib,struct
h.capture=False
exec((h.WORK/'pilot.py').read_text().replace("sys.path.insert(0,'Tests');import state_five_helpers as h",'').replace("print(hex(f),flush=True);",'').replace("print('PASS',h.calls,h.eventCount)",''))
# Every actual retail IFC name/image selector, repeated under source options.
profile=json.loads((h.ROOT/'Tests/state_five_interface_profile.json').read_text());assert hashlib.sha256((h.ROOT/'work/original-disc-assets/STATES/MENU/CLAW.IFC').read_bytes()).hexdigest()==profile['assetSHA256'];tree=profile['nodes'];names=sorted({v for n in tree for v in n['images']})
for flags in range(8):
 for name in names:
  h.fresh();h.put(h.APP+16,[flags&1,(flags>>1)&1]);h.put(h.APP+0x118,[(flags>>2)&1,flags&1,(flags>>1)&1,(flags>>2)&1,flags&1]);h.put(h.APP+120,[8 if flags&1 else 16]);payload=name.encode();h.put(h.STRING+20,[1,len(payload),len(payload)]);h.writebytes(h.STRING+32,payload+b'\0');h.compare(0x45f940,f'image/{flags}/{name}',(h.STRING+32,),cdecl=True)
# Public helper output spans, no match, zero/signed limits, source empty owner.
for payload in(b'0_main_zero',b'-1_main_signed',b'2147483647_optionsaudio_sound',b'31_optionsaudio_sound',b'36_optionsaudio_music',b'9_UNKNOWN',b'  +4_QUIT_test'):
 h.fresh();h.put(h.STRING+20,[1,len(payload),len(payload)]);h.writebytes(h.STRING+32,payload+b'\0');h.compare(0x45be10,f'prefix/{payload}',(h.STRING+32,h.OUTSTRING,h.OUTFRAME))
h.fresh();h.put(0x537b58,[0]);h.compare(0x45f940,'no-owner-owned-string',(h.STRING+32,),cdecl=True)
# Source action routing for every IFC item, enabled/disabled and gates.
for enabled in(0,1):
 for available in(0,1):
  for node in tree:
   h.fresh();h.availability=available;h.compare(0x45c240,f'route/{node["id"]}/{enabled}/{available}',(node['id'],enabled))
for level in(0,1,2,14,15,0x7fffffff,0x80000000,0xffffffff):
 for slot in(0,1,2,3,0xffffffff):
  h.fresh();h.compare(0x42b990,f'new/{level}',(level,),receiver=h.APP,meaningful=False)
  h.fresh();h.compare(0x42b9c0,f'load/{level}/{slot}',(level,slot),receiver=h.APP,meaningful=False)
# All source load-sub slots and gaps, not a guessed contiguous checkpoint grid.
for id in range(0x1b58a,0x1b612):
 h.fresh();h.compare(0x45d150,f'load-id/{id}',(id,))
for enabled in(0,1):
 for found in(0,1):
  h.fresh();payload=b'Single Player';h.put(h.STRING+20,[1,len(payload),len(payload)]);h.writebytes(h.STRING+32,payload+b'\0');h.dictionaryValue=83;h.dictionaryFound=found;h.put(h.ITEM+68,[0 if enabled else 32]);h.compare(0x45e990,f'accelerator/{enabled}/{found}',(83,0),meaningful=False)
# Edge/held/repeat profiles use separate54132c versus53720c deltas.
for pressed in(0,1,0xffffff,0x80000000,0x40000000,0x10000000,0x20000000,0xf0000000):
 for held in(0,1,0x80000000,0x40000000,0x10000000,0x20000000,0xf0000000):
  for delta in(0,17,350,0xffffffff):
   h.fresh();h.itemCount=3;h.put(h.INPUT+528,[pressed,held]);h.put(0x53720c,[delta]);h.compare(0x45bbc0,f'input/{pressed:x}/{held:x}/{delta}',meaningful=False)
for key in(13,32,27,37,38,39,40,65,0,0xffffffff):
 h.fresh();h.itemCount=4;h.compare(0x45ba50,f'key/{key}',(key,0x123456))
for delta in(0,17,120000,120001,0x80000000,0xffffffff):
 for flag in(0,1):
  h.fresh();h.put(0x54132c,[delta]);h.put(0x528a68,[flag]);h.compare(0x45b650,f'frame/{delta}/{flag}')
# Scalar slider stores and option rebind histories, actual original constants.
for mode in(0,1,2,3,0xffffffff):
 for volume in(0,1,7,8,40,79,80,100,0xffffffff):
  h.fresh();h.put(0x532c10,[volume]);h.compare(0x45f100,f'volume/{mode}/{volume}',(mode,0x3459),meaningful=False)
 for rank in(1,2,5,9,10,11,0xffffffff):
  h.fresh();h.put(h.APP+104,[rank]);h.compare(0x45f360,f'detail/{mode}/{rank}',(mode,0x34c0),meaningful=False)
 h.fresh();h.compare(0x45f100,f'music/{mode}',(mode,0x345c),meaningful=False)
for flags in range(16):
 for method in(0x45e370,0x45e5c0):
  h.fresh();h.put(h.OWNER+0x28c,[flags,flags]);h.compare(method,f'rebind/{method:x}/{flags}')
for sound in(0,1):
 for id in range(0x3459,0x345e):
  h.fresh();h.put(0x532c0c,[sound]);h.put(h.APP+16,[sound]);h.compare(0x45c880,f'audio/{sound}/{id}',(id,))
for id in range(0x34bd,0x34c3):
 h.fresh();h.compare(0x45cb90,f'display/{id}',(id,))
# Rendering captures exact DC/string/RECT/colors and source version formats.
for dc in(0,0x1234):
 for easy in(0,4):
  for patch in(0,1,99):
   h.fresh();h.dcValue=dc;h.put(h.RES+4,[easy]);h.put(0x53ec38,[1,4,patch,5]);h.compare(0x45fbb0,f'draw/{dc}/{easy}/{patch}',(h.FW,0xfffffffd,10,640,480),meaningful=False,cdecl=True)
h.dcValue=0
# Complete source roll wrappers; image/DS/fader source modules are explicit graph services.
for skip in(0,1):
 for paper in(0,h.IMAGE):
  h.fresh();h.put(h.OWNER+16,[h.GRAPHICS]);h.put(h.GRAPHICS,[h.VT]);h.put(h.TW+20,[640,480]);h.put(h.IMAGE+20,[640,480]);h.put(h.OWNER+64,[paper]);h.put(0x537238,[skip]);h.compare(0x45dc90,f'roll/{skip}/{paper}',(10000,))
for boundary in('rollResource','rollImage','rollFade','failAllocation'):
 h.fresh();h.put(h.OWNER+16,[h.GRAPHICS]);h.put(h.GRAPHICS,[h.VT]);h.put(h.TW+20,[640,480]);h.put(h.IMAGE+20,[640,480]);setattr(h,boundary,1 if boundary=='failAllocation'else 0);h.compare(0x45dc90,f'roll-failure/{boundary}',(10000,),unsafe=boundary=='failAllocation')
# Init/readiness/resource/parser failures preserve reached mutations/ownership.
for missing in(0,0x528b08,0x52372c,0x523ce0,0x523cd8,0x523734,0x4b61c0):
 h.fresh();h.missing=missing;h.compare(0x45ace0,f'init/{missing}',(h.APP,1,0))
for parse in(0,1):
 h.fresh();h.parseResult=parse;h.compare(0x45ace0,f'parse/{parse}',(h.APP,14,5))
# Callback-mutated aliases, not only passive dependencies.
for func,address,value in[(0x4b3490,h.INPUT+528,0x80000000),(0x42c0a0,0x528a68,1),(0x4dd270,h.OWNER+0x29c,13003),(0x4b3e70,0x532c0c,1)]:
 h.fresh();h.mutations={func:[(address,value)]};h.put(0x54132c,[120000]);h.compare(0x45b650,f'mutation/{func:x}')
retained=[]
for level in range(1,15):
 h.fresh();h.compare(0x45ace0,f'life-init/{level}',(h.APP,level,0));h.compare(0x45b3f0,f'life-enter/{level}',(13,));h.compare(0x45ba50,f'life-select/{level}',(32,0));h.compare(0x45b650,f'life-frame/{level}');h.compare(0x45c240,f'life-new/{level}',(11100+level,1));h.compare(0x45c240,f'life-load/{level}',(0x1b58b+(level-1)*10,1));h.compare(0x45b540,f'life-depart/{level}',(3,));h.compare(0x429510,f'life-destroy/{level}',(1,));retained.append(level)
# Explicit unchecked source prefixes.
h.fresh();h.put(h.OWNER+0x25c,[0]);h.compare(0x45ef30,'null-coin-prefix',(10001,),meaningful=False,unsafe=True)
h.fresh();h.failCreation=1;h.compare(0x45b240,'null-cursor-prefix',meaningful=False,unsafe=True)
textAddresses={a for a in h.m.executed if 0x401000<=a<=0x50adb5};result=dict(wholeCalls=h.calls,snapshots=h.eventCount,originalMappedTextAddresses=len(textAddresses),instrumentedAddresses=len(h.m.executed),unsafePrefixes=h.unsafeCases,retailNodes=len(tree),retailImageNames=len(names),retainedLevels=retained,sourceSHA256=hashlib.sha256((h.ROOT/'Original/claw10/CLAW.EXE').read_bytes()).hexdigest())
(h.WORK/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
