#!/bin/zsh
# install.sh western <737848 Western zip or folder>
#     A (Cross) bottom / B (Circle) right everywhere, X / Y (Triangle / Square) at their Nintendo positions, with the
#     "Western" icons of "DualSense & Xbox Button Prompts" by Makine Çeviri (gamebanana.com/mods/737848): download
#     its DualSense or Xbox "Western" file and give the zip (or the folder you unpacked it to).
# install.sh menu
#     Switch icons; menus confirm with the bottom button / cancel with the right one, gameplay keeps Nintendo positions.
# install.sh --uninstall
#     The game module back byte for byte (SHA-256 checked), no icon overlay.
# Quit the game first. Needs Xcode's command line tools (clang, otool). The app is the upstream nxnative one: buttons by
# position, as on a Switch (an app with a Buttons setting: keep it at Switch).
set -e
APP=${APP:-"/Applications/The Legend of Zelda - Ocarina of Time.app"}
HERE=${0:A:h}
BIN="$APP/Contents/Resources/dm/main.patched.bin"
SUP="$HOME/Library/Application Support/nxnative/0400486024DEC000"
OVL="$SUP/mods/oot-western-buttons"
usage() { echo "usage: install.sh western <737848 Western zip or folder> | menu | --uninstall"; exit 1; }
[[ -f "$BIN" ]] || { echo "No game module at $BIN (set APP=<the app>)."; exit 1; }
pgrep -f "$APP/Contents/MacOS/dmhost" >/dev/null && { echo "Quit the game first."; exit 1; }
mode=${1:-}
[[ $mode == (menu|western|--uninstall) ]] || usage
SRC=""; TMP=""; ORIG=""
trap 'rm -f "$TMP" "$ORIG"; [[ -n $SRC ]] && rm -rf "$SRC"' EXIT

# icons: find the pack's romfs folder before touching anything
if [[ $mode == western ]]; then
  [[ -n ${2:-} && -e $2 ]] || usage
  SRC=$(mktemp -d)
  if [[ -f $2 ]]; then unzip -q "$2" -d "$SRC"; else cp -R "$2" "$SRC/pack"; fi
  ROMFS=("$SRC"/**/romfs(/N))
  (( ${#ROMFS} == 1 )) || { echo "Expected one romfs folder in $2, found ${#ROMFS}."; exit 1; }
  ROMFS=$ROMFS[1]
  [[ -f "$ROMFS/Font2/Scalable/External.Nin_Ounce_NVN2.bfotf.zs" ]] || { echo "$2 is not a button prompt pack for this game."; exit 1; }
  [[ ${ROMFS:h:t} == *Western* ]] || echo "Note: ${ROMFS:h:t} is not a Western version; the icons will not match the buttons."
fi

# game module: back to the original first, then the chosen layout
state=$(python3 "$HERE/build_mod.py" --check "$BIN")
TMP=$(mktemp "${BIN:h}/.main.XXXXXX"); ORIG=$(mktemp "${BIN:h}/.orig.XXXXXX")
case $state in
  original) cp "$BIN" "$ORIG" ;;
  menu|western|western-ab) python3 "$HERE/build_mod.py" --restore "$BIN" "$ORIG" ;;
  *) echo "main.patched.bin is not a file this mod knows ($state)."; exit 1 ;;
esac
case $mode in
  western) python3 "$HERE/build_mod.py" --layout western-ab "$ORIG" "$TMP" ;;
  menu) python3 "$HERE/build_mod.py" --layout menu "$ORIG" "$TMP" ;;
  --uninstall) cp "$ORIG" "$TMP" ;;
esac
chmod 644 "$TMP"; mv -f "$TMP" "$BIN"

# icon overlay: a RomFS overlay folder named in the game's env.txt (DM_ROMFS_OVERLAY)
mkdir -p "$SUP"; touch "$SUP/env.txt"
grep -v -e '^DM_ROMFS_OVERLAY=.*/mods/oot-western' -e '^# oot-' "$SUP/env.txt" > "$SUP/env.txt.new" || true
rm -rf "$SUP"/mods/oot-western*(N)
if [[ $mode == western ]]; then
  grep -q '^DM_ROMFS_OVERLAY=' "$SUP/env.txt.new" && { rm "$SUP/env.txt.new"; echo "env.txt already sets another DM_ROMFS_OVERLAY; the icons are not installed."; exit 1; }
  mkdir -p "${OVL:h}"; cp -R "$ROMFS" "$OVL"
  printf '# oot-western-buttons: %s\nDM_ROMFS_OVERLAY=%s\n' "${ROMFS:h:t}" "$OVL" >> "$SUP/env.txt.new"
fi
mv "$SUP/env.txt.new" "$SUP/env.txt"

# the bundle seals Resources: sign the outer app again, ad-hoc as packed, keeping its identifier and flags. A custom
# Finder icon (an Icon\r file in the bundle and its Finder info) is not allowed in a signed bundle: set it aside for that.
ICON=$(printf '%s/Icon\r' "$APP"); KEEP=$(mktemp -d); FI=""
[[ -e $ICON ]] && { ditto "$ICON" "$KEEP/Icon"; rm "$ICON"; }
FI=$(xattr -px com.apple.FinderInfo "$APP" 2>/dev/null) && xattr -d com.apple.FinderInfo "$APP"
codesign --force --sign - --preserve-metadata=identifier,entitlements,requirements,flags,runtime "$APP"
codesign --verify --deep --strict "$APP" && echo "signature OK"
[[ -e $KEEP/Icon ]] && ditto "$KEEP/Icon" "$ICON"; [[ -n $FI ]] && xattr -wx com.apple.FinderInfo "$FI" "$APP"; rm -rf "$KEEP"
echo "module: $(python3 "$HERE/build_mod.py" --check "$BIN")"
[[ $mode == western ]] && echo "icons: ${ROMFS:h:t} (overlay in $OVL)"
exit 0
