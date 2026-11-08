"""A four-function x86 program, written by hand for testing the harness itself.

    0x401000  sum_and_store   thiscall(this)          this[2] = this[0] + this[1]; returns the sum
    0x401010  scaled_global   stdcall(a, b)           global 0x402010 += a * 3 + b; returns a * 3 + b
    0x401030  make_buffer     thiscall(this, count)   this[0] = allocate(count); fill(buffer, count); returns buffer
    0x401060  fill            cdecl(buffer, count)    buffer[i] = i for i < count

The import slot at 0x402000 stands for an allocator in another library.
"""
from ..program import Program, Section

CODE = {
    0x401000: "8b01 034104 894108 c3",
    0x401010: "8b442404 8d0440 03442408 010510204000 c20800",
    0x401030: "56 8bf1 ff742408 ff1500204000 83c404 8906 85c0 740f ff742408 50 e810000000 83c408 8b06 5e c20400",
    0x401060: "8b542404 8b4c2408 33c0 3bc1 7d06 880402 40 ebf6 c3",
}
TEXT_START, TEXT_END, DATA_START = 0x401000, 0x401080, 0x402000


def program():
    text = bytearray(b"\xCC" * (TEXT_END - TEXT_START))
    for address, encoded in CODE.items():
        code = bytes.fromhex(encoded.replace(" ", ""))
        text[address - TEXT_START:address - TEXT_START + len(code)] = code
    sections = [Section(".text", TEXT_START, len(text), bytes(text)), Section(".data", DATA_START, 0x1000, bytes(0x1000))]
    return Program("synthetic", "", 0x400000, 0x3000, sections, (TEXT_START, TEXT_END), {0x402000: "SYNTH.dll!allocate"})
