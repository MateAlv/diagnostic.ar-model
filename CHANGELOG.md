# Changelog

Cada versión publicada del modelo lleva un tag `model-vX.Y.Z` y una entrada acá con
las métricas de evaluación y el experimento del que sale.

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
