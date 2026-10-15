#!/usr/bin/env bash
# Packs the v4 layer into the tarball the model-v4.0.0 release carries, and
# prints its sha256: the value diagnostic.ar-api pins in model.lock.
#
#   scripts/package_v4_layer.sh dist/
#
# Only what the service loads goes in: v4.json, v4_layer.py and the bundle,
# each checked against v4.json first. The staging fixture is for tests and
# stays out. Reproducible, as scripts/package_bundle.sh.
set -euo pipefail

out=${1:?usage: package_v4_layer.sh <out-dir>}
src=models/v4/v4-layer
name=v4-layer
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

python3 - "$src" <<'PY'
import hashlib, json, pathlib, sys
src = pathlib.Path(sys.argv[1])
for name, entry in json.loads((src / "v4.json").read_text())["files"].items():
    actual = hashlib.sha256((src / name).read_bytes()).hexdigest()
    if actual != entry["sha256"]:
        sys.exit(f"{src / name}: sha256 {actual}, expected {entry['sha256']}")
PY

mkdir -p "$work/$name" "$out"
cp "$src/v4.json" "$src/v4_layer.py" "$src/v4-layer-bundle.json.gz" "$work/$name/"
scripts/package_bundle.sh "$work/$name" "$out"
