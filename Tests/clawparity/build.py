"""Builds shared libraries for the harness, cached by the content of their inputs.

Nothing is compiled when a test module is imported. Every build has its own
output file, so parallel runs never share a path.
"""
import hashlib
import os
import platform
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / "Sources"
CACHE = Path(os.environ.get("CLAW_BUILD_DIR", ROOT / "work" / "build" / "clawparity"))
COMMON = ["-std=c++17", "-Wall", "-Wextra", "-Werror", "-ffp-contract=off", "-fno-strict-aliasing"]
FLAVORS = {
    "O2": ["-O2"],
    "O0": ["-O0"],
    "sanitize": ["-O1", "-g", "-fno-omit-frame-pointer", "-fsanitize=address,undefined", "-fno-sanitize-recover=all"],
}
DARWIN = platform.system() == "Darwin"


def compiler():
    if DARWIN:
        return ["xcrun", "clang++"]
    found = shutil.which("clang++") or shutil.which("c++")
    if not found:
        raise RuntimeError("no C++ compiler found")
    return [found]


def _digest(sources, flags, dependencies=(), cache_context=""):
    state = hashlib.sha256()
    for path in sorted(str(p) for p in sources):
        state.update(path.encode())
        state.update(Path(path).read_bytes())
    for header in sorted(SOURCES.glob("ClawRuntime.h*")):
        state.update(header.read_bytes())
    for path in dependencies:
        state.update(str(path).encode())
        state.update(Path(path).read_bytes())
    state.update(" ".join(flags).encode())
    state.update(cache_context.encode())
    return state.hexdigest()[:16]


def library(name, sources, flavor="O2", defines=(), *, guest_transfer=False,
            dependencies=(), cache_context=""):
    """Compile `sources` into a shared library and return its path. Raises with the compiler output on failure."""
    sources = [Path(s) for s in sources]
    flags = COMMON + FLAVORS[flavor] + [f"-D{d}" for d in defines]
    dependencies, linked = list(dependencies), []
    if guest_transfer:
        support = guest_support(flavor)
        flags += ["-DCLAW_ENABLE_GUEST_TRANSFER=1"]
        dependencies += [SOURCES / "ClawGuestTransfer.h", SOURCES / "ClawGuestTransfer.cpp", support]
        linked = [str(support)]
    elif name == "guest-support":
        dependencies += [SOURCES / "ClawGuestTransfer.h"]
    suffix = ".dylib" if DARWIN else ".so"
    output = CACHE / f"{name}-{flavor}-{_digest(sources, flags, dependencies, cache_context)}{suffix}"
    if output.exists():
        return output
    CACHE.mkdir(parents=True, exist_ok=True)
    shared = ["-dynamiclib"] if DARWIN else ["-shared", "-fPIC"]
    partial = output.with_suffix(f".{os.getpid()}.partial")
    identity = ["-Wl,-install_name," + str(output)] if DARWIN and name == "guest-support" else []
    command = compiler() + flags + shared + identity + ["-I", str(SOURCES)] + [str(s) for s in sources] + linked + ["-o", str(partial)]
    done = subprocess.run(command, capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError("compile failed:\n" + done.stderr[-4000:])
    partial.replace(output)
    return output


def hostlib(flavor="O2"):
    return library("hostlib", [Path(__file__).with_name("hostlib.cpp")], flavor)


def guest_support(flavor="O2"):
    """One shared registry owner, linked by identity by every opted-in module."""
    return library("guest-support", [SOURCES / "ClawGuestTransfer.cpp"], flavor)


def sanitizer_runtime():
    """Path of the AddressSanitizer runtime that must be preloaded to load a sanitized library into Python."""
    if DARWIN:
        done = subprocess.run(["xcrun", "clang++", "-print-file-name=libclang_rt.asan_osx_dynamic.dylib"],
                              capture_output=True, text=True)
    else:
        done = subprocess.run(compiler() + ["-print-file-name=libclang_rt.asan-x86_64.so"], capture_output=True, text=True)
    path = Path(done.stdout.strip())
    return path if path.exists() else None


def sanitized_python():
    """Command prefix and environment that run Python with the sanitizer runtime loaded first.

    On macOS the virtual environment's launcher drops the preload variable, so
    the real interpreter is started directly with the environment's packages on
    its path. Returns (None, None) when no sanitizer runtime is available.
    """
    import site
    import sys

    runtime = sanitizer_runtime()
    if runtime is None:
        return None, None
    environment = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:halt_on_error=1",
                       UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1", CLAW_SANITIZER_PRELOADED="1")
    if not DARWIN:
        environment["LD_PRELOAD"] = str(runtime)
        return [sys.executable], environment
    base = Path(os.path.realpath(sys._base_executable))
    application = base.parent.parent / "Resources" / "Python.app" / "Contents" / "MacOS" / "Python"
    interpreter = application if application.exists() else base
    environment["DYLD_INSERT_LIBRARIES"] = str(runtime)
    environment["PYTHONPATH"] = os.pathsep.join(site.getsitepackages() + [environment.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    return [str(interpreter)], environment


def sanitizer_preloaded():
    """True when this process was started through sanitized_python().

    The sanitizer runtime removes its own preload variable from the environment
    once it has started, so a marker variable is used instead.
    """
    return os.environ.get("CLAW_SANITIZER_PRELOADED") == "1"
