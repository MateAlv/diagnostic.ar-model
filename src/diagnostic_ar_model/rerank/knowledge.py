"""What rr-v1's negation and onset features need: the HPO is_a graph and the gene knowledge base.

Provenance, negation: copied from MateAlv/diagnostic.ar-training@9a573fd5bde1c2533e7a9ddcdc0ec4db59628a27
(unchanged since 0b1bae8, the commit EXP-B-003 ran from):
- src/diagnostic_ar_training/ontology.py: `_curie`, the parent construction of
  `Ontology.from_json`, `Ontology.ancestors`;
- src/diagnostic_ar_training/rerank/features.py: `FeatureParams`,
  `GeneKnowledge.diseases`, `GeneKnowledge._propagated`,
  `GeneKnowledge.term_probability`, and the `neg_llr` term of `components`.

Provenance, onset (rerank-v1.1.0, EXP-B-006): copied from
MateAlv/diagnostic.ar-training@5970d8dd674d982646ff3d1f15f66434c49ce8c5,
src/diagnostic_ar_training/rerank/features.py: `ONSET_BIN_EDGES`, `onset_bin`,
`N_BINS`, `_interval_bins`, `FeatureParams.onset_smoothing`,
`GeneKnowledge._disease_onset`, `GeneKnowledge.onset_distribution`, the
`onset_background` of `GeneKnowledge.__init__` and the `onset` term of
`components`.

Only the negation and onset paths are kept: sex and age keep weight 0. The
arithmetic and its order are unchanged, so results match the training repo
bit for bit.
"""

import bisect
import json
import math
from dataclasses import dataclass
from functools import cached_property, lru_cache
from pathlib import Path

_OBO = "http://purl.obolibrary.org/obo/"

# Onset bins (years): prenatal, neonatal, infantile, early childhood, childhood, young adult, adult, late.
ONSET_BIN_EDGES = (0.0, 28 / 365.25, 1.0, 5.0, 15.0, 40.0, 60.0)
N_BINS = len(ONSET_BIN_EDGES) + 1


def _curie(value: str) -> str:
    if value.startswith(_OBO):
        value = value[len(_OBO) :]
    return value.replace("_", ":", 1) if value.startswith("HP_") else value


def onset_bin(years: float) -> int:
    return bisect.bisect_right(ONSET_BIN_EDGES, years) if years >= 0 else 0


def _interval_bins(lo: float, hi: float) -> list[float]:
    """Share of an age interval falling in each onset bin (a point interval puts all in one bin)."""
    out = [0.0] * N_BINS
    if hi <= lo:
        out[onset_bin(lo)] = 1.0
        return out
    edges = (-math.inf, *ONSET_BIN_EDGES, math.inf)
    for b in range(N_BINS):
        overlap = max(0.0, min(hi, edges[b + 1]) - max(lo, edges[b]))
        out[b] = overlap / (hi - lo)
    return out


class Ontology:
    def __init__(self, parents: dict[str, tuple[str, ...]]) -> None:
        self._parents = parents

    @classmethod
    def from_json(cls, path: Path) -> "Ontology":
        graph = json.loads(Path(path).read_text())["graphs"][0]
        parents: dict[str, set[str]] = {}
        for node in graph["nodes"]:
            term = _curie(node["id"])
            if term.startswith("HP:"):
                parents.setdefault(term, set())
        for edge in graph["edges"]:
            if edge["pred"] != "is_a":
                continue
            child, parent = _curie(edge["sub"]), _curie(edge["obj"])
            if child.startswith("HP:") and parent.startswith("HP:"):
                parents.setdefault(child, set()).add(parent)
        return cls({k: tuple(sorted(v)) for k, v in parents.items()})

    def __contains__(self, term: str) -> bool:
        return term in self._parents

    def parents(self, term: str) -> tuple[str, ...]:
        return self._parents.get(term, ())

    @lru_cache(maxsize=65536)  # noqa: B019 -- one Ontology per process, cache lives with it
    def ancestors(self, term: str) -> frozenset[str]:
        """Strict ancestors (the term itself excluded)."""
        out: set[str] = set()
        for p in self.parents(term):
            out.add(p)
            out |= self.ancestors(p)
        return frozenset(out)


