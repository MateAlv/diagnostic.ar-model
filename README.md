# diagnostic.ar-model

Modelos de priorización de genes a partir de fenotipos HPO para diagnostic.ar.

El punto de partida es la red GenPhenia v3.0 (GIN de 3 capas sobre el subgrafo HPO
del paciente, embeddings BioBERT de 768 dimensiones, 5.229 genes de salida). Sobre su
salida se agregan módulos de reranking que incorporan información que la red no ve:
síntomas ausentes, edad y sexo.

## Entorno

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/dvc pull
```

## Organización

| Ruta | Contenido | Versionado |
|---|---|---|
| `data/raw/` | Datos externos sin modificar, fijados a una versión | DVC (`*.dvc` en git) |
| `data/processed/` | Tablas derivadas generadas por el pipeline | DVC (salidas de `dvc.yaml`) |
| `models/` | Checkpoints y artefactos de modelos | DVC |
| `results/` | Métricas y reportes de cada evaluación | git |
| `src/diagnostic_ar_model/` | Código | git |
| `params.yaml` | Todos los hiperparámetros | git |

Los datos de HPO vienen del release `v2026-02-16` y se importaron con
`dvc import-url`, así que cada `.dvc` guarda la URL de origen y el hash del archivo.

## Versionado de experimentos y resultados

- Todo parámetro que afecte un resultado vive en `params.yaml`. El código no tiene
  valores fijos de hiperparámetros.
- El pipeline se define en `dvc.yaml`. `dvc repro` solo recalcula las etapas cuyas
  dependencias cambiaron.
- Cada corrida es un experimento de DVC:
  ```bash
  dvc exp run -n <nombre> -S reranker.neg_floor=0.1
  dvc exp show            # tabla de parámetros y métricas de todas las corridas
  dvc exp push origin <nombre>
  ```
  El experimento queda asociado al commit de código, los parámetros, los hashes de
  los datos y las métricas, así que cualquier resultado se puede reproducir.
- Las métricas se escriben en `results/` como JSON y se commitean en git, de modo que
  el historial de resultados se lee sin bajar artefactos.
- Un experimento que se promueve a versión del modelo se commitea en `main`, se
  etiqueta `model-vX.Y.Z` y se registra en `CHANGELOG.md` con sus métricas.

## Publicar una versión del modelo

Los checkpoints no viajan en git. Una versión promovida se empaqueta y se adjunta
a un release de GitHub con su tag:

```bash
scripts/package_bundle.sh models/base/genphenia-v3.0 dist/
gh release create model-v3.0.0 dist/genphenia-v3.0.tar.gz dist/genphenia-v3.0.tar.gz.sha256 \
  --title model-v3.0.0 --notes-file <(sed -n '/^## model-v3.0.0/,/^## /p' CHANGELOG.md | sed '$d')
```

`diagnostic.ar-api` fija el tag y el sha256 del tarball, y su build lo baja y lo
verifica. `vendor/genphenia_inference_engine/` es el motor que lo ejecuta; la API
lleva una copia.

## Re-ranker

`src/diagnostic_ar_model/rerank/` re-ordena la distribución de v3.0 con los
términos HPO que el paciente no tiene (rr-v1[neg=0.5]). Las negaciones son
opcionales: sin ellas devuelve la salida de v3.0 sin tocarla. Qué hace, con qué
evidencia y cómo se habilita está en [docs/rerank-v1.0.0.md](docs/rerank-v1.0.0.md),
y lo que tendría que cambiar la app en
[docs/integracion-app-rerank-v1.md](docs/integracion-app-rerank-v1.md).

Su bundle (`models/rerank/rerank-v1.0/`) guarda en git solo `rerank.json` y el
manifiesto de origen del KB. Los archivos grandes se bajan y se verifican con:

```bash
scripts/build_rerank_bundle.sh models/rerank/rerank-v1.0
scripts/package_bundle.sh models/rerank/rerank-v1.0 dist/
```

Los tests corren con `.venv/bin/pip install -e ".[test]"` y `.venv/bin/pytest`.
Los que necesitan v3.0 buscan el bundle descomprimido en
`models/base/genphenia-v3.0`, o donde indique `DXM_GENPHENIA_BUNDLE`, y se saltean
si no está. La paridad con diagnostic.ar-training usa 50 casos de R1-dev
(`tests/fixtures/`, armados con `scripts/make_rerank_parity_fixture.py`). Con
`DXM_PARITY_CASES` corre sobre otro conjunto de casos.
