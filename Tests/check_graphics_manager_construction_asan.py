from pathlib import Path
import json,struct,subprocess
root=Path(__file__).resolve().parents[1];w=root/'work/graphics-manager-construction'
fixtures=json.loads((w/'fixtures.json').read_text());data=bytearray()
for f in fixtures:
 before=bytes.fromhex(f['before']);after=bytes.fromhex(f['after']);data+=struct.pack('<II',f['entry'],len(before))+before+after
(w/'exact-fixtures.bin').write_bytes(data)
(w/'asan.cpp').write_text(r'''
#include "GraphicsManagerConstructionRuntime.h"
#include <fstream>
#include <vector>
#include <cstring>
#include <cassert>
struct Block{uint32_t* p;uint32_t n;};
uint32_t* lookup(void* u,uint32_t t,uint32_t n){auto&b=*static_cast<Block*>(u);if(t<0x1000000||t%4)return nullptr;uint64_t offset=t-0x1000000;return offset/4+n<=b.n?b.p+offset/4:nullptr;}
int main(int argc,char**argv){assert(argc==2);std::ifstream in(argv[1],std::ios::binary);unsigned count=0;
 while(true){uint32_t entry=0,n=0;if(!in.read(reinterpret_cast<char*>(&entry),4))break;in.read(reinterpret_cast<char*>(&n),4);assert(n==2180||n==20);auto*p=new uint32_t[n/4];std::vector<char> expected(n);in.read(reinterpret_cast<char*>(p),n);in.read(expected.data(),n);Block b{p,n/4};ClawSceneActorHost h{};h.context=&b;h.lookup=lookup;uint32_t fault=0,result=0;
 auto f=entry==0x4bc120?claw_graphics_manager_construct:claw_graphics_string_array_construct;
 assert(f(0x1000000,h,&fault,&result)==1&&fault==0&&result==0x1000000);assert(!std::memcmp(p,expected.data(),n));delete[]p;++count;}
 assert(count==64);return 0;
}''')
names=['GraphicsManagerConstructionRuntime','SoundTriggerLogicRuntime','EnemySpeechRuntime','SpeechActor','AudioEvents','ActorResourceBindings','ActorDestruction','SceneActorRuntime','WorldObjectRuntime','GameTiming','ActorAnimationRuntime','AnimationEngine','AnimationOperations']
subprocess.run(['clang++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(root/'Sources'),str(w/'asan.cpp'),*[str(root/'Sources'/f'{n}.cpp') for n in names],'-o',str(w/'asan')],check=True)
subprocess.run([str(w/'asan'),str(w/'exact-fixtures.bin')],check=True)
print('PASS64 unchanged-original exact2180/20-byte seeded constructor replays under ASAN/UBSAN')
