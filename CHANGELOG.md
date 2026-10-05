# Changelog

Cada versión publicada del modelo lleva un tag `model-vX.Y.Z`, y cada re-ranker un
tag `rerank-vX.Y.Z`, con una entrada acá con las métricas de evaluación y el
experimento del que sale. Los embeddings de HPO del extractor de síntomas llevan su
propio tag, `hpo-embeddings-vX.Y.Z` (ver README).

## rerank-v1.1.0 — no publicado (2026-10-05)

No publicado (2026-10-05), por decisión de Mateo. Bóveda R1, MRR: v1.1 0,4106,
v1.0 0,4114, E0 0,4136 (EXP-V-001, descriptivo, n = 1.771); v1.1 vs E0 −0,0031
[−0,0055, −0,0005]. Nunca tuvo tag. Se conserva
como registro; ver el estado en [docs/rerank-v1.1.0.md](docs/rerank-v1.1.0.md).
La entrada de abajo es el candidato tal como se armó.

rr-v1 + edad de inicio: a `rerank-v1.0.0` le suma `0,25 · onset_llr`. La edad de
inicio es opcional, en años; sin ella la salida es la de `rerank-v1.0.0` bit a
bit. Nota de release: [docs/rerank-v1.1.0.md](docs/rerank-v1.1.0.md).

- Asset: `rerank-v1.1.tar.gz`, sha256
  `cf4cc0d28b7a391bea5df21fbdb00f8c9af85d626e5b22e9919ab6dc58e515a3`. Mismo
  `kb-v3` y mismo `hp.json` que v1.0.0.
- Código: `rerank/onset.py` (de los campos de la web a años) y el término de
  edad de inicio en `rerank/knowledge.py` y `rerank/model.py`, copiados de
  diagnostic.ar-training@5970d8d.
- Evidencia: EXP-B-006, gate PASA. R1-test: candidato − rr-v1 −0,0003
  [−0,0019, +0,0008] (n = 2.548). En simulación: S3-v3b-dev +0,0021
  [+0,0007, +0,0035].
- Paridad con el candidato de diagnostic.ar-training a 1e-9; identidad con
  v1.0.0 sin edad de inicio.

## rerank-v1.0.0 — 2026-10-03

rr-v1[neg=0.5]: re-ordena la salida de `model-v3.0.0` penalizando los genes que
anotan los términos HPO que el paciente no tiene. Sexo, edad y edad de inicio
tienen peso 0. Las negaciones son opcionales: sin ellas la salida es la de v3.0
bit a bit. Nota de release: [docs/rerank-v1.0.0.md](docs/rerank-v1.0.0.md).

- Asset del release: `rerank-v1.0.tar.gz`, sha256
  `4b83f5e39e003aca2dde834948392800655102199f8af099985191b69f8e79e2`. Se arma
  con `scripts/build_rerank_bundle.sh` y `scripts/package_bundle.sh`, y es
  reproducible.
- Conocimiento: `kb-v3` de diagnostic.ar-training, sin cambios, sha256
  `39d5f9213afab40090d15bdace663dc94d650b099e6b13643ced0633f4970fa8`. Su
  manifiesto de origen viaja en el bundle. La ontología es HPO 2026-02-16,
  sha256 `cb3b756ac11d1308372136bf4f7f8db2ad1c51f64a795e09400e5ffb2a273243`.
- Código: `src/diagnostic_ar_model/rerank/`, copiado de
  diagnostic.ar-training@9a573fd, con la procedencia en cada archivo.
- Evidencia: EXP-B-003, el gate sellado de la Fase 4.
  - S3-test: Δ MRR +0,0044 [+0,0032, +0,0057] vs v3.0 con las respuestas "sí";
    perjudica al 3,9 %.
  - R1-test: sin regresión, Δ −0,0025 [−0,0070, +0,0013]; sin negaciones,
    Δ exactamente 0.
- Paridad: en los 1.680 casos puntuables de R1-dev, los ranks son idénticos a
  los de `dxt rerank eval` (EXP-B-003).
- Latencia en R1-dev: p95 de 6,77 ms por caso sobre v3.0.
- Alcance de la medición: entrevistas simuladas (S3). Sexo, edad y edad de inicio
  tienen peso 0 en esta versión.
- Limitaciones de datos: no hay pacientes reales con respuestas sí/no de entrevista
  (R1 tiene negativos de publicaciones), así que `rerank-v1.0.0` (re-ranking por
  síntomas ausentes) queda solo en staging hasta que haya sesiones reales con
  diagnóstico confirmado; Q2b, en cambio, va a producción; ver el README.

## hpo-embeddings-v1.0.0

Los embeddings de los términos HPO en castellano que usa el extractor de síntomas
(spanish-symptoms-recognizer) para traducir lo que escribe la persona a códigos HPO.
Hasta ahora cada build del extractor los recalculaba: 11 de sus 17 minutos en GitHub.
Desde esta versión se generan una vez y el build los baja de este release.

- Asset: `hpo-embeddings-clinlinker-kb-gp.tar.gz` (más su `.sha256` y una copia del
  `manifest.json`), con los lotes `hpo/hpo_batches/clinlinker-kb-gp/*.pt`, la lista
  `hpo/hp-es.babelon.tsv` de la que salen, y un manifest con el origen y el sha256 de
  cada archivo.
- Encoder: `ICB-UMA/ClinLinker-KB-GP` en `8f914c58a1cbcff43331eb15b101eaa5e5c6920a`,
  el que se evaluó el 2026-09-21.
- Etiquetas: `obophenotype/hpo-translations` en `69f7f96fba5ae4c1b999028991510088f3480487`.
- Generador: `hpo_tsv_reader.py` del reconocedor, sin cambios
  (`ad5674b619922c8498a1ab54128618cd7a287165`), en el entorno del extractor:
  torch 2.13.0 (CPU), transformers 5.15.0.
- Son los mismos insumos que el extractor usaba para calcularlos en cada build, así
  que el resultado no cambia.

## model-v3.0.0 — 2026-09-25

La red GenPhenia v3.0 tal como la sirve producción desde el 2026-02-20: la línea
de base sobre la que se van a medir los rerankers. No sale de un experimento de
este repo; se publica para que el modelo tenga una versión fija y un único lugar
de donde bajarlo.

- Asset del release: `genphenia-v3.0.tar.gz`, sha256
  `2201b7f2868afaf00439f76a6197bcf1d94eccc5ea171173719ca48c517a61c8`
  (armado con `scripts/package_bundle.sh`, reproducible).
- Checkpoint `best_model.pt`, sha256 `ee10aa429ba1a134ceec0e38002f3d9d0c17babe87fb755e5329778e28973955`,
  el mismo que registró el servidor de inferencia de brainy.
- Corre el export ONNX en CPU con `vendor/genphenia_inference_engine`.
- Métricas: todavía no medidas en este repo.

## Unreleased

- Estructura inicial del repo: DVC para datos y artefactos, datos de HPO fijados al
  release 2026-02-16.
