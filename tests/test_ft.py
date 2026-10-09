"""ft-v1.1-confirmed: the vendored package, its parity with diagnostic.ar-training, and identity with v3.0.

Ported from diagnostic.ar-training's tests/test_ft_prod.py (HANDOFF-ft-v1.1-prod.md, step 4). The parity
fixture holds v3.0's logits for 200 r1-v1 dev cases and 7 synthetic edge cases, with the probabilities
diagnostic.ar-training's FtV1 gave for them.
"""

import base64
import gzip
import hashlib
import json
import shutil
import time

import numpy as np
import pytest

from diagnostic_ar_model import ft

from conftest import rank_of

PINNED = {
    "ft_prod.py": "054893684cfda65d7ddbc835f5c1baa45bb159690e98ca14bf192e2ebaaea63d",
    "ft-v1.1-confirmed-bundle.json.gz": "6bb6bb40d85a815c3bf8fb467cbfa9c32d34164ced280eb96d4f4228ddeee6c4",
    "parity-fixture.json.gz": "440580df3c8e039965e3fb2b7e8f756de691e30111769a1fba47e4002ad37b0d",
}
THETA = [2.132, 2.472, 2.206, 2.786, 2.982]
P95_BUDGET_MS = 50.0


def decode_f32(text: str) -> np.ndarray:
    return np.frombuffer(base64.b64decode(text), dtype="<f4")


def rank(probs: np.ndarray, idx: int) -> int:
    """Pessimistic rank, as diagnostic.ar-training's eval.metrics.rank_of."""
    return int(1 + np.sum(probs > probs[idx]) + (np.sum(probs == probs[idx]) - 1))


@pytest.fixture(scope="module")
def ft_prod():
    return ft.load_module(ft.PACKAGE_DIR)


@pytest.fixture(scope="module")
def fixture():
    return json.loads(gzip.decompress((ft.PACKAGE_DIR / "parity-fixture.json.gz").read_bytes()))


@pytest.fixture(scope="module")
def model(fixture):
    bundle = ft.PACKAGE_DIR / "ft-v1.1-confirmed-bundle.json.gz"
    with gzip.open(bundle, "rt", encoding="utf-8") as handle:
        genes = json.load(handle)["genes"]
    return ft.load(ft.PACKAGE_DIR, genes)


def test_vendored_files_are_the_published_ones():
    for name, sha in PINNED.items():
        assert hashlib.sha256((ft.PACKAGE_DIR / name).read_bytes()).hexdigest() == sha
    for line in (ft.PACKAGE_DIR / "SHA256SUMS").read_text().splitlines():
        sha, name = line.split()
        assert PINNED[name] == sha
    config = ft.read_config(ft.PACKAGE_DIR)
    assert config["name"] == "ft-v1.1-confirmed"
    assert config["base_model"]["release"] == "model-v3.0.0"
    assert {n: e["sha256"] for n, e in config["files"].items()} == {
        n: s for n, s in PINNED.items() if n != "parity-fixture.json.gz"
    }
    assert config["tests_only"]["parity-fixture.json.gz"]["sha256"] == PINNED["parity-fixture.json.gz"]


def test_the_bundle_is_the_confirmed_artifact(model):
    provenance = model.bundle["provenance"]
    assert provenance["knowledge"]["id"] == "ft-kb-all-v2" and provenance["knowledge"]["mask_scope"] == "all"
    assert provenance["theta"]["bundle"] == "ft-v1.1-c1-lin-all-ens"
    assert provenance["theta"]["sha256"] == "89e3ea09c1e491de29b2d7c6f7955bba7ab6bbb575c47fc17756336c601db340"
    assert provenance["e0"]["sha256"] == ft.read_config(ft.PACKAGE_DIR)["base_model"]["sha256"]
    assert len(model.genes) == 5229
    assert np.round(model.theta, 3).tolist() == THETA


@pytest.mark.parametrize("name", ["ft_prod.py", "ft-v1.1-confirmed-bundle.json.gz"])
def test_a_modified_file_is_refused(tmp_path, name, model):
    package = tmp_path / "pkg"
    shutil.copytree(ft.PACKAGE_DIR, package, ignore=shutil.ignore_patterns("parity-fixture.json.gz"))
    with (package / name).open("ab") as handle:
        handle.write(b"\n")
    with pytest.raises(ValueError, match="sha256"):
        ft.load(package, model.genes)


def test_a_different_gene_order_is_refused(model):
    with pytest.raises(ValueError, match="gene order"):
        ft.load(ft.PACKAGE_DIR, tuple(reversed(model.genes)))


@pytest.mark.parametrize(
    "value, on",
    [(None, False), ("", False), ("false", False), ("0", False), ("no", False),
     ("true", True), ("TRUE", True), ("1", True), (" yes ", True), ("on", True)],
)
def test_the_flag_is_off_unless_set(value, on):
    environ = {} if value is None else {ft.FLAG: value}
    assert ft.enabled(environ) is on


