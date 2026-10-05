# HANDOFF: rerank-v1.1.0 (edad de inicio) en staging

Para el agente que despliega en nodo0. Fecha: 2026-10-05. Continúa
`HANDOFF-deploy-staging-rerank-q2b.md`: ese cambio (re-ranker con negaciones en
la API) va primero, y esto lo actualiza a v1.1. Nota de release:
[rerank-v1.1.0.md](rerank-v1.1.0.md).

**Antes de empezar:** el release `rerank-v1.1.0` y su asset tienen que existir.
Se crean solo con el OK explícito de Mateo. Si el release no existe, no se puede
fijar el bundle: avisar a Mateo y esperar.

## Decisiones de Mateo (2026-10-05)
| Tema | Decisión |
|---|---|
| Alcance | **Solo staging.** Producción no se toca |
| Producción, después | Enrutar `/genphenai` a la imagen fijada por `model.lock`, como staging |
| Modo sombra | No |

## Qué hay que saber de la evidencia
- Gate EXP-B-006: PASA (no regresión en pacientes reales, identidades en 0).
- **No hay ganancia medible en pacientes reales:** candidato − rr-v1
  −0,0003 [−0,0019, +0,0008]. La ganancia es solo simulada
  (+0,0021 [+0,0007, +0,0035] en S3-v3b-dev).
- No presentar la edad de inicio como una mejora comprobada. Staging sirve para
  verificar la integración, no para medir eficacia.

## Cambios en MateAlv/diagnostic.ar-api, `services/genphenai`

1. **Fijar el bundle** en `model.lock`:
   - `RERANK_TAG=rerank-v1.1.0`
   - `RERANK_ASSET=rerank-v1.1.tar.gz`
   - `RERANK_SHA256=cf4cc0d28b7a391bea5df21fbdb00f8c9af85d626e5b22e9919ab6dc58e515a3`
   (verificarlo contra el `rerank-v1.1.tar.gz.sha256` del release). El servicio
   no arranca si no coincide.
2. **Traer el código** de `src/diagnostic_ar_model/rerank/` del tag
   `rerank-v1.1.0`, con el mismo mecanismo que v1.0.0. Hay un archivo nuevo,
   `onset.py`. Solo depende de numpy.
3. **Leer los tres campos opcionales de `RankRequest`** y pasarlos al helper:
   - `onset_hpo_id: Optional[str] = None`
   - `onset_age_years: Optional[float] = None`
   - `symptom_onsets: List[dict] = []`, con elementos
     `{hpo_id, onset_hpo_id, onset_age_years?}`

   Hay que declararlos de forma que un valor inválido no dé 422 (por ejemplo
   `Any`): el helper trata lo inválido como "sin edad de inicio".
   ```python
   years = rerank.onset_years(req.onset_hpo_id, req.onset_age_years, req.symptom_onsets)
   ```
4. **Pasar los años al re-ranker**, en el mismo punto donde hoy se pasan las
   negaciones (antes de pasar los genes a mayúsculas y de cortar el top k):
   ```python
   distribution = reranker.rerank_distribution(result["distribution"], excluded, years)
   ```
5. **Trazabilidad.**
   - Agregar a la respuesta `onset_years_used`: el número, o `null` si no hubo.
   - `rerank` pasa a informar `"rr-v1[neg=0.5,onset=0.25]"` (el `name` del
     `rerank.json`).
   - `/healthz` informa el tag `rerank-v1.1.0` y el sha256 del bundle.
6. **Tests de la API:** los de abajo.

La llamada inicial de la web, y toda llamada sin los campos, no cambia. Los
cambios son aditivos.

## Verificaciones en staging
- [ ] `/healthz` informa `rerank-v1.1.0` y el sha256 `cf4cc0d2…15a3`.
- [ ] Si el sha256 del bundle no coincide, el servicio no arranca.
- [ ] **Sin edad de inicio** (ningún campo, o campos inválidos o con clases
      desconocidas o que no son de edad, como HP:0034197), la respuesta es
      **idéntica** a la de `rerank-v1.0.0` con las mismas negaciones: mismo
      orden y mismos scores. `onset_years_used` es `null`. Sin negaciones, es la
      de v3.0.
- [ ] **Con edad de inicio, se mueven genes.** Mismo pedido con y sin
      `onset_age_years: 0.02`: cambian scores y orden, y `onset_years_used` es
      0.02. Probar también `onset_hpo_id` solo (HP:0011463 da 3.0) y
      `symptom_onsets` (gana el mínimo).
- [ ] Un id de edad de inicio desconocido no da error: `onset_years_used` es `null`.
- [ ] Las negaciones siguen funcionando igual que en v1.0.0.
- [ ] `results`, `specialties` y `confidence` salen de la misma distribución
      re-rankeada.
- [ ] El p95 de `/rank-genes` no sube más de unos 10 ms respecto de v1.0.0
      (la latencia del término de edad de inicio no está medida; informar el dato).
- [ ] El modal "Precisar" ofrece la edad de inicio y el pedido la manda.

## Vuelta atrás
- **Sin redeploy:** que la web deje de mandar los campos de edad de inicio (o
  `onset_years_used` queda en `null`): la salida es la de `rerank-v1.0.0`.
- **Con redeploy:** volver `model.lock` a `rerank-v1.0.0`, `rerank-v1.0.tar.gz`,
  sha256 `4b83f5e39e003aca2dde834948392800655102199f8af099985191b69f8e79e2`.

## Restricciones
- Solo staging. No tocar producción ni el servicio de brainy.
- No reconstruir ni modificar el bundle ni el KB.
- No tocar nada bajo `GenPhenAI/`.
- Commits y PRs sin co-autoría ni menciones de IA.
- Cambios de API solo aditivos.
