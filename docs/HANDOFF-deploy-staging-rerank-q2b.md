# HANDOFF: rerank-v1.0.0 y el agente con Q2b en staging

Para el agente que despliega en nodo0/brainy. Fecha: 2026-10-05. Reemplaza el
orden de pasos de `HANDOFF-deploy-rerank-v1.md`. Las especificaciones de ese
archivo y de `integracion-app-rerank-v1.md` siguen valiendo.

## Decisiones de Mateo (2026-10-05)
| Tema | Decisión |
|---|---|
| Quién despliega | El agente de despliegue, con este HANDOFF |
| Alcance | **Por ahora, solo staging.** Producción no se toca |
| Producción, cuando se habilite | Opción (a): enrutar `/genphenai` a la imagen fijada por `model.lock`, como staging. No se actualiza el servicio de brainy |
| Modo sombra | No |

## Qué cambia

| # | Qué | Dónde | Estado |
|---|---|---|---|
| 1 | Re-ranker `rr-v1[neg=0.5]` en el modelo. Hay que fijar el bundle `rerank-v1.0.0`, aceptar `excluded_hpo_ids` (opcional) y re-rankear la distribución completa antes del top-k | MateAlv/diagnostic.ar-api, `services/genphenai` | Por hacer. Spec: `integracion-app-rerank-v1.md` §1 |
| 2 | Agente de preguntas con el selector **Q2b** por defecto (D-19) y los "no" mandados como `excluded_hpo_ids` (D-18 revertida) | MarBL00126/diagnosticar-question-agent, `feat/agente-v2` @ `495bfacd5609251642b4beb2ab3446326ab748a7` | Hecho (PRs #1 a #3 mergeados) |
| 3 | Web: subir `QUESTION_AGENT_COMMIT` de `48d901e…` a `495bfacd5609251642b4beb2ab3446326ab748a7` | MateAlv/diagnostic.ar, `.github/question-agent.env` | Por hacer |
| 4 | Web: agregar `PREGUNTAS_SELECTOR:` y `PREGUNTAS_RERANK_NEGATIONS:` (sin valor) a la lista `environment` del servicio `question-agent` | MateAlv/diagnostic.ar, `docker-compose.yml` (líneas 87-103) | Por hacer. No hace falta para usar Q2b, porque es el default, pero sí para poder volver atrás con una variable |
| 5 | Web: la edad de inicio en "Precisar" (PR #87, mergeado, `84db86b`) entra con el próximo tag de release | MateAlv/diagnostic.ar | Hecho en `main` |

### Sobre los campos de edad de inicio
Desde el PR #87, la web manda en `/rank-genes` tres campos opcionales cuando el
paciente indicó una edad: `onset_hpo_id`, `onset_age_years` y
`symptom_onsets`.
- La API actual los ignora (`RankRequest` es un `BaseModel` sin `extra`).
  **Tiene que seguir ignorándolos.**
- `rerank-v1.0.0` tiene peso 0 para la edad de inicio.
- Usarla requiere `rerank-v1.1.0`, que depende de EXP-B-006 (lectura sellada
  pendiente) y de un HANDOFF aparte.

## Pasos, en orden
1. **API:** PR con el cambio 1, revisado por el equipo, con sus tests.
   - Sin `excluded_hpo_ids`, la salida es idéntica a v3.0.
   - El servicio no arranca si el sha256 del bundle no coincide.
2. **Web:** PR con los cambios 3 y 4. `GATEWAY_COMMIT` (`.github/recognizer.env`)
   tiene que apuntar a un commit de la API que tenga el cambio 1 y el
   `Dockerfile` del agente.
3. **Release:** tag `vX.Y.Z` de la web. `release.yml` construye las imágenes,
   incluida la del agente en `495bfac`.
4. **Staging:**
   - Levantar con `MODEL_ROUTED=true` y `COMPOSE_PROFILES=question-agent ops/staging.sh up vX.Y.Z`.
   - En `.env.staging`, poner `QUESTION_AGENT_URL=http://question-agent:8010`.
5. **Verificar** con la lista de abajo, e informar a Mateo con los resultados.
6. **Producción: no.** Se habilita después, por la opción (a), con el OK de Mateo.

## Verificaciones en staging
- [ ] `/healthz` del modelo informa el tag `rerank-v1.0.0` y el sha256 del bundle.
- [ ] Un pedido sin `excluded_hpo_ids`, o con la lista vacía, devuelve
      **exactamente** lo mismo que v3.0, con el mismo orden y los mismos scores.
- [ ] Un pedido con `onset_hpo_id`, `onset_age_years` o `symptom_onsets`
      devuelve exactamente lo mismo que sin ellos.
- [ ] Un pedido con negaciones anotadas a genes del top los baja. La respuesta
      trae `rerank: "rr-v1[neg=0.5]"` y `excluded_hpo_count`.
- [ ] Los ids desconocidos aparecen en `unknown_excluded_hpo_ids` y no mueven nada.
- [ ] En una sesión de prueba, los logs del agente muestran el selector `q2b`.
      Las preguntas de una ronda no salen todas del mismo sistema de órganos.
- [ ] El agente manda solo los "no" efectivos de las respuestas. Nunca manda las
      negaciones del texto libre (`absent_hpo_ids`) ni los "No sé".
- [ ] Con `PREGUNTAS_SELECTOR=legacy` vuelve el selector anterior. Con
      `PREGUNTAS_RERANK_NEGATIONS=false` el agente deja de mandar los "no".
- [ ] El p95 de `/rank-genes` sube como mucho unos 10 ms.
- [ ] El modal "Precisar" ofrece la edad de inicio y la guarda con el síntoma.

## Vuelta atrás
- **Re-ranker:** `PREGUNTAS_RERANK_NEGATIONS=false`. La salida vuelve a ser la
  de v3.0, bit a bit.
- **Selector:** `PREGUNTAS_SELECTOR=legacy`.
- **Todo:** volver al tag de release anterior.

## Evidencia
- **Re-ranker, EXP-B-003 (gate sellado):**
  - en S3-test, Δ MRR +0,0044 [+0,0032, +0,0057], perjudica al 3,9 %;
  - en R1-test, sin regresión: −0,0025 [−0,0070, +0,0013].
- **Q2b, EXP-Q-001 (sellado):**
  - Q2b − Q0 = +0,0049 [+0,0027, +0,0069];
  - el re-ranker perjudica al 4,77 % con Q2b.

  Las fuentes están en `diagnostic.ar-training`: `docs/experiments/`, y
  `docs/evidence/` para el índice de evidencia.

## Restricciones
- No tocar nada bajo `GenPhenAI/`.
- No reconstruir el bundle ni el KB.
- Commits y PRs sin co-autoría ni menciones de IA.
- Cambios de API solo aditivos.
