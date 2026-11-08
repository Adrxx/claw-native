"""Declared REZ/decompression input adapter; no reconstructed gameplay bodies."""
from pathlib import Path
import struct,hashlib,zlib
ROOT=Path(__file__).resolve().parents[1]
def worlds():
 b=(ROOT/'Original/claw-disc/files/DATA/CLAW.REZ').read_bytes()
 assert hashlib.sha256(b).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596'
 def word(o):return struct.unpack_from('<I',b,o)[0]
 result=[]
 def walk(offset,size,parent=()):
  end=offset+size
  while offset<end:
   kind,target,length=word(offset),word(offset+4),word(offset+8)
   name_start=offset+(16 if kind else 28);n=b.index(0,name_start,end);name=b[name_start:n].decode('ascii')
   if kind:walk(target,length,parent+(name,));offset=n+1
   else:
    ext=b[offset+20:offset+24].split(b'\0')[0][::-1].decode('ascii');offset=n+2
    path='/'.join(parent+(name+'.'+ext,))
    if len(parent)==2 and parent[0].startswith('LEVEL')and parent[1]=='WORLDS'and name=='WORLD'and ext=='WWD':
     payload=b[target:target+length];count,start=struct.unpack_from('<2I',payload,732)
     raw=payload[:start]+zlib.decompress(payload[start:])if struct.unpack_from('<I',payload,8)[0]&2 else payload
     result.append((path,raw,count,start,hashlib.sha256(payload).hexdigest()))
 walk(word(131),word(135));assert len(result)==14;return sorted(result,key=lambda r:int(r[0].split('/')[0][5:]))
if __name__=='__main__':
 for path,raw,count,start,_ in worlds():
  print(path,len(raw),count,[(struct.unpack_from('<I',raw,start+i*160+8)[0],*struct.unpack_from('<4I',raw,start+i*160+88))for i in range(count)])
