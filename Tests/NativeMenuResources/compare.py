"""Actual native shared-heap resource graph against the pinned original."""
import hashlib
import json
import sys
import os
import struct
from pathlib import Path
from Tests.NativeMenuBase.trace import MenuTrace
from Tests.clawparity.program import claw
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'work/native-menu-resources'

def prepare(interface=False):
 WORK.mkdir(parents=True,exist_ok=True)
 p=claw()
 spans=((0x513568,36),(0x532298,4),(0x5324cc,8),(0x534938,1))
 if interface:spans+=((0x50c1e4,0xe0),(0x513a00,0x900),(0x5371fc,4),(0x53ec44,4),(0x54316c,12),(0x527e00,0x200),(0x528b20,0x260),(0x528ae8,24))
 if interface and os.environ.get('CLAW_MENU_FULL_INITIALIZER')=='1':
  spans+=((0x50b000,0x16820),(0x522400,0x6660),(0x528a64,0x79c),
          (0x537200,0x360),(0x541314,20),(0x53ec38,16),(0x528a60,4),(0x45d6fc,28),(0x45db24,28),
          (0x5430c4,64),(0x537e88,4),(0x537b48,16),(0x532c0c,4),(0x45b518,36),(0x541178,404),
          # Original keyboard selector, main-menu and Options command tables.
          # Controls selects the third Options entry at 0x45c6d4.
          (0x45bb7c,60),(0x45c560,32),(0x45c6cc,24),
          # State-five exit dispatch also reads code-section table data.
          (0x45b628,25),
          # Popup construction publishes its current instance here.
          (0x5375bc,4))
 metadata={}
 for address,size in spans:
  section=next(s for s in p.sections if s.address<=address and address+size<=s.address+s.size)
  metadata[f'{address:x}']=list(section.data.ljust(section.size,b"\0")[address-section.address:address-section.address+size])
 if interface and os.environ.get('CLAW_MENU_FULL_INITIALIZER')=='1':
  for slot in p.imports:metadata[f'{slot:x}']=list(slot.to_bytes(4,'little'))
  versions=[]
  marker='FileVersion\0'.encode('utf-16le')
  for section in p.sections:
   at=section.data.find(marker)
   if at<6:continue
   length,count,kind=struct.unpack_from('<3H',section.data,at-6);start=(at+len(marker)+3)&~3
   assert kind==1 and start+2*count<=at-6+length
   versions.append([int(v) for v in section.data[start:start+2*count].decode('utf-16le').rstrip('\0').split(', ')])
  assert len(versions)==1 and len(versions[0])==4
  metadata.pop('53ec44',None);metadata['53ec38']=list(struct.pack('<4I',*versions[0]))
 (WORK/('interface-metadata.json' if interface else 'metadata.json')).write_text(json.dumps(metadata)+'\n')
 if interface:
  # A physical font atlas, independent of game strings and state. The original
  # reference uses the same pinned Pillow font and monochrome raster policy.
  from PIL import Image,ImageDraw,ImageFont,__version__
  assert __version__=='12.0.0'
  font=ImageFont.load_default(size=13)
  glyphs={}
  for code in range(32,127):
   glyph=chr(code);tile=Image.new('1',(32,32))
   ImageDraw.Draw(tile).text((8,0),glyph,font=font,fill=1,anchor='la')
   advance=font.getlength(glyph,mode='1')
   assert advance==int(advance)
   glyphs[str(code)]=dict(advance=int(advance),measureAdvance=int(font.getlength(glyph)),top=font.getbbox(glyph,mode='1')[1],pixels=list(tile.getdata()))
  (WORK/'menu-font.json').write_text(json.dumps(dict(height=sum(font.getmetrics()),glyphs=glyphs)))

def main():
 if sys.argv[1:]==['--prepare']:prepare();return
 if sys.argv[1:]==['--prepare-interface']:prepare(True);return
 witness=json.loads((WORK/'swift.json').read_text())
 original=MenuTrace()
 archive=original.allocate(0x48)
 original.run(0x4b7210,archive)
 path=original.cstring(b'CLAW.REZ')
 assert original.run(0x4b72e0,archive,(path,1,0))==1
 resources=[]
 for row in witness['resources']:
  directory=original.run(0x4b7f20,archive,(original.cstring(row['path'].encode()),))
  token=original.run(0x4b67f0,directory,(original.cstring(row['name'].encode()),row['type'])) if directory else 0
  data=None
  if token:
   address=original.run(0x4b61c0,token)
   if address:data=bytes(original.machine.mem_read(address,original.word(token+20)))
   original.run(0x4b6230,token)
  resources.append(dict(path=row['path'],name=row['name'],type=row['type'],found=data is not None,
                        bytes=len(data) if data is not None else 0,sha256=hashlib.sha256(data).hexdigest() if data is not None else ''))
 assert resources==witness['resources'],(resources,witness['resources'])
 reads=[{k:e[k] for k in ('offset','requested','bytes','sha256')} for e in original.physical_events if e['service']=='CRT fread']
 native_reads=[{k:e[k] for k in ('offset','requested','bytes','sha256')} for e in witness['services'] if e['service']=='read']
 assert reads==native_reads,(len(reads),len(native_reads))
 original.run(0x4b7250,archive,phase='archive-destruction')
 assert list(original.machine.mem_read(archive,72))==witness['destroyedArchive']
 closes=[e.get('result',0) for e in original.physical_events if e['service']=='CRT fclose']
 assert closes==[e.get('result',0) for e in witness['cleanupServices'] if e['service']=='close']
 assert witness['cleanupRemaining']==0 and witness['cleanupFault']==0
 result=dict(status='compared',resource_count=len(resources),reads=len(reads),cleanup_fault=witness['cleanupFault'])
 (WORK/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result))
 for stream in original.files.values():stream.close()
if __name__=='__main__':main()
