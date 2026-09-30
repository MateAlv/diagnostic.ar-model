# Changelog

Cada versión publicada del modelo lleva un tag `model-vX.Y.Z`, y cada re-ranker un
tag `rerank-vX.Y.Z`, con una entrada acá con las métricas de evaluación y el
experimento del que sale.

## rerank-v1.0.0 — sin publicar

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
- Límite: la ganancia se midió en entrevistas simuladas. No se afirma nada
  sobre sexo, edad ni edad de inicio.

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
