# ft-v1.1.0: ft-v1.1-confirmed

Nota de release del modelo de la Fase 2 de diagnostic.ar-training: GenPhenia v3.0
(`model-v3.0.0`, E0) sin cambios, más un residuo sobre sus logits que **solo puede
bajar** un gen. Decisión: ADR-0018 de diagnostic.ar-training. Handoff:
`docs/HANDOFF-ft-v1.1-prod.md` de ese repo, en `0b189f7`.

## Qué hace

    probs = softmax(z + r),   r_g = −Σ_k θ_k f_k(paciente, g),   θ_k ≥ 0

Cinco rasgos, cada uno 0 cuando falta su dato:

| Rasgo | Dato que usa | θ |
|---|---|---|
| `sex_mismatch`: el gen está limitado al otro sexo | sexo | 2,132 |
| `onset_strict_late`: el inicio más temprano del gen es posterior a la edad de inicio (o a la edad) | edad de inicio o edad | 2,472 |
| `onset_strict_gap`: log1p de esos años | edad de inicio o edad | 2,206 |
| `xlr_female`: paciente mujer y gen solo recesivo ligado al X | sexo | 2,786 |
| `neg_obligate`: un término excluido contradice un fenotipo obligatorio de cada enfermedad del gen | términos excluidos | 2,982 |

- **Sin datos nuevos el residuo es 0** y la salida es la de v3.0 bit a bit.
- θ es el promedio de 3 semillas, ajustado sobre 4.103 pacientes reales (`r1-v1` train, EXP-P-003).
- La edad de inicio, si está, reemplaza a la edad. Una edad negativa cuenta como 0 y una no finita, como desconocida.
- Los términos excluidos son HPO del release 2026-02-16; un id desconocido no cambia nada.

## Archivos

`models/ft/ft-v1.1-confirmed/`, copiados sin cambios de `dist/ft-v1.1-confirmed/`
de diagnostic.ar-training@0b189f7:

| Archivo | sha256 |
|---|---|
| `ft_prod.py` (numpy y la biblioteca estándar) | `054893684cfda65d7ddbc835f5c1baa45bb159690e98ca14bf192e2ebaaea63d` |
| `ft-v1.1-confirmed-bundle.json.gz` | `6bb6bb40d85a815c3bf8fb467cbfa9c32d34164ced280eb96d4f4228ddeee6c4` |
| `parity-fixture.json.gz` (solo tests) | `440580df3c8e039965e3fb2b7e8f756de691e30111769a1fba47e4002ad37b0d` |

- `ft.json` fija los dos primeros y `model-v3.0.0`.
- `diagnostic_ar_model.ft.load()` se niega a cargar un archivo modificado o un bundle con otro orden de genes que v3.0. El servicio no arranca si falla.
- El release `ft-v1.1.0` lleva `ft-v1.1-confirmed.tar.gz` (`scripts/package_ft.sh`, reproducible): `ft.json`, `ft_prod.py` y el bundle, sin el fixture.

## Cómo se usa

```python
from diagnostic_ar_model import ft

model = ft.load(ft.PACKAGE_DIR, engine.genes)        # una vez, al arrancar
inputs = ft.case_inputs(sex="female", age_years=7.0, onset_years=2.0, excluded=["HP:0001250"])
probs = ft.apply(model, v3_probs, inputs, ft.enabled())  # después de v3.0, antes del top-k
```

- **Flag `FT_V11_ENABLED`**, apagado por defecto: solo `1`, `true`, `yes` u `on` lo prenden.
  - Con el flag apagado, o sin datos nuevos, `ft.apply` devuelve el mismo arreglo de v3.0.
  - Es la vuelta atrás inmediata, sin redeploy.
- `results`, `specialties` y `confidence` salen de la distribución que devuelve.

## Evidencia

Lecturas selladas sobre pacientes reales (ADR-0018). Δ MRR vs E0, IC 95 % por bootstrap pareado:

| Lectura | Pacientes | Δ MRR [IC 95 %] | Perjudicados |
|---|---|---|---|
| EXP-P-005, `p2-v1` test | 3.587 | +0,00138 [+0,00070, +0,00232] | 6 (0,17 %) |
| EXP-P-006, control final | 1.072 | +0,00054 [+0,00005, +0,00129] | 3 (0,28 %) |

**Paridad en este repo** (`tests/test_ft.py`):

| Prueba | Resultado |
|---|---|
| 207 casos del fixture, desde logits | máximo \|Δp\| 1,5e-20 (tolerancia 1e-9) |
| Los mismos casos, desde probabilidades | máximo \|Δp\| 5,6e-16 |
| Ranks | todos iguales a `rank_expected` |
| v3.0 con el motor de `vendor/` sobre los términos presentes de cada caso | idéntico al fixture (\|Δp\| = 0), sin diferencias de rank |
| Identidad | sin datos nuevos, `apply` es el softmax de v3.0 bit a bit y `apply_probs` devuelve el mismo objeto |
| Latencia del residuo | p95 0,25 ms por caso en la máquina de desarrollo |

## Límites

- **El artefacto del enmascarado.** OFD1, F8, SLC9A6 y THOC2 cuentan como solo recesivos ligados al X sin serlo, y bajan en pacientes mujeres. Los 6 perjudicados de EXP-P-005 son eso, y está incluido en los números de arriba.
- **Los términos excluidos de la app vienen de los "no" del agente de preguntas**, no de negativos de publicaciones como en R1.
  - El rasgo de negación solo puede bajar genes, lo que acota la diferencia.
  - Su efecto sobre respuestas de entrevista no está medido. Lo mismo vale para cualquier dato.
- **La regla de fenotipo obligatorio puede equivocarse con pacientes reales.** Cuenta como obligatoria una frecuencia n/n con n ≥ 5 de phenotype.hpoa.
- **No se combina con `rerank-v1.0.0`.** Lo medido es E0 + ft-v1.1. Con el flag prendido, la API usa ft-v1.1 en lugar de rr-v1.
- El paquete `ft-v1.1-prod` (sin enmascarar) no se usa: agrega perjuicios por negación en dev.
