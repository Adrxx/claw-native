"""Blind byte-search inputs; all backing and canaries remain observable heap."""
from clawparity.cases import Case

STRSTR = 0x4A3990
STRCHR = 0x4A3A20


def search_case(label, function, haystack, operand, alignment=0, needle_alignment=0):
    def setup(env):
        # Interior aliases have distinct leading bytes and readable terminal words.
        prefix = bytes([0xD3, 0xA7, 0xE1, 0xB9]) * 2
        padding = bytes([0xF5, 0x83, 0xC7, 0xED, 0x91, 0xAF, 0xDD, 0xB1])
        storage = prefix[:4 + alignment] + haystack + b"\0" + padding
        base = env.object(len(storage), "haystack backing", data=storage)
        hay = base + 4 + alignment
        if function == STRSTR:
            needle_storage = prefix[:4 + needle_alignment] + operand + b"\0" + padding
            needle_base = env.object(len(needle_storage), "needle backing", data=needle_storage)
            arg = needle_base + 4 + needle_alignment
        else:
            arg = operand
        return hay, arg
    return Case(label, function, setup, arguments=(lambda t: t[0], lambda t: t[1]))


def cases(random_source):
    examples = [
        (b"", b""), (b"", b"a"), (b"", b"ab"),
        (b"abc", b""), (b"abc", b"abc"), (b"abc", b"ab"),
        (b"abc", b"bc"), (b"abc", b"cd"), (b"ab", b"abc"),
        (b"xabcabc", b"abc"), (b"aaaaaab", b"aaab"),
        (b"ababababac", b"ababac"), (b"abXabcYabcdZabcdef", b"abcdef"),
        (b"abXabcYabcdZabcde", b"abcdef"), (b"aab", b"ab"),
        (b"abcXabcYabcZ", b"abcZ"), (b"abcdefghi", b"abcdefgh"),
        (b"abcdefghi", b"abcdefghi"), (b"axayaz", b"aa"),
        (b"\x80\xff\x81\x80\xff\x81", b"\x80\xff\x81"),
        (b"\xff\xfe\x7f\x81", b"\xfe\x7f"),
        (b"ab\0abcdef", b"abcd"), (b"abcdef", b"ab\0X"),
    ]
    for alignment in range(4):
        for needle_alignment in range(4):
            for index, (hay, needle) in enumerate(examples):
                yield search_case(f"substring {index} alignment {alignment}/{needle_alignment}",
                                  STRSTR, hay, needle, alignment, needle_alignment)
    # Both public entries independently encounter every byte and every stop slot.
    for alignment in range(4):
        for char in (0, 1, 0x41, 0x7F, 0x80, 0x81, 0xFE, 0xFF):
            other = 0x62 if char != 0x62 else 0x63
            for position in range(12):
                hay = bytes([other]) * position + bytes([char]) + b"xyz" + bytes([char])
                integer = (random_source.getrandbits(24) << 8) | char
                yield search_case(f"character {char} first {position} align {alignment}",
                                  STRCHR, hay, integer, alignment)
                if char:
                    yield search_case(f"single needle {char} first {position} align {alignment}",
                                      STRSTR, hay, bytes([char]), alignment, position % 4)
            for position in range(4):
                # A matching trailing canary after NUL must never become a result.
                hay = bytes([other]) * position + b"\0" + bytes([char]) * 4
                yield search_case(f"terminator before character {char} slot {position} align {alignment}",
                                  STRCHR, hay, integer, alignment)
                if char:
                    yield search_case(f"terminator before needle {char} slot {position} align {alignment}",
                                      STRSTR, hay, bytes([char]), alignment)
    # Sentinel candidates include high-bit words without matches or terminators.
    for alignment in range(4):
        for word in (b"\x80" * 4, b"\xff" * 4, b"\x01\x01\x01\x80",
                     b"\x7f\xfe\x81\xff", b"\x81\x80\xfe\x7f"):
            for char in (0, 0x31, 0x80, 0xFF):
                hay = word * 4 + b"123"
                yield search_case(f"sentinel {word.hex()} char {char} align {alignment}",
                                  STRCHR, hay, 0xFEDCBA00 | char, alignment)
                if char:
                    yield search_case(f"sentinel needle {word.hex()} char {char} align {alignment}",
                                      STRSTR, hay, bytes([char]), alignment)
    for index in range(400):
        length = random_source.randrange(0, 160)
        alphabet = [1, 2, 0x41, 0x42, 0x43, 0x7F, 0x80, 0x81, 0xFE, 0xFF]
        hay = bytes(random_source.choice(alphabet) for _ in range(length))
        alignment = random_source.randrange(4)
        char = random_source.randrange(256)
        yield search_case(f"random character {index}", STRCHR, hay,
                          (random_source.getrandbits(24) << 8) | char, alignment)
        if index % 3 == 0 and hay:
            start = random_source.randrange(len(hay))
            needle = hay[start:start + random_source.randrange(1, 18)]
        else:
            needle = bytes(random_source.choice(alphabet)
                           for _ in range(random_source.randrange(0, 20)))
        yield search_case(f"random substring {index}", STRSTR, hay, needle,
                          alignment, random_source.randrange(4))
