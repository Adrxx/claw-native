# Original Gabriel boss core

The first bounded `GabrielRuntime` handoff contains the complete original
Gabriel boss callback, constructor, eleven registered specialized state bodies,
all their specialized entries, hit/death/reset/destruction, and the original
inline bomb-target helper446130. It preserves the cannon/bomb facades and class
selectors with explicit constructor/state dependencies. Their remaining bodies
are listed below; this handoff does not claim the complete three-actor arena.

The unchanged oracle EXE SHA256 is
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Retail REZ SHA256 is
`b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`.
Private Ghidra output/logs and source-derived record/vtable/literal JSON are in
`work/gabriel-agent/`. Every implemented entry was boundary-verified. The
specialized physics helper is compared directly against its inline original
instructions, rather than assumed equal to the superficially similar420dd0.

## Retail identity and host recipe

| Original registration | Literal | Callback | Flags | Private bytes(hex) | Vtable |
| --- | --- | --- | --- | --- | --- |
| Gabriel, ordinal71 |522b08|443290|1|538|50de1c|
| GabrielCannon, ordinal70 |522b10|446550|0|98|50df44|
| GabrielBomb, ordinal72 |522afc|4459d0|0|198|50ded4|

All14 worlds contain34,784 records. Only Level8 has these static actors:
Gabriel row1511,id2618,(43223,5068,2000),imageLEVEL_GABRIEL; cannon
row1293,id2698,(43203,5184,1000),imageLEVEL_GABRIELCANNON. No world has a static
GabrielBomb record; its source factory election is dynamic. The retail fixture
selects the actual Gabriel row and flag1, not the first family row. The
fingerprinted resources contain42 boss PIDs/18 boss ANI groups,27 cannon
PIDs/5 cannon ANIs,19 bomb PIDs/4 bomb ANIs. The boss fixture consumes all its
PIDs/ANIs plusGAME_NULL; cannon/bomb resources are inventoried for the next
closure, rather than claimed as executed actor histories here.

The C11 API accepts original function, raw ECX receiver, actual stack arguments,
`ClawGabrielContext`, and a rich service receiving12 raw words and optional
verified literal name. Facades are cdecl(receiver0,[actor]). Constructors use
ECX private,[actor]; selectors use ECX private,[state];444120 deleting destructor
uses[mode];446130 uses[horizontal displacement]. Other owned entries take no
arguments. Names are transport metadata, not replacements for pointer identity.
`claw_gabriel_function` exposes only45/9/16 callable slots; adjacent doubles and
RTTI words are not methods. Support/completion differs from meaningful source
EAX. Unknown entry returns0; fault1 missing span/service,2 unsafe arithmetic,
3 invalid/bounded ABI. Clear a previous fault before an independent call.

Borrow `ClawRauxGlobals` for actual CBoss aliases/scaling. Direct raw53774c is
Gabriel private, distinct from5349dc generic boss actor. Constructor publishes
53774c; destructor clears it. Cannon signals use private518/51c/534, completion
uses520, thug-count524 and cannon-hit-count514. Source class arrays are537728
boss,537758 bomb,537788 cannon; global name dictionary/ID array537668/537698.
Use full frozen registry boot identities, not fresh shared-only IDs. Absolute
537210 tick and5430c4 animation delta remain distinct.532c10 is master volume.

The source actor is1b4 bytes/109 words, boss private538/334 words, primary
logic174/93 words. The native ANI adapter pads locally to128 words and commits
only109; it does not require an extra actor allocation tail. Frozen Human/Common
portable services in the differential bridge still use their declared128-word
local views; the large oracle fixture preserves/compares those surrounding words.
The separate exact-allocation test allocates actor109/private334/logic93 as
individual objects and tests whole specialized ctor→20 nativeANI updates→delete
under ASAN/UBSAN, with an explicit inherited-constructor/resource transport.

## Recovered core

Gabriel443290 is the complete180-byte facade. It stores1000 before malloc538,
constructs443ab0, invokes virtual10, then publishes primary18.29/30 elect20/1c;
1000 skips; other modes elect original cdecl4dc870(private). Null allocation
faults after the original prefix. Cannon/bomb facades follow the same complete
original sequencing with98/198 allocation and exact respective constructors.

Constructor443ab0 is1640 bytes. It composes CBoss40e0d0/Human, zeroes4dc..508,
selects50de1c, publishes53774c, binds source images and sixteen separate ANI
getters with individualGAME_NULL fallback. Sound lookup order, actor masks,
relative/image rectangles, range stores3000/2000, Y-32 ground placement, scaled
health100, integer target X-10/X-160, targetY5234 and startup/reset words are
source-derived. Unnamed fields preserve heap contents.

