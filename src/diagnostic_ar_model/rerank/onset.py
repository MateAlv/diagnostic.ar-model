"""Maps the web's onset fields to the one number the onset feature takes: onset in years.

Provenance: HPO_ONSET_YEARS is copied from
MateAlv/diagnostic.ar-training@5970d8dd674d982646ff3d1f15f66434c49ce8c5,
src/diagnostic_ar_training/rerank/kb.py. The class-midpoint rule is
`case_onset_years` in rerank/features.py of the same commit. The field names are
those of diagnostic.ar's /rank-genes (frontend/src/lib/onset.ts, PR #87).
"""

import math
from collections.abc import Iterable, Mapping
from typing import Any

_DAY = 1 / 365.25
# Age intervals in years (negative = prenatal) from the HPO onset term definitions.
HPO_ONSET_YEARS: dict[str, tuple[float, float]] = {
    "HP:0030674": (-0.75, 0.0),  # antenatal
    "HP:0011460": (-0.75, -0.6),  # embryonal
    "HP:0011461": (-0.6, 0.0),  # fetal
    "HP:0003577": (0.0, 0.0),  # congenital
    "HP:0003623": (0.0, 28 * _DAY),  # neonatal
    "HP:0003593": (28 * _DAY, 1.0),  # infantile
    "HP:0011463": (1.0, 5.0),  # childhood
    "HP:0003621": (5.0, 15.0),  # juvenile
    "HP:0410280": (0.0, 16.0),  # pediatric
    "HP:0003581": (16.0, 100.0),  # adult
    "HP:0011462": (16.0, 40.0),  # young adult
    "HP:0025708": (16.0, 19.0),  # early young adult
    "HP:0025709": (19.0, 25.0),  # intermediate young adult
    "HP:0025710": (25.0, 40.0),  # late young adult
    "HP:0003596": (40.0, 60.0),  # middle age
    "HP:0003584": (60.0, 100.0),  # late
}


def class_years(onset_hpo_id: Any) -> float | None:
    """Midpoint of an HPO onset class; None for unknown ids and for classes that are not an age range."""
    if not isinstance(onset_hpo_id, str):
        return None
    interval = HPO_ONSET_YEARS.get(onset_hpo_id.strip().upper())
    if interval is None:
        return None
    lo, hi = interval
    return (lo + hi) / 2


def _age(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value) if math.isfinite(value) and value >= 0 else None


def _symptom_years(entry: Any) -> float | None:
    """One symptom's onset: its exact age if usable, else the midpoint of its class."""
    if not isinstance(entry, Mapping):
        return None
    age = _age(entry.get("onset_age_years"))
    return age if age is not None else class_years(entry.get("onset_hpo_id"))


def onset_years(
    onset_hpo_id: str | None = None,
    onset_age_years: float | None = None,
    symptom_onsets: Iterable[Mapping[str, Any]] | None = None,
) -> float | None:
    """Onset of the first symptom, in years, from the web's optional fields; None when there is none.

    Order: the earliest per-symptom value of `symptom_onsets`, then `onset_age_years`, then the
    midpoint of the `onset_hpo_id` class. Anything unusable counts as absent and never raises.
    """
    if isinstance(symptom_onsets, Iterable) and not isinstance(symptom_onsets, str | bytes | Mapping):
        values = [v for v in map(_symptom_years, symptom_onsets) if v is not None]
        if values:
            return min(values)
    age = _age(onset_age_years)
    if age is not None:
        return age
    return class_years(onset_hpo_id)
