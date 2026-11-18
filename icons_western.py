#!/usr/bin/env python3
"""Western button icons for the nxnative Ocarina of Time app's Xbox or PlayStation icon pack (Resources/icons/<style>).

Western: A bottom (confirm), B right (cancel), X top, Y left (Nintendo positions for X/Y), which is what the app's
Xbox / PlayStation setting plus build_mod.py --layout western gives. From the bundled pack (symbols by label) it changes:
- Font2/Scalable/External...bfotf.zs: glyphs U+E042 (Switch X) and U+E043 (Switch Y) trade places, so the top button
  shows Y and the left one X (CFF charstrings swapped in place: the font keeps its size);
- UI/Layout2Archive/Common...blarc.zs: the HUD's action-button diamond (DoCommand_00) moves only A and B (bottom /
  right), X and Y stay at the top / left as in the original game, with A's and B's base shapes turned to match.
  The values are those of the "Western" layout of "DualSense & Xbox Button Prompts" (gamebanana.com/mods/737848).
- UI/Layout2Archive/Common...bntx.zs: the letter images KeyTexFontX_00 and KeyTexFontY_00 trade places (the pack's
  file when it has one, as the PlayStation pack does, else the game's own).
- the same bntx: the ocarina's note images (OcarinaButtonA/B/X/Y_00, which no bundled pack changes): for Xbox X and Y
  trade places; for PlayStation they are drawn anew as Cross / Circle / Triangle / Square (A / B / X / Y, i.e. bottom /
  right / top / left) on the game's own circle, and encoded as ASTC 4x4 with macOS sips.
File sizes stay the same, so the pack's ResourceSizeTable stays valid. Swapping is its own inverse for the font and
the images; the layout values are checked against the game's before they are written.

usage: icons_western.py <icons/<style> folder (the packed one)> <out folder> <xbox|playstation>
"""
import hashlib, os, struct, sys
import zstandard

ROMFS = os.environ.get('OOT_ROMFS', '/Applications/The Legend of Zelda - Ocarina of Time.app/Contents/Resources/romfs.img')
FONT = 'Font2/Scalable/External.Nin_Ounce_NVN2.bfotf.zs'
BLARC = 'UI/Layout2Archive/Common.Product.100.Nin_Ounce_NVN2.blarc.zs'
BNTX = 'UI/Layout2Archive/Common.Product.100.Nin_Ounce_NVN2.bntx.zs'
# DoCommand_00.buil (67108 bytes): offset -> the Western layout's 4 bytes (the original's are checked below)
DOCMD = {
    0x0aac: ('00000000', 'db0fc9bf'),   # A base: rotation -pi/2
    0x0af4: ('00000000', '0000a042'), 0x0af8: ('0000a0c2', '00000000'),
    0x0bc0: ('0000a042', '00000000'), 0x0bc4: ('00000000', '0000a0c2'),
    0x0d98: ('00000000', 'db0fc93f'),   # B base: rotation +pi/2
    0x0de0: ('0000a042', '00000000'), 0x0de4: ('00000000', '0000a0c2'),
    0x0eac: ('00000000', '0000a042'), 0x0eb0: ('0000a0c2', '00000000'),
    0x10cc: ('0000a042', '00000000'), 0x10d0: ('00000000', '0000a0c2'),
    0x1110: ('000000a9', '0000a042'), 0x1114: ('0000a0c2', '00000000'),
    0x13b8: ('0000a042', '00000000'), 0x13bc: ('00000000', '0000a0c2'),
    0x13fc: ('000000a9', '0000a042'), 0x1400: ('0000a0c2', '00000000'),
}

def romfs_read(path):
    f = open(ROMFS, 'rb'); h = f.read(32); ioff, isz, n = struct.unpack_from('<QQQ', h, 8)
    f.seek(ioff); d = f.read(isz); names = d[n * 24:]
    e = [struct.unpack_from('<QQIHBB', d, k * 24) for k in range(n)]
    k = 0
    for part in path.split('/'):
        a, b = e[k][0], e[k][1]
        k = next(j for j in range(a, a + b) if names[e[j][2]:e[j][2] + e[j][3]].decode() == part)
    f.seek(e[k][0]); return f.read(e[k][1])

