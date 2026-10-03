# rerank-v1.0.0: rr-v1[neg=0.5]

Nota de release del primer re-ranker sobre GenPhenia v3.0 (`model-v3.0.0`).

## Qué hace

Reordena la distribución de genes que devuelve v3.0 usando los términos HPO que
el paciente **no** tiene. Para los 200 genes más probables según v3.0 calcula

    score(g) = log p_v3(g) + 0,5 · Σ_t log(1 − 0,5 · P(t | g))

donde t recorre los términos negados y P(t | g) sale de la base de conocimiento
`kb-v3`: las anotaciones HPO de las enfermedades del gen, propagadas por la
ontología y ponderadas por el peso de cada enfermedad. Los demás genes conservan
su log-probabilidad y la salida es el softmax de los puntajes. Un gen que anota
con frecuencia un hallazgo negado baja; uno que no lo anota no se mueve.

- Sexo, edad y edad de inicio tienen peso 0: el módulo no los usa.
- Las negaciones son un campo **opcional**. Sin negaciones, o si ningún gen del
  top 200 anota las negadas, la salida es la de v3.0 bit a bit.

## Evidencia

El gate sellado de la Fase 4,
[EXP-B-003](https://github.com/MateAlv/diagnostic.ar-training/blob/9a573fd5bde1c2533e7a9ddcdc0ec4db59628a27/docs/experiments/EXP-B-003.md)
en diagnostic.ar-training. Los IC son del 95 % por bootstrap pareado.

| Cohorte | Comparación | Δ MRR | IC 95 % | Perjudicados | Mejorados |
|---|---|---|---|---|---|
| S3-test, 9.990 pacientes simulados entrevistados | vs v3.0 con las respuestas "sí" | **+0,0044** | [+0,0032, +0,0057] | 3,9 % | 17,6 % |
| R1-test, 2.548 pacientes reales, vista "all" | vs v3.0 | −0,0025 | [−0,0070, +0,0013] | 9,0 % | 6,3 % |
| R1-test, vista sin negaciones | vs v3.0 | 0 exacto | | 0 | 0 |

- En S3 cada caso tuvo en promedio 6,89 preguntas, 6,13 respondidas "no".
- La configuración se eligió en S3-dev (EXP-S3-001) y R1 funciona como control
  de daño (EXP-B-001).

**Paridad con diagnostic.ar-training.** v3.0 corre con el motor de `vendor/`,
como lo corre diagnostic.ar-api. Sobre ese resultado, este módulo reproduce
exactamente los ranks de `dxt rerank eval` en EXP-B-003:

- en los 1.680 casos puntuables de R1-dev coinciden los ranks de E0 y de rr-v1
  (367 casos cambian de rank con rr-v1);
- el test commiteado usa una muestra fija de 50 de esos casos
  (`tests/fixtures/r1-dev-parity-sample.json`);
- no se usan datos sellados.

**Latencia**, en esos 1.575 casos de R1-dev con negaciones y en la máquina de
desarrollo:

| Qué | p50 | p95 | Máximo |
|---|---|---|---|
| Re-ranker, primera llamada por caso | 2,46 ms | 6,77 ms | 40,66 ms |
| v3.0 solo | 0,77 ms | 2,25 ms | 10,63 ms |

Cargar el bundle lleva 0,70 s.

## Límites

- **La ganancia se midió en entrevistas simuladas.**
  - En S3 las respuestas salen de la verdad del simulador.
  - Las preguntas las eligió un cuestionador por ganancia de información
    (7 preguntas sobre el top 10 de v3.0), no el agente de preguntas de la app.
  - No hay medición en usuarios reales.
- **Es una ganancia chica**, de unos +0,004 de MRR.
- **No hay afirmación sobre sexo, edad ni edad de inicio.** Tienen peso 0, y S3
  no es una prueba justa para ellos (EXP-S3-001, adenda 1).
- **Las negaciones validadas son respuestas "no" a preguntas.** En R1, donde las
  negaciones son hallazgos que los autores eligieron reportar como ausentes, el
  re-ranker no ayuda (Δ ≈ 0, no significativo). Pasarle las negaciones que el
  extractor encuentra en el texto libre no está validado.
- **Versión de los IDs.** Tienen que ser de la release de HPO 2026-02-16. Un
  término que la ontología no conoce no mueve ningún gen;
  `ReRanker.unknown_terms` los lista.
- **Es el KB validado, no el más completo.** `kb-v3` excluye las anotaciones que
  citan publicaciones de R1 dev/test/vault. Se usa tal cual porque es el
  artefacto validado en R1-test.

## Contenido del bundle

`rerank-v1.0.tar.gz`, sha256
`4b83f5e39e003aca2dde834948392800655102199f8af099985191b69f8e79e2`, trae:

| Archivo | Qué es | sha256 |
|---|---|---|
| `rerank.json` | Pesos, parámetros y el sha256 de cada archivo | |
| `kb.json.gz` | `kb-v3`, el asset del release `kb-v3` de diagnostic.ar-training, sin cambios | `39d5f9213afab40090d15bdace663dc94d650b099e6b13643ced0633f4970fa8` |
| `kb-v3.manifest.json` | El manifiesto de origen de `kb-v3`: fuentes, commit y hashes | |
| `hp.json` | HPO 2026-02-16, la misma ontología con la que se evaluó | `cb3b756ac11d1308372136bf4f7f8db2ad1c51f64a795e09400e5ffb2a273243` |

`rerank.load` verifica los sha256 al cargar.

Para rearmar el bundle:

```bash
scripts/build_rerank_bundle.sh models/rerank/rerank-v1.0
scripts/package_bundle.sh models/rerank/rerank-v1.0 dist/
```

El tarball es reproducible: sale el mismo sha256.

## Cómo se habilita

1. **Publicar el release.** Después del merge:
   ```bash
   gh release create rerank-v1.0.0 dist/rerank-v1.0.tar.gz dist/rerank-v1.0.tar.gz.sha256 \
     --title rerank-v1.0.0 --notes-file docs/rerank-v1.0.0.md
   ```
2. **Bajar el asset en el servicio** que corre v3.0 y verificar su sha256, igual
   que se hace con `genphenia-v3.0.tar.gz`.
3. **Cargar el re-ranker y aplicarlo a la distribución completa.** Tiene que ser
   antes de pasar los genes a mayúsculas y antes de cortar el top k:
   ```python
   from diagnostic_ar_model import rerank

   reranker = rerank.load("/app/model/rerank-v1.0", engine.genes)
   result = engine.predict(known_ids, top_k=len(engine.genes), return_distribution=True)
   distribution = reranker.rerank_distribution(result["distribution"], excluded_ids)
   ```
4. **Mandar las respuestas "no"** del agente de preguntas como el campo opcional
   de negaciones.

Los cambios concretos en la API, el agente y la web están en
[integracion-app-rerank-v1.md](integracion-app-rerank-v1.md).

## Cómo se vuelve atrás

- **Sin redeploy:** no mandar negaciones. Con el campo vacío o ausente, la
  salida es idéntica a la de v3.0.
- **Fijando el bundle anterior:**
  - dejar el servicio en `model-v3.0.0` y no cargar `rerank-v1.0`;
  - v3.0 no cambia con este release, porque el re-ranker es un bundle aparte.
