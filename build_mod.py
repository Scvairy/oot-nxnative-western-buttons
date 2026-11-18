#!/usr/bin/env python3
"""Menu confirm/cancel on the bottom/right face buttons for The Legend of Zelda: Ocarina of Time (nxnative Mac app).

usage: build_mod.py [--layout menu|western|western-ab] <in main.patched.bin> <out main.patched.bin>   (assembles hooks.s)
         menu (default): with Buttons = Switch; menus confirm bottom / cancel right, play keeps Nintendo positions
         western: with Buttons = Xbox / PlayStation; A bottom and B right everywhere, X/Y at their Nintendo positions
         western-ab: the same for an app with no Buttons setting (upstream nxnative, buttons by position): swaps A/B
       build_mod.py --restore <modded main.patched.bin> <out>        (the original file, byte for byte, checked by SHA-256)
       build_mod.py --check <main.patched.bin>                       (prints mod / original / unknown)

Only for main build e0f3ccfaf50065ae4ea01eb5aeb13b1a (game v131072), as packed by the nxnative versions in ORIGINALS;
the script refuses any other file.
"""
import os, struct, subprocess, sys, tempfile

BUILD = 'e0f3ccfaf50065ae4ea01eb5aeb13b1a'
PATCH_BASE = 0x5102000         # hooks appended here: inside the module's RX patch area (the loader maps the whole file)
STATE = 0x4ea8000              # RW page between the frame-step state page and the patch area, zero in the image
VTABLE = 0x4c61b00             # npad device controller (sead::Controller subclass) vtable
SITE1, ORIG1 = 0x2d1380, 0xd503237f    # menu screen update: pacibsp
SITE2, ORIG2 = 0x36a298, 0xb9410663    # sead::Controller::calc: ldr w3, [x19, #0x104]
MARKS = {'menu': b'OOT-MENU-AB-MOD1', 'western': b'OOT-WESTERN-XY-1', 'western-ab': b'OOT-WESTERN-AB-1'}
# the packed module (SHA-256 -> size) as nxnative versions write it; their layouts (main.fixups.tsv) are the same
ORIGINALS = {
    'cb05f4cab9a61d877a0e50af167a958d1df5b57d28bff8b64771b58a597f3d2c': 0x51017a4,   # the prebuilt app (07e41655bab7)
    '0356a52d950c79318f79949f6033d6f6ef79681d66f8b399a73006b75ca04feb': 0x51015d8,   # upstream 0b5fd602 (2026-11-18)
}
import hashlib

def u32(b, o): return struct.unpack_from('<I', b, o)[0]
def p32(b, o, v): struct.pack_into('<I', b, o, v)
def B(src, dst):
    d = (dst - src) >> 2
    assert -(1 << 25) <= d < (1 << 25) and (dst - src) % 4 == 0
    return 0x14000000 | (d & 0x3ffffff)
def ADRP(word, src, dst):
    imm = ((dst & ~0xfff) - (src & ~0xfff)) >> 12
    assert -(1 << 20) <= imm < (1 << 20)
    return (word & 0x9f00001f) | ((imm & 3) << 29) | (((imm >> 2) & 0x7ffff) << 5)

def build_id(path):
    for line in open(os.path.join(os.path.dirname(os.path.abspath(path)), 'main.fixups.tsv')):
        if line.startswith('# BUILD_ID'): return line.split()[-1]

def assemble():
    here = os.path.dirname(os.path.abspath(__file__))
    with tempfile.TemporaryDirectory() as t:
        o = os.path.join(t, 'h.o')
        subprocess.check_call(['clang', '-c', '-target', 'arm64-apple-macos13', os.path.join(here, 'hooks.s'), '-o', o])
        syms = {}
        for line in subprocess.check_output(['nm', '-n', o], text=True).split('\n'):
            p = line.split()
            if len(p) == 3: syms[p[2].lstrip('_')] = int(p[0], 16)
        raw = subprocess.check_output(['otool', '-X', '-t', o], text=True)
    words = []
    for line in raw.split('\n'):
        p = line.split()
        if len(p) > 1: words += [int(w, 16) for w in p[1:]]
    return bytearray(struct.pack('<%dI' % len(words), *words)), syms

