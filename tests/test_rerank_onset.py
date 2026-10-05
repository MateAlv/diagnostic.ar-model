"""rerank-v1.1: the onset feature, its input mapping, the bundle check, and parity and identity."""

import json
import math

import numpy as np
import pytest

from diagnostic_ar_model.rerank import onset_years
from diagnostic_ar_model.rerank.bundle import V1_1_WEIGHTS, read_config, verify
from diagnostic_ar_model.rerank.knowledge import GeneKnowledge, Ontology, onset_bin
from diagnostic_ar_model.rerank.model import ReRanker
from diagnostic_ar_model.rerank.onset import HPO_ONSET_YEARS

from conftest import RERANK_BUNDLE, RERANK_V11_BUNDLE, rank_of

DAY = 1 / 365.25
WEB_CLASSES = {
    "HP:0030674": -0.375,
    "HP:0003577": 0.0,
    "HP:0003623": 14 * DAY,
    "HP:0003593": (28 * DAY + 1.0) / 2,
    "HP:0011463": 3.0,
    "HP:0003621": 10.0,
    "HP:0011462": 28.0,
    "HP:0003596": 50.0,
    "HP:0003584": 80.0,
}
WEB_BINS = {
    "HP:0030674": 0,
    "HP:0003577": 1,
    "HP:0003623": 1,
    "HP:0003593": 2,
    "HP:0011463": 3,
    "HP:0003621": 4,
    "HP:0011462": 5,
    "HP:0003596": 6,
    "HP:0003584": 7,
}


@pytest.mark.parametrize("hpo_id", WEB_CLASSES)
def test_every_web_class_maps_to_its_interval_midpoint(hpo_id):
    assert onset_years(onset_hpo_id=hpo_id) == pytest.approx(WEB_CLASSES[hpo_id], abs=1e-12)
    assert onset_years(onset_hpo_id=hpo_id.lower()) == onset_years(onset_hpo_id=hpo_id)


@pytest.mark.parametrize("hpo_id", WEB_CLASSES)
def test_each_class_midpoint_lands_in_the_bin_of_its_own_class(hpo_id):
    assert onset_bin(onset_years(onset_hpo_id=hpo_id)) == WEB_BINS[hpo_id]


def test_mapping_table_covers_the_training_classes():
    assert len(HPO_ONSET_YEARS) == 16
    assert set(WEB_CLASSES) <= set(HPO_ONSET_YEARS)


@pytest.mark.parametrize("age", [0, 0.0, 0.25, 7, 15.5, 60.0, 99.9])
def test_an_exact_age_wins_over_the_class(age):
    assert onset_years(onset_hpo_id="HP:0003584", onset_age_years=age) == float(age)


@pytest.mark.parametrize("bad", [-1, -0.001, math.nan, math.inf, "3", True, None])
def test_an_unusable_age_falls_back_to_the_class(bad):
    assert onset_years(onset_hpo_id="HP:0011463", onset_age_years=bad) == 3.0
    assert onset_years(onset_age_years=bad) is None


def test_symptom_onsets_take_the_earliest_value_per_symptom():
    symptoms = [
        {"hpo_id": "HP:1", "onset_hpo_id": "HP:0003584"},
        {"hpo_id": "HP:2", "onset_hpo_id": "HP:0003596", "onset_age_years": 45},
        {"hpo_id": "HP:3", "onset_hpo_id": "HP:0011463"},
    ]
    assert onset_years("HP:0003584", 45, symptoms) == 3.0
    assert onset_years(symptom_onsets=symptoms[:2]) == 45.0
    assert onset_years(symptom_onsets=iter(symptoms[:2])) == 45.0


def test_a_symptom_age_beats_its_own_class_even_when_later():
    entry = {"hpo_id": "HP:1", "onset_hpo_id": "HP:0003623", "onset_age_years": 2}
    assert onset_years(symptom_onsets=[entry]) == 2.0


def test_unusable_symptom_onsets_fall_through_to_the_patient_fields():
    junk = [{"hpo_id": "HP:1", "onset_hpo_id": "HP:9999999"}, {"onset_hpo_id": "HP:0011463x"}, "x", None, 3]
    assert onset_years("HP:0003621", None, junk) == 10.0
    assert onset_years(None, 4, junk) == 4.0
    assert onset_years(None, None, junk) is None
    assert onset_years(symptom_onsets=[]) is None
    assert onset_years(symptom_onsets="HP:0003621") is None
    assert onset_years(symptom_onsets=5) is None


