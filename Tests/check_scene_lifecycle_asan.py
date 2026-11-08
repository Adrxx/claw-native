"""Strict ABI and exact-span scene teardown fixtures; physical services remain explicit."""
import ast,pathlib,subprocess
root=pathlib.Path(__file__).resolve().parents[1];work=root/'work/scene-lifecycle-agent'
tree=ast.parse((root/'Tests/scene_lifecycle_helpers.py').read_text());names=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='names'for t in n.targets))
def run(*args):subprocess.run(list(map(str,args)),cwd=root,check=True)
(work/'header.c').write_text('#include "SceneLifecycleRuntime.h"\n_Static_assert(CLAW_SCENE_LIFECYCLE_BYTES==60,"scene");\n')
(work/'header.swift').write_text('let value=ClawSceneLifecycleCall()\nprecondition(MemoryLayout.size(ofValue:value)==96)\nprint("PASS Swift lifecycle call ABI")\n')
run('clang','-std=c11','-pedantic-errors','-Wall','-Wextra','-Werror','-I','Sources','-fsyntax-only',work/'header.c');run('clang++','-std=c++17','-pedantic-errors','-Wall','-Wextra','-Werror','-I','Sources','-fsyntax-only','Sources/SceneLifecycleRuntime.cpp')
run('swiftc','-import-objc-header','Sources/SceneLifecycleRuntime.h',work/'header.swift','-o',work/'swift-abi');run(work/'swift-abi')
run('clang++','-std=c++17','-pedantic-errors','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I','Sources',root/'Tests/scene_lifecycle_exact_smoke.cpp',*[root/'Sources'/f'{n}.cpp'for n in names],'-o',work/'smoke');run(work/'smoke')
print('PASS strict ABI +64 exact scene/controller/map/string/display/graphics ASAN UBSAN chains')
