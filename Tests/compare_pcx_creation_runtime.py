"""Whole unchanged4be810; physical CreateSurface/GetDesc are declared services."""
import ctypes as C
import json
import struct
import subprocess
import pcx_image_helpers as H
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP

WORK=H.ROOT/'work/pcx-creation-root';WORK.mkdir(exist_ok=True)
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off',
               '-dynamiclib',*[str(H.ROOT/'Sources'/f'{n}.cpp') for n in
                ('PCXCreationRuntime','PCXImageRuntime','GameImageRuntime','SpriteGeometry','PIDSurfaceRaster')],
               '-o',str(WORK/'libCreation.dylib')],check=True)
lib=C.CDLL(str(WORK/'libCreation.dylib'))
lib.claw_pcx_creation_entry.argtypes=[H.U,C.POINTER(H.U),H.U,C.POINTER(H.Context),H.Dep,C.c_void_p,C.POINTER(H.U)]
lib.claw_pcx_creation_entry.restype=H.U
base_effect=H.effect
padding=0;creation_status=0;description_status=0;initialize_failure=0
mutation=None;physical=[{},{}]

def effect(f,r,a,native):
    index=0 if native else 1
    if f==0x700018:
        if creation_status:return creation_status
        desc=H.get(a[1],27,native);depth=desc[21] if desc[1]&0x1000 else H.get(H.MANAGER+0x474,1,native)[0]
        actual=[0]*27;actual[0]=108;actual[1]=7;actual[2]=desc[2];actual[3]=desc[3]
        actual[4]=desc[3]*(1 if depth==8 else 2 if depth==16 else 3 if depth==24 else 4)+padding
        actual[9]=H.PIXELS;actual[21]=depth;physical[index]=dict(descriptor=actual)
        H.put(a[2],[H.DEVICE],native)
        if mutation:mutation(native,'create')
        return 0
    if f==0x700058:
        H.put(a[1],physical[index]['descriptor'],native)
        if mutation:mutation(native,'describe')
        return description_status
    if f==0x70000c:return initialize_failure
    return base_effect(f,r,a,native)

H.effect=effect
for address,definition in {0x700018:(4,16,False),0x700058:(2,8,False),0x70000c:(5,20,True)}.items():
    H.COUNTS[address]=definition
    H.m.u.hook_add(UC_HOOK_CODE,H.hook,begin=address,end=address)

def prepare(w=8,h=3,planes=1,target=None,pad=0):
    global padding,physical,creation_status,description_status,initialize_failure,mutation
    H.prepare(w,h,planes,target,pad);padding=pad;physical=[{},{}]
    creation_status=description_status=initialize_failure=0;mutation=None
    H.put(H.MANAGER,[H.DEVICE]);H.put(H.VT+0x18,[0x700018]);H.put(H.VT+0x58,[0x700058])

calls=snapshots=0
generated=[]
def compare(args,label,trace=True):
    global calls,snapshots,physical
    H.sync();H.events[0].clear();H.events[1].clear();H.errors.clear();H.context.fault=0;physical=[{},{}]
    out=H.U();raw=(H.U*4)(*args)
    assert lib.claw_pcx_creation_entry(H.SURFACE,raw,4,C.byref(H.context),H.dependency,None,C.byref(out)),(label,H.context.fault,H.errors)
    assert not H.errors,H.errors
    handle=H.m.u.hook_add(UC_HOOK_CODE,H.m.hook,begin=0x401000,end=0x50adb4) if trace else None
    try:result=H.m.call(0x4be810,H.SURFACE,struct.pack('<4I',*args),max_instructions=500000000)
    finally:
        if handle:H.m.u.hook_del(handle)
    assert result==out.value,(label,'EAX',result,out.value)
    assert H.snapshot(True)==H.snapshot(False),(label,'full heap/globals')
    assert H.events[0]==H.events[1],(label,'ordered full snapshots',[(e[0],f[0]) for e,f in zip(*H.events) if e!=f][:1])
    assert physical[0]==physical[1]
    assert H.m.u.reg_read(UC_X86_REG_ESP)==H.m.stack+20
    calls+=1;snapshots+=len(H.events[0]);return result

for planes in (1,3):
    for target in (8,24):
        for i in range(16):
            width=1+i;height=1+i%3;prepare(width,height,planes,target,i%4)
            data=H.pcx(width,height,planes,i);H.write(H.DATA,data)
            result=compare([H.MANAGER,H.DATA,len(data),0x40],('whole creation',planes,target,width))
            assert result==int(target==planes*8 or width%2==0)
            if target!=planes*8 and width%2==0:
                n=len(generated);prefix=WORK/f'generated-{n}'
                pitch=width*(1 if target==8 else 3)+i%4
                prefix.with_suffix('.input').write_bytes(data)
                prefix.with_suffix('.surface').write_bytes(H.read(H.PIXELS,pitch*height))
                prefix.with_suffix('.before').write_bytes(H.baseSeed[H.PIXELS-H.BASE:H.PIXELS-H.BASE+pitch*height])
                prefix.with_suffix('.palette').write_bytes(H.read(H.MANAGER+0x478,1024))
                generated.append((n,width,height,planes,target,i%4,len(data),pitch*height))
