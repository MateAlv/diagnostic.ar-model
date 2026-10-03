# Integración de rerank-v1.0.0 en la app

Este documento lista cambios propuestos, y ninguno está hecho. Describe qué
tendría que cambiar para que las respuestas "no" lleguen al re-ranker. Se armó
leyendo, sin modificar, estas versiones:

| Repo | Versión leída |
|---|---|
| MateAlv/diagnostic.ar (web) | `main` en `5274b33` |
| MateAlv/diagnostic.ar-api | `main` en `970ba9c`, el `GATEWAY_COMMIT` de `web/.github/recognizer.env` |
| MarBL00126/diagnosticar-question-agent (el agente) | `53a4107`, el `QUESTION_AGENT_COMMIT` de `web/.github/question-agent.env` |

## Cómo está hoy

**El modelo solo recibe términos presentes.**
- `POST /rank-genes` acepta `{hpo_ids, top_k}` y nada más
  (API `services/genphenai/app/main.py:118-120`, `RankRequest`).
- Devuelve el top k; nunca la distribución completa.

**La web no le manda negaciones al modelo.**
- La llamada inicial manda `{hpo_ids, top_k}` (`frontend/src/app/nuevo/page.tsx:970`).
- Las negaciones del texto se descartan (`page.tsx:900`) y solo se muestran
  (`page.tsx:487-494`, `negatedFindings`).

**Las respuestas llegan al agente, pero los "no" se quedan ahí.**
- El backend manda al agente `present_hpo_ids`, `absent_hpo_ids` (las
  negaciones del texto) y todas las respuestas, "no" incluidos
  (`backend/src/services/questionSession.ts:191-210` y `:345-363`).
- El agente vuelve a llamar a `/rank-genes` en cada ronda con los presentes más
  los "sí" (`ranking/strategy.py:36-46`, `MODEL_SEES_PRESENT`;
  `agent/round.py:151-156`). Los "no" no se mandan: es la decisión D-18 del
  28/09/2026 (`docs/NEGACIONES.md`).

**Sexo y fecha de nacimiento no salen de la base.**
- Se guardan en Postgres (`patients.sexo`, `patients.fecha_nacimiento`), pero
  nunca se mandan a la API ni al agente.
- rr-v1 no los usa: tienen peso 0 y no hay evidencia para usarlos.

**Producción no corre la imagen fijada.**
- `/genphenai` va por un túnel a brainy (`docker-compose.prod.yml:75-93`).
- Solo staging corre la imagen fijada por `model.lock`, y solo con
  `MODEL_ROUTED=true` (`docker-compose.staging.yml:197-229`).

## Lo que corresponde a lo validado

En S3, el caso validado, el modelo recibe los presentes más los "sí", y el
re-ranker recibe los "no" como negados. Eso es exactamente lo que ya hace la
llamada del agente, sumándole los "no". La llamada inicial de la web, que se
hace antes de cualquier pregunta, no tiene respuestas y queda como está.

## Cambios

### 1. diagnostic.ar-api, `services/genphenai`

1. **Fijar el bundle.**
   - En `model.lock`, agregar `RERANK_TAG=rerank-v1.0.0`,
     `RERANK_ASSET=rerank-v1.0.tar.gz` y
     `RERANK_SHA256=4b83f5e39e003aca2dde834948392800655102199f8af099985191b69f8e79e2`.
   - `fetch_model.sh` y el `Dockerfile` lo bajan, verifican el sha256 y lo
     descomprimen junto a `genphenia-v3.0`, igual que hoy con el modelo.
   - Agregar una variable `RERANK_BUNDLE_DIR`.
2. **Traer el código.** Copiar `src/diagnostic_ar_model/rerank/` como hoy se
   copia `inference_engine/`, con el tag de origen. Solo depende de numpy.
3. **Aceptar el campo de negaciones.**
   - Agregar a `RankRequest` un campo opcional
     `excluded_hpo_ids: List[str] = []`, con el mismo tope que `hpo_ids`.
   - Normalizarlos con `normalize_hpo_id` y descartar los que también estén en
     `hpo_ids`.
   - Informar los que la ontología no conoce en `unknown_excluded_hpo_ids`,
     usando `ReRanker.unknown_terms`. No mueven nada.
4. **Aplicar el re-ranker a la distribución completa**, en `predict_scores`,
   `main.py:146-153`.
   - Pedir `engine.predict(..., return_distribution=True)`.
   - Pasar `result["distribution"]`, con los genes en el orden y las mayúsculas
     del motor, a `reranker.rerank_distribution(distribution, excluded)`.
   - Recién después armar el `score_map` en mayúsculas.
   - Así `results`, `specialties` y `confidence` salen de la misma distribución.
5. **Hacerlo trazable.**
   - Agregar a la respuesta `rerank: "rr-v1[neg=0.5]"` o `null`, y
     `excluded_hpo_count`.
   - Agregar a `/healthz` el tag y el sha256 del bundle del re-ranker.
6. **Tests.**
   - Un pedido sin `excluded_hpo_ids` devuelve exactamente lo mismo que antes.
   - Un pedido con negaciones anotadas mueve genes.
   - Si el bundle no coincide con el sha256 fijado, el servicio no arranca.

### 2. El agente de preguntas (repo de Mariano; lo cambia él)

1. **Mandar los "no".**
   - `ranking/model_client.py:46-51`: `rank()` acepta y manda
     `excluded_hpo_ids`.
   - `ranking/strategy.py:36-46`: `model_query` devuelve, además, las respuestas
     efectivas "no" (`answered(AnswerValue.NO)` de `agent/evidence.py:54-68`).
     No devuelve `absent_hpo_ids`, porque esas negaciones del texto no están
     validadas.
   - `agent/round.py:151-156`: pasar esa lista en la llamada.
2. **"No sé" no es una negación.** Nunca se manda.
3. **La llamada del resumen antes/después** (`round.py:370-388`) queda igual.
4. **Actualizar la documentación.** D-18 y `docs/NEGACIONES.md` dicen hoy que
   los "no" no mueven nada. Con este cambio sí mueven; hay que revisarlo con el
   equipo.

### 3. Web, MateAlv/diagnostic.ar

1. **La llamada inicial a `/rank-genes`** (`page.tsx:950-1052`) no cambia. Las
   negaciones del texto siguen sin mandarse, y el comentario de
   `page.tsx:487-494` sigue siendo cierto. Mandarlas sería una decisión aparte:
   la única evidencia es la de R1, donde no ayudan.
2. **El backend de preguntas no cambia.** El agente ya recibe los "no" en
   `answers` (`questionSession.ts:345-363`).
3. **La lista "Con tus respuestas"** (`page.tsx:431-437`) va a mostrar el orden
   re-rankeado, pero está apagada por defecto (`preferAnswersList`,
   `page.tsx:398`). Mostrarla por defecto es una decisión de producto.
4. **Si se actualiza `QUESTION_AGENT_COMMIT`** en `.github/question-agent.env`,
   tiene que apuntar a un commit del agente con el cambio 2.

### 4. Despliegue

- El cambio 1 solo llega a quien use la imagen fijada. Hoy eso es staging con
  `MODEL_ROUTED=true`, donde el agente llama a `http://model:18020`
  (`docker-compose.staging.yml:248`).
- Producción sigue en brainy hasta que se enrute a la imagen.

## Cómo se vuelve atrás

- **Sin redeploy:** el agente deja de mandar `excluded_hpo_ids`, y la salida
  vuelve a ser la de v3.0 bit a bit.
- **Con redeploy:** sacar las líneas `RERANK_*` de `model.lock`.
