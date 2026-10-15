# model-v4.0.0: GenPhenia v4 (F3)

Nota de release del modelo de las Fases 3 y 4 de diagnostic.ar-training. Decisión: ADR-0020 de ese repo. Handoff:
`docs/HANDOFF-v4-prod.md` de ese repo, en `801fa85`. Registro completo:
`docs/evidence/RETRAINING-RECORD.md`.

## Qué es
F3 = **red v4** + **capa v4** (add-on + regla dura de sexo).

- **Red v4:** la misma arquitectura que GenPhenia v3.0 (GIN de 3 capas, mismas entradas, mismos 5.229 genes), con
  pesos nuevos.
  - Se reentrenó desde cero sobre pacientes simulados con el conocimiento de v3.0 (HPOA 2025-03-03).
  - Luego se ajustó con 4.369 pacientes reales de phenopacket-store (`p3-v1` train, folds 0–3), sorteando cada gen
    como lo sortea el simulador, para que ningún gen gane por tener más pacientes.
  - Entra en `genphenia-v4.0.tar.gz`, que es el bundle de v3.0 con `model.onnx` y `best_model.pt` reemplazados.
- **Capa v4** (`models/v4/v4-layer/`), después de los logits de la red:
  - **Add-on:** un residuo que **solo baja** genes, por sexo, edad de inicio (o edad) y recesivo ligado al X en
    mujeres. θ promedio: `sex_mismatch` 2,85; `onset_strict_late` 0,05; `onset_strict_gap` 0,02;
    `onset_lenient_gap` 0,06; `xlr_female` 3,75.
  - **Regla dura de sexo** (`sex-kb-v3`): manda al final de la lista los genes que el sexo del paciente no puede
    tener. Son 101 genes para una mujer y 36 para un hombre. Un gen entra solo si todas sus enfermedades están
    limitadas a un sexo, o si está en el cromosoma Y fuera de las regiones pseudoautosómicas.
- **Sin sexo, edad ni edad de inicio, la capa no cambia nada:** la salida es softmax(logits de la red), bit a bit.

## Evidencia (diagnostic.ar-training)
MRR acotado: cada publicación cuenta como máximo 10 pacientes. Δ es contra v3.0 (E0), con IC 95% por bootstrap de
publicaciones. "No citados": pacientes de publicaciones que el conocimiento de v3.0 no cita.

| Lectura | Pacientes no citados | Δ MRR acotado vs v3.0 [IC 95%] |
|---|---|---|
| Folds 0–3, fuera del fold (red) | 2.316 | +0,071 [+0,049, +0,096] |
| CONFIRM, primera lectura (red + add-on) | 406 | +0,072 [+0,033, +0,120] |
| **Bóveda, lectura única (EXP-V-002, red + add-on)** | **2.678** | **+0,065 [+0,047, +0,083]** |
| **CONFIRM, segunda lectura (F3, P4-CONFIRM)** | 406 | +0,072 [+0,033, +0,120] |

- **En la bóveda**, el gen correcto queda primero en el 16,0% de los no citados (v3.0: 11,7%) y entre los 10
  primeros en el 34,5% (29,5%). En los citados: +0,060.
- **Regla de sexo:** 31 ayudados y 0 perjudicados en CONFIRM; 130 y 0 en folds 0–3. Sin ella, el top 50 de la red
  muestra un gen imposible para el sexo del paciente en el 1% de los casos.
- **Add-on:** 101 ayudados y 5 perjudicados en CONFIRM; en la bóveda, +0,0011.
- **Límites:**
  - la ganancia está en los genes con pacientes reales de entrenamiento (+0,137 contra +0,001 en la bóveda);
  - es mayor con términos HPO como los codifican los curadores (al pasar los términos a sus padres queda el 35%);
  - no hay ganancia medible en las publicaciones más nuevas.

## Archivos y assets

| Archivo | sha256 |
|---|---|
| `genphenia-v4.0.tar.gz` (asset; `scripts/package_bundle.sh`, reproducible) | `62b2c5e8eb4609d1003a81c3632ea82cf2b1173f4ffc646a02ecb66d38d95cc3` |
| su `model.onnx` | `fafbecbed8585073b2afe9b6a481ee3182f21ff733f6e96745945d75bc7daf29` |
| su `best_model.pt` (la red v4, en el formato de checkpoint de v3.0) | `bff1a05b982bf2be5711c76ec3850d66d3c629921b25aa43c956d45146d621e2` |
| `v4-layer.tar.gz` (asset; `scripts/package_v4_layer.sh`, reproducible) | `80d1b159472b5730cfa57f3c636c864c854c820be0c2ee740f67e68c2f399df9` |
| `models/v4/v4-layer/v4_layer.py` (numpy y la biblioteca estándar) | `2ca18111c9586c182156d98242299faa054da67f239affe922645e16562090b3` |
| `models/v4/v4-layer/v4-layer-bundle.json.gz` | `3bdeeaedff851dc81983425f489d66bcff2b124a20df2283332d6c16bd69e21e` |
| `models/v4/v4-layer/staging-fixture.json` (solo tests: 32 casos con el top 10 esperado) | `99d83c92838f8059a3335eb08701f7762f6838ee6143c573a45b60c012b5734c` |

- `models/v4/v4-layer/v4.json` fija los archivos y el bundle de la red. Los archivos se copiaron sin cambios de
  `dist/v4-layer/` de diagnostic.ar-training@801fa85.
- **Paridad** (diagnostic.ar-training, 5.053 pacientes de desarrollo):
  - el motor de `vendor/` sobre el tarball da los mismos rangos que la red de referencia (4.369/4.369) y el mismo
    orden del top 10 (5.053/5.053);
  - la capa empaquetada coincide bit a bit con la referencia.

## Para integrar (handoff, pasos 2–6)
- **Entradas nuevas de la API,** todas opcionales: `sex`, `age_years`, `onset_years`. `excluded` se puede aceptar,
  pero **no tiene efecto** en F3, porque sus pesos son 0.
- **La capa necesita los logits de la red,** no sus probabilidades: `engine.runtime.predict_logits(...)`.
- **El motor sigue informando la versión "3.0".** `spec.json` elige la arquitectura, y el motor solo acepta 2.0, 2.5
  y 3.0. v4 se identifica por el tag y los sha256.
- **Conservar el `model.onnx` publicado y verificarlo por sha256.** La ruta de re-exportación del motor está rota,
  también para v3.0.
- **No apilar `rerank-v1.0.0` sobre v4:** en folds 0–3 baja −0,0030 [−0,0065, −0,0001].
- **Rollback:** volver a `model-v3.0.0`, o apagar `V4_LAYER_ENABLED` para usar la red v4 sola.

## Alcance
Pre-release. La integración en el servicio (handoff, pasos 2–6), staging y producción esperan; producción necesita
el visto bueno de Mateo.