@dataclass(frozen=True)
class FeatureParams:
    neg_strength: float = 0.5
    unknown_frequency: float = 0.3
    onset_smoothing: float = 0.1


class GeneKnowledge:
    def __init__(self, kb: dict, ontology: Ontology, params: FeatureParams = FeatureParams()) -> None:
        if kb.get("schema") != 2:
            raise ValueError("features need a schema-2 KB (kb-v3 or later)")
        self.kb = kb
        self.ontology = ontology
        self.params = params
        self.vocabulary = kb.get("vocabulary", {})

    def diseases(self, gene: str) -> dict[str, float]:
        return self.kb["genes"].get(self.vocabulary.get(gene, gene), {})

    @lru_cache(maxsize=16384)  # noqa: B019 -- one instance per process
    def _propagated(self, disease_id: str) -> dict[str, float]:
        """P(t | disease) for every term the disease annotates, directly or through a descendant."""
        absent: dict[str, float] = {}
        for term, pheno in self.kb["diseases"][disease_id]["phenotypes"].items():
            f = pheno["freq"] if pheno["freq"] is not None else self.params.unknown_frequency
            for t in (term, *self.ontology.ancestors(term)):
                absent[t] = absent.get(t, 1.0) * (1.0 - f)
        return {t: 1.0 - a for t, a in absent.items()}

    def term_probability(self, gene: str, term: str) -> float:
        return sum(w * self._propagated(d).get(term, 0.0) for d, w in self.diseases(gene).items())

    def neg_llr(self, gene: str, excluded: tuple[str, ...]) -> float:
        """Sum over excluded terms t of log(1 - k * P(t | gene)); 0 without excluded terms or knowledge."""
        out = 0.0
        if not excluded or not self.diseases(gene):
            return out
        for term in excluded:
            out += math.log(1.0 - self.params.neg_strength * self.term_probability(gene, term))
        return out

    @cached_property
    def onset_background(self) -> list[float]:
        """Mean onset-bin distribution over the diseases that have onset data."""
        with_onset = [
            self._disease_onset(d) for d in self.kb["diseases"] if self.kb["diseases"][d]["onset_years"]
        ]
        return [sum(col) / len(with_onset) for col in zip(*with_onset, strict=True)]

    @lru_cache(maxsize=16384)  # noqa: B019 -- one instance per process
    def _disease_onset(self, disease_id: str) -> tuple[float, ...]:
        intervals = self.kb["diseases"][disease_id]["onset_years"]
        bins = [_interval_bins(lo, hi) for lo, hi in intervals]
        return tuple(sum(col) / len(bins) for col in zip(*bins, strict=True))

    def onset_distribution(self, gene: str) -> list[float] | None:
        """Mixture over the gene's diseases; diseases without onset data contribute the background."""
        ds = self.diseases(gene)
        known = [d for d in ds if self.kb["diseases"][d]["onset_years"]]
        if not known:
            return None
        a = self.params.onset_smoothing
        out = [0.0] * N_BINS
        for d, w in ds.items():
            dist = self._disease_onset(d) if self.kb["diseases"][d]["onset_years"] else self.onset_background
            for b in range(N_BINS):
                out[b] += w * ((1 - a) * dist[b] + a / N_BINS)
        return out

    def onset_llr(self, gene: str, onset_years: float) -> float:
        """log(P(onset bin | gene) / P(onset bin | background)); 0 when the gene has no onset knowledge."""
        if not self.diseases(gene):
            return 0.0
        dist = self.onset_distribution(gene)
        if dist is None:
            return 0.0
        a = self.params.onset_smoothing
        b = onset_bin(onset_years)
        background = (1 - a) * self.onset_background[b] + a / N_BINS
        return math.log(dist[b] / background)
