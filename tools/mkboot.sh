#!/bin/bash
# Pack the Moonstone XNU boot image: ADT -> SWEETXNU payload -> shim boot image.
#   tools/mkboot.sh KERNEL [OUT.img] [--qemu]
# KERNEL is kernel.development.sweet from the CI artifact (xnu-kernel).
#   CMDLINE=...   boot args (default: safe first-kernel-entry smoke test)
# --qemu writes a payload for tools/qemu-sweet.py instead.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
KERNEL=$(realpath "$1")
OUT=${2:-$ROOT/out/moonstone-xnu-boot.img}
OUT_V4="${OUT%.img}-v4.img"
mkdir -p "$ROOT/out"
CMDLINE=${CMDLINE:-'debug=0xc cpus=1 keepsyms=1 -noprogress wdt=-1 sweetgpu=0 sweetfb_flip=0'}

if [ "${3:-}" = --qemu ]; then
	python3 "$ROOT/tools/mkadt.py" "$ROOT/out/qemu.adt" --qemu
	python3 "$ROOT/tools/mkpayload.py" "$KERNEL" "$ROOT/out/qemu.adt" "$ROOT/out/qemu-payload.bin" \
		--cmdline "${CMDLINE/rd=ufsroot0/}"
	echo "QEMU payload: $ROOT/out/qemu-payload.bin"
	exit 0
fi

python3 "$ROOT/tools/mkadt.py" "$ROOT/out/moonstone.adt"
python3 "$ROOT/tools/mkpayload.py" "$KERNEL" "$ROOT/out/moonstone.adt" "$ROOT/out/payload.bin" --cmdline "$CMDLINE"
"$ROOT/shim/build.sh" "$ROOT/out/payload.bin" >/dev/null
cp "$ROOT/shim/out/shim-boot.img" "$OUT"
cp "$ROOT/shim/out/shim-boot-v4.img" "$OUT_V4"
size=$(stat -c%s "$OUT")
size_v4=$(stat -c%s "$OUT_V4")
# boot_a is 128 MiB
[ "$size" -lt $((128 << 20)) ] || { echo "error: $OUT is $size bytes, boot_a is 128 MiB" >&2; exit 1; }
[ "$size_v4" -lt $((128 << 20)) ] || { echo "error: $OUT_V4 is $size_v4 bytes, boot_a is 128 MiB" >&2; exit 1; }
echo "cmdline: $CMDLINE"
ls -l "$OUT" "$OUT_V4"
sha256sum "$OUT" "$OUT_V4"