The eleven class overrides are STARTUP4441b0,IDLE4442c0,
MULTIBOMBATTACK4445d0,THUGATTACK1 444760,CANNONATTACK444960,
CANNONHIT444b70,BLOCKED444d00,DEADACT1 445090,DEADACT2 4455b0,
DEADACT3 445660,DEADACT4 445720. Selector4433b0 preserves double lookup,
cache/error/default writes, and CBoss fallback. Specialized entries444140,
4441f0,444330,4444d0,4446f0,444850,444aa0,444c20,444f80,4452d0,445600,
4456c0,reset445810 and destructor444120→445950 are complete.

The attack source retains signed CRT remainders, exact integer wrapping, marker
image401, temporary latches and callback order. MULTIBOMB excludes one of four
125-unit velocity slots and invokes each real child callback before446130.
RedTailPirate creation is null-checked and emits483e40; bomb creation's original
null prefix dereferences without such a check. Cannon requests change518;
startup/reset534 is cleared by the cannon, represented explicitly by the
fixture's source signal, not an inferred timer.

Hit444d90 reads actor74, player-privatee8 serial, original current-state strings,
and immunity clocks. Type40 enters cannon-hit directly; other types preserve
blocked/death-state exclusion and500ms gate. Cannon hit increments514; its
completed state subtracts20 and the fifth hit forces health0/death. Ordinary
attack/projectile flags and particle helper440e20 retain source calls.

The inline4452d0/446130 physics has two measured differences from420dd0:
unary-negated Z preserves signed zero, and the near-zero-acceleration Manhattan
sum is(|dx|+|dz|)+|dy|. Disassembly at4454d1..4454f1 establishes that order.
Shared physics supplies the common velocity formula; the original inline
threshold and sum order are preserved separately, including zero-distance
behavior.1,000 directed/generated finite original comparisons cover both
helpers, all acceleration axes, zero/signed-zero and varied targets. This is
finite numeric evidence, not a claim for arbitrary NaN/invalid machine state.

Death retains the actual four ANI phases,4000ms source deadline and100ms facing
toggle. It waits for speech predicate48cf90, uses an explicit ground signal,
and only after real completion/positive player health calls420590 and40e5c0,
sets520 and bit4 of the original bitset.420590 sets player primary5010; it does
not bypass the later player/controller flow. Gem creation delegates frozen
EndLevelGemRuntime. Audio405f60, speech predicate, scene creation, secondary
binders, collision, physical allocation/free and resource dictionary remain
named transports. Metadata uses declared empty secondary/core-registration
profile, not full WinMain evidence.

## Verification and remaining closure

Run `work/test-env/bin/python Tests/compare_gabriel_runtime.py`, then
`zsh work/gabriel-agent/run-sanitizers.sh`. The oracle compares complete512KiB
raw heap plus192KiB image/global region, ordered full-buffer hashes at services,
meaningful facade/constructor/destructor EAX, and RNG/query consumption.

Final core suite passes6,028 complete normal original calls,7,958 ordered
complete-buffer events,4,529 original instruction addresses and two original
unsafe prefixes. It includes six120-frame actual boss/FSM histories and four
retained five-hit→80/60/40/20/0 health→real death ANIs→player5010/gem request→
cleanup/delete histories, with explicit terminal assertions. The ground signal,
cleared hit-contact pointer and cannon-ready signal are declared fixture services.
Physical palette pixels/renderer, full Level8 arena completion, device acceptance
and full-game behavior identity remain separate. Exact C11/Swift and optimized
C++Werror checks pass; sanitizer replay counts are in the private log.

Remaining child closure is explicit: Cannon constructor446a70/base414030,
class fallback4141f0 and states/helpers446c20/446ca0/446d70/446e10/446ef0 plus
base4145b0/414640; Bomb constructor445ef0, states446340/4463f0/446490 and inherited
4084b0/408580/408860/408870/408510/432550/432560. Their source bodies have been
traced privately; existing frozen PlayerProjectile/Bullet services should supply
actual inherited bodies where supported. No substitute pickup/projectile/arena
behavior is installed. This module's exact child facades/selectors require those
original-address services to complete their paths. RedTailPirate483e40 and
physical creator/lifecycle transport also remain explicit.

Final sanitizer corpus passes182 original-matched replays/898 ordered full-buffer
snapshots. The exact-allocation actor/private/logic smoke passes ASAN/UBSAN.
Stable source-derived integration metadata is `work/gabriel-agent/integration.json`.
