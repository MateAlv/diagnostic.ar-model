"""Builds the parity fixture: R1-dev cases with the ranks diagnostic.ar-training measured for them.

Inputs, all from diagnostic.ar-training (R1-dev only; no sealed split):
- a JSON list of R1-dev cases {case_id, gene, present, excluded}, dumped with
  `splits.load_part("r1-v1", "dev", Purpose.EVAL)`;
- `results/EXP-B-003/r1-v1-dev__E0__all.ranks.jsonl`;
- `results/EXP-B-003/r1-v1-dev__rr-v1[neg=0.5]__all.ranks.jsonl`.

By default it keeps a fixed sample, ordered by sha256(case_id): 30 cases whose
rank rr-v1 moved, 15 with negated terms whose rank did not move, and 5 without
negated terms. `--all` keeps every scorable case.

    python scripts/make_rerank_parity_fixture.py CASES E0_RANKS RR_RANKS OUT [--all]
"""

import argparse
import hashlib
import json
from pathlib import Path

SAMPLE = {"moved": 30, "excluded_unmoved": 15, "no_excluded": 5}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ranks(path: Path) -> dict[str, dict]:
    return {r["case_id"]: r for r in map(json.loads, path.read_text().splitlines())}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", type=Path)
    parser.add_argument("e0_ranks", type=Path)
    parser.add_argument("rr_ranks", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    e0, rr = ranks(args.e0_ranks), ranks(args.rr_ranks)
    rows = []
    for case in json.loads(args.cases.read_text()):
        a, b = e0[case["case_id"]], rr[case["case_id"]]
        if a["scorable"] and a["gene_in_vocab"]:
            rows.append({**case, "rank_e0": a["rank"], "rank_rr": b["rank"]})
    rows.sort(key=lambda r: hashlib.sha256(r["case_id"].encode()).hexdigest())

    if args.all:
        kept, selection = rows, "every scorable R1-dev case whose gene is in v3.0's vocabulary"
    else:
        groups = {
            "moved": [r for r in rows if r["rank_rr"] != r["rank_e0"]],
            "excluded_unmoved": [r for r in rows if r["excluded"] and r["rank_rr"] == r["rank_e0"]],
            "no_excluded": [r for r in rows if not r["excluded"]],
        }
        kept = [r for name, n in SAMPLE.items() for r in groups[name][:n]]
        selection = f"first cases by sha256(case_id) per group: {SAMPLE}"

    fixture = {
        "source": {
            "repo": "https://github.com/MateAlv/diagnostic.ar-training.git",
            "cohort": "r1-v1/dev",
            "e0_ranks": {"path": f"results/EXP-B-003/{args.e0_ranks.name}", "sha256": sha256(args.e0_ranks)},
            "rr_ranks": {"path": f"results/EXP-B-003/{args.rr_ranks.name}", "sha256": sha256(args.rr_ranks)},
        },
        "selection": selection,
        "cases": kept,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(fixture, indent=1) + "\n")
    print(f"{len(kept)} cases -> {args.out}")


if __name__ == "__main__":
    main()
