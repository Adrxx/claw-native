"""Original-only diagnostic policy cases; formatting remains original code."""
from clawparity.cases import Case

AUDIO = 0x4B4ED0
DISPLAY = 0x4BD260
BEEP = 0x546CA4
LOG = 0x546A08
DIALOG = 0x546D48
ENTRY = 0x02008000
FLAGS = {AUDIO: 0x54130C, DISPLAY: 0x54139C}

AUDIO_CODES = (
    0, 0x80004001, 0x80004005, 0x80040110, 0x8007000E, 0x80070057,
    0x8878000A, 0x8878001E, 0x88780032, 0x88780046, 0x88780064,
    0x88780078, 0x88780096, 0x887800A0,
)
DISPLAY_CODES = (
    0, 0x80004001, 0x80004005, 0x8007000E, 0x80070057,
    0x88760064, 0x88760078, 0x88760082, 0x88760091, 0x88760096,
    0x887600A0, 0x887600AA, 0x887600B4, 0x887600D2, 0x887600D4,
    0x887600E1, 0x887600F0, 0x887600FA, 0x887600FF, 0x88760104,
    0x88760118, 0x88760122, 0x88760136, 0x88760140, 0x8876014A,
    0x8876014F, 0x88760154, 0x88760168, 0x8876017C, 0x88760183,
    0x887601AE, 0x887601B8, 0x887601C2, 0x887601CC, 0x887601E0,
    0x887601EA, 0x88760219, 0x8876021C, 0x88760245, 0x88760248,
    *range(0x88760230, 0x8876023E),
)


def diagnostic(function, label, code=0xFEDC1357, flags=(1, 1, 0, 0),
               filename=b"unique/source.cpp", line=731, beep_flags=None,
               beep_arguments=None, log_flags=None, log_arguments=None,
               rewrite_filename=False, service_result=0, observe_local_tails=False):
    """Effects record observations in surviving memory, without assertions."""
    base = FLAGS[function]

    def setup(env):
        # Both groups are distinct so an accidental use of the other group's
        # enable bits is observable, including during callback mutation.
        other = FLAGS[DISPLAY if function == AUDIO else AUDIO]
        env.put(other, 0xA1020304, 0xB2030405, 0xC3040506, 0xD4050607)
        env.put(base, *flags)
        source = env.object(160, "filename", fill=0xAD)
        env.write(source, (filename if filename is not None else b"unused.cpp") + b"\0")
        replacement = env.object(160, "replacement-filename", fill=0xD3)
        env.write(replacement, b"replacement/after-callback.cpp\0")
        trace = env.object(8192, "callback-observations", fill=0xE7)
        env.put(trace, 0)

        def record(env, call, tag, text_argument=None, caption_argument=None):
            count = env.get(trace)
            row = trace + 4 + count * 2048
            env.put(row, tag, call.receiver, len(call.arguments), *call.arguments)
            env.put(row + 32, *(env.get(base + i * 4) for i in range(4)))
            env.put(row + 48, env.get(ENTRY + 4), env.get(ENTRY + 8), env.get(ENTRY + 12))
            if text_argument is not None:
                env.write(row + 64, env.cstr(call.arguments[text_argument]) + b"\0")
            if caption_argument is not None:
                env.write(row + 576, env.cstr(call.arguments[caption_argument]) + b"\0")
            if observe_local_tails and tag != 0xBEE0:
                # Observe all local bytes, including the poisoned unused tails.
                # This detects a copy of one byte too many even when its text
                # remains identical as a C string.
                env.write(row + 640, env.read(ENTRY - 0x340, 0x340))
            env.put(trace, count + 1)

        def change_arguments(env, new_arguments):
            if new_arguments is not None:
                new_file, new_line, new_code = new_arguments
                env.put(ENTRY + 4, replacement if new_file else 0, new_line, new_code)

        def beep(env, call):
            record(env, call, 0xBEE0)
            if observe_local_tails:
                env.write(ENTRY - 0x340, bytes([0xA7]) * 64)
                env.write(ENTRY - 0x300, bytes([0xB9]) * 256)
                env.write(ENTRY - 0x200, bytes([0xCB]) * 512)
            if beep_flags is not None:
                env.put(base, *beep_flags)
            change_arguments(env, beep_arguments)
            return service_result

        def log(env, call):
            record(env, call, 0x1060, text_argument=0)
            if log_flags is not None:
                env.put(base, *log_flags)
            change_arguments(env, log_arguments)
            if rewrite_filename:
                env.write(source, b"edited/original-buffer.cpp\0")
            return service_result

        def dialog(env, call):
            record(env, call, 0xD1A0, text_argument=1, caption_argument=2)
            return service_result

        env.override(BEEP, beep)
        env.override(LOG, log)
        env.override(DIALOG, dialog)
        return {"filename": source if filename is not None else 0}

    return Case(label, function, setup, arguments=(lambda t: t["filename"], line, code))


