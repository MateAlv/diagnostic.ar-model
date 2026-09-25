#!/usr/bin/env bash
# Packs a model bundle into the tarball a GitHub release carries, and prints
# its sha256 — the value diagnostic.ar-api pins to serve it.
#
#   scripts/package_bundle.sh models/base/genphenia-v3.0 dist/
#
# The archive is reproducible: fixed order, owner and mtime, and gzip without
# a timestamp, so packing the same files twice gives the same hash. The
# engine's state/ directory is written on load and is not part of a bundle.
set -euo pipefail

bundle=${1:?usage: package_bundle.sh <bundle-dir> <out-dir>}
out=${2:?usage: package_bundle.sh <bundle-dir> <out-dir>}
name=$(basename "$bundle")
mkdir -p "$out"

tar --sort=name --mtime='2026-02-20 00:00Z' --owner=0 --group=0 --numeric-owner \
    --exclude=state -C "$(dirname "$bundle")" -cf - "$name" \
  | gzip -n -9 > "$out/$name.tar.gz"

(cd "$out" && sha256sum "$name.tar.gz" | tee "$name.tar.gz.sha256")
