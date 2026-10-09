# HANDOFF: ft-v1.1 en producción, primero en modo sombra

Para el agente que despliega en producción, **cuando Mateo lo decida**. Fecha: 2026-10-09.
Hasta entonces producción no se toca.

## Estado

| Componente | Staging | Producción |
|---|---|---|
| `ft-v1.1.0` (ft-v1.1-confirmed) sobre `model-v3.0.0` | **encendido** (`FT_V11_ENABLED=true`) | **apagado**; espera la decisión de Mateo |
| `rerank-v1.0.0` (rr-v1, "no" del agente) | reemplazado por ft-v1.1 mientras el flag está prendido | apagado (HANDOFF-deploy-prod-q2b.md) |

Qué es, con qué evidencia y sus límites: [ft-v1.1.md](ft-v1.1.md). Los resultados de
staging están en el PR de diagnostic.ar-api que lo integra.

## Por qué modo sombra primero

- Los datos de la app no son los del entrenamiento:
  - el sexo y la edad salen del paso 1 del asistente;
  - la edad de inicio sale de "Precisar";
  - los términos excluidos son los "no" del agente de preguntas.
- Su efecto sobre respuestas de entrevista no está medido (ADR-0018, "Inputs in the app").
- El residuo solo baja genes, así que el riesgo es acotado, pero no nulo: está el artefacto de OFD1, F8, SLC9A6 y THOC2 en mujeres.

## Pasos sugeridos

1. **Sombra.** Calcular los dos órdenes y registrar los dos, pero mostrar el de E0.
   - Hace falta un modo nuevo en `services/genphenai` de diagnostic.ar-api, por ejemplo `FT_V11_MODE=shadow`. Hoy el flag es encendido o apagado.
   - El registro no debe guardar los términos HPO ni datos del paciente. Alcanza con:
     - el rank de E0 y de ft de los primeros genes;
     - cuántos genes bajaron;
     - qué rasgos se activaron.
2. **Revisar** con Mateo un período de sombra:
   - cuántas búsquedas cambian el primer gen y cuáles;
   - si aparecen OFD1, F8, SLC9A6 o THOC2 en pacientes mujeres;
   - si los "no" del agente activan `neg_obligate` con frecuencia.
3. **Encender** con `FT_V11_ENABLED=true` en el entorno del modelo de producción, si Mateo lo aprueba.
   - Producción hoy no corre la imagen fijada: `/genphenai` va a brainy por el túnel (HANDOFF-deploy-prod-q2b.md). Enrutar a la imagen es parte de este paso.

## Verificaciones

- [ ] `/healthz` informa `ft-v1.1-confirmed`, su sha256 y el estado del flag.
- [ ] Con el flag apagado, una búsqueda da exactamente el orden y los puntajes de v3.0.
- [ ] Sin sexo, edad, edad de inicio ni excluidos, con el flag prendido, también.
- [ ] Un caso con un gen limitado al otro sexo en el top 10 lo baja.
- [ ] La latencia p95 de `/rank-genes` sigue en línea con staging.

## Vuelta atrás

- **Inmediata:** `FT_V11_ENABLED=false` y recrear el contenedor del modelo. No hace falta construir otra imagen.
- **Completa:** sacar `FT_*` de `model.lock` en diagnostic.ar-api y volver a construir.

## Restricciones

- No reconstruir ni editar el bundle: se usa el publicado, con su sha256.
- No usar `dist/ft-v1.1-prod/` (sin enmascarar).
- Commits y PRs sin co-autoría ni menciones de IA.
