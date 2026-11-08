"""Level 2 static call closure, following objects created at run time through their vtables.

Roots: every Level 2 class logic callback (census.json), the state bindings registered after each class in
Sources/LogicStateRegistry.cpp, classes created by logic name, and the player vtable. From each reached
game function we follow direct calls, code-address immediates, and every data table a function references
(vtables written by constructors, state and dispatch tables): all consecutive code pointers from the
referenced address up to the next address some other code references. Platform ranges (C runtime and MFC,
0x4a1300-0x4b3400 and >= 0x4f0000) and Windows imports are excluded; menu native-reuse entries stop the walk.

Owner rule (the same as census.py and make status): "admitted" means claimed in a canonical family's
`owned` list whose gate evidence is admitted with no admission errors; "native" means a menu native-reuse
address accepted in work/menu-map/final-reviewed-batches.json; everything else is unowned. Unowned
addresses already assigned in the queue are "pending: <task id>": a finished task
without current admission remains an unresolved owner.
Writes work/level-two-map/closure.json and ownership.json; annotates trace.json with owner status.
Run with work/test-env/bin/python -m Tests.NativeLevelTwo.plan.
"""
from Tests.NativeLevels.storage import read_trace, write_trace, fingerprint
import argparse, hashlib, json, re, struct, sys, zlib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.claw import index, manifest, progress_page  # noqa: E402
from Tests.clawparity import build_inputs  # noqa: E402
from Tests.clawparity.program import claw  # noqa: E402

GAME = progress_page.GAME_RANGES
HEX = re.compile(r"0x([0-9a-f]{6})\b")
OUT = ROOT / "work/level-two-map"
PLAYER_VTABLE = 0x50C264  # the play state object the Level 2 trace calls "player"
APP_VTABLE = 0x50BEE4  # the application object: frame tick and command handler (respawn, level end)
# Admitted functions where the walk would leave Level 2 play: the application state factory builds every
# other application state (menus, booty, credits); what follows level completion is a separate task.
# Application command handler 0x426e30 (a switch over every game command) is not walked whole: only the case
# handlers of commands that reached code posts. Mapping read from the handler's cases. 0x800e (gem pickup,
# level complete) is the boundary; 0x8005, 0x8006 and 0x8080 leave play through the state factory (STOP).
APP_FRAME = 0x428B60  # application frame tick, executed in every traced phase
COMMANDS = {
    0x8005: [0x429B70, 0x429E10], 0x8006: [], 0x8007: [0x42A570], 0x8008: [0x42ABB0], 0x800E: [], 0x803A: [0x42A630, 0x46BE40, 0x429E10],
    0x805C: [0x42A630], 0x8075: [0x429BE0, 0x429E10], 0x8080: [], 0x809F: [0x429B70, 0x429E10],
}
POST = re.compile(r"(?:push|mov [^,]+,) 0x(80[0-9a-f]{2})$")
STOP = {0x428C40: "application state factory: leaves Level 2 play for other application states"}


