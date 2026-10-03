"""Ranks must match diagnostic.ar-training's `dxt rerank eval` (EXP-B-003, R1-dev) exactly.

v3.0 runs through the vendored engine, as diagnostic.ar-api runs it, so the
E0 ranks check the base model path and the rr-v1 ranks check this module.
"""

from conftest import rank_of


def test_ranks_match_the_training_repo(v3, reranker, parity_cases):
    e0_mismatch, rr_mismatch, moved = [], [], 0
    for case in parity_cases:
        p = v3.probabilities(case["present"])
        e0 = rank_of(p, v3.genes, case["gene"])
        rr = rank_of(reranker.rerank(p, case["excluded"]), v3.genes, case["gene"])
        moved += rr != e0
        if e0 != case["rank_e0"]:
            e0_mismatch.append((case["case_id"], e0, case["rank_e0"]))
        if rr != case["rank_rr"]:
            rr_mismatch.append((case["case_id"], rr, case["rank_rr"]))
    print(f"\nparity: {len(parity_cases)} cases, {moved} moved by rr-v1, "
          f"E0 mismatches {len(e0_mismatch)}, rr-v1 mismatches {len(rr_mismatch)}")
    assert not e0_mismatch, e0_mismatch[:10]
    assert not rr_mismatch, rr_mismatch[:10]
