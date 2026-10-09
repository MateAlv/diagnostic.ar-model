#!/usr/bin/env bash
# Packs ft-v1.1-confirmed into the tarball its GitHub release carries, and
# prints its sha256: the value diagnostic.ar-api pins in model.lock.
#
#   scripts/package_ft.sh dist/
#
# Only what the service loads goes in: ft.json, ft_prod.py and the bundle,
# each checked against ft.json first. The parity fixture is for tests and
# stays out. Reproducible, as scripts/package_bundle.sh.
set -euo pipefail

out=${1:?usage: package_ft.sh <out-dir>}
src=models/ft/ft-v1.1-confirmed
name=ft-v1.1-confirmed
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

python3 - "$src" <<'PY'
import hashlib, json, pathlib, sys
src = pathlib.Path(sys.argv[1])
for name, entry in json.loads((src / "ft.json").read_text())["files"].items():
    actual = hashlib.sha256((src / name).read_bytes()).hexdigest()
    if actual != entry["sha256"]:
        sys.exit(f"{src / name}: sha256 {actual}, expected {entry['sha256']}")
PY

mkdir -p "$work/$name" "$out"
cp "$src/ft.json" "$src/ft_prod.py" "$src/ft-v1.1-confirmed-bundle.json.gz" "$work/$name/"
scripts/package_bundle.sh "$work/$name" "$out"
