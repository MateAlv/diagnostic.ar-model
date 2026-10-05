"""rr-v1: re-score v3.0's top genes with the patient's negated terms and onset.

score(g) = log p_v3(g) + w_neg * neg_llr(g) + w_onset * onset_llr(g) for the top-K
genes by p_v3; the rest keep log p_v3. The result is the softmax of the scores.
Without negated terms and onset, or when no top gene has knowledge about them,
the input array is returned as is, so the output is bit-identical to v3.0. With
no onset, the output is bit-identical to rerank-v1.0.0.

Provenance: copied from MateAlv/diagnostic.ar-training@9a573fd5bde1c2533e7a9ddcdc0ec4db59628a27
(unchanged since 0b1bae8, the commit EXP-B-003 ran from),
src/diagnostic_ar_training/rerank/model.py: the top-K selection of
`feature_table` and `FeatureTable.combine`, restricted to the negation feature.
The onset term (rerank-v1.1.0) follows the same file at
5970d8dd674d982646ff3d1f15f66434c49ce8c5 (EXP-B-006, `Weights(neg=0.5, onset=0.25)`).
"""

from collections.abc import Iterable, Sequence

import numpy as np

from diagnostic_ar_model.rerank.knowledge import GeneKnowledge


class ReRanker:
    def __init__(
        self,
        knowledge: GeneKnowledge,
        genes: Sequence[str],
        neg_weight: float,
        top_k: int,
        onset_weight: float = 0.0,
    ) -> None:
        self.knowledge = knowledge
        self.genes = tuple(genes)
        self.neg_weight = neg_weight
        self.onset_weight = onset_weight
        self.top_k = top_k

    def unknown_terms(self, terms: Iterable[str]) -> list[str]:
        """Terms the ontology does not know; they cannot move any gene."""
        return [t for t in terms if t not in self.knowledge.ontology]

    def rerank(
        self,
        probs: np.ndarray,
        excluded: Sequence[str] | None = None,
        onset_years: float | None = None,
    ) -> np.ndarray:
        """v3.0's distribution over `genes`, re-scored with the patient's negated HPO terms and onset."""
        if probs.shape != (len(self.genes),):
            raise ValueError(f"expected {len(self.genes)} probabilities, got shape {probs.shape}")
        use_neg = bool(excluded) and self.neg_weight != 0
        use_onset = onset_years is not None and self.onset_weight != 0
        if not use_neg and not use_onset:
            return probs
        excluded = tuple(excluded) if use_neg else ()
        top = np.argsort(probs)[::-1][: self.top_k]
        delta = np.zeros(len(top))
        if use_neg:
            delta = self.neg_weight * np.array(
                [self.knowledge.neg_llr(self.genes[i], excluded) for i in top], dtype=float
            )
        if use_onset:
            delta = delta + self.onset_weight * np.array(
                [self.knowledge.onset_llr(self.genes[i], onset_years) for i in top], dtype=float
            )
        if not np.any(delta):
            return probs
        scores = np.log(np.clip(probs, 1e-300, None))
        scores[top] += delta
        scores -= scores.max()
        exp = np.exp(scores)
        return exp / exp.sum()

    def rerank_distribution(
        self,
        distribution: dict[str, float],
        excluded: Sequence[str] | None = None,
        onset_years: float | None = None,
    ) -> dict[str, float]:
        """The same, on the engine's `predict(..., return_distribution=True)["distribution"]`."""
        if tuple(distribution) != self.genes:
            raise ValueError("distribution keys must be the v3.0 genes, in the engine's order")
        probs = np.fromiter(distribution.values(), dtype=float, count=len(self.genes))
        out = self.rerank(probs, excluded, onset_years)
        if out is probs:
            return distribution
        return {gene: float(p) for gene, p in zip(self.genes, out, strict=True)}
