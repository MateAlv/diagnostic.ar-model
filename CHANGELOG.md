# Changelog

Cada versión publicada del modelo lleva un tag `model-vX.Y.Z` y una entrada acá con
las métricas de evaluación y el experimento del que sale. Los embeddings de HPO del
extractor de síntomas llevan su propio tag, `hpo-embeddings-vX.Y.Z` (ver README).

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
