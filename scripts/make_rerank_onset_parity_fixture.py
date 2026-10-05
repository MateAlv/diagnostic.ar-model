"""Builds the onset parity fixture: what diagnostic.ar-training's candidate scores for fixed cases.

Run it with the training repo's Python, which provides the implementation
(`rerank.model.feature_table` and `FeatureTable.combine`) and the GenPhenia v3.0 system:

    /path/to/diagnostic.ar-training/.venv/bin/python scripts/make_rerank_onset_parity_fixture.py \
        tests/fixtures/r1-dev-parity-sample.json models/rerank/rerank-v1.1 OUT.json

Cases are those of the committed R1-dev parity sample (present and excluded terms). Each gets two onsets
in years, picked by sha256(case_id), so every onset bin is exercised. For each (case, onset) the fixture
keeps the top 20 genes of the candidate `Weights(neg=0.5, onset=0.25)` with their probabilities, and the
ranks of the true gene under E0, rr-v1 (neg only) and the candidate. No sealed split is read.
"""

import argparse
import gzip
import hashlib
import json
import subprocess
from pathlib import Path

from diagnostic_ar_training.cohorts.schema import Case
from diagnostic_ar_training.ontology import Ontology
from diagnostic_ar_training.rerank.features import FeatureParams, GeneKnowledge
from diagnostic_ar_training.rerank.model import Weights, feature_table
from diagnostic_ar_training.systems.genphenia_v3 import GenPheniaV3

ONSETS = (-0.375, 0.0, 14 / 365.25, 0.5383, 2.5, 3.0, 10.0, 28.0, 50.0, 80.0, 0.2, 7.0)
TOP_K = 200
KEEP = 20
REFERENCE = Weights(neg=0.5)
CANDIDATE = Weights(neg=0.5, onset=0.25)


def rank(probs, idx: int) -> float:
    target = probs[idx]
    return float(1 + (probs > target).sum() + ((probs == target).sum() - 1))


def pick_onsets(case_id: str) -> list[float]:
    digest = hashlib.sha256(case_id.encode()).digest()
    first = digest[0] % len(ONSETS)
    second = (first + 1 + digest[1] % (len(ONSETS) - 1)) % len(ONSETS)
    return [ONSETS[first], ONSETS[second]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", type=Path)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()

    config = json.loads((args.bundle / "rerank.json").read_text())
    params = config["params"]
    kb = json.loads(gzip.open(args.bundle / "kb.json.gz", "rt", encoding="utf-8").read())
    knowledge = GeneKnowledge(
        kb,
        Ontology.from_json(args.bundle / "hp.json"),
        FeatureParams(
            neg_strength=params["neg_strength"],
            unknown_frequency=params["unknown_frequency"],
            onset_smoothing=params["onset_smoothing"],
        ),
    )
    base = GenPheniaV3()
    lookup = {g.upper(): i for i, g in enumerate(base.genes)}
    commit = subprocess.run(
        ["git", "-C", str(Path(__import__("diagnostic_ar_training").__file__).parents[2]), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    source = json.loads(args.cases.read_text())["cases"]
    rows = []
    for item in source:
        for onset in pick_onsets(item["case_id"]):
            case = Case(
                case_id=item["case_id"], cohort="r1-v1/dev", gene=item["gene"],
                present=tuple(item["present"]), excluded=tuple(item["excluded"]), onset_years=onset,
            )
            table = feature_table(base, knowledge, case, TOP_K)
            if table.probs is None:
                continue
            cand, ref = table.combine(CANDIDATE), table.combine(REFERENCE)
            idx = lookup[case.gene.upper()]
            order = list(cand.argsort()[::-1][:KEEP])
            rows.append({
                "case_id": case.case_id,
                "gene": case.gene,
                "present": list(case.present),
                "excluded": list(case.excluded),
                "onset_years": onset,
                "rank_e0": rank(table.probs, idx),
                "rank_rr1": rank(ref, idx),
                "rank_candidate": rank(cand, idx),
                "top": [[base.genes[i], float(cand[i])] for i in order],
            })

    fixture = {
        "source": {
            "repo": "https://github.com/MateAlv/diagnostic.ar-training.git",
            "commit": commit,
            "cases": "tests/fixtures/r1-dev-parity-sample.json (R1-dev only; no sealed split)",
            "candidate": "Weights(neg=0.5, onset=0.25), kb-v3, top_k 200, config hash 71713c8d15b0",
        },
        "tolerance": 1e-9,
        "cases": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(fixture, separators=(",", ":")) + "\n")
    moved = sum(r["rank_candidate"] != r["rank_rr1"] for r in rows)
    print(f"{len(rows)} (case, onset) pairs -> {args.out}; candidate moves the true gene vs rr-v1 in {moved}")


if __name__ == "__main__":
    main()
