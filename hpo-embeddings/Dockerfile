# syntax=docker/dockerfile:1.7
#
# Generates the HPO embeddings of the symptom extractor and exports them as one
# tarball. Run through build.sh, which reads embeddings.lock:
#
#   hpo-embeddings/build.sh            # -> hpo-embeddings/dist/
#
# The environment is the extractor's own (diagnostic.ar-api,
# services/api-gateway/Dockerfile.recognizer): Python 3.12, CPU torch and the
# library versions spanish-symptoms-recognizer pins, so the vectors are the
# ones the extractor would compute itself.

FROM python:3.12-slim AS generate

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# CPU wheels first, so nothing below pulls the CUDA build back in.
RUN pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cpu
RUN pip install transformers==5.15.0 tokenizers==0.22.2 safetensors==0.8.0 \
        huggingface_hub==1.27.0 numpy==2.5.2

ARG CLINLINKER_REPO
ARG CLINLINKER_REVISION
ARG HPO_TRANSLATIONS_COMMIT

# The script resolves its paths next to itself: the encoder in
# semantic_model/, the labels in hpo/, the output in hpo/hpo_batches/.
WORKDIR /work/mapper
RUN test -n "$CLINLINKER_REVISION" && test -n "$HPO_TRANSLATIONS_COMMIT" \
    && python -c "from huggingface_hub import snapshot_download; snapshot_download('${CLINLINKER_REPO}', revision='${CLINLINKER_REVISION}', local_dir='semantic_model/clinlinker-kb-gp', allow_patterns=['*.json', '*.txt', 'pytorch_model.bin'])" \
    && rm -rf semantic_model/clinlinker-kb-gp/.cache \
    && mkdir -p hpo \
    && curl -fsSL -o hpo/hp-es.babelon.tsv \
        "https://raw.githubusercontent.com/obophenotype/hpo-translations/${HPO_TRANSLATIONS_COMMIT}/babelon/hp-es.babelon.tsv"

COPY generator/hpo_tsv_reader.py ./hpo_tsv_reader.py
COPY embeddings.lock /work/embeddings.lock

RUN python hpo_tsv_reader.py

# The package: the embeddings, the labels they were made from (the extractor
# reads both at run time, so they travel together) and a manifest recording
# where they came from and the sha256 of every file. No timestamps anywhere,
# so the tarball's own hash depends only on its contents.
RUN mkdir -p /pkg/hpo \
    && cp -r hpo/hpo_batches /pkg/hpo/ \
    && cp hpo/hp-es.babelon.tsv /pkg/hpo/ \
    && python - <<'PY'
import hashlib, json, pathlib
import torch, transformers

lock = dict(
    line.split("=", 1)
    for line in pathlib.Path("/work/embeddings.lock").read_text().splitlines()
    if line and not line.startswith("#")
)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
pkg = pathlib.Path("/pkg")
files = sorted(p for p in pkg.rglob("*") if p.is_file())
batches = [p for p in files if p.suffix == ".pt"]
manifest = {
    "version": lock["VERSION"],
    "clinlinker_repo": lock["CLINLINKER_REPO"],
    "clinlinker_revision": lock["CLINLINKER_REVISION"],
    "hpo_translations_commit": lock["HPO_TRANSLATIONS_COMMIT"],
    "generator_source_commit": lock["GENERATOR_SOURCE_COMMIT"],
    "generator_sha256": sha(pathlib.Path("/work/mapper/hpo_tsv_reader.py")),
    "torch": torch.__version__,
    "transformers": transformers.__version__,
    "terms": sum(len(torch.load(p, weights_only=False)) for p in batches),
    "files": {str(p.relative_to(pkg)): sha(p) for p in files},
}
(pkg / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
print(f"{manifest['terms']} terms in {len(batches)} batches")
PY

RUN mkdir /out \
    && tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C /pkg -cf - . \
        | gzip -n -9 > /out/hpo-embeddings-clinlinker-kb-gp.tar.gz \
    && cd /out && sha256sum hpo-embeddings-clinlinker-kb-gp.tar.gz > hpo-embeddings-clinlinker-kb-gp.tar.gz.sha256 \
    && cp /pkg/manifest.json /out/manifest.json

FROM scratch AS export
COPY --from=generate /out/ /