@pytest.mark.parametrize(
    "hpo_id",
    ["HP:9999999", "", "HP:0034197", "HP:0011010", "HP:0003581x", None, 3, "acute"],
)
def test_unknown_and_non_age_classes_are_no_onset(hpo_id):
    assert onset_years(onset_hpo_id=hpo_id) is None


def test_nothing_is_no_onset():
    assert onset_years() is None


GENES = ("A", "B", "C", "D", "E")
KB = {
    "schema": 2,
    "diseases": {
        "D1": {"phenotypes": {"HP:0000003": {"freq": 0.8}}, "onset_years": [[0.0, 0.05]]},
        "D2": {"phenotypes": {"HP:0000004": {"freq": None}}, "onset_years": [[20.0, 30.0]]},
        "D3": {"phenotypes": {}, "onset_years": []},
    },
    "genes": {"A": {"D1": 1.0}, "B": {"D2": 1.0}, "C": {"D3": 1.0}},
    "vocabulary": {},
}
PARENTS = {"HP:0000002": (), "HP:0000003": ("HP:0000002",), "HP:0000004": ()}


def toy(onset_weight=0.25, top_k=5) -> ReRanker:
    knowledge = GeneKnowledge(KB, Ontology(PARENTS))
    return ReRanker(knowledge, GENES, neg_weight=0.5, top_k=top_k, onset_weight=onset_weight)


def probs() -> np.ndarray:
    return np.array([0.3, 0.3, 0.2, 0.1, 0.1])


def test_no_onset_returns_the_input_unchanged():
    p = probs()
    assert toy().rerank(p, None, None) is p
    assert toy().rerank(p, [], None) is p


def test_no_onset_equals_the_negation_only_reranker_bit_for_bit():
    for excluded in (["HP:0000002"], ["HP:0000004", "HP:0000002"]):
        a = toy().rerank(probs(), excluded, None)
        b = toy(onset_weight=0.0).rerank(probs(), excluded, 80.0)
        assert a.tobytes() == b.tobytes()


def test_onset_moves_genes_whose_diseases_start_in_that_bin():
    out = toy().rerank(probs(), None, 0.02)
    assert out[0] > 0.3 > out[1]
    assert out.sum() == pytest.approx(1.0)
    late = toy().rerank(probs(), None, 25.0)
    assert late[1] > 0.3 > late[0]


def test_onset_without_knowledge_leaves_the_input_unchanged():
    p = np.array([0.1, 0.1, 0.4, 0.2, 0.2])
    assert toy(top_k=1).rerank(p, None, 0.02) is p


def test_onset_and_negation_add_their_scores():
    p = probs()
    both = toy().rerank(p, ["HP:0000002"], 0.02)
    k = toy().knowledge
    scores = np.log(p)
    for i, gene in enumerate(GENES):
        scores[i] += 0.5 * k.neg_llr(gene, ("HP:0000002",)) + 0.25 * k.onset_llr(gene, 0.02)
    scores -= scores.max()
    expected = np.exp(scores) / np.exp(scores).sum()
    assert np.allclose(both, expected, rtol=0, atol=1e-15)


def test_distribution_passes_onset_through():
    dist = dict(zip(GENES, probs().tolist(), strict=True))
    assert toy().rerank_distribution(dist) is dist
    out = toy().rerank_distribution(dist, None, 0.02)
    assert list(out) == list(GENES) and out["A"] > dist["A"]


def config(weights, params=None, files=None) -> dict:
    return {
        "weights": weights,
        "params": params or {},
        "files": files or {},
    }


def write(tmp_path, cfg):
    (tmp_path / "rerank.json").write_text(json.dumps(cfg))
    return tmp_path


def test_verify_accepts_exactly_the_v1_1_weights(tmp_path):
    assert verify(write(tmp_path, config(V1_1_WEIGHTS)))["weights"] == V1_1_WEIGHTS