def in_game(a):
    return any(lo <= a < hi for lo, hi in GAME)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--static-only', action='store_true', help='Preview only; not the final census')
    args = parser.parse_args()
    functions = index.functions()
    program = claw()
    data = [s for s in program.sections if s.name in (".rdata", ".data")]

    def dword(a):
        for s in data:
            if s.address <= a and a + 4 <= s.address + len(s.data):
                return struct.unpack_from("<I", s.data, a - s.address)[0]
        return None

    def is_data(a):
        return any(s.address <= a < s.address + s.size for s in data)

    asm = {}
    for a in functions:
        path = ROOT / f"work/corpus/asm/{a:08x}.asm"
        asm[a] = path.read_text().splitlines() if path.exists() else []

    # Every data address referenced by any code: table boundaries.
    data_refs = defaultdict(set)
    for a, lines in asm.items():
        for line in lines:
            parts = line.split("  ", 1)
            if len(parts) == 2:
                for m in HEX.findall(parts[1]):
                    v = int(m, 16)
                    if is_data(v):
                        data_refs[v].add(a)
    boundaries = set(data_refs)

    table_cache = {}

    def table(start):
        if start not in table_cache:
            out, at = [], start
            while len(out) < 512:
                if at != start and at in boundaries:
                    break
                v = dword(at)
                if v is None or v not in functions:
                    break
                out.append(v)
                at += 4
            table_cache[start] = out
        return table_cache[start]

    tables_used = {}

    def refs(a):
        out = {int(c, 16) for c in functions[a]["callees"]}
        for line in asm[a]:
            parts = line.split("  ", 1)
            if len(parts) != 2:
                continue
            for m in HEX.findall(parts[1]):
                v = int(m, 16)
                if v in functions:
                    out.add(v)
                elif is_data(v):
                    t = table(v)
                    if t:
                        tables_used.setdefault(v, (a, len(t)))
                        out.update(t)
        return {x for x in out if x in functions and x != a}

    manifests = manifest.load_all()
    claims = defaultdict(list)
    for fam, spec in manifests.items():
        for e in spec.get("owned", []):
            claims[int(e["address"] if isinstance(e, dict) else e, 16)].append(fam)
    cache = {}

    def admitted(fam):
        if fam not in cache:
            spec = manifests[fam]
            gate = spec.get("evidence", {}).get("gate") or {}
            cache[fam] = (spec.get("abi") == "canonical" and spec["evidence"]["level"] == "admitted"
                          and gate.get("status") == "admitted" and not build_inputs.admission_errors(spec))
        return cache[fam]

    native_reuse = {int(a, 16) for a in json.loads((ROOT / "work/menu-map/final-reviewed-batches.json").read_text())["native_reuse_addresses"]}
    legacy_owner = progress_page.ownership(manifests)

    # The retained trace also covers startup and teardown. Preserve its exact
    # ownership classification separately from the static gameplay closure.
    from Tests.NativeLevelOne.plan import census as trace_census
    if args.static_only:
        ownership = dict(rows=[],counts={})
    else:
        ownership = trace_census(OUT / 'trace.json')
        trace_path = OUT / 'trace.json'
        trace_report = read_trace(trace_path)
        by_address = {r['address']:r for r in ownership['rows']}
        for entry in trace_report['game_functions']:
            row = by_address.get(entry['address'])
            if row:
                entry.update(owner=row['owner'], owner_status=row['classification'])
        trace_report['ownership_counts'] = ownership['counts']
        write_trace(trace_path, trace_report)
        ownership['trace_sha256'] = fingerprint(trace_path)
        (OUT / 'ownership.json').write_text(json.dumps(ownership, indent=2)+'\n')
        traced = {int(r['address'],16): r for r in ownership['rows']}
        native_reuse.update(a for a,r in traced.items() if r['classification']=='native-reuse')

    queue = json.loads((ROOT / "tools/queue.json").read_text())
    pending = {}
    for t in queue["tasks"]:
        if t.get("addresses"):
            for x in t.get("addresses", []):
                pending.setdefault(int(x, 16), t["id"])

    from collections import Counter
    # Read the actual Level 2 world records, then cross-check the existing
    # native inventory used by the Level 1 closure method.
    world_path = ROOT/'Original/retail-assets/LEVEL2/WORLDS/WORLD.WWD'
    packed = world_path.read_bytes()
    header = struct.unpack_from('<I', packed)[0]
    assert header == 1524
    world = packed[:header]+zlib.decompress(packed[header:]) if struct.unpack_from('<I',packed,8)[0]&2 else packed
    plane_count = struct.unpack_from('<I',world,0x2dc)[0]
    plane_offset = struct.unpack_from('<I',world,0x2e0)[0]
    placed = Counter()
    world_objects = []
    for pi in range(plane_count):
        plane = plane_offset+pi*160
        count = struct.unpack_from('<I',world,plane+0x80)[0]
        offset = struct.unpack_from('<I',world,plane+0x8c)[0]
        for _ in range(count):
            lengths = struct.unpack_from('<4I',world,offset+4)
            name_len, logic_len, image_len, animation_len = lengths
            logic = world[offset+284+name_len:offset+284+name_len+logic_len].split(b'\0')[0].decode('ascii')
            x,y = struct.unpack_from('<2i',world,offset+20)
            if logic:
                placed[logic] += 1
                world_objects.append(dict(plane=pi,logic=logic,x=x,y=y))
            offset += 284+sum(lengths)
    level = json.loads((ROOT / 'work/coordinator/all-levels/native.json').read_text())[1]
    assert level['level'] == 2
    assert placed == Counter(n for p in level['planes'] for n in p['logic'])
    (OUT/'world-objects.json').write_text(json.dumps(dict(world_sha256=hashlib.sha256(packed).hexdigest(), objects=world_objects),indent=2)+'\n')
    placed.setdefault('CaptainClaw', 0)
    names = progress_page.class_addresses()
    src = (ROOT / "Sources/LogicStateRegistry.cpp").read_text()
    body = src[src.index("const Binding bootstrap[] = {"):]
    body = body[:body.index("};")]
    states, current = defaultdict(list), None
    for kind, _t, _l, fn, _f, nm in re.findall(r'\{(0x[0-9a-f]+), (0x[0-9a-f]+), (0x[0-9a-f]+), (0x[0-9a-f]+), (0x[0-9a-f]+), "([^"]*)"\}', body):
        if kind == "0x0":
            current = nm
        else:
            states[current].append(int(fn, 16))

    roots = {}
    unknown_classes = sorted(n for n in placed if n not in names)
    if unknown_classes:
        raise ValueError(f'Placed classes without callbacks: {unknown_classes}')
    for name in placed:
        roots.setdefault(names[name], f"class {name}")
        for s in states.get(name, []):
            roots.setdefault(s, f"state {name}")
    for v in table(PLAYER_VTABLE):
        roots.setdefault(v, "player vtable 0x50c264")
    roots.setdefault(APP_FRAME, "application frame tick")
    # Command 0x8084 (restart from checkpoint) is not posted by any code immediate (menu or accelerator resource).
    roots.setdefault(0x46C110, "command 0x8084 handler")
    # Dynamic complement: every game function the original executed during traced Level 2 play
    # (work/level-two-map/trace.json level-two-* phases), which covers engine objects built by level loading.
    trace = dict(game_functions=[]) if args.static_only else read_trace(OUT / 'trace.json')
    for e in trace["game_functions"]:
        if e["entry_kind"] == "function" and any(p.startswith("level-two-") for p in e["phases"]):
            roots.setdefault(int(e["address"], 16), "traced in Level 2 play")

    edges = {}
    parent, seen, stack = {}, set(), list(roots)
    classes_reached = set()
    posted = defaultdict(set)
    while stack:
        a = stack.pop()
        if a in seen:
            continue
        seen.add(a)
        if not in_game(a) or a in native_reuse or a in STOP:
            continue
        command_edges = set()
        for line in asm[a]:
            m = POST.search(line)
            if m:
                cmd = int(m.group(1), 16)
                posted[cmd].add(a)
                for h in COMMANDS.get(cmd, []):
                    command_edges.add(h)
                    if h not in seen:
                        roots.setdefault(h, f"command {cmd:#x} handler")
                        parent.setdefault(h, a)
                        stack.append(h)
        edges[a] = refs(a) | command_edges
        for x in edges[a]:
            if x not in seen:
                parent.setdefault(x, a)
                stack.append(x)
        for text in functions[a].get("strings", []):
            r = names.get(text)
            if r is not None and text not in classes_reached:
                classes_reached.add(text)
                edges[a].add(r)
                parent.setdefault(r, a)
                stack.append(r)
                for state in states.get(text, []):
                    edges[a].add(state)
                    roots.setdefault(state, f"state of created class {text}")
                    parent.setdefault(state, a)
                    stack.append(state)

    def status(a):
        fams = claims.get(a, [])
        adm = [f for f in fams if admitted(f)]
        if adm:
            return "admitted", adm[0]
        if a in native_reuse:
            return "native-reuse", None
        if a in pending:
            return f"pending: {pending[a]}", fams[0] if fams else legacy_owner.get(a)
        return "unowned", fams[0] if fams else legacy_owner.get(a)

    rows = []
    for a in sorted(seen):
        if not in_game(a):
            continue
        st, owner = status(a)
        f = functions[a]
        ind = len(index.indirect_call_sites(a))
        rows.append(dict(address=f"{a:#x}", name=index.name(a), status=st, owner=owner, size=f.get("size"),
                         root=roots.get(a), reached_from=f"{parent[a]:#x}" if a in parent else None,
                         indirect_calls=ind))
    from collections import Counter
    tot = Counter("pending" if r["status"].startswith("pending") else r["status"] for r in rows)
    result = dict(schema=1, level=2, static_only=args.static_only, method=__doc__.strip(),
                  world_source=str(world_path.relative_to(ROOT)), world_sha256=hashlib.sha256(packed).hexdigest(),
                  inputs_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
                      ('work/coordinator/all-levels/native.json','Sources/LogicStateRegistry.cpp')},
                  totals=dict(reachable=len(rows), **tot),
                  tables_followed=len(tables_used),
                  stop={f"{k:#x}": v for k, v in STOP.items()},
                  commands_posted={f"{k:#x}": sorted(f"{x:#x}" for x in v) for k, v in sorted(posted.items())},
                  commands_unmapped=sorted(f"{k:#x}" for k in posted if k not in COMMANDS),
                  roots=len(roots), pending_by_task=dict(Counter(r["status"][9:] for r in rows if r["status"].startswith("pending"))),
                  functions=rows,
                  placed_classes=[dict(name=n, placed=c, callback=hex(names[n]), states=[hex(a) for a in states[n]]) for n,c in sorted(placed.items())],
                  created_classes=sorted(classes_reached),
                  tables=[dict(address=hex(t), reached_from=hex(v[0]), entries=[hex(a) for a in table(t)]) for t,v in sorted(tables_used.items())],
                  edges={hex(a):[hex(x) for x in sorted(xs) if in_game(x)] for a,xs in sorted(edges.items())},
                  trace_owner_counts=ownership['counts'],
                  trace_sha256=None if args.static_only else fingerprint(OUT/'trace.json'))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "closure.json").write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({"command": "level-two-closure", "totals": result["totals"], "tables": len(tables_used), "status": "pass"}))


if __name__ == "__main__":
    main()
