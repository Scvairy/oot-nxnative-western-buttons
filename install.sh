#!/bin/zsh
# install.sh western [xbox|playstation]
#                      A (Cross) bottom / B (Circle) right everywhere, X/Y at Nintendo positions, with icons to match
#                      (X/Y symbols, HUD action diamond, ocarina notes).
#                      - An app with the launcher's Buttons setting (the prebuilt app): set Buttons = Xbox or
#                        PlayStation; both of its icon packs are fixed, the style argument is not needed.
#                      - An app without it (upstream nxnative, which maps buttons by position like Nintendo): the hook
#                        swaps A/B, and the chosen style's icons (default playstation) go into a RomFS overlay folder
#                        in the game's Application Support folder, named in its env.txt (DM_ROMFS_OVERLAY).
# install.sh menu      Buttons = Switch (or an app without the setting): menus confirm bottom / cancel right, gameplay
#                      keeps Nintendo positions
# install.sh --uninstall   everything back as packed
# Quit the game first. Needs the tools venv (zstandard, fontTools, Pillow, numpy) for the icons, and macOS sips.
set -e
APP=${APP:-"/Applications/The Legend of Zelda - Ocarina of Time.app"}
HERE=${0:A:h}
PY=${PY:-$([[ -x $HERE/.venv/bin/python ]] && echo $HERE/.venv/bin/python || echo python3)}   # zstandard, fontTools, Pillow, numpy
export OOT_ROMFS="$APP/Contents/Resources/romfs.img"
BIN="$APP/Contents/Resources/dm/main.patched.bin"
SUP="$HOME/Library/Application Support/nxnative/0400486024DEC000"
STYLES=(xbox playstation)
FILES=(Font2/Scalable/External.Nin_Ounce_NVN2.bfotf.zs UI/Layout2Archive/Common.Product.100.Nin_Ounce_NVN2.blarc.zs
       UI/Layout2Archive/Common.Product.100.Nin_Ounce_NVN2.bntx.zs)
RSIZE=System/Resource/ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable.zs
pgrep -f "$APP/Contents/MacOS/dmhost" >/dev/null && { echo "Quit the game first."; exit 1; }
mode=${1:-menu}
[[ $mode == (menu|western|--uninstall) ]] || { echo "usage: install.sh western [xbox|playstation] | menu | --uninstall"; exit 1; }
style=${2:-playstation}
[[ $style == (xbox|playstation) ]] || { echo "style: xbox or playstation"; exit 1; }
grep -q DM_PAD_STYLE "$APP/Contents/Resources/dm/launcher.json" && packs=1 || packs=0

# icons: keep each packed pack's files once (backup/icons_<style>; ABSENT lists the files a pack did not have)
for st in $STYLES; do
  ICONS="$APP/Contents/Resources/icons/$st"; BAK="$HERE/backup/icons_$st"
  [[ -f "$BAK/.done" ]] && continue
  (( packs )) || { echo "No backup of the $st pack: run this once on the prebuilt app (with the Buttons setting) first."; exit 1; }
  mkdir -p "$BAK"; : > "$BAK/ABSENT"
  for f in $FILES $RSIZE; do
    if [[ -f "$BAK/$f" ]]; then continue
    elif [[ -f "$ICONS/$f" ]]; then mkdir -p "$BAK/${f:h}"; cp "$ICONS/$f" "$BAK/$f"
    else echo "$f" >> "$BAK/ABSENT"; fi
  done
  touch "$BAK/.done"
done

# game module: back to the original first, then the chosen layout
state=$(python3 "$HERE/build_mod.py" --check "$BIN")
TMP=$(mktemp "${BIN:h}/.main.XXXXXX"); ORIG=$(mktemp "${BIN:h}/.orig.XXXXXX")
trap 'rm -f "$TMP" "$ORIG"' EXIT
case $state in
  original) cp "$BIN" "$ORIG" ;;
  menu|western|western-ab) python3 "$HERE/build_mod.py" --restore "$BIN" "$ORIG" ;;
  *) echo "main.patched.bin is not a file this mod knows ($state)."; exit 1 ;;
esac
layout=$mode; [[ $mode == western ]] && (( ! packs )) && layout=western-ab
if [[ $mode == --uninstall ]]; then cp "$ORIG" "$TMP"; else python3 "$HERE/build_mod.py" --layout $layout "$ORIG" "$TMP"; fi
chmod 644 "$TMP"; mv -f "$TMP" "$BIN"

# icons
set_overlay() {   # env.txt: drop our DM_ROMFS_OVERLAY line, then add $1 if given
  mkdir -p "$SUP"; touch "$SUP/env.txt"
  grep -v -e '^DM_ROMFS_OVERLAY=.*/mods/oot-western-' -e '^# oot-menu-buttons' "$SUP/env.txt" > "$SUP/env.txt.new" || true
  if [[ -n $1 ]]; then
    grep -q '^DM_ROMFS_OVERLAY=' "$SUP/env.txt.new" && { rm "$SUP/env.txt.new"; echo "env.txt already sets another DM_ROMFS_OVERLAY"; exit 1; }
    printf '# oot-menu-buttons: western button icons\nDM_ROMFS_OVERLAY=%s\n' "$1" >> "$SUP/env.txt.new"
  fi
  mv "$SUP/env.txt.new" "$SUP/env.txt"
}
if (( packs )); then
  for st in $STYLES; do
    ICONS="$APP/Contents/Resources/icons/$st"; BAK="$HERE/backup/icons_$st"
    if [[ $mode == western ]]; then
      OUT=$(mktemp -d); "$PY" "$HERE/icons_western.py" "$BAK" "$OUT" $st
      for f in $FILES; do mkdir -p "$ICONS/${f:h}"; cp "$OUT/$f" "$ICONS/$f"; done; rm -rf "$OUT"
    else
      for f in $FILES; do
        if grep -qxF "$f" "$BAK/ABSENT"; then rm -f "$ICONS/$f"; else cp "$BAK/$f" "$ICONS/$f"; fi
      done
    fi
  done
else
  rm -rf "$SUP"/mods/oot-western-*(N)
  if [[ $mode == western ]]; then
    OVL="$SUP/mods/oot-western-$style"; mkdir -p "$OVL/${RSIZE:h}"
    "$PY" "$HERE/icons_western.py" "$HERE/backup/icons_$style" "$OVL" $style
    cp "$HERE/backup/icons_$style/$RSIZE" "$OVL/$RSIZE"   # the pack's size table (its font is larger than the game's)
    set_overlay "$OVL"
  else
    set_overlay ""
  fi
fi

# the bundle seals Resources: sign the outer app again, ad-hoc as packed, keeping its identifier and flags
codesign --force --sign - --preserve-metadata=identifier,entitlements,requirements,flags,runtime "$APP"
codesign --verify --deep --strict "$APP" && echo "signature OK"
echo "module: $(python3 "$HERE/build_mod.py" --check "$BIN")"
case $mode in
  western) (( packs )) && echo "Set Buttons = Xbox or PlayStation in the game's launcher." || echo "Icons: $style (overlay in $OVL)." ;;
  menu) (( packs )) && echo "Set Buttons = Switch in the game's launcher." ;;
esac
