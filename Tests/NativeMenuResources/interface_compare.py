"""Compare the Swift IFC/native surfaces with fresh retail menu initialization."""
import hashlib
import json
from .compare import ROOT,WORK
from Tests.NativeMenuBase.trace import MenuTrace
from Tests.NativeMenuBase.native_join import NativeJoin

def main():
 witness=json.loads((WORK/'interface-swift.json').read_text())
 original=MenuTrace();original.frame_count=0
 try:
  NativeJoin.execute(original)
  nodes=[]
  for node in original.interface_nodes:
   selected=[]
   for surface in node['selected']:
    token=int(surface['surface'],16)
    physical=original.com_objects[original.word(token+8)]
    data=bytes(original.machine.mem_read(physical['pixels'],physical['pitch']*physical['height']))
    selected.append(dict(width=physical['width'],height=physical['height'],sha256=hashlib.sha256(data).hexdigest()))
   nodes.append({**{k:node[k] for k in ('depth','id','name','children','images')},'selected':selected})
  (WORK/'interface-original.json').write_text(json.dumps(nodes,indent=2)+'\n')
  mismatch=[dict(index=i,native=a,original=b) for i,(a,b) in enumerate(zip(witness['nodes'],nodes)) if a!=b]
  assert len(nodes)==len(witness['nodes']) and not mismatch,json.dumps(mismatch[:2])
  assert not any(witness[k] for k in ('cleanupFault','resourceFault','cleanupRemaining','displayFault'))
  result=dict(status='compared',nodes=len(nodes),selections=sum(len(n['selected']) for n in nodes),
              scope='Swift shared menu heap, original archive/IFC/image owners, native display pixels and source cleanup; full menu initializer and frames remain separate')
  (WORK/'interface-result.json').write_text(json.dumps(result,indent=2)+'\n')
  print(json.dumps(result))
 finally:
  for file in original.files.values():file.close()
if __name__=='__main__':main()
