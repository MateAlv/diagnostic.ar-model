# HANDOFF: Q2b en producción, sin re-ranking por síntomas ausentes

Para el agente que despliega en nodo0/brainy. Fecha: 2026-10-05.

## Decisión de Mateo (2026-10-05)
| Componente | Staging | Producción |
|---|---|---|
| Agente de preguntas con selector **Q2b** (`495bfacd5609251642b4beb2ab3446326ab748a7`) | encendido | **encendido** (este HANDOFF) |
| Re-ranking por síntomas ausentes (`rerank-v1.0.0`) | encendido | **apagado**. Su efecto con respuestas de entrevista reales no se puede medir todavía: no hay datos de pacientes reales con esas respuestas (ADR-0016 de `diagnostic.ar-training`, "Data limitations") |
| `rerank-v1.1.0` (edad de inicio) | no publicado | no publicado |
| Edad de inicio en "Precisar" y en la salida para el médico | sí | sí, con el próximo release de la web |

## Qué hay que hacer
1. **Release de la web.** Usar un tag `vX.Y.Z` de MateAlv/diagnostic.ar que incluya `785060d`, que fija el agente en `495bfac` y agrega los switches.
2. **En el entorno de producción del agente,** poner `PREGUNTAS_RERANK_NEGATIONS=false`.
   - Con esto el agente no manda `excluded_hpo_ids`, y el orden de genes es el de v3.0 bit a bit.
   - El selector queda en Q2b, que es el default.
3. **El modelo no cambia.** `/genphenai` sigue yendo a brainy por el túnel (`docker-compose.prod.yml`).
   - No hace falta enrutar a la imagen fijada ni actualizar brainy.
   - Si en algún momento se enruta a la imagen fijada, el switch del punto 2 tiene que seguir en `false`.
4. **Verificar** con la lista de abajo e informar a Mateo.

## Verificaciones en producción
- [ ] Los logs del agente muestran el selector `q2b` en una sesión de prueba.
- [ ] Los pedidos del agente a `/rank-genes` no traen `excluded_hpo_ids`.
- [ ] El orden de genes de una sesión de prueba coincide con el de v3.0 para los mismos términos presentes.
- [ ] El modal "Precisar" ofrece la edad de inicio, y la salida para el médico la muestra.
- [ ] La latencia de una ronda de preguntas está en línea con staging.

## Vuelta atrás
- **Selector anterior:** `PREGUNTAS_SELECTOR=legacy`.
- **Todo:** volver al tag de release anterior.

## Evidencia
**Q2b, EXP-Q-001 (sellado, entrevistas simuladas S3-v2-test):**
- Q2b vs Q0: +0,0049 [+0,0027, +0,0069] de MRR final.
- Por caso: 1,04 hallazgos confirmados y 7,87 descartados, en 8,90 preguntas.

Las fuentes están en `diagnostic.ar-training`: `docs/experiments/EXP-Q-001.md` y `docs/evidence/`.

## Restricciones
- No tocar nada bajo `GenPhenAI/`.
- Commits y PRs sin co-autoría ni menciones de IA.
