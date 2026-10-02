#!/usr/bin/env bash
# Generates the extractor's HPO embeddings as pinned in embeddings.lock and
# leaves them in hpo-embeddings/dist/:
#
#   hpo-embeddings-clinlinker-kb-gp.tar.gz          the package (embeddings + labels + manifest)
#   hpo-embeddings-clinlinker-kb-gp.tar.gz.sha256
#   manifest.json                                   a copy, to read without unpacking
#
# The publishing workflow runs this after a merge that changes the lock; anyone
# can run it too, to inspect or compare. Needs Docker with BuildKit. A few
# minutes on a recent CPU, ~11 on a GitHub runner.
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=/dev/null
. "$here/embeddings.lock"

for v in VERSION CLINLINKER_REPO CLINLINKER_REVISION HPO_TRANSLATIONS_COMMIT GENERATOR_SHA256; do
    [ -n "${!v:-}" ] || { echo "ERROR: $v is empty in embeddings.lock" >&2; exit 1; }
done

# The copy must be the recognizer's script, unchanged: the extractor compares
# its own script against the hash recorded in the package.
echo "$GENERATOR_SHA256  $here/generator/hpo_tsv_reader.py" | sha256sum -c --quiet \
    || { echo "ERROR: generator/hpo_tsv_reader.py does not match GENERATOR_SHA256" >&2; exit 1; }

rm -rf "$here/dist"
docker buildx build \
    --build-arg CLINLINKER_REPO="$CLINLINKER_REPO" \
    --build-arg CLINLINKER_REVISION="$CLINLINKER_REVISION" \
    --build-arg HPO_TRANSLATIONS_COMMIT="$HPO_TRANSLATIONS_COMMIT" \
    --target export \
    --output "type=local,dest=$here/dist" \
    "$here"

(cd "$here/dist" && sha256sum -c --quiet hpo-embeddings-clinlinker-kb-gp.tar.gz.sha256)
echo "hpo-embeddings-v$VERSION: $(cut -d' ' -f1 "$here/dist/hpo-embeddings-clinlinker-kb-gp.tar.gz.sha256")"