def sarc_files(b):
    hl = struct.unpack_from('<H', b, 4)[0]; data = struct.unpack_from('<I', b, 0xc)[0]
    n = struct.unpack_from('<H', b, hl + 6)[0]; names = hl + 12 + 16 * n + 8
    for i in range(n):
        _, attr, s, e = struct.unpack_from('<IIII', b, hl + 12 + 16 * i)
        no = names + (attr & 0xffff) * 4
        yield b[no:b.index(b'\0', no)].decode(), data + s, data + e

def swap_glyphs(otf, a, b):
    """Swap the CFF charstrings of glyph ids a < b in place and fix the table checksums."""
    otf = bytearray(otf); ntab = struct.unpack_from('>H', otf, 4)[0]; tabs = {}
    for i in range(ntab):
        tag, cs, off, ln = struct.unpack_from('>4sIII', otf, 12 + 16 * i); tabs[tag] = (12 + 16 * i, off, ln)
    _, coff, _ = tabs[b'CFF ']
    from fontTools.cffLib import CFFFontSet
    import io
    cff = CFFFontSet(); cff.decompile(io.BytesIO(bytes(otf[coff:coff + tabs[b'CFF '][2]])), None)
    top = cff[cff.fontNames[0]]
    cs_off = coff + top.rawDict['CharStrings']
    count, osz = struct.unpack_from('>HB', otf, cs_off)
    rd = lambda i: int.from_bytes(otf[cs_off + 3 + i * osz: cs_off + 3 + (i + 1) * osz], 'big')
    offs = [rd(i) for i in range(count + 1)]; base = cs_off + 3 + (count + 1) * osz - 1
    ga, gb = otf[base + offs[a]:base + offs[a + 1]], otf[base + offs[b]:base + offs[b + 1]]
    mid = otf[base + offs[a + 1]:base + offs[b]]
    otf[base + offs[a]:base + offs[b + 1]] = gb + mid + ga
    d = len(gb) - len(ga)
    for i in range(a + 1, b + 1): offs[i] += d
    for i, v in enumerate(offs): otf[cs_off + 3 + i * osz: cs_off + 3 + (i + 1) * osz] = v.to_bytes(osz, 'big')
    # hmtx: trade the advance / side bearing too
    _, hoff, _ = tabs[b'hmtx']; nh = struct.unpack_from('>H', otf, tabs[b'hhea'][1] + 34)[0]
    if b < nh:
        ea, eb = otf[hoff + 4 * a:hoff + 4 * a + 4], otf[hoff + 4 * b:hoff + 4 * b + 4]
        otf[hoff + 4 * a:hoff + 4 * a + 4], otf[hoff + 4 * b:hoff + 4 * b + 4] = eb, ea
    def csum(bs):
        bs = bytes(bs) + bytes(-len(bs) % 4); return sum(struct.unpack('>%dI' % (len(bs) // 4), bs)) & 0xffffffff
    hd = tabs[b'head'][1]; otf[hd + 8:hd + 12] = bytes(4)
    for tag, (rec, off, ln) in tabs.items(): struct.pack_into('>I', otf, rec + 4, csum(otf[off:off + ln]))
    struct.pack_into('>I', otf, hd + 8, (0xB1B0AFBA - csum(otf)) & 0xffffffff)
    return bytes(otf)

def bntx_texture(b, name):
    """(offset, size) of level 0 of a texture in a BNTX file, found by its BRTI block's name"""
    i = 0
    while True:
        i = b.find(b'BRTI', i, 0x400000)
        if i < 0: raise KeyError(name)
        try:
            size, = struct.unpack_from('<I', b, i + 0x50); nm, = struct.unpack_from('<Q', b, i + 0x60)
            ln, = struct.unpack_from('<H', b, nm)
            if b[nm + 2:nm + 2 + ln] == name.encode():
                ptrs, = struct.unpack_from('<Q', b, i + 0x70); return struct.unpack_from('<Q', b, ptrs)[0], size, b[i + 0x10:i + 0x60]
        except struct.error: pass
        i += 4

def astc_index(bx, by, bw, bh):
    """byte offset of ASTC block (bx, by) in a block-linear (Tegra) texture: 16-byte elements, GOBs 4 x 8 blocks"""
    inner = (by & 1) | ((by >> 1) & 1) << 1 | (bx & 1) << 2 | ((by >> 2) & 1) << 3 | ((bx >> 1) & 1) << 4
    gobs_x = (bw + 3) // 4
    return ((by // (8 * bh) * gobs_x + bx // 4) * bh + by % (8 * bh) // 8) * 512 + inner * 16

def astc_texture(bntx, name):
    """(offset, size, w, h, block height) of an ASTC 4x4 texture"""
    o, sz, d = bntx_texture(bntx, name)
    fmt, = struct.unpack_from('<I', d, 0xc); w, h = struct.unpack_from('<II', d, 0x14)
    assert fmt >> 8 == 0x2d, (name, hex(fmt))
    return o, sz, w, h, 1 << struct.unpack_from('<I', d, 0x24)[0]

def sips(src, fmt, tmp):
    import subprocess
    out = os.path.join(tmp, 'out.' + fmt)
    subprocess.run(['sips', '-s', 'format', fmt, src, '--out', out], check=True, capture_output=True,
                   env=dict(os.environ, TMPDIR=tmp))
    return out

def astc_get(bntx, name, tmp):
    """decode a texture to a PIL image"""
    from PIL import Image
    o, sz, w, h, bh = astc_texture(bntx, name); bw, bhh = (w + 3) // 4, (h + 3) // 4
    lin = b''.join(bntx[o + a:o + a + 16] for a in (astc_index(x, y, bw, bh) for y in range(bhh) for x in range(bw)))
    p = os.path.join(tmp, 'in.astc')
    open(p, 'wb').write(struct.pack('<I3B', 0x5CA1AB13, 4, 4, 1) + b''.join(v.to_bytes(3, 'little') for v in (w, h, 1)) + lin)
    return Image.open(sips(p, 'png', tmp)).convert('RGBA')

def astc_put(bntx, name, img, tmp):
    o, sz, w, h, bh = astc_texture(bntx, name); bw, bhh = (w + 3) // 4, (h + 3) // 4
    from PIL import Image
    p = os.path.join(tmp, 'in.png'); img.transpose(Image.FLIP_TOP_BOTTOM).save(p)   # sips writes ASTC rows bottom-up
    a = open(sips(p, 'astc', tmp), 'rb').read()
    assert a[4:7] == bytes((4, 4, 1)) and len(a) == 16 + 16 * bw * bhh, 'sips wrote another ASTC block size'
    for y in range(bhh):
        for x in range(bw):
            k = astc_index(x, y, bw, bh); bntx[o + k:o + k + 16] = a[16 + 16 * (y * bw + x):32 + 16 * (y * bw + x)]

def ps_note(base, kind):
    """the game's note circle (white, alpha from base) with a black PlayStation symbol"""
    import math
    import numpy as np
    from PIL import Image, ImageDraw
    n = base.size[0]; S = 8; c = n * S / 2; w = int(6.5 * S)
    big = Image.new('L', (n * S, n * S), 0); d = ImageDraw.Draw(big)
    if kind == 'cross':
        r = 16 * S
        for sx in (1, -1): d.line([(c - r, c - sx * r), (c + r, c + sx * r)], fill=255, width=w)
    elif kind == 'circle':
        r = 18.5 * S; d.ellipse([c - r, c - r, c + r, c + r], outline=255, width=w)
    elif kind == 'square':
        r = 15 * S; d.rectangle([c - r, c - r, c + r, c + r], outline=255, width=w)
    else:   # triangle: outer minus inner (an even stroke means 2w less circumradius)
        cy = c + 4 * S
        tri = lambda R: [(c + R * math.cos(math.radians(t)), cy - R * math.sin(math.radians(t))) for t in (90, 210, 330)]
        d.polygon(tri(24 * S), fill=255); d.polygon(tri(24 * S - 2 * w), fill=0)
    m = np.asarray(big.resize(base.size, Image.LANCZOS)).astype(float) / 255
    a = np.asarray(base).copy(); a[..., 0] = a[..., 1] = a[..., 2] = (255 * (1 - m)).round().astype(np.uint8)
    return Image.fromarray(a, 'RGBA')

def main():
    src, out, style = sys.argv[1], sys.argv[2], sys.argv[3]
    assert style in ('xbox', 'playstation'), style
    pack = zstandard.ZstdDecompressor().decompress(romfs_read('Pack/ZsDic.pack.zs'), max_output_size=1 << 26)
    zs = next(pack[s:e] for name, s, e in sarc_files(pack) if name == 'zs.zsdic')
    D = zstandard.ZstdCompressionDict(zs)
    dec = lambda b: zstandard.ZstdDecompressor(dict_data=D).decompress(b, max_output_size=1 << 28)
    enc = lambda b: zstandard.ZstdCompressor(level=19 if len(b) < 1 << 24 else 9, dict_data=D, threads=-1).compress(b)
    # font
    raw = dec(open(os.path.join(src, FONT), 'rb').read())
    key = struct.unpack('>I', raw[8:12])[0] ^ 0x4F54544F
    n = len(raw) - 8; w = struct.unpack('>%dI' % (n // 4), raw[8:8 + n // 4 * 4]); assert n % 4 == 0
    otf = struct.pack('>%dI' % len(w), *[x ^ key for x in w])
    from fontTools.ttLib import TTFont
    import io
    order = TTFont(io.BytesIO(otf)).getGlyphOrder(); ga, gb = order.index('uniE042'), order.index('uniE043')
    new = swap_glyphs(otf, min(ga, gb), max(ga, gb)); assert len(new) == len(otf)
    cm = TTFont(io.BytesIO(new)); cm['CFF '].cff[0].CharStrings['uniE042'].decompile()   # parses
    w = struct.unpack('>%dI' % (len(new) // 4), new)
    font = raw[:8] + struct.pack('>%dI' % len(w), *[x ^ key for x in w])
    # layout archive
    blarc = bytearray(dec(open(os.path.join(src, BLARC), 'rb').read()))
    # The archive lists DoCommand_00.buil four times (same name and hash, identical data); the game reads the last
    # (the one prompt packs change), all four are patched so no lookup order can show the old diamond.
    orig = dec(romfs_read(BLARC))
    ents = [(s, e) for name, s, e in sarc_files(blarc) if name == 'DoCommand_00.buil']
    assert ents and [(s, e) for name, s, e in sarc_files(orig) if name == 'DoCommand_00.buil'] == ents
    for s, e in ents:
        docmd = bytearray(orig[s:e])   # the game's own layout
        assert len(docmd) == 67108 and docmd[:4] == b'BFFH'
        for off, (old, newv) in DOCMD.items():
            if docmd[off:off + 4].hex() != old: sys.exit('DoCommand_00 at %#x is %s, not %s: another game version?' % (off, docmd[off:off + 4].hex(), old))
            docmd[off:off + 4] = bytes.fromhex(newv)
        blarc[s:e] = docmd
    # letter images
    src_bntx = os.path.join(src, BNTX)
    bntx = bytearray(dec(open(src_bntx, 'rb').read()) if os.path.exists(src_bntx) else dec(romfs_read(BNTX)))
    (xo, xs, xd), (yo, ys, yd) = bntx_texture(bntx, 'KeyTexFontX_00'), bntx_texture(bntx, 'KeyTexFontY_00')
    assert xs == ys and xd == yd and abs(xo - yo) >= xs   # same format, size and tiling
    bntx[xo:xo + xs], bntx[yo:yo + ys] = bntx[yo:yo + ys], bntx[xo:xo + xs]
    # ocarina notes
    if style == 'xbox':
        (xo, xs, xd), (yo, ys, yd) = bntx_texture(bntx, 'OcarinaButtonX_00'), bntx_texture(bntx, 'OcarinaButtonY_00')
        assert xs == ys and xd == yd
        bntx[xo:xo + xs], bntx[yo:yo + ys] = bntx[yo:yo + ys], bntx[xo:xo + xs]
    else:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            base = astc_get(bntx, 'OcarinaButtonA_00', tmp)
            for b, kind in zip('ABXY', ('cross', 'circle', 'triangle', 'square')):
                img = ps_note(base, kind); astc_put(bntx, 'OcarinaButton%s_00' % b, img, tmp)
                import numpy as np
                back = np.asarray(astc_get(bntx, 'OcarinaButton%s_00' % b, tmp)).astype(int)
                assert np.abs(back - np.asarray(img)).mean() < 2, 'ASTC round trip of the %s note differs' % kind
    for rel, data in ((FONT, font), (BLARC, bytes(blarc)), (BNTX, bytes(bntx))):
        p = os.path.join(out, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
        c = enc(data); assert dec(c) == data
        open(p, 'wb').write(c); print('wrote', p, len(data), 'bytes')

if __name__ == '__main__': main()
