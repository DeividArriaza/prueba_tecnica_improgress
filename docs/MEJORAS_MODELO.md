# Análisis crítico del modelo de datos

> Plantilla a completar por el candidato. El modelo analizado es el de
> `sql/01_ddl_electoral.sql`, documentado en `docs/BASE_DE_DATOS.md`.

## 1. Problemas identificados

Ordenados por impacto (mayor a menor).

| # | Problema | Tabla / columna afectada | Consecuencia concreta | Severidad |
|---|---|---|---|---|
| 1 | | | | Alta / Media / Baja |

## 2. Modelo propuesto

Explica el enfoque elegido (normalizado, dimensional, por capas) y por qué.

### 2.1 DER propuesto

```mermaid
erDiagram
    %% Reemplazar con tu propuesta
```

### 2.2 Cambios clave respecto al modelo actual

| # | Cambio | Qué resuelve | Costo o riesgo |
|---|---|---|---|
| 1 | | | |

### 2.3 Historización

¿Cómo representarías en el tiempo los cambios de asignación de un empadronado
y los cambios en los atributos de un centro de votación? ¿Qué preguntas de
negocio habilita eso que hoy no se pueden responder?

## 3. Plan de migración

Pasos para pasar del modelo actual al propuesto sin interrumpir el consumo del
dashboard.

| Paso | Acción | Reversible | Riesgo |
|---|---|---|---|
| 1 | | | |
