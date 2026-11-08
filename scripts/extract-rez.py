#!/usr/bin/env python3
"""Reference-informed REZ index reader. Extract selected local asset-reference roots."""
import argparse,struct,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('rez',type=Path);p.add_argument('destination',type=Path);p.add_argument('--all',action='store_true',help='Extract every root (original inputs stay local)');a=p.parse_args();b=a.rez.read_bytes()
def u(o):
 if o<0 or o+4>len(b):raise ValueError('Truncated REZ')
 return struct.unpack_from('<I',b,o)[0]
def name(o,end):
 n=b.index(0,o,end);s=b[o:n].decode('ascii')
 if not s or s in ('.','..') or any(c in s for c in '/\\'):raise ValueError('Unsafe REZ name')
 return s,n+1
files={};seen=set()
def walk(offset,size,parent,depth=0):
 if size==0:return
 if depth>32 or (offset,size) in seen or offset+size>len(b):raise ValueError('Invalid directory')
 seen.add((offset,size));end=offset+size
 while offset<end:
  kind=u(offset);target,length=u(offset+4),u(offset+8)
  if kind:
   s,nextpos=name(offset+16,end);walk(target,length,parent/s,depth+1)
  else:
   s,nextpos=name(offset+28,end);nextpos+=1
   ext=b[offset+20:offset+24].split(b'\0')[0][::-1].decode('ascii')
   if any(c in ext for c in '/\\'):raise ValueError('Unsafe extension')
   path=parent/(s+'.'+ext)
   if target+length>len(b):raise ValueError('Truncated payload')
   if a.all or path.parts[0] in ('CLAW','LEVEL1'):
    data=b[target:target+length];out=a.destination/path;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
    files[str(path)]={'size':length,'sha256':hashlib.sha256(data).hexdigest()}
  if nextpos<=offset or nextpos>end:raise ValueError('Invalid entry size')
  offset=nextpos
if len(b)<139:raise ValueError('Truncated header')
walk(u(131),u(135),Path())
print(json.dumps({'rez_sha256':hashlib.sha256(b).hexdigest(),'files':files},indent=2))
