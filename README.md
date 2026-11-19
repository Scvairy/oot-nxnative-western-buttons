# Ocarina of Time: western buttons for the nxnative Mac app

Xbox / PlayStation-style face buttons for the [nxnative](https://github.com/seedds/nxnative) Mac app of
*The Legend of Zelda: Ocarina of Time* (Switch 2, `0400486024DEC000`, game v131072 / 2.0.0, main build
`e0f3ccfaf50065ae4ea01eb5aeb13b1a`): **confirm / action on the bottom button, cancel on the right**, while the top
and left buttons keep their Nintendo roles. With the icons of
[DualSense & Xbox Button Prompts](https://gamebanana.com/mods/737848) by **Makine Çeviri** (its *Western* version),
the HUD, menus, dialogue, the ocarina's song sheets and the Controls screen show ✕ ○ △ □ (or Xbox A B Y X) where you
press them.

nxnative maps a controller's buttons by position, as on a Switch (bottom = B, right = A). The emulator instructions of
737848's Western version swap A and B; nxnative has no such setting, so this mod does it in the game:

| | `western` | `menu` |
|---|---|---|
| Bottom / right | A (confirm, action) / B (cancel) everywhere | menus: confirm / cancel; play: Switch B / Switch A |
| Top / left | Switch X / Switch Y (Nintendo positions) | Switch X / Switch Y |
| Icons | 737848 Western (DualSense or Xbox) | Switch icons |

This repository holds no game files and no icons.

## Install / remove

1. Download the **DualSense – Western** or **Xbox – Western** file of [737848](https://gamebanana.com/mods/737848).
2. Quit the game, then:

```
./install.sh western ~/Downloads/<the Western zip, or the folder you unpacked it to>
./install.sh menu
./install.sh --uninstall                  # the module back byte for byte (SHA-256 checked), no icons
APP=/path/to/Other.app ./install.sh ...   # default: /Applications/The Legend of Zelda - Ocarina of Time.app
```

Needs Python 3 and Xcode's command line tools (`clang`, `otool`). The script patches
`Contents/Resources/dm/main.patched.bin` and re-signs the app ad-hoc, as it was packed (a custom Finder icon is set
aside while signing and put back). The icons go into a RomFS overlay folder,
`~/Library/Application Support/nxnative/0400486024DEC000/mods/oot-western-buttons/`, named by a `DM_ROMFS_OVERLAY=`
line in that folder's `env.txt`. Re-packing the app with nxnative replaces the module, so run the script again
afterwards. Builds of the module it knows are listed in `ORIGINALS` in [`build_mod.py`](build_mod.py) (all with the
same layout); others are refused.

An app with a launcher "Buttons" setting (Switch / Xbox / PlayStation, not in upstream nxnative) maps buttons by label
for Xbox and PlayStation; keep it at Switch with this mod.

## How it works

The code is in [`hooks.s`](hooks.s); [`build_mod.py`](build_mod.py) links it into the patch area after the module
(offset `0x5102000`, which the host maps read + execute) and branches to it from the game:

- **Swap** in `sead::Controller::calc` (`main+0x36a298`), right after the npad device controllers (vtable
  `main+0x4c61b00`) produce the frame's hold bits (`+0x114`: bit 0 A, 1 B, 3 X, 4 Y); trig, release and repeat
  come from those bits afterwards. `western` swaps A and B (layout `western-ab`). Merged controllers, which OR their
  children's bits, are skipped so nothing is swapped twice. (Layout `western`, swapping X and Y, is for an app whose
  Buttons setting maps every face button by its label.)
- **`menu` only:** menu detection at the menu-screen update (`main+0x2d1380`): if any button of the screen's list
  (`+136/+144/+156`, entry `+24`, button `+56`, as miojo-recomp's `oot_menu.c` reads it) has focus, the frame is
  recorded, and A/B are swapped while a menu had focus within the last 24 frames. A/B held across a switch are
  ignored until released. State lives in an unused read-write page at `main+0x4ea8000`.

## Tested

Upstream nxnative `0b5fd602` (built with `5df3dbe8` reverted, which breaks this game's shader tables), scripted input
with a copy of a save, DualSense Western icons: the bottom button confirms and the right one cancels on the title,
Load and pause screens; the HUD shows R1/R2, the pause menu ✕ select / ○ back, and the Controls screen the DualSense
with ✕ action, ○ put away, △ jump, □ attack. Not tested with a physical controller in these runs.

## Credits

Icons: [DualSense & Xbox Button Prompts](https://gamebanana.com/mods/737848) by Makine Çeviri. Menu-screen layout:
miojo-recomp's `oot_menu.c`.

Related: [joaobyss/oot-switch2-button-prompts](https://github.com/joaobyss/oot-switch2-button-prompts) (emulator icons,
Nintendo positions); nxnative [#2773](https://github.com/seedds/nxnative/pull/2773) /
[#2774](https://github.com/seedds/nxnative/pull/2774) (a `DM_PAD_LAYOUT` setting and OoT icon overlays proposed
upstream).
