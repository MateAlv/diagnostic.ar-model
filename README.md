# diagnostic.ar-model

El modelo que usa [diagnostic.ar](https://github.com/MateAlv/diagnosticar-plataforma) para ordenar los genes según los síntomas del paciente.

Parte de GenPhenia v3.0, de Gianlucca Colangelo ([GraPhens](https://github.com/gianluccacolangelo/GraPhens)). La versión que corre hoy, **model-v4.0.0**, es esa misma red reentrenada desde cero en [diagnostic.ar-training](https://github.com/MateAlv/diagnostic.ar-training), más una capa que tiene en cuenta el sexo y la edad del paciente.

Acá está el código para empaquetar, probar y publicar cada versión. Los modelos listos para usar están en las versiones publicadas del repo (Releases). La [API](https://github.com/MateAlv/diagnostic.ar-api) baja la versión fijada y verifica su sha256 antes de usarla.

En `docs/` hay una nota por cada versión: qué cambia, con qué evidencia y sus límites.

Es parte del Trabajo Profesional de Ingeniería en Informática (FIUBA) de Mateo Alvarez, Mariano Brizuela López, Gonzalo Bustamante y Lucía Lourengo Caridade.

## Probarlo

```bash
pip install -e ".[test]"
pytest
```

## Datos

Usa la ontología HPO, casos publicados de phenopacket-store y datos de Orphanet (CC BY 4.0), con sus versiones fijadas en cada nota de `docs/`.

## Licencia

GPL-3.0. La carpeta `vendor/genphenia_inference_engine/` es el motor de GenPhenia, de Gianlucca Colangelo, y no está bajo esta licencia.