def test_case_inputs_keep_only_what_the_model_reads():
    assert ft.case_inputs() == {"sex": None, "age_years": None, "onset_years": None, "excluded": []}
    assert ft.case_inputs(sex=" Female ")["sex"] == "female"
    assert ft.case_inputs(sex="no_binario")["sex"] is None
    assert ft.case_inputs(age_years=float("nan"))["age_years"] is None
    assert ft.case_inputs(onset_years="2.5")["onset_years"] == 2.5
    assert not ft.has_inputs(ft.case_inputs(sex="prefiero_no_decir", age_years=float("inf")))
    assert ft.has_inputs(ft.case_inputs(excluded=["HP:0001250"]))
    assert ft.has_inputs(ft.case_inputs(age_years=0.0))


def test_parity_with_the_training_code(model, ft_prod, fixture):
    assert len(fixture["cases"]) == 207
    worst_logits = worst_probs = 0.0
    for case in fixture["cases"]:
        z = decode_f32(case["e0_logits_f32_b64"])
        idx = case["indices"]
        e0 = ft_prod.softmax64(z)
        assert np.abs(e0[idx] - case["e0_probs"]).max() <= 1e-15
        from_logits = model.apply(z, case["inputs"])
        from_probs = ft.apply(model, e0, case["inputs"], True)
        worst_logits = max(worst_logits, float(np.abs(from_logits[idx] - case["expected_probs"]).max()))
        worst_probs = max(worst_probs, float(np.abs(from_probs[idx] - case["expected_probs"]).max()))
        assert rank(from_logits, case["gene_index"]) == case["rank_expected"]
        assert rank(from_probs, case["gene_index"]) == case["rank_expected"]
        assert int((model.residual(case["inputs"]) < 0).sum()) == case["genes_lowered"]
    print(f"\nparity: max |dp| {worst_logits:.2e} from logits, {worst_probs:.2e} from probabilities")
    assert worst_logits <= fixture["tolerance"] and worst_probs <= fixture["tolerance"]


def test_identity_without_new_inputs(model, ft_prod, fixture):
    for case in fixture["cases"]:
        z = decode_f32(case["e0_logits_f32_b64"])
        p = ft_prod.softmax64(z)
        assert model.apply(z, {}).tobytes() == p.tobytes()
        assert model.apply_probs(p, {"sex": "unknown", "excluded": []}) is p
        assert ft.apply(model, p, ft.case_inputs(), True) is p
        assert ft.apply(model, p, case["inputs"], False) is p
    (empty,) = [c for c in fixture["cases"] if c["case_id"] == "synthetic:no-inputs"]
    assert empty["expected_probs"] == empty["e0_probs"] and empty["genes_lowered"] == 0


def test_no_gene_rises_above_renormalisation(model, ft_prod, fixture):
    for case in fixture["cases"]:
        z = decode_f32(case["e0_logits_f32_b64"])
        p, r = ft_prod.softmax64(z), model.residual(case["inputs"])
        out = model.apply(z, case["inputs"])
        ceiling = p / np.sum(p * np.exp(r))
        assert np.all(r <= 0)
        assert np.all(out <= ceiling * (1 + 1e-12))
        assert np.all(out[r < 0] < ceiling[r < 0])


def test_determinism(model, fixture):
    again = ft.load(ft.PACKAGE_DIR, model.genes)
    for case in fixture["cases"][:25] + fixture["cases"][-7:]:
        z = decode_f32(case["e0_logits_f32_b64"])
        first = model.apply(z, case["inputs"]).tobytes()
        assert model.apply(z, case["inputs"]).tobytes() == first
        assert again.apply(z, case["inputs"]).tobytes() == first


# With the vendored engine, as diagnostic.ar-api runs v3.0


def test_the_engine_gives_the_fixture_logits_distribution(v3, model, fixture):
    assert model.genes == tuple(v3.genes)
    worst, rank_mismatch = 0.0, []
    for case in fixture["cases"]:
        p = v3.probabilities(case["present"])
        worst = max(worst, float(np.abs(p[case["indices"]] - case["e0_probs"]).max()))
        if rank_of(p, v3.genes, case["gene"]) != case["rank_e0"]:
            rank_mismatch.append(case["case_id"])
        out = ft.apply(model, p, case["inputs"], True)
        if rank(out, case["gene_index"]) != case["rank_expected"]:
            rank_mismatch.append(f"{case['case_id']} (ft)")
    print(f"\nengine vs fixture: max |dp| {worst:.2e}, rank mismatches {len(rank_mismatch)}")
    assert worst <= 1e-6
    assert not rank_mismatch, rank_mismatch[:10]


def test_latency_per_case(v3, model, fixture):
    cases = [c for c in fixture["cases"] if ft.has_inputs(c["inputs"])]
    probs = [v3.probabilities(c["present"]) for c in cases]
    ms = []
    for p, case in zip(probs, cases, strict=True):
        started = time.perf_counter()
        ft.apply(model, p, case["inputs"], True)
        ms.append((time.perf_counter() - started) * 1000)
    print(f"\nft-v1.1 over {len(cases)} cases: p50 {np.percentile(ms, 50):.2f} ms, "
          f"p95 {np.percentile(ms, 95):.2f} ms, max {max(ms):.2f} ms")
    assert np.percentile(ms, 95) < P95_BUDGET_MS
