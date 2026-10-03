#!/usr/bin/env bash
# Fills a re-ranker bundle directory with the files its rerank.json pins, and
# checks each one's sha256. Nothing is rebuilt: the KB is the published
# diagnostic.ar-training artifact, and hp.json the HPO release.
#
#   scripts/build_rerank_bundle.sh models/rerank/rerank-v1.0
#   scripts/package_bundle.sh models/rerank/rerank-v1.0 dist/
#
# hp.json is copied from data/raw/hpo/hp.json (dvc pull) when present, and
# downloaded from its source URL otherwise. The KB comes from the training
# repo's release, which needs gh with access to it. The bundle directory must
# hold only rerank.json, the source manifest and the files this script adds.
set -euo pipefail

bundle=${1:?usage: build_rerank_bundle.sh <bundle-dir>}
repo_root=$(cd "$(dirname "$0")/.." && pwd)
config="$bundle/rerank.json"
if [ ! -f "$config" ]; then
  echo "missing $config" >&2
  exit 1
fi

field() {
  python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["files"][sys.argv[2]][sys.argv[3]])' \
    "$config" "$1" "$2"
}

check() {
  local name=$1 expected actual
  expected=$(field "$name" sha256)
  actual=$(sha256sum "$bundle/$name" | cut -d' ' -f1)
  if [ "$actual" != "$expected" ]; then
    echo "$bundle/$name: sha256 $actual, expected $expected" >&2
    exit 1
  fi
  echo "ok  $name  $actual"
}

kb_url=$(field kb.json.gz source)
kb_tag=$(basename "$(dirname "$kb_url")")
if ! gh release download "$kb_tag" -R MateAlv/diagnostic.ar-training -p kb.json.gz -D "$bundle" --clobber; then
  echo "could not download kb.json.gz from release $kb_tag" >&2
  exit 1
fi
check kb.json.gz

if [ -f "$repo_root/data/raw/hpo/hp.json" ]; then
  cp "$repo_root/data/raw/hpo/hp.json" "$bundle/hp.json"
elif ! curl -fsSL -o "$bundle/hp.json" "$(field hp.json source)"; then
  echo "could not download hp.json" >&2
  exit 1
fi
check hp.json

# The tarball stores file modes, so they must not depend on the umask.
chmod 0755 "$bundle"
chmod 0644 "$bundle"/*
