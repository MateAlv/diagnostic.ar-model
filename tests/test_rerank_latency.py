"""Per-case cost of the re-ranker on top of v3.0, measured on the parity cases."""

import time

import numpy as np

from diagnostic_ar_model import rerank

from conftest import RERANK_BUNDLE

P95_BUDGET_MS = 50.0


def test_latency_per_case(v3, reranker, parity_cases):
    with_negations = [c for c in parity_cases if c["excluded"]]
    probs = [v3.probabilities(c["present"]) for c in with_negations]

    started = time.perf_counter()
    fresh = rerank.load(RERANK_BUNDLE, v3.genes)
    load_s = time.perf_counter() - started

    cold, warm = [], []
    for p, case in zip(probs, with_negations, strict=True):
        for sink in (cold, warm):
            started = time.perf_counter()
            fresh.rerank(p, case["excluded"])
            sink.append((time.perf_counter() - started) * 1000)

    v3_ms = []
    for case in with_negations:
        started = time.perf_counter()
        v3.probabilities(case["present"])
        v3_ms.append((time.perf_counter() - started) * 1000)

    def stats(xs):
        return f"p50 {np.percentile(xs, 50):.2f} ms, p95 {np.percentile(xs, 95):.2f} ms, max {max(xs):.2f} ms"

    negs = [len(c["excluded"]) for c in with_negations]
    print(
        f"\nlatency over {len(with_negations)} cases with negations "
        f"(median {np.median(negs):.0f}, max {max(negs)} negated terms):"
        f"\n  bundle load {load_s:.2f} s"
        f"\n  rerank, first call per case {stats(cold)}"
        f"\n  rerank, repeated call {stats(warm)}"
        f"\n  v3.0 alone {stats(v3_ms)}"
    )
    assert np.percentile(cold, 95) < P95_BUDGET_MS
