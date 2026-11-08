"""Resolve ownership without silently shrinking a whole original function.

Explicit body_ranges describe byte ownership, not guest-exception admission. Original
bytes always come from the hash-checking loader; corpus range starts are decode
anchors, never a substitute for checking the bytes being claimed.
"""
import hashlib
import re

from . import index
from .paths import ORIGINAL_SHA256
from Tests.clawparity import program as programs

ADDRESS = re.compile(r"0x[0-9a-f]{6,8}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def _address(value):
    if not isinstance(value, str) or not ADDRESS.fullmatch(value):
        raise ValueError("address must be a lowercase 6-8 digit hex string")
    return int(value, 16)


def _corpus_number(value):
    return int(value, 16) if isinstance(value, str) else value


def _corpus_ranges(function):
    return [tuple(_corpus_number(v) for v in pair) for pair in function.get("ranges", [])]


def _overlap(a, b):
    return max(a[0], b[0]) < min(a[1], b[1])


def _covers(ranges, low, high):
    cursor = low
    for first, last in sorted(ranges):
        if first > cursor:
            break
        cursor = max(cursor, last)
        if cursor >= high:
            return True
    return False


class _Reference:
    def __init__(self, corpus):
        # claw() checks the full file before parsing any sections. Do not accept
        # a caller-supplied program or an alternative expected hash here.
        self.program = programs.claw()
        if self.program.sha256 != ORIGINAL_SHA256:
            raise ValueError("original program SHA-256 is not the pinned reference")
        self.anchors = sorted({a for root, f in corpus.items()
                               for a in [root, *(lo for lo, _ in _corpus_ranges(f))]})
        self.decoded = {}

    def check(self, low, high, digest):
        p = self.program
        if not p.text[0] <= low < high <= p.text[1]:
            raise ValueError("body range must lie in original executable text")
        section = next((s for s in p.sections
                        if s.address <= low < high <= s.address + len(s.data)), None)
        if section is None:
            raise ValueError("body range is not backed by one original section")
        raw = section.data[low - section.address:high - section.address]
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("body range SHA-256 mismatch")
        anchors = [a for a in self.anchors if max(p.text[0], section.address) <= a <= low]
        if not anchors:
            raise ValueError("body range has no original corpus instruction anchor")
        anchor = anchors[-1]
        # Decode from an independent anchor, not low: x86 often decodes the
        # middle of an instruction as a different, superficially valid stream.
        key = (anchor, high)
        if key not in self.decoded:
            from capstone import Cs, CS_ARCH_X86, CS_MODE_32
            stop = min(p.text[1], section.address + len(section.data), high + 15)
            data = section.data[anchor - section.address:stop - section.address]
            boundaries, cursor = {anchor}, anchor
            for instruction in Cs(CS_ARCH_X86, CS_MODE_32).disasm(data, anchor):
                if instruction.address != cursor:
                    break
                cursor += instruction.size
                boundaries.add(cursor)
                if cursor >= high:
                    break
            self.decoded[key] = boundaries
        boundaries = self.decoded[key]
        if low not in boundaries or high not in boundaries:
            raise ValueError("body range cuts an instruction or crosses undecodable bytes")


def _body_ranges(entry, corpus, reference):
    root = _address(entry.get("address"))
    if "interval_end" in entry:
        raise ValueError("body_ranges and inline interval_end are mutually exclusive")
    rows = entry["body_ranges"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("body_ranges must be a nonempty list")
    ranges = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"start", "end", "sha256"}:
            raise ValueError("body range requires exactly start, end and sha256")
        low, high = _address(row["start"]), _address(row["end"])
        if low >= high:
            raise ValueError("body range must have start < end")
        if not isinstance(row["sha256"], str) or not DIGEST.fullmatch(row["sha256"]):
            raise ValueError("body range sha256 must be a lowercase SHA-256 digest")
        if ranges and low < ranges[-1][1]:
            raise ValueError("body ranges must be sorted and nonoverlapping")
        ranges.append((low, high))
    if not any(lo <= root < hi for lo, hi in ranges):
        raise ValueError("body ranges do not include the public root")
    if root not in corpus:
        raise ValueError("body root is not an original corpus function entry")
    for row, (low, high) in zip(rows, ranges):
        reference.check(low, high, row["sha256"])
    # A range could contain a claimed root in the middle of an instruction.
    containing = next((lo, hi) for lo, hi in ranges if lo <= root < hi)
    if root != containing[0]:
        p = reference.program
        s = next(s for s in p.sections if s.address <= root < s.address + len(s.data))
        reference.check(containing[0], root,
                        hashlib.sha256(s.data[containing[0] - s.address:root - s.address]).hexdigest())
    if any(not _covers(ranges, lo, hi) for lo, hi in _corpus_ranges(corpus[root])):
        raise ValueError("body ranges omit bytes already owned by the corpus root")
    return ranges


def resolve_owned_ranges(spec, *, corpus=None):
    """Return {root: [(start, end), ...]}, or raise ValueError on bad ownership.

    Old interval_end and corpus-derived ranges retain their existing meaning.
    Unknown old roots still have no measured range. New whole-body declarations
    are strict, pinned, and cannot overlap another root in the same family.
    The optional corpus argument supplies index data, never original bytes.
    """
    if spec.get("program") == "claw-v1.3":
        from Tests.clawparity.profiles import owned_ranges
        return owned_ranges(spec)
    entries = spec.get("owned", [])
    if not isinstance(entries, list):
        raise ValueError("owned must be a list")
    explicit = any(isinstance(e, dict) and "body_ranges" in e for e in entries)
    if explicit and (spec.get("abi") != "canonical" or spec.get("program", "claw-v1.0") != "claw-v1.0"):
        raise ValueError("body_ranges require the canonical pinned original program")
    needs_corpus = any("interval_end" not in e for e in entries if isinstance(e, dict))
    corpus = index.functions() if corpus is None and needs_corpus else (corpus or {})
    reference = _Reference(corpus) if explicit else None
    result = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("owned entry must be an object")
        root = _address(entry.get("address"))
        if root in result:
            raise ValueError(f"duplicate owned root {root:#x}")
        if "body_ranges" in entry:
            ranges = _body_ranges(entry, corpus, reference)
        elif "interval_end" in entry:
            end = _address(entry["interval_end"])
            if end <= root:
                raise ValueError("inline interval_end must follow its root")
            ranges = [(root, end)]
        else:
            ranges = _corpus_ranges(corpus.get(root, {}))
        if explicit:
            for other, prior in result.items():
                if any(_overlap(a, b) for a in ranges for b in prior):
                    raise ValueError(f"owned bodies {other:#x} and {root:#x} overlap")
        result[root] = ranges
    return result


def body_range_errors(spec):
    """No new binary/index requirement for manifests without body_ranges."""
    entries = spec.get("owned", [])
    # The schema reports malformed legacy ownership containers; this helper
    # only adds semantic checks for the explicit extension.
    if not isinstance(entries, list) or not any(isinstance(e, dict) and "body_ranges" in e for e in entries):
        return []
    try:
        resolve_owned_ranges(spec)
    except (ValueError, OSError, ImportError) as error:
        return [f"{spec.get('id', '?')}: invalid whole-body ownership: {error}"]
    return []


def canonical_overlap_errors(manifests, *, corpus=None):
    """Check numeric roots and every resolved interval across canonical families.

    Legacy overlaps remain outside this policy. A missing old corpus root does
    not invent a byte range, but its root address still cannot be claimed twice.
    """
    specs = manifests.values() if isinstance(manifests, dict) else manifests
    claims, roots, errors = {}, {}, []
    for spec in specs:
        if spec.get("abi") != "canonical":
            continue
        family = spec.get("id", "?")
        profile = spec.get("program", "claw-v1.0")
        profile_claims = claims.setdefault(profile, [])
        try:
            resolved = resolve_owned_ranges(spec, corpus=corpus)
        except (ValueError, OSError, ImportError) as error:
            errors.append(f"{family}: cannot check ownership overlap: {error}")
            continue
        for root, ranges in resolved.items():
            key = (profile, root)
            if key in roots and roots[key] != family:
                errors.append(f"canonical root {root:#x} is owned by both {roots[key]} and {family}")
            roots[key] = family
            for low, high in ranges:
                for old_low, old_high, owner, old_root in profile_claims:
                    if owner != family and _overlap((low, high), (old_low, old_high)):
                        errors.append(f"canonical bodies overlap: {owner}:{old_root:#x} and {family}:{root:#x} "
                                      f"at [{max(low, old_low):#x}, {min(high, old_high):#x})")
                profile_claims.append((low, high, family, root))
    return errors
