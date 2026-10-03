# HANDOFF: desplegar rerank-v1.0.0 (nodo0 / brainy)

Para el agente o la persona a cargo del despliegue en nodo0/brainy. Se puede
seguir sin otro contexto. Fecha: 2026-10-03.

## Qué hay que desplegar
`rr-v1[neg=0.5]` re-ordena la salida de GenPhenia v3.0 usando los términos HPO
que el paciente **no** tiene, es decir las respuestas "no" del agente de
preguntas. Sin negaciones, la salida es la de v3.0 **bit a bit**.

| Qué | Dónde |
|---|---|
| Release | https://github.com/MateAlv/diagnostic.ar-model/releases/tag/rerank-v1.0.0 |
| Asset | `rerank-v1.0.tar.gz`, sha256 `4b83f5e39e003aca2dde834948392800655102199f8af099985191b69f8e79e2` (también en `rerank-v1.0.tar.gz.sha256`) |
| Conocimiento dentro del bundle | `kb.json.gz` (kb-v3), sha256 `39d5f9213afab40090d15bdace663dc94d650b099e6b13643ced0633f4970fa8`; `hp.json` (HPO 2026-02-16), sha256 `cb3b756ac11d1308372136bf4f7f8db2ad1c51f64a795e09400e5ffb2a273243` |
| Código | `src/diagnostic_ar_model/rerank/`. Solo depende de numpy; `rerank.load` verifica los sha256 al cargar |
| Base | `model-v3.0.0`, sin cambios |
| Nota de release | `docs/rerank-v1.0.0.md` |
| **Cambios por repo, con archivo y línea** | **`docs/integracion-app-rerank-v1.md`**. Es la especificación; este HANDOFF dice el orden y las verificaciones |

## Evidencia y límites
Hay que tenerlos en cuenta para decidir el rollout.
- **Gate sellado (EXP-B-003).** En entrevistas simuladas (S3-test), Δ MRR
  +0,0044 [+0,0032, +0,0057] frente a v3.0 con las respuestas "sí": ayuda al
  17,6 % de los casos y perjudica al 3,9 %. En pacientes reales (R1-test), sin
  regresión: Δ −0,0025 [−0,0070, +0,0013].
- **Ganancia chica y medida en simulación.** No hay medición en usuarios
  reales.
- **Latencia:** +2,5 ms de mediana y +6,8 ms en el p95 por pedido.
- **Sexo y edad no se usan** (peso 0).
- **Solo las respuestas "no" del agente** son negaciones válidas. **Nunca**
  se mandan las negaciones del texto libre (`absent_hpo_ids`) ni "No sé": no
  están validadas.

## Pasos, en orden

| # | Paso | Repo o lugar | Responsable |
|---|---|---|---|
| 1 | API: fijar el bundle, aceptar `excluded_hpo_ids` (opcional) y re-rankear la distribución completa antes del top-k. Ver la sección 1 de la integración | MateAlv/diagnostic.ar-api, `services/genphenai` | Quien despliega, con PR revisado por el equipo |
| 2 | Agente: mandar las respuestas "no" efectivas como `excluded_hpo_ids`. Revierte D-18. **Hecho:** PR https://github.com/MarBL00126/diagnosticar-question-agent/pull/1 (`feat/rerank-negaciones` sobre `feat/agente-v2`). La flag es `PREGUNTAS_RERANK_NEGATIONS` y viene activada: la API actual ignora campos desconocidos (`RankRequest` es un `BaseModel` sin `extra`), así que no rompe nada antes de que se actualice | MarBL00126/diagnosticar-question-agent | Falta que Mariano revise el PR y lo mergee |
| 3 | Web: subir `QUESTION_AGENT_COMMIT` al commit del agente con el paso 2. Nada más cambia | MateAlv/diagnostic.ar, `.github/question-agent.env` | Equipo |
| 4 | Staging: desplegar con `MODEL_ROUTED=true`, que ya corre la imagen fijada por `model.lock`, y hacer las verificaciones | staging | Quien despliega |
| 5 | Producción: hoy `/genphenai` va por túnel a brainy (`docker-compose.prod.yml:75-93`). Hay que **(a)** enrutar producción a la imagen fijada, como staging, o **(b)** actualizar el servicio de brainy para que cargue el bundle y acepte el campo | nodo0 / brainy | Quien despliega, con OK de Mateo |

**Rollout sugerido** (decide Mateo):
1. Staging.
2. Producción en **modo sombra**: calcular ambos órdenes, registrar los dos y
   mostrar el de v3.0.
3. Activar.

El paso 2 da datos de uso real sin riesgo.

## Verificaciones (checklist)
- [ ] `/healthz` informa el tag `rerank-v1.0.0` y el sha256 del bundle.
- [ ] Si el bundle no coincide con el sha256 fijado, el servicio **no
      arranca**.
- [ ] Un pedido **sin** `excluded_hpo_ids`, o con la lista vacía, devuelve
      **exactamente** lo mismo que v3.0. Comparar scores y orden de punta a
      punta.
- [ ] Un pedido con negaciones anotadas a genes del top mueve esos genes hacia
      abajo. La respuesta trae `rerank: "rr-v1[neg=0.5]"` y
      `excluded_hpo_count`.
- [ ] Los ids desconocidos aparecen en `unknown_excluded_hpo_ids` y no mueven
      nada.
- [ ] `results`, `specialties` y `confidence` salen de la misma distribución
      re-rankeada.
- [ ] Latencia: el p95 del endpoint sube como mucho unos 10 ms.
- [ ] El agente no manda negaciones del texto ni "No sé" (revisar los logs de
      una sesión de prueba). El PR #1 del agente ya lo testea.
- [ ] Con la API actualizada, la respuesta trae `rerank`, y solo entonces el
      agente le dice al usuario que los "no" mueven la lista.

## Vuelta atrás
- **Inmediata, sin redeploy:** el agente deja de mandar `excluded_hpo_ids`. La
  salida vuelve a ser la de v3.0 bit a bit.
- **Con redeploy:** sacar las líneas `RERANK_*` de `model.lock`, o volver a
  enrutar a brainy sin el bundle.

## Restricciones
- No tocar nada bajo `GenPhenAI/`, que es upstream y de solo lectura.
- No reconstruir ni modificar el bundle ni el KB. Se usan los publicados, con
  sus sha256.
- Commits y PRs sin co-autoría ni menciones de IA.
- Los cambios en la API son aditivos: el campo es opcional y los clientes
  actuales no cambian.

## Decisiones abiertas, para Mateo y el equipo
1. Producción: ¿opción (a), enrutar a la imagen fijada, u opción (b),
   actualizar brainy?
2. ¿Modo sombra antes de activar? Se recomienda que sí.
3. Mariano: revisar el PR #1 del agente. Revierte D-18 y deja una nota fechada en `docs/NEGACIONES.md`. Hay un punto abierto ahí: si también se bloquean los ancestros de un "no" anterior.
4. Producto: ¿la lista "Con tus respuestas" muestra el orden re-rankeado por
   defecto (`preferAnswersList`)? Hoy está apagada.