@pytest.mark.parametrize(
    "weights",
    [
        {"neg": 0.5, "sex": 0.0, "age": 0.0, "onset": 0.5},
        {"neg": 0.4, "sex": 0.0, "age": 0.0, "onset": 0.25},
        {"neg": 0.5, "sex": 0.1, "age": 0.0, "onset": 0.25},
        {"neg": 0.5, "sex": 0.0, "age": 0.1, "onset": 0.25},
        {"neg": 0.5, "onset": 0.25},
    ],
)
def test_verify_refuses_any_other_onset_weights(tmp_path, weights):
    with pytest.raises(ValueError, match="onset weights"):
        verify(write(tmp_path, config(weights)))


@pytest.mark.parametrize("weights", [{"neg": 0.5, "sex": 0.1, "age": 0.0, "onset": 0.0}, {"neg": 0.5, "age": 0.2}])
def test_verify_still_refuses_sex_and_age_without_onset(tmp_path, weights):
    with pytest.raises(ValueError, match="unsupported"):
        verify(write(tmp_path, config(weights)))


def test_verify_still_accepts_the_v1_0_weights(tmp_path):
    v10 = {"neg": 0.5, "sex": 0.0, "age": 0.0, "onset": 0.0}
    assert verify(write(tmp_path, config(v10)))["weights"] == v10


def test_declared_v1_1_configuration_is_the_validated_one():
    new, old = read_config(RERANK_V11_BUNDLE), read_config(RERANK_BUNDLE)
    assert new["release"] == "rerank-v1.1.0"
    assert new["weights"] == {"neg": 0.5, "sex": 0.0, "age": 0.0, "onset": 0.25}
    assert new["params"] == {**old["params"], "onset_smoothing": 0.1}
    assert new["files"] == old["files"]
    assert new["base_model"] == old["base_model"]


def test_v1_1_bundle_files_match_their_pins():
    from conftest import KB as KB_NAME

    if not (RERANK_V11_BUNDLE / KB_NAME).is_file():
        pytest.skip("rerank-v1.1 bundle not filled")
    verify(RERANK_V11_BUNDLE)


def test_parity_with_the_training_candidate(v3, reranker_v11, onset_parity):
    tolerance = onset_parity["tolerance"]
    rows = onset_parity["cases"]
    assert len(rows) >= 100
    moved = 0
    for row in rows:
        p = v3.probabilities(row["present"])
        out = reranker_v11.rerank(p, row["excluded"], row["onset_years"])
        label = (row["case_id"], row["onset_years"])
        assert rank_of(p, v3.genes, row["gene"]) == row["rank_e0"], label
        assert rank_of(out, v3.genes, row["gene"]) == row["rank_candidate"], label
        top = np.argsort(out)[::-1][: len(row["top"])]
        assert [v3.genes[i] for i in top] == [g for g, _ in row["top"]], label
        np.testing.assert_allclose(out[top], [s for _, s in row["top"]], rtol=0, atol=tolerance, err_msg=str(label))
        moved += row["rank_candidate"] != row["rank_rr1"]
    assert moved > 0


def test_without_onset_the_output_is_rerank_v1_0_0_bit_for_bit(v3, reranker, reranker_v11, parity_cases):
    changed = 0
    for case in parity_cases:
        p = v3.probabilities(case["present"])
        old = reranker.rerank(p, case["excluded"])
        new = reranker_v11.rerank(p, case["excluded"], None)
        assert new.tobytes() == old.tobytes(), case["case_id"]
        changed += old is not p
    assert changed > 0


def test_without_onset_or_negations_the_output_is_v3_0(v3, reranker_v11, parity_cases):
    for case in parity_cases:
        p = v3.probabilities(case["present"])
        before = p.tobytes()
        for excluded in (None, [], ()):
            out = reranker_v11.rerank(p, excluded, None)
            assert out is p and out.tobytes() == before


def test_onset_changes_scores_on_real_cases(v3, reranker_v11, onset_parity):
    row = next(r for r in onset_parity["cases"] if r["rank_candidate"] != r["rank_rr1"])
    p = v3.probabilities(row["present"])
    with_onset = reranker_v11.rerank(p, row["excluded"], row["onset_years"])
    without = reranker_v11.rerank(p, row["excluded"], None)
    assert not np.array_equal(with_onset, without)
