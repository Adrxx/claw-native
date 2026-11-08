"""Fingerprint an original REZ and capture independent directory/payload facts.
Private generated inventory stays under work/. No game assets are exported.
"""
from pathlib import Path
import hashlib,json,struct,sys
ROOT=Path(__file__).resolve().parents[1]
source=Path(sys.argv[1])if len(sys.argv)>1 else ROOT/'Original/claw-disc/files/DATA/CLAW.REZ'
rez=source.read_bytes()
assert hashlib.sha256(rez).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596'
def word(at):return struct.unpack_from('<I',rez,at)[0]
folders=[];resources=[]
def walk(at,size,path=(),stamp=0):
    folders.append(dict(path='\\'.join(path),offset=at,bytes=size,stamp=stamp))
    end=at+size
    while at<end:
        kind=word(at);offset,length,stamp=word(at+4),word(at+8),word(at+12)
        namepos=at+(16 if kind==1 else 28);nul=rez.index(0,namepos,end)
        name=rez[namepos:nul].decode('ascii')
        if kind==1:
            walk(offset,length,path+(name,),stamp);at=nul+1
        else:
            metanul=rez.index(0,nul+1,end);count=word(at+24)
            assert count==0 and metanul==nul+1
            resources.append(dict(folder='\\'.join(path),name=name,offset=offset,
                bytes=length,stamp=stamp,id=word(at+16),tag=word(at+20),
                sha256=hashlib.sha256(rez[offset:offset+length]).hexdigest()))
            at=metanul+1+count*4
    assert at==end
walk(word(131),word(135),stamp=word(139))
assert len(folders)==1384 and len(resources)==13077
assert sum(r['bytes']for r in resources)==117018527
out=ROOT/'work/native-resource-archive-check/retail-inventory.json';out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(dict(folders=folders,resources=resources)))
print('PASS pinned REZ1384 folders/13077 resources/117018527 payload bytes; independent raw inventory captured privately')
