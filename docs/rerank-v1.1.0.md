> **Estado, 2026-10-05: no publicado (decisión de Mateo).** Bóveda R1, MRR: v1.1
> 0,4106, v1.0 0,4114, E0 0,4136 (EXP-V-001; v1.1 vs E0 −0,0031 [−0,0055, −0,0005],
> n = 1.771). No se crea el tag ni el release. Se mantiene en el repo como registro: el código, el
> bundle y los tests están mergeados (PR #7) y siguen valiendo para reproducir el
> experimento. En staging corre `rerank-v1.0.0`. Contexto de esa medición: E0 está
> favorecido en R1 (se entrenó con anotaciones de las mismas publicaciones) y los
> términos excluidos de R1 son negativos de publicaciones, no respuestas "no" de
> una entrevista.

# rerank-v1.1.0: rr-v1 + edad de inicio

Nota de release del segundo re-ranker sobre GenPhenia v3.0 (`model-v3.0.0`).
Candidato que no se publicó (ver el estado arriba). Pasó el gate de no regresión
de EXP-B-006 en R1-test (candidato − rr-v1 −0,0003 [−0,0019, +0,0008], n = 2.548).

## Qué hace

Es `rerank-v1.0.0` más un término de **edad de inicio**. Para los 200 genes más
probables según v3.0:

    score(g) = log p_v3(g) + 0,5 · Σ_t log(1 − 0,5 · P(t | g)) + 0,25 · onset_llr(g)

- El término de negación es el de v1.0.0, sin cambios.
- `onset_llr(g)` es `log(P(bin | g) / P(bin | fondo))`, donde `bin` es el tramo de
  edad en el que cae el inicio del paciente (prenatal, neonatal, infantil, 1 a 5,
  5 a 15, 15 a 40, 40 a 60, más de 60) y `P(bin | g)` es la mezcla, ponderada por
  el peso de cada enfermedad, de las edades de inicio que `kb-v3` registra
  (HPOA y Orphanet). Un gen sin enfermedades con edad de inicio no se mueve.
  Suavizado de 0,1.
- La entrada del re-ranker es **un número: la edad de inicio en años**
  (`ReRanker.rerank(probs, excluded, onset_years)`). Es opcional.
- **Sin edad de inicio la salida es la de `rerank-v1.0.0` bit a bit.** Sin edad
  de inicio ni negaciones, la de v3.0 bit a bit.
- "Edad de inicio" significa cuándo empezó el primer síntoma.

### De los campos de la web a la edad de inicio

`diagnostic_ar_model.rerank.onset_years(onset_hpo_id, onset_age_years, symptom_onsets)`,
en orden:

1. **`symptom_onsets`:** por cada síntoma, su edad exacta si es válida, y si no
   el punto medio de su clase; se toma el **mínimo**. Las entradas inservibles
   se saltean.
2. Si no, **`onset_age_years`**, si es un número finito mayor o igual a 0.
3. Si no, el **punto medio de la clase `onset_hpo_id`**, con la tabla
   `HPO_ONSET_YEARS` de diagnostic.ar-training.
4. Si no, ninguna edad de inicio.

| Clase | Id | Años |
|---|---|---|
| Antes de nacer | HP:0030674 | −0,375 |
| Al nacer | HP:0003577 | 0 |
| Primer mes | HP:0003623 | 0,038 |
| 1 a 12 meses | HP:0003593 | 0,538 |
| 1 a 5 años | HP:0011463 | 3 |
| 5 a 15 años | HP:0003621 | 10 |
| 16 a 40 años | HP:0011462 | 28 |
| 40 a 60 años | HP:0003596 | 50 |
| Después de los 60 | HP:0003584 | 80 |

Los ids desconocidos y las clases que no son un rango de edad (agudo,
crónico, …) no dan edad de inicio. Nada de esto lanza un error. La tabla completa
tiene 16 clases; la web manda estas nueve.

La regla 1 es una decisión de este release, no un resultado medido. EXP-B-006
(punto 1 de sus discrepancias) advierte que `onset_hpo_id` y `onset_age_years`
de la web son mínimos independientes y pueden venir de síntomas distintos;
tomar el mínimo por síntoma evita usar una edad posterior a la del primer síntoma.
No hay datos de la web para validarla.

## Evidencia

El gate sellado es
[EXP-B-006](https://github.com/MateAlv/diagnostic.ar-training/blob/5970d8dd674d982646ff3d1f15f66434c49ce8c5/docs/experiments/EXP-B-006.md)
(R1-test, una lectura, leída el 2026-10-05). Candidato `RerankConfig(kb-v3, llr,
k 0,5, top_k 200, pesos {neg_llr 0,5, onset 0,25})`, hash `71713c8d15b0`. **El
gate PASA.** IC del 95 % por bootstrap pareado sobre publicaciones.

| Chequeo | Resultado | Regla |
|---|---|---|
| ID1, sin edad de inicio = rr-v1 | 0 diferencias en 2.548 | bit a bit |
| ID2, solo presentes = v3.0 | 0 diferencias en 2.548 | bit a bit |
| ID3, casos sin edad de inicio usable = rr-v1 | 0 diferencias en 1.238 | bit a bit |
| N2, candidato vs v3.0 | −0,0028 [−0,0078, +0,0013], perjudica 11,3 % | IC superior ≥ 0 y punto ≥ −0,02 |
| N3, candidato − rr-v1 | −0,0003 [−0,0019, +0,0008], perjudica 5,3 %, mejora 10,0 % | IC inferior ≥ −0,01 |

### Ganancia: no medible en pacientes reales

**El gate es de no regresión. En pacientes reales la edad de inicio no mejora
nada que se pueda medir:**
- R1-test, candidato − rr-v1: **−0,0003 [−0,0019, +0,0008]**.
- Los 1.310 pacientes con edad de inicio usable: **−0,0006 [−0,0038, +0,0015]**
  (perjudica 10,2 %, mejora 19,5 %).
- Los 1.238 sin edad de inicio: 0, idéntico a rr-v1.

La ganancia es solo simulada:
- S3-v3b-dev, este sistema vs rr-v1, 2.934 casos con edad de inicio de la
  literatura: **+0,0021 [+0,0007, +0,0035]** (perjudica 4,40 % frente a v3.0).
- EXP-B-005, sellado, F + edad de inicio 0,25: **+0,0023 [+0,0013, +0,0034]**.
  Es otro sistema (sin la fórmula de negación de rr-v1).

## Límites

- **No hay evidencia de ganancia en pacientes reales.** Se libera porque pasó
  el gate de no regresión y por la ganancia simulada, con la aprobación de
  Mateo.
- **La evidencia de ganancia es de edades exactas.** S3 usó solo edades
  exactas; la web mandará sobre todo clases. Para los puntos medios de clase, la
  única evidencia es la no regresión de R1.
- **Por síntoma contra por paciente.** La edad de inicio se construyó y probó
  sobre la edad de inicio de la enfermedad del paciente (en R1, la del
  fenopaquete). La web pregunta por síntoma y manda el primero. En R1-train, el
  primer síntoma cae en el mismo tramo que la enfermedad en el 84,2 % de los
  1.133 pacientes que tienen ambos.
- **Sesgo temprano.** En R1-train la edad de inicio usable es sobre todo
  temprana; hay 13 pacientes de inicio tardío.
- **Bordes de clase.** La web asigna 15 a 16 años a juvenil y 60 a edad media;
  los tramos del feature empiezan en 15 y 60. Una edad exacta de 15,5 es juvenil
  en el formulario y está en el tramo 15 a 40 del feature. Una edad exacta
  gana a la clase.
- **No hay afirmación sobre sexo ni edad actual.** Siguen en peso 0.
- **Latencia:** no se midió la del término de edad de inicio. Se calcula solo
  para los 200 genes del top y solo si hay edad de inicio.
- Valen los límites de [rerank-v1.0.0](rerank-v1.0.0.md) sobre las negaciones,
  los ids y el KB.

## Contenido del bundle

`rerank-v1.1.tar.gz`, sha256
`cf4cc0d28b7a391bea5df21fbdb00f8c9af85d626e5b22e9919ab6dc58e515a3`
(reproducible: dos empaquetados dan el mismo hash). Se arma en `dist/`, que git
ignora, y todavía no se subió a ningún release.

| Archivo | Qué es | sha256 |
|---|---|---|
| `rerank.json` | Pesos `{neg 0,5, sex 0, age 0, onset 0,25}`, parámetros (incluye `onset_smoothing` 0,1) y el sha256 de cada archivo | |
| `kb.json.gz` | `kb-v3`, el mismo de v1.0.0 | `39d5f9213afab40090d15bdace663dc94d650b099e6b13643ced0633f4970fa8` |
| `kb-v3.manifest.json` | El manifiesto de origen de `kb-v3` | |
| `hp.json` | HPO 2026-02-16, el mismo de v1.0.0 | `cb3b756ac11d1308372136bf4f7f8db2ad1c51f64a795e09400e5ffb2a273243` |

`rerank.load` verifica los sha256 al cargar. `bundle.verify` acepta para v1.1
exactamente esos pesos; los de v1.0 siguen verificando como antes, y cualquier
otro peso de sexo, edad o edad de inicio se rechaza.

Para rearmar el bundle:

```bash
scripts/build_rerank_bundle.sh models/rerank/rerank-v1.1
scripts/package_bundle.sh models/rerank/rerank-v1.1 dist/
```

## Pruebas

- **Paridad** (`tests/test_rerank_onset.py`, fixture
  `tests/fixtures/rerank-v1.1-onset-parity.json`). Con el motor de `vendor/`:
  100 pares (caso, edad de inicio), con los 50 casos de R1-dev del fixture de
  v1.0.0 y dos edades de inicio cada uno. La esperada sale de la implementación
  de diagnostic.ar-training en `5970d8dd674d982646ff3d1f15f66434c49ce8c5`
  (`scripts/make_rerank_onset_parity_fixture.py`). Coinciden el rank del gen
  verdadero, el orden de los 20 primeros genes y sus probabilidades, con
  tolerancia de 1e-9. No se usan datos sellados.
- **Identidad:** sin edad de inicio, la salida es idéntica byte a byte a la de
  `rerank-v1.0.0` en los 50 casos; sin edad de inicio ni negaciones es el mismo
  arreglo de v3.0.
- **Mapeo:** cada clase de la web, edades exactas, el mínimo de `symptom_onsets`,
  entradas inválidas y clases desconocidas.
- Los tests existentes siguen pasando.

## Cómo se habilita

1. **Etiquetar y publicar** solo con el OK de Mateo. Los comandos están en el
   PR.
2. **Staging:** [HANDOFF-deploy-staging-rerank-v1.1.md](HANDOFF-deploy-staging-rerank-v1.1.md).
   Producción más adelante, por la imagen fijada; sin modo sombra.
3. **Uso:**
   ```python
   from diagnostic_ar_model import rerank

   reranker = rerank.load("/app/model/rerank-v1.1", engine.genes)
   years = rerank.onset_years(onset_hpo_id, onset_age_years, symptom_onsets)
   result = engine.predict(known_ids, top_k=len(engine.genes), return_distribution=True)
   distribution = reranker.rerank_distribution(result["distribution"], excluded_ids, years)
   ```

## Cómo se vuelve atrás

- **Sin redeploy:** no mandar edad de inicio (o que `onset_years` sea `None`). La
  salida es la de `rerank-v1.0.0` bit a bit.
- **Fijando el bundle anterior:** volver a `rerank-v1.0.0` y `rerank-v1.0.tar.gz`
  en `model.lock`.
