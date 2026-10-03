"""Without negated terms the re-ranker must return v3.0's output bit for bit."""

import json
import shutil

import numpy as np
import pytest

from diagnostic_ar_model.rerank.bundle import CONFIG, read_config, verify
from diagnostic_ar_model.rerank.knowledge import GeneKnowledge, Ontology
from diagnostic_ar_model.rerank.model import ReRanker

from conftest import RERANK_BUNDLE

GENES = ("A", "B", "C", "D")
KB = {
    "schema": 2,
    "diseases": {
        "OMIM:1": {"phenotypes": {"HP:0000003": {"freq": 0.8, "onset": [], "sex": None}}},
        "OMIM:2": {"phenotypes": {"HP:0000004": {"freq": None, "onset": [], "sex": None}}},
    },
    "genes": {"A": {"OMIM:1": 1.0}, "B": {"OMIM:2": 1.0}},
    "vocabulary": {},
}
PARENTS = {"HP:0000001": (), "HP:0000002": ("HP:0000001",), "HP:0000003": ("HP:0000002",), "HP:0000004": ()}


def toy(top_k: int = 4) -> ReRanker:
    return ReRanker(GeneKnowledge(KB, Ontology(PARENTS)), GENES, neg_weight=0.5, top_k=top_k)


def probs() -> np.ndarray:
    return np.array([0.4, 0.3, 0.2, 0.1])


@pytest.mark.parametrize("excluded", [None, (), []])
def test_no_negations_returns_the_input_unchanged(excluded):
    p = probs()
    out = toy().rerank(p, excluded)
    assert out is p
    assert out.tobytes() == probs().tobytes()


def test_negations_no_gene_annotates_leave_the_input_unchanged():
    p = probs()
    assert toy().rerank(p, ["HP:0000009", "HP:0000001x"]) is p


def test_a_negated_annotated_term_penalises_its_gene():
    out = toy().rerank(probs(), ["HP:0000002"])
    assert out[0] < 0.4 and out[1:].tolist() == sorted(out[1:].tolist(), reverse=True)
    assert out.sum() == pytest.approx(1.0)


def test_only_the_top_k_genes_move():
    p = np.array([0.1, 0.2, 0.3, 0.4])
    out = toy(top_k=2).rerank(p, ["HP:0000002"])
    assert out is p


def test_distribution_without_negations_is_the_same_object():
    dist = dict(zip(GENES, probs().tolist(), strict=True))
    assert toy().rerank_distribution(dist) is dist


def test_distribution_keys_must_follow_the_engine_order():
    dist = dict(zip(reversed(GENES), probs().tolist(), strict=True))
    with pytest.raises(ValueError):
        toy().rerank_distribution(dist, ["HP:0000002"])


def test_declared_configuration_is_the_validated_one():
    config = read_config(RERANK_BUNDLE)
    assert config["name"] == "rr-v1[neg=0.5]"
    assert config["weights"] == {"neg": 0.5, "sex": 0.0, "age": 0.0, "onset": 0.0}
    assert config["params"] == {"neg_strength": 0.5, "unknown_frequency": 0.3, "top_k": 200}
    assert config["files"]["kb.json.gz"]["artifact_id"] == "kb-v3"
    manifest = json.loads((RERANK_BUNDLE / config["files"]["kb.json.gz"]["manifest"]).read_text())
    assert manifest["artifact_id"] == "kb-v3"
    assert manifest["outputs"][0]["sha256"] == config["files"]["kb.json.gz"]["sha256"]
    hpo = next(i for i in manifest["inputs"] if i["id"] == config["files"]["hp.json"]["artifact_id"])
    assert hpo["sha256"] == config["files"]["hp.json"]["sha256"]


def test_a_tampered_file_is_refused(tmp_path):
    bundle = tmp_path / "b"
    bundle.mkdir()
    shutil.copy(RERANK_BUNDLE / CONFIG, bundle / CONFIG)
    for name in read_config(bundle)["files"]:
        (bundle / name).write_bytes(b"not the pinned file")
    with pytest.raises(ValueError, match="sha256"):
        verify(bundle)


def test_real_v3_outputs_pass_through_bit_identical(v3, reranker, parity_cases):
    for case in parity_cases:
        p = v3.probabilities(case["present"])
        before = p.tobytes()
        out = reranker.rerank(p, None)
        assert out is p and out.tobytes() == before
        assert reranker.rerank(p, []) is p