def main():
    if sys.argv[1] == '--check':
        b = open(sys.argv[2], 'rb').read()
        if hashlib.sha256(b).hexdigest() in ORIGINALS: print('original')
        else:
            for k, m in MARKS.items():
                if b[PATCH_BASE:].endswith(m): print(k); return
            print('unknown')
        return
    if sys.argv[1] == '--restore':
        b = bytearray(open(sys.argv[2], 'rb').read())
        if not any(b[PATCH_BASE:].endswith(m) for m in MARKS.values()): sys.exit('%s does not hold this mod' % sys.argv[2])
        p32(b, SITE1, ORIG1); p32(b, SITE2, ORIG2)
        for size in ORIGINALS.values():
            if hashlib.sha256(b[:size]).hexdigest() in ORIGINALS and ORIGINALS[hashlib.sha256(b[:size]).hexdigest()] == size:
                b = b[:size]; break
        else: sys.exit('restored file does not match a known original hash')
        open(sys.argv[3], 'wb').write(b); print('restored the original to', sys.argv[3])
        return
    args = sys.argv[1:]; layout = 'menu'
    if args[0] == '--layout': layout = args[1]; args = args[2:]
    assert layout in MARKS
    src, dst = args
    if build_id(src) != BUILD: sys.exit('main.fixups.tsv build %s is not %s' % (build_id(src), BUILD))
    img = bytearray(open(src, 'rb').read())
    if ORIGINALS.get(hashlib.sha256(img).hexdigest()) != len(img) or len(img) > PATCH_BASE or u32(img, SITE1) != ORIG1 or u32(img, SITE2) != ORIG2 or any(img[STATE:STATE + 0x1000]):
        sys.exit('%s is not the unmodified packed module this mod was made for' % src)
    code, s = assemble()
    a = lambda name: PATCH_BASE + s[name]
    o = lambda name: s[name]
    p32(code, o('FIX_STATE1'), ADRP(u32(code, o('FIX_STATE1')), a('FIX_STATE1'), STATE))
    p32(code, o('FIX_STATE2'), ADRP(u32(code, o('FIX_STATE2')), a('FIX_STATE2'), STATE))
    for fix in ('FIX_VT', 'FIX_VT2', 'FIX_VT3'):
        p32(code, o(fix), ADRP(u32(code, o(fix)), a(fix), VTABLE))
        add = u32(code, o(fix) + 4); assert add & 0xffc00000 == 0x91000000
        p32(code, o(fix) + 4, (add & ~(0xfff << 10)) | ((VTABLE & 0xfff) << 10))
    p32(code, o('FIX_RET1'), B(a('FIX_RET1'), SITE1 + 4))
    p32(code, o('FIX_RET2'), B(a('FIX_RET2'), SITE2 + 4))
    p32(code, o('FIX_RET3'), B(a('FIX_RET3'), SITE2 + 4))
    p32(code, o('FIX_RET4'), B(a('FIX_RET4'), SITE2 + 4))
    orig_size = len(img)
    img += bytes(PATCH_BASE - len(img)) + code + MARKS[layout]
    if layout == 'menu':
        p32(img, SITE1, B(SITE1, a('menu_tick')))
        p32(img, SITE2, B(SITE2, a('pad_swap')))
    else:
        p32(img, SITE2, B(SITE2, a('xy_swap' if layout == 'western' else 'ab_swap')))
    assert ((len(img) + 0x3fff) & ~0x3fff) == ((orig_size + 0x3fff) & ~0x3fff)   # module size unchanged
    open(dst, 'wb').write(img)
    print('wrote %s: %s layout, hooks at %#x (%d bytes)' % (dst, layout, PATCH_BASE, len(code)))

if __name__ == '__main__': main()
