"""Pinned v1.3 loader, imported only when that profile is selected."""
import hashlib

from .program import ROOT, Program

CLAW_V13_WRAPPER = ROOT / "Original" / "claw-rip" / "files" / "App_EXE" / "CLAW.EXE"
CLAW_V13_WRAPPER_SHA256 = "5130d7d951e4a350fc19fe3134aa447a17c3e220ae49e7834d06ec79724fa0c0"
CLAW_V13_SHA256 = "8f5069541a1c7d3f62896fb935ba591efa6fbfa4450798b96fe6f48f9cf396a0"


def claw_v13():
    """The pinned game in the pinned launcher, EXE/101/1033; never the launcher itself.

    Extract in memory so no unverified or stale work/ copy can become the oracle.
    Like v1.0, startup runs only the original CRT floating-point precision setup,
    not WinMain, static constructors, or game initialization.
    """
    import pefile

    raw = CLAW_V13_WRAPPER.read_bytes()
    found = hashlib.sha256(raw).hexdigest()
    if found != CLAW_V13_WRAPPER_SHA256:
        raise ValueError(f"{CLAW_V13_WRAPPER}: expected SHA-256 {CLAW_V13_WRAPPER_SHA256}, found {found}")
    with pefile.PE(data=raw) as wrapper:
        directory = wrapper.DIRECTORY_ENTRY_RESOURCE
        for key in ("EXE", 101, 1033):
            matches = [e for e in directory.entries
                       if (str(e.name) if e.name is not None else e.id) == key]
            if len(matches) != 1:
                raise ValueError("pinned v1.3 launcher requires exactly resource EXE/101/1033")
            entry = matches[0]
            if key != 1033:
                directory = entry.directory
        resource = entry.data.struct
        game = wrapper.get_data(resource.OffsetToData, resource.Size)
    return Program.from_bytes(game, CLAW_V13_SHA256, "claw-v1.3",
                              startup_calls=(0x4A9A52,), control_word=(0x0F3F, 0x023F),
                              origin=f"{CLAW_V13_WRAPPER}:EXE/101/1033")

