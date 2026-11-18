# Ocarina of Time: western buttons for the nxnative Mac app

Xbox / PlayStation-style face buttons for the [nxnative](https://github.com/seedds/nxnative) Mac app of
*The Legend of Zelda: Ocarina of Time* (Switch 2, `0400486024DEC000`, game v131072, main build
`e0f3ccfaf50065ae4ea01eb5aeb13b1a`): **confirm / action on the bottom button, cancel on the right**, while X and Y
stay where Nintendo puts them (top / left). The button icons follow: the HUD, menus, dialogue and the ocarina's
song sheets show ✕ ○ △ □ (or Xbox A B Y X) in the places you press them.

This repository holds no game files. It patches your own app and generates the icons from your own copy.

## Layouts

| | `western` | `menu` |
|---|---|---|
| Bottom / right | A (confirm, action) / B (cancel) everywhere | menus: confirm / cancel; play: Switch B / Switch A |
| Top / left | Switch X / Switch Y (Nintendo positions) | Switch X / Switch Y |
| Icons | PlayStation or Xbox, fixed for this layout | Switch icons |

`western` is the "Western" layout of the TotK prompt mods.

## Two kinds of app

`install.sh` tells them apart by the launcher's settings:

- **An app with a "Buttons" setting (Switch / Xbox / PlayStation) and icon packs in `Resources/icons/`** (a
  prebuilt app that adds this setting; not upstream nxnative). With Buttons = Xbox or PlayStation every face button
  is mapped by its label; the hook swaps X and Y back to their Nintendo positions, and both bundled icon packs are
  fixed in place. Set Buttons = Xbox or PlayStation.
- **Upstream nxnative** (no Buttons setting; buttons by position, as on a Switch: bottom = B). The hook swaps A and
  B. The chosen style's icons go into a RomFS overlay folder,
  `~/Library/Application Support/nxnative/0400486024DEC000/mods/oot-western-<style>/`, named by a
  `DM_ROMFS_OVERLAY=` line in that folder's `env.txt`. The icons are built from the icon packs of the first kind of
  app, so run `install.sh` once on such an app first: it keeps its packs in `backup/` (ignored by git).

## Install / remove

Quit the game first. Needs Python 3 with `zstandard`, `fontTools`, `Pillow` and `numpy` (or `PY=<python>`, or a
`.venv` beside the script), Xcode's command line tools (`clang`, `otool`) and macOS `sips`.

```
./install.sh western [playstation|xbox]   # the style matters only for upstream apps (default playstation)
./install.sh menu
./install.sh --uninstall                  # module back byte for byte (SHA-256 checked), icons as packed
APP=/path/to/Other.app ./install.sh ...   # default: /Applications/The Legend of Zelda - Ocarina of Time.app
```

The script patches `Contents/Resources/dm/main.patched.bin` (and the icons), then re-signs the app ad-hoc, as it
was packed. Re-packing the app with nxnative replaces the module, so run it again afterwards. Builds of the module
it knows are listed in `ORIGINALS` in [`build_mod.py`](build_mod.py) (all with the same layout); others are refused.

## How it works

The code is in [`hooks.s`](hooks.s); [`build_mod.py`](build_mod.py) links it into the patch area after the module
(offset `0x5102000`, which the host maps read + execute) and branches to it from the game:

- **Swap** in `sead::Controller::calc` (`main+0x36a298`), right after the npad device controllers (vtable
  `main+0x4c61b00`) produce the frame's hold bits (`+0x114`: bit 0 A, 1 B, 3 X, 4 Y); trig, release and repeat
  come from those bits afterwards. `western` swaps X/Y (app with Buttons setting) or A/B (upstream). Merged
  controllers, which OR their children's bits, are skipped so nothing is swapped twice.
- **`menu` only:** menu detection at the menu-screen update (`main+0x2d1380`): if any button of the screen's list
  (`+136/+144/+156`, entry `+24`, button `+56`, as miojo-recomp's `oot_menu.c` reads it) has focus, the frame is
  recorded, and A/B are swapped while a menu had focus within the last 24 frames. A/B held across a switch are
  ignored until released. State lives in an unused read-write page at `main+0x4ea8000`.

[`icons_western.py`](icons_western.py) builds the icons from a pack (glyph font, layout archive, textures):

- `Font2/Scalable/External…bfotf.zs` (XOR-obfuscated OTF): the X and Y glyphs (U+E042 / U+E043) trade places,
  CFF charstrings swapped in place.
- `UI/Layout2Archive/Common…blarc.zs`: the HUD's action-button diamond (`DoCommand_00.buil`) moves only A and B,
  with values from the "Western" version of [DualSense & Xbox Button Prompts](https://gamebanana.com/mods/737848).
  The archive lists `DoCommand_00.buil` four times; all four copies are patched.
- `UI/Layout2Archive/Common…bntx.zs`: the letter images `KeyTexFontX/Y_00` trade places, and the ocarina's note
  images `OcarinaButtonA/B/X/Y_00` (93×93 ASTC 4×4, block-linear; untouched by the packs) follow: for Xbox X and Y
  trade places, for PlayStation they are redrawn as ✕ ○ △ □ on the game's own circle and encoded with `sips`.

File sizes stay the same, so the pack's resource size table still holds. Everything is recompressed with the
game's own zstd dictionary (`Pack/ZsDic.pack.zs`).

## Tested

Scripted input on the Mac with a copy of a save. Prebuilt app with Buttons = Xbox / PlayStation, and upstream
nxnative (`0b5fd602`) with the PlayStation overlay: the bottom button confirms and the right one cancels on the
title, Load and pause screens; the HUD and pause menu show the controller's glyphs (PlayStation: L1/R1/R2,
✕ select, ○ back). The ocarina notes were checked by decoding the written textures. Not tested with a physical
controller in these runs, nor on a screen that shows X/Y prompts.

## Related

- [joaobyss/oot-switch2-button-prompts](https://github.com/joaobyss/oot-switch2-button-prompts): PlayStation /
  Xbox / Steam Deck icons for emulators, Nintendo positions.
- nxnative [#2773](https://github.com/seedds/nxnative/pull/2773) / [#2774](https://github.com/seedds/nxnative/pull/2774):
  a `DM_PAD_LAYOUT` setting and OoT icon overlays proposed upstream.
