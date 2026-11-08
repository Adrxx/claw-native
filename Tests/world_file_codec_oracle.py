#!/usr/bin/env python3
"""Separate original zlib1.0.4 payload proof; no native-zlib heap parity claim."""
import hashlib,json,struct,sys,zlib
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/world-file-agent'
# The verified REZ input adapter is separate from the original codec body.
from world_plane_assets import worlds as decoded_worlds
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;base,size=0x4000000,0x1000000;u.mem_map(base,size);m.executed.clear();cursor=base+0xb00000;allocations=[];frees=[];inputToken=base+0x10000;outputToken=base+0x400000;countToken=base+0x1000;guard=128
blob=(ROOT/'Original/claw-disc/files/DATA/CLAW.REZ').read_bytes();assert hashlib.sha256(blob).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596'
payloads={}
def word(o):return struct.unpack_from('<I',blob,o)[0]
def walk(offset,length,parent=()):
 end=offset+length
 while offset<end:
  kind,target,n=word(offset),word(offset+4),word(offset+8);start=offset+(16 if kind else 28);nul=blob.index(0,start,end);name=blob[start:nul].decode('ascii')
  if kind:walk(target,n,parent+(name,));offset=nul+1
  else:
   ext=blob[offset+20:offset+24].split(b'\0')[0][::-1].decode('ascii');offset=nul+2
   if len(parent)==2 and parent[0].startswith('LEVEL')and parent[1]=='WORLDS'and name=='WORLD'and ext=='WWD':payloads['/'.join(parent)+'/WORLD.WWD']=blob[target:target+n]
walk(word(131),word(135));assert len(payloads)==14

def returned(result):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,result);u.reg_write(UC_X86_REG_ESP,sp+4);u.reg_write(UC_X86_REG_EIP,ret)
def hook(uc,address,instructionSize,user):
 global cursor
 sp=u.reg_read(UC_X86_REG_ESP)
 if address==0x4adf50:
  count,bytesEach=m.read_words(sp+4,2);n=count*bytesEach;token=cursor;cursor+=max(16,(n+15)&~15);assert cursor<base+size;u.mem_write(token,bytes(n));allocations.append((token,n));returned(token)
 elif address==0x4a49b0:token=m.read_words(sp+4,1)[0];frees.append(token);returned(0)
u.hook_add(UC_HOOK_CODE,hook)
results=[]
for name,raw,_,_,_ in decoded_worlds():
 payload=payloads[name];header=struct.unpack_from('<I',payload)[0];declared=struct.unpack_from('<I',payload,744)[0];expected=raw[header:];assert len(expected)==declared and zlib.decompress(payload[header:])==expected
 capacity=declared+32;u.mem_write(inputToken,payload[header:]);u.mem_write(outputToken-guard,bytes([0x9a])*(capacity+guard*2));m.write_words(countToken,[capacity]);u.mem_write(m.stack,struct.pack('<5I',m.stop,outputToken,countToken,inputToken,declared));u.reg_write(UC_X86_REG_ESP,m.stack);u.reg_write(UC_X86_REG_ECX,0);u.emu_start(0x4d5fe0,m.stop,count=300000000);assert u.reg_read(UC_X86_REG_EIP)==m.stop;assert u.reg_read(UC_X86_REG_EAX)==0 and m.read_words(countToken,1)==[declared]
 actual=bytes(u.mem_read(outputToken-guard,capacity+guard*2));assert actual==bytes([0x9a])*guard+expected+bytes([0x9a])*(32+guard),(name,'full output/guards')
 results.append({'world':name,'decodedBytes':declared,'sha256':hashlib.sha256(expected).hexdigest()});print('PASS original codec',name,declared,flush=True)
report={'originalWholeCodecCalls':len(results),'originalImageAddresses':len([a for a in m.executed if a<0x1000000]),'callocCalls':len(allocations),'freeCalls':len(frees),'decodedWorlds':results}
(WORK/'codec-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='decodedWorlds'}))
