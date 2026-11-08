#!/usr/bin/env python3
"""Fingerprint a local PE and optionally disassemble a bounded VA range."""
import argparse, hashlib, json, struct
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('exe',type=Path); p.add_argument('--start',type=lambda s:int(s,0)); p.add_argument('--size',type=lambda s:int(s,0),default=512); a=p.parse_args()
b=a.exe.read_bytes()
if len(b)<64 or b[:2]!=b'MZ': p.error('not MZ')
pe=struct.unpack_from('<I',b,60)[0]
if pe+24>len(b) or b[pe:pe+4]!=b'PE\0\0': p.error('not a bounded PE')
count=struct.unpack_from('<H',b,pe+6)[0]; opt=struct.unpack_from('<H',b,pe+20)[0]; base=struct.unpack_from('<I',b,pe+52)[0]
sections=[]
for i in range(count):
 o=pe+24+opt+40*i
 name=b[o:o+8].rstrip(b'\0').decode('ascii'); vs,va,rs,ro=struct.unpack_from('<4I',b,o+8)
 sections.append(dict(name=name,va=hex(base+va),virtual_size=vs,raw_size=rs,raw_offset=ro))
if a.start is None:
 print(json.dumps(dict(sha256=hashlib.sha256(b).hexdigest(),size=len(b),machine=hex(struct.unpack_from('<H',b,pe+4)[0]),image_base=hex(base),entry=hex(base+struct.unpack_from('<I',b,pe+40)[0]),sections=sections),indent=2))
else:
 from capstone import Cs,CS_ARCH_X86,CS_MODE_32
 for s in sections:
  delta=a.start-int(s['va'],16)
  if 0<=delta<s['raw_size']:
   if a.size<1 or delta+a.size>s['raw_size']: p.error('range outside raw section')
   offset=s['raw_offset']+delta
   for ins in Cs(CS_ARCH_X86,CS_MODE_32).disasm(b[offset:offset+a.size],a.start): print(f'{ins.address:08x}: {ins.mnemonic:8s} {ins.op_str}')
   break
 else: p.error('address not backed by section bytes')