print('PASS PCX creation directed',calls,snapshots,flush=True)
for profile in ('null','planes','createFailure','oddAfterInit','allocationFailure','missingPalette','lockFailure','callbackWidth','callbackDepth'):
    prepare(5 if profile=='oddAfterInit' else 8,2,1,24 if profile in ('oddAfterInit','allocationFailure') else 8)
    data=bytearray(H.pcx(5 if profile=='oddAfterInit' else 8,2,1,14));H.write(H.DATA,data)
    token=H.DATA
    if profile=='null':token=0
    if profile=='planes':H.write(H.DATA+65,b'\x02')
    if profile=='createFailure':creation_status=0x80004005
    if profile=='allocationFailure':H.allocFailure=1
    if profile=='missingPalette':H.put(H.MANAGER+0x474,[8]);H.write(H.DATA+65,b'\x03');H.put(H.MANAGER+0x878,[0])
    if profile=='lockFailure':H.status['lock']=0x80004005
    if profile=='callbackWidth':
        def mutate(native,step):
            if step=='describe':H.put(H.SURFACE+24,[4],native)
        mutation=mutate
    if profile=='callbackDepth':
        def mutate(native,step):
            if step=='create':H.put(H.MANAGER+0x474,[24],native)
        mutation=mutate
    compare([H.MANAGER,token,len(data),0x40],profile)

#The virtual initializer is read from the live surface table; custom failure
#returns and changed-depth non8/24 service election keep their source order.
for value in (0,1):
    prepare(4,2);H.put(H.SURFACE,[H.VT]);H.put(H.VT+12,[0x70000c]);initialize_failure=value
    data=H.pcx(4,2,1,19);H.write(H.DATA,data)
    assert compare([H.MANAGER,H.DATA,len(data),0x81240],('customInit',value))==value
for planes in (1,3):
    for target in (0,1,8,16,24,32):
        for width in (2,3):
            prepare(width,2,planes,target);data=H.pcx(width,2,planes,26);H.write(H.DATA,data)
            compare([H.MANAGER,H.DATA,len(data),0],('depthAdmission',planes,target,width))
for planes in (0,1,2,3,255):
    for coords in ((-4,-7,1,-3),(0,0,-1,-1),(-32768,-32768,-32768,-32768),(2,0,0,1)):
        width=coords[2]-coords[0]+1;height=coords[3]-coords[1]+1
        prepare(width,height,planes,8);data=bytearray(1024);struct.pack_into('<4h',data,4,*coords);data[65]=planes;H.write(H.DATA,data)
        compare([H.MANAGER,H.DATA,len(data),0x40],('signedDimensions',planes,coords))
for planes in (1,3):
    for profile in ('lostRestoreFailure','lostRetryFailure','lostRecovery','unlockIgnored'):
        prepare(4,2,planes);data=H.pcx(4,2,planes,45);H.write(H.DATA,data)
        if profile.startswith('lost'):H.status['lock']=0x887601c2
        if profile=='lostRestoreFailure':H.restore=0
        if profile=='lostRetryFailure':H.status['retry']=0x887601c2
        if profile=='unlockIgnored':H.status['unlock']=0x80004005
        compare([H.MANAGER,H.DATA,len(data),0x40],profile)
print('PASS PCX creation extended',calls,snapshots,flush=True)

retail=0
for path in sorted((H.ROOT/'work/original-disc-assets').rglob('*.PCX')):
    data=path.read_bytes();x,y,X,Y=struct.unpack_from('<4h',data,4)
    prepare(X-x+1,Y-y+1,data[65],pad=retail%4);H.write(H.DATA,data)
    assert compare([H.MANAGER,H.DATA,len(data),0x40],str(path.relative_to(H.ROOT)),False)==1
    retail+=1
    if retail%40==0:print('PCX creation retail',retail,'of469',flush=True)
report=dict(originalSHA256='350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263',
            wholeOriginalCalls=calls,orderedFullSnapshots=snapshots,retailFiles=retail,
            instrumentedTextAddresses=sum(0x401000<=a<0x50adb5 for a in H.m.executed),
            boundaries='Physical CreateSurface/GetDesc, allocator, non8/24 conversion and seeded input/pixel tails explicit; no archive/controller/native boot acceptance')
(WORK/'report.json').write_text(json.dumps(report,indent=2)+'\n')
(WORK/'generated-manifest.txt').write_text('\n'.join(' '.join(map(str,p))for p in generated)+'\n')
print('PASS whole original PCX creation',json.dumps(report,sort_keys=True),flush=True)
