"""Shared fixtures. Tests that need a bundle skip when it is not on disk.

- DXM_GENPHENIA_BUNDLE: an unpacked genphenia-v3.0 (model-v3.0.0), writable,
  since the engine writes its state/ there. Default models/base/genphenia-v3.0.
- DXM_RERANK_BUNDLE: a filled re-ranker bundle (scripts/build_rerank_bundle.sh).
  Default models/rerank/rerank-v1.0.
- DXM_PARITY_CASES: the parity cases. Default tests/fixtures/r1-dev-parity-sample.json.
"""

import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

from diagnostic_ar_model import rerank
from diagnostic_ar_model.rerank.bundle import CONFIG, KB, ONTOLOGY

REPO = Path(__file__).resolve().parents[1]
GENPHENIA_BUNDLE = Path(os.environ.get("DXM_GENPHENIA_BUNDLE", REPO / "models/base/genphenia-v3.0"))
RERANK_BUNDLE = Path(os.environ.get("DXM_RERANK_BUNDLE", REPO / "models/rerank/rerank-v1.0"))
PARITY_CASES = Path(os.environ.get("DXM_PARITY_CASES", REPO / "tests/fixtures/r1-dev-parity-sample.json"))


def _import_engine():
    """The vendored engine imports itself as `inference_engine`, as diagnostic.ar-api installs it."""
    if "inference_engine" not in sys.modules:
        vendor = REPO / "vendor" / "genphenia_inference_engine"
        spec = importlib.util.spec_from_file_location(
            "inference_engine", vendor / "__init__.py", submodule_search_locations=[str(vendor)]
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["inference_engine"] = module
        spec.loader.exec_module(module)
    from inference_engine import engine, preprocess

    return engine, preprocess


class V3:
    """v3.0 probabilities for a list of present terms, the way diagnostic.ar-api computes them."""

    def __init__(self, bundle_dir: Path) -> None:
        engine_mod, preprocess = _import_engine()
        self.engine = engine_mod.GenpheniaEngine.load(bundle_dir)
        self._softmax = engine_mod._softmax
        self._normalize = preprocess.normalize_hpo_id
        self.genes = self.engine.genes

    def known(self, present: list[str]) -> list[str]:
        """diagnostic.ar-api's split_known_ids, keeping the known part."""
        index = self.engine.preprocessor.hpo_dag.id_to_idx
        return [t for t in map(self._normalize, present) if t in index]

    def probabilities(self, present: list[str]) -> np.ndarray:
        graph = self.engine.preprocessor.preprocess(self.known(present))
        logits = self.engine.runtime.predict_logits(graph)
        return self._softmax(logits.reshape(1, -1)[0])


def rank_of(probs: np.ndarray, genes: tuple[str, ...], gene: str) -> float:
    """diagnostic.ar-training rerank/grid.py `_records`: ties count against the true gene."""
    idx = {g.upper(): i for i, g in enumerate(genes)}[gene.upper()]
    target = probs[idx]
    return float(1 + (probs > target).sum() + ((probs == target).sum() - 1))


@pytest.fixture(scope="session")
def v3() -> V3:
    pytest.importorskip("onnxruntime")
    if not (GENPHENIA_BUNDLE / "checkpoints").is_dir():
        pytest.skip(f"no genphenia-v3.0 bundle at {GENPHENIA_BUNDLE}")
    return V3(GENPHENIA_BUNDLE)


@pytest.fixture(scope="session")
def reranker(v3):
    if not all((RERANK_BUNDLE / f).is_file() for f in (CONFIG, KB, ONTOLOGY)):
        pytest.skip(f"no filled re-ranker bundle at {RERANK_BUNDLE}")
    return rerank.load(RERANK_BUNDLE, v3.genes)


@pytest.fixture(scope="session")
def parity_cases() -> list[dict]:
    return json.loads(PARITY_CASES.read_text())["cases"]
