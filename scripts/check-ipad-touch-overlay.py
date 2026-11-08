"""Real iPad simulator touches, including concurrent contacts and checkpoint gesture.

Builds a small XCTest driver in the lane's existing derived-data folder. Its
private XCTest event synthesizer supplies multiple real simulator contacts;
no game actions or UIKit touch callbacks are invoked by the check itself.
Run with the shared ios-sim lane held. Evidence stays under work/touch-overlay.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import plistlib
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work/touch-overlay'
UDID = 'EC00F0C0-E5B0-4DE3-A269-402E6C117619'
def _bundle_id():
    # Claw.xcconfig holds the public default; an ignored Local.xcconfig may override it.
    value = 'org.claw.reconstruction'
    for name in ('Claw.xcconfig', 'Local.xcconfig'):
        path = Path(__file__).resolve().parents[1] / name
        if path.exists():
            for line in path.read_text().splitlines():
                key, _, rest = line.partition('=')
                if key.strip() == 'CLAW_BUNDLE_IDENTIFIER' and rest.strip():
                    value = rest.strip()
    return value


BUNDLE = _bundle_id()
DRIVER = r'''
#import <XCTest/XCTest.h>
#import <UIKit/UIKit.h>
@interface XCPointerEventPath : NSObject
- (instancetype)initForTouchAtPoint:(CGPoint)point offset:(double)offset;
- (void)moveToPoint:(CGPoint)point atOffset:(double)offset;
- (void)liftUpAtOffset:(double)offset;
@end
@interface XCSynthesizedEventRecord : NSObject
- (instancetype)initWithName:(NSString *)name interfaceOrientation:(NSInteger)orientation;
- (void)addPointerEventPath:(XCPointerEventPath *)path;
@end
@interface NSObject (TouchSynthesizer)
- (id)eventSynthesizer;
- (void)synthesizeEvent:(id)event completion:(void (^)(BOOL, NSError *))completion;
@end
@interface XCUIApplication (ProbeOrientation)
- (NSInteger)interfaceOrientation;
@end
@interface TouchProbe : XCTestCase @end
@implementation TouchProbe
- (CGPoint)physicalPoint:(NSArray *)point app:(XCUIApplication *)app {
    CGFloat x = [point[0] doubleValue], y = [point[1] doubleValue];
    if (app.interfaceOrientation == 3) { return CGPointMake(app.frame.size.height-y,x); }
    if (app.interfaceOrientation == 4) { return CGPointMake(y,app.frame.size.width-x); }
    return CGPointMake(x,y);
}
- (void)testDrive {
    self.continueAfterFailure = NO;
    NSString *directory = @"__WORK__";
    XCUIApplication *app = [[XCUIApplication alloc] initWithBundleIdentifier:@"__BUNDLE__"];
    NSUInteger previous = 0;
    CGRect frame = CGRectZero;
    for (int i=0; i<18000; i++) {
        NSData *data = [NSData dataWithContentsOfFile:[directory stringByAppendingPathComponent:@"command.json"]];
        NSDictionary *command = data ? [NSJSONSerialization JSONObjectWithData:data options:0 error:nil] : nil;
        NSUInteger seq = [command[@"seq"] unsignedIntegerValue];
        if (seq > previous) {
            previous = seq;
            NSString *verb = command[@"verb"];
            if ([verb isEqual:@"launch"]) {
                [XCUIDevice sharedDevice].orientation = UIDeviceOrientationLandscapeLeft;
                app.launchArguments = @[@"--mute", @"--menu-allow-live-input", @"--custom-checkpoint-check", @"--save-dir", [directory stringByAppendingPathComponent:@"saves"], @"--settings-dir", [directory stringByAppendingPathComponent:@"settings"]];
                app.launchEnvironment = @{@"CLAW_REAL_SPEED_LOG":directory, @"CLAW_REAL_SPEED_CONTROL":[directory stringByAppendingPathComponent:@"control.txt"]};
                [app launch];
            } else if ([verb isEqual:@"stop"]) { [app terminate]; }
            else if ([verb isEqual:@"key"]) {
                NSDictionary *keys = @{@38:XCUIKeyboardKeyUpArrow, @40:XCUIKeyboardKeyDownArrow, @13:XCUIKeyboardKeyReturn, @27:XCUIKeyboardKeyEscape, @88:@"x"};
                [app typeKey:keys[command[@"code"]] modifierFlags:0];
            } else if ([verb isEqual:@"toggle"]) {
                XCUIElement *toggle = app.switches[@"On-screen touch controls"];
                XCTAssertTrue([toggle waitForExistenceWithTimeout:5]);
                NSString *before = [toggle.value description];
                [[toggle coordinateWithNormalizedOffset:CGVectorMake(0.94,0.5)] tap];
                XCTAssertNotEqualObjects(before, [toggle.value description]);
            } else if ([verb isEqual:@"button"]) {
                XCUIElement *button = app.buttons[command[@"name"]];
                XCTAssertTrue([button waitForExistenceWithTimeout:5]); [button tap];
            } else if ([verb isEqual:@"shot"]) {
                [[app screenshot].PNGRepresentation writeToFile:[directory stringByAppendingPathComponent:command[@"name"]] atomically:YES];
            } else if ([verb isEqual:@"touch"]) {
                XCSynthesizedEventRecord *record = [[NSClassFromString(@"XCSynthesizedEventRecord") alloc] initWithName:@"Claw touch check" interfaceOrientation:[app interfaceOrientation]];
                for (NSArray *points in command[@"paths"]) {
                    NSArray *start = points[0];
                    XCPointerEventPath *path = [[NSClassFromString(@"XCPointerEventPath") alloc] initForTouchAtPoint:[self physicalPoint:start app:app] offset:start.count > 2 ? [start[2] doubleValue] : 0];
                    for (NSUInteger j=1;j<points.count;j++) {
                        NSArray *point = points[j];
                        [path moveToPoint:[self physicalPoint:point app:app] atOffset:[point[2] doubleValue]];
                    }
                    [path liftUpAtOffset:[command[@"duration"] doubleValue]];
                    [record addPointerEventPath:path];
                }
                XCTestExpectation *done = [self expectationWithDescription:@"simulator contacts delivered"];
                [[[XCUIDevice sharedDevice] eventSynthesizer] synthesizeEvent:record completion:^(BOOL ok, NSError *error) { XCTAssertTrue(ok, @"%@",error); [done fulfill]; }];
                [self waitForExpectationsWithTimeout:15 handler:nil];
            }
            if (![verb isEqual:@"stop"] && ![verb isEqual:@"quit"]) { frame = app.frame; }
            NSDictionary *ack = @{@"seq":@(seq), @"width":@(frame.size.width), @"height":@(frame.size.height)};
            [[NSJSONSerialization dataWithJSONObject:ack options:0 error:nil] writeToFile:[directory stringByAppendingPathComponent:@"ack.json"] atomically:YES];
            if ([verb isEqual:@"quit"]) { [app terminate]; return; }
        }
        [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.05]];
    }
    XCTFail(@"Driver timed out");
}
@end
'''


def run(*args, **kw):
    return subprocess.run(list(map(str, args)), check=True, **kw)


def wait_load():
    while float(subprocess.check_output(['sysctl', '-n', 'vm.loadavg']).split()[1]) >= 16:
        print('Waiting for load below 16', flush=True)
        time.sleep(30)


def project():
    """A standalone UI driver avoids changes to the app's generated project."""
    folder = WORK / 'TouchProbe.xcodeproj'
    folder.mkdir(parents=True, exist_ok=True)
    source = DRIVER.replace('__WORK__', str(WORK)).replace('__BUNDLE__', BUNDLE)
    (WORK / 'TouchProbe.m').write_text(source)
    def ident(n): return f'{n:024X}'
    objects = {}
    def add(n, value): objects[ident(n)] = value
    add(1, {'isa':'PBXProject','buildConfigurationList':ident(10),'compatibilityVersion':'Xcode 14.0','mainGroup':ident(2),'targets':[ident(3)],'projectDirPath':''})
    add(2, {'isa':'PBXGroup','children':[ident(4),ident(5)],'sourceTree':'<group>'})
    add(3, {'isa':'PBXNativeTarget','name':'TouchProbe','productName':'TouchProbe','productType':'com.apple.product-type.bundle.ui-testing','productReference':ident(5),'buildConfigurationList':ident(11),'buildPhases':[ident(6)],'dependencies':[]})
    add(4, {'isa':'PBXFileReference','path':'TouchProbe.m','sourceTree':'<group>','lastKnownFileType':'sourcecode.c.objc'})
    add(5, {'isa':'PBXFileReference','path':'TouchProbe.xctest','sourceTree':'BUILT_PRODUCTS_DIR','explicitFileType':'wrapper.cfbundle'})
    add(6, {'isa':'PBXSourcesBuildPhase','files':[ident(7)],'buildActionMask':2147483647})
    add(7, {'isa':'PBXBuildFile','fileRef':ident(4)})
    for n,c in [(10,12),(11,13)]: add(n, {'isa':'XCConfigurationList','buildConfigurations':[ident(c)],'defaultConfigurationName':'Release'})
    add(12, {'isa':'XCBuildConfiguration','name':'Release','buildSettings':{'SDKROOT':'iphoneos','IPHONEOS_DEPLOYMENT_TARGET':'17.0','CLANG_ENABLE_MODULES':'YES','CLANG_ENABLE_OBJC_ARC':'YES'}})
    add(13, {'isa':'XCBuildConfiguration','name':'Release','buildSettings':{'PRODUCT_BUNDLE_IDENTIFIER':'org.claw.TouchProbe','PRODUCT_NAME':'$(TARGET_NAME)','GENERATE_INFOPLIST_FILE':'YES','TARGETED_DEVICE_FAMILY':'2','CODE_SIGNING_ALLOWED':'NO'}})
    (folder/'project.pbxproj').write_bytes(plistlib.dumps({'archiveVersion':'1','objectVersion':'56','objects':objects,'rootObject':ident(1)}))
    schemes = folder/'xcshareddata/xcschemes';schemes.mkdir(parents=True,exist_ok=True)
    ref = f'<BuildableReference BuildableIdentifier="primary" BlueprintIdentifier="{ident(3)}" BuildableName="TouchProbe.xctest" BlueprintName="TouchProbe" ReferencedContainer="container:TouchProbe.xcodeproj"/>'
    (schemes/'TouchProbe.xcscheme').write_text(f'<Scheme version="1.3"><BuildAction><BuildActionEntries><BuildActionEntry buildForTesting="YES" buildForRunning="YES" buildForProfiling="NO" buildForArchiving="NO" buildForAnalyzing="YES">{ref}</BuildActionEntry></BuildActionEntries></BuildAction><TestAction buildConfiguration="Release"><Testables><TestableReference skipped="NO">{ref}</TestableReference></Testables></TestAction></Scheme>')
    return folder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-only', action='store_true')
    parser.add_argument('--skip-build', action='store_true')
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    derived = ROOT / os.environ.get('CLAW_DERIVED_DATA', 'work/MacCatalyst')
    if not args.skip_build:
        with (ROOT/'work/.claw-app-build.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX);wait_load()
            with (WORK/'sim-build.log').open('w') as log:
                run('xcodebuild','-project','Claw.xcodeproj','-scheme','Claw','-configuration','Release','-destination',f'platform=iOS Simulator,id={UDID}','-derivedDataPath',derived,'-jobs','1','ONLY_ACTIVE_ARCH=YES','CODE_SIGNING_ALLOWED=NO','build',stdout=log,stderr=subprocess.STDOUT)
    if args.build_only:return
    app = derived/'Build/Products/Release-iphonesimulator/Claw.app'
    subprocess.run(['xcrun','simctl','uninstall',UDID,BUNDLE],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    run('xcrun','simctl','install',UDID,app)
    for name in ['command.json','ack.json','live.json']:(WORK/name).unlink(missing_ok=True)
    (WORK/'control.txt').write_text('')
    folder = project()
    with (ROOT/'work/.claw-app-build.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX);wait_load()
        with (WORK/'driver-build.log').open('w') as log:
            run('xcodebuild','build-for-testing','-project',folder,'-scheme','TouchProbe','-configuration','Release','-destination',f'platform=iOS Simulator,id={UDID}','-derivedDataPath',derived,'-jobs','1','CODE_SIGNING_ALLOWED=NO',stdout=log,stderr=subprocess.STDOUT)
    log = (WORK/'driver.log').open('w')
    wait_load()
    driver = subprocess.Popen(['xcodebuild','test-without-building','-project',str(folder),'-scheme','TouchProbe','-configuration','Release','-destination',f'platform=iOS Simulator,id={UDID}','-derivedDataPath',str(derived),'CODE_SIGNING_ALLOWED=NO','-parallel-testing-enabled','NO'],stdout=log,stderr=subprocess.STDOUT)
    seq = 0
    def read(name='live.json'):
        try:return json.loads((WORK/name).read_text())
        except (ValueError,OSError):return {}
    def wait(predicate,timeout=45):
        until=time.monotonic()+timeout
        while time.monotonic()<until:
            if predicate():return
            if driver.poll() is not None:raise RuntimeError('XCTest driver exited: see driver.log')
            time.sleep(.05)
        raise RuntimeError('Timed out; see work/touch-overlay/live.json and driver.log')
    def command(verb, sample=None, **fields):
        nonlocal seq
        seq+=1
        temp=WORK/'command.tmp';temp.write_text(json.dumps(dict(seq=seq,verb=verb,**fields)));temp.replace(WORK/'command.json')
        def done():
            if sample is not None: sample(read())
            return read('ack.json').get('seq')==seq
        wait(done,120)
    result = dict(check='ipad-touch-overlay', status='fail', steps=[])
    def require(condition, message):
        if not condition:raise RuntimeError(message)
    def key(code, vk):
        # Menu navigation/remap is fixture setup. Gameplay assertions below
        # use only XCTest-delivered simulator touch contacts.
        for down in (1,0):
            frame=read().get('frame',0)
            with (WORK/'control.txt').open('a') as output:output.write(f'k {vk} {down}\n')
            wait(lambda:read().get('frame',0)>frame+2)
            time.sleep(.08)
        time.sleep(.2)
    def main_controls():
        for _ in range(4):key(82,38)
        key(40,13);key(81,40);key(40,13)
        wait(lambda:read().get('controls',{}).get('open'))
    def launch():
        wait_load()
        (WORK/'live.json').unlink(missing_ok=True)
        (WORK/'control.txt').write_text('')
        command('launch');wait(lambda:read().get('frame',0)>2)
    def mark(name, samples=None):
        result['steps'].append(dict(name=name, samples=samples or [], state=read()))
    try:
        launch()
        require(read()['touch_controls']==dict(enabled=False,visible=False),'fresh install overlay must be off')
        key(40,13);key(40,13);key(40,13)
        wait(lambda:read().get('state_vtable')=='0x50c264' and read().get('game_ms',0)>3000,90)
        require(not read()['touch_controls']['visible'],'overlay visible by default during gameplay')
        command('shot',name='fresh-install-off.png');mark('fresh-install-off-in-level-one')
        command('stop');launch()
        main_controls();command('toggle');command('button',name='Cancel')
        require(not read()['touch_controls']['enabled'],'Cancel changed saved setting')
        key(40,13);wait(lambda:read().get('controls',{}).get('open'))
        key(81,40);key(40,13);key(27,88)  # Rebind Hand Attack to X.
        command('toggle');command('button',name='Save')
        wait(lambda:read().get('touch_controls',{}).get('enabled'))
        require(read()['controls']['keys'][1]==88,'attack remapping not saved')
        mark('enabled-in-controls')
        command('stop');launch()
        require(read()['touch_controls']==dict(enabled=True,visible=False),'setting did not persist, or overlay covers menu')
        mark('persisted-after-relaunch')
        key(40,13);key(40,13);key(40,13)
        wait(lambda:read().get('state_vtable')=='0x50c264' and read().get('game_ms',0)>3000,90)
        wait(lambda:read().get('touch_controls',{}).get('visible'))
        command('shot',name='enabled-level-one.png')
        width,height=read('ack.json')['width'],read('ack.json')['height']
        unit=min(76,height/7);left=24;right=width-24;bottom=height-28
        points={
            'left':[left+unit/2,bottom-1.5*unit],
            'right':[left+2.5*unit,bottom-1.5*unit],
            'up':[left+1.5*unit,bottom-2.5*unit],
            'down':[left+1.5*unit,bottom-.5*unit],
            'jump':[right-unit/2,bottom-unit/2],
            'attack':[right-1.65*unit,bottom-1.1*unit],
            'fire':[right-unit/2,bottom-1.7*unit],
            'weapon':[right-1.65*unit,bottom-2.325*unit],
            'pause':[width/2,bottom-.325*unit]}
        def touch(name,paths,duration=.5):
            samples=[]
            def sample(live):
                samples.append({k:live.get(k) for k in ('frame','x','y','input_mask','weapons','touch_controls','checkpoint_chooser','state_vtable')})
            command('touch',paths=paths,duration=duration,sample=sample)
            wait(lambda:not read().get('weapons',{}).get('held_keys'))
            mark(name,samples);return samples
        def press(name,duration=.5):return touch(name,[[points[name]]],duration)
        start=read();moved=press('right',.7)
        require(any(s['x']>start['x'] for s in moved),'right touch did not move Claw')
        both=touch('move-and-jump',[[points['right']],[points['jump']]],.4)
        require(any((s['input_mask'] or 0)&0x2000000 and (s['input_mask'] or 0)&1 for s in both),'concurrent move/jump not delivered')
        require(any(s['y']<both[0]['y'] for s in both),'jump touch did not jump')
        time.sleep(.8)
        for name,mask in [('up',0x4000000),('down',0x8000000)]:
            samples=press(name,.2)
            require(any((s['input_mask'] or 0)&mask for s in samples),name+' touch not polled')
        time.sleep(.8)  # Let the original duck-to-stand animation finish.
        attack=touch('move-and-attack',[[points['right']],[points['attack']+[.15]]],.5)
        require(any((s['input_mask'] or 0)&2 and s['weapons'].get('attack_active') for s in attack),'remapped touch attack did not attack')
        time.sleep(.6)
        before_fire=sum(read()['weapons']['projectile_invokes'].values())
        fire=press('fire',.3)
        require(any((s['input_mask'] or 0)&4 for s in fire),'fire touch not polled')
        require(any(sum(s['weapons']['projectile_invokes'].values())>before_fire for s in fire),'fire touch did not produce a projectile')
        time.sleep(.6)
        before=read()['weapons'];weapon=press('weapon',.2)
        require(any(s['weapons'].get('weapon') != before.get('weapon') for s in weapon),'weapon touch did not switch weapon')
        slide=touch('slide-directions',[[points['right'],points['left']+[.6]]],.9)
        require(any((s['input_mask'] or 0)&0x2000000 for s in slide) and any((s['input_mask'] or 0)&0x1000000 for s in slide),'direction sliding lost a zone')
        press('pause',.2)
        wait(lambda:not read()['touch_controls']['visible'])
        require(read().get('menu_page') is not None,'pause did not open menu')
        key(41,27);wait(lambda:read()['touch_controls']['visible'])
        touch('three-finger-checkpoint',[[points['right']],[points['jump']],[[width/2,height/2]]],.12)
        wait(lambda:read().get('checkpoint_chooser',{}).get('visible'))
        require(not read()['touch_controls']['visible'],'overlay covers checkpoint panel')
        command('shot',name='three-finger-checkpoint.png')
        command('button',name='Cancel');wait(lambda:read()['touch_controls']['visible'])
        key(41,27);key(81,40);key(81,40);key(40,13);key(40,13)
        wait(lambda:read().get('controls',{}).get('open'))
        command('toggle');command('button',name='Save')
        wait(lambda:not read()['touch_controls']['enabled'])
        for _ in range(4):
            if read().get('state_vtable')=='0x50c264':break
            key(41,27)
        wait(lambda:read().get('state_vtable')=='0x50c264')
        require(not read()['touch_controls']['visible'],'disabled overlay still visible')
        mark('disabled-again-during-gameplay')
        result['status']='pass'
    except Exception as error:
        result['error']=str(error)
        raise
    finally:
        (WORK/'check.json').write_text(json.dumps(result,indent=2))
        if driver.poll() is None:
            command('quit')
            try:driver.wait(timeout=30)
            except subprocess.TimeoutExpired:
                # Xcode 27 can linger collecting results after XCTest finishes.
                # Only stop collection after the suite itself reports success;
                # the Python gameplay assertions above remain authoritative.
                require("Test Suite 'All tests' passed" in (WORK/'driver.log').read_text(), 'XCTest did not finish')
                driver.terminate();driver.wait(timeout=15)
        if driver.returncode and result['status']=='pass':
            require("Test Suite 'All tests' passed" in (WORK/'driver.log').read_text(), 'XCTest driver failed')
    print(json.dumps(dict(check=result['check'],status=result['status'],steps=[s['name'] for s in result['steps']])))



if __name__ == '__main__':main()