def cases(random_source):
    for function, codes in ((AUDIO, AUDIO_CODES), (DISPLAY, DISPLAY_CODES)):
        name = "audio" if function == AUDIO else "display"
        # Every named HRESULT, each immediate neighbor, and every display table
        # slot (including holes) distinguish full-word equality from low16 tests.
        selection = sorted({(code + delta) & 0xFFFFFFFF
                            for code in codes for delta in (-1, 0, 1)} |
                           {0x80000000, 0x7FFFFFFF, 0xFFFF, 0x10000,
                            0xFFFFFFFF, 0x00004005, 0x00760064})
        for index, code in enumerate(selection):
            yield diagnostic(function, f"{name} selection {code:08x}", code,
                             filename=b"selection/arm_%03d.cpp" % index,
                             line=index + 1, service_result=(code ^ 0x51A37D92))
        # Poison before initialization, then observe the complete code,
        # description and output buffers at each real observable service.
        # All literal arms exercise their independent NUL-inclusive copy lengths
        # and remainders modulo four. Unknown preserves initializer suffixes.
        for index, code in enumerate((*codes, 0xFEDC1357)):
            yield diagnostic(function, f"{name} poisoned local tails {code:08x}",
                             code=code, flags=(1, 1, 1, 0),
                             filename=b"tail/%s.cpp" % (b"x" * (index % 7)),
                             line=index + 1, observe_local_tails=True)
        # All sixteen independent policies, with several non-boolean enabled
        # words. An empty filename is nonnull and still includes its location.
        for mask in range(16):
            flags = tuple((0x80000000 if bit & 1 else 0x76543210)
                          if mask & (1 << bit) else 0 for bit in range(4))
            yield diagnostic(function, f"{name} policy mask {mask:04b}",
                             flags=flags, code=codes[mask % len(codes)])
        for filename in (None, b"", b"a", b"ABCD.cpp", b"long/" + b"x" * 120):
            for line in (0x80000000, 0xFFFFFFFF, 0, 1, 0x7FFFFFFF):
                yield diagnostic(function, f"{name} location {filename!r} line {line:08x}",
                                 filename=filename, line=line)
        # Beep happens before any admission flags or incoming args are read.
        for target in ((0, 0, 0, 0), (1, 0, 0, 0), (0, 2, 0, 0),
                       (0, 0, 0, 0xFFFFFFFF), (0x80000000, 7, 0, 1)):
            yield diagnostic(function, f"{name} beep replaces policy {target}",
                             flags=(0, 0, 3, 0), beep_flags=target,
                             service_result=0xFFFFFFFF)
        for new_file in (False, True):
            for new_line in (0x80000000, 0, 1, 0x7FFFFFFF):
                yield diagnostic(function, f"{name} beep reload args {new_file} {new_line}",
                                 code=0x11223344, flags=(1, 1, 0x80000000, 0),
                                 beep_arguments=(new_file, new_line, codes[-2]),
                                 service_result=0x89ABCDEF)
        # Whole sprintf and the RET-only display sink cannot be replaced by
        # callbacks. Audio's log is the remaining reachable effect: dialog
        # enable reloads, but filename/line/HRESULT stay cached across it.
        if function == AUDIO:
            for initially_enabled, afterwards_enabled in ((0, 1), (1, 0), (1, 0x80000000)):
                for new_file, new_line, new_code in ((False, 0, 0), (True, 0xFFFFFFFF, 0x887800A0)):
                    yield diagnostic(function, f"audio log dialog reload {initially_enabled} {afterwards_enabled} {new_file}",
                                     flags=(1, initially_enabled, 0, 0),
                                     log_flags=(0, afterwards_enabled, 0xFFFFFFFF, 0),
                                     log_arguments=(new_file, new_line, new_code))
            yield diagnostic(function, "audio log edits cached filename contents",
                             log_arguments=(True, 0, 0), rewrite_filename=True)
            yield diagnostic(function, "audio no-location remains cached after log",
                             filename=None, line=0xFFFFFFFF,
                             log_arguments=(True, 99, 0x80004005))
        for index in range(32):
            code = random_source.choice(codes) if index & 1 else random_source.getrandbits(32)
            flags = tuple(random_source.choice((0, 1, 0x80000000, random_source.getrandbits(32)))
                          for _ in range(4))
            filename = bytes(random_source.randrange(33, 127)
                             for _ in range(random_source.randrange(0, 100)))
            yield diagnostic(function, f"{name} randomized {index}", code=code,
                             flags=flags, filename=filename if index % 4 else None,
                             line=random_source.getrandbits(32),
                             service_result=random_source.getrandbits(32))
