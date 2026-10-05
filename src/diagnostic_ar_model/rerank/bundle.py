"""Load a re-ranker bundle: `rerank.json` plus the files it pins by sha256."""

import gzip
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

from diagnostic_ar_model.rerank.knowledge import FeatureParams, GeneKnowledge, Ontology
from diagnostic_ar_model.rerank.model import ReRanker

CONFIG = "rerank.json"
KB = "kb.json.gz"
ONTOLOGY = "hp.json"
V1_1_WEIGHTS = {"neg": 0.5, "sex": 0.0, "age": 0.0, "onset": 0.25}
DEFAULT_ONSET_SMOOTHING = 0.1


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_config(bundle_dir: Path) -> dict:
    return json.loads((Path(bundle_dir) / CONFIG).read_text())


def verify(bundle_dir: Path) -> dict:
    """The bundle's config, once every pinned file matches its sha256."""
    bundle_dir = Path(bundle_dir)
    config = read_config(bundle_dir)
    for name, entry in config["files"].items():
        actual = sha256_file(bundle_dir / name)
        if actual != entry["sha256"]:
            raise ValueError(f"{bundle_dir / name}: sha256 {actual}, expected {entry['sha256']}")
    weights = config["weights"]
    if weights.get("onset", 0) != 0:
        if weights != V1_1_WEIGHTS:
            raise ValueError(f"the only onset weights this module implements are {V1_1_WEIGHTS}, got {weights}")
    else:
        unsupported = {f: w for f, w in weights.items() if f != "neg" and w != 0}
        if unsupported:
            raise ValueError(f"unsupported weights {unsupported}: only negation, or rerank-v1.1's onset")
    return config


def load(bundle_dir: Path, genes: Sequence[str]) -> ReRanker:
    """A ReRanker over `genes`, the v3.0 output order (the engine's `genes`)."""
    bundle_dir = Path(bundle_dir)
    config = verify(bundle_dir)
    params = config["params"]
    with gzip.open(bundle_dir / KB, "rt", encoding="utf-8") as handle:
        kb = json.load(handle)
    knowledge = GeneKnowledge(
        kb,
        Ontology.from_json(bundle_dir / ONTOLOGY),
        FeatureParams(
            neg_strength=params["neg_strength"],
            unknown_frequency=params["unknown_frequency"],
            onset_smoothing=params.get("onset_smoothing", DEFAULT_ONSET_SMOOTHING),
        ),
    )
    return ReRanker(
        knowledge,
        genes,
        neg_weight=config["weights"]["neg"],
        top_k=params["top_k"],
        onset_weight=config["weights"].get("onset", 0.0),
    )
