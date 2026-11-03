# ETL — Sistema de análisis de resultados electorales

Repositorio base de la prueba técnica para **Ingeniero de Datos Junior**.
El enunciado completo está en [`ENUNCIADO.md`](ENUNCIADO.md).

> **Candidato:** este README es un punto de partida. Debes actualizarlo para que
> refleje tu solución final y permita a un tercero ejecutar todo desde cero.

## Contenido del repositorio

```
.
├── ENUNCIADO.md              # qué se pide y cómo se evalúa
├── DECISIONES.md             # (a completar) supuestos y hallazgos
├── data/
│   ├── historico/            # carga única
│   └── empadronados/         # fuente viva, un archivo por día
├── docs/
│   ├── BASE_DE_DATOS.md      # DER + diccionario de datos del modelo actual
│   ├── der_modelo_actual.dbml
│   ├── MEJORAS_MODELO.md     # (a completar) análisis crítico del modelo
│   └── ORQUESTACION.md       # (a completar) estrategia de orquestación
├── sql/
│   └── 01_ddl_electoral.sql  # modelo entregado — no modificar
├── src/
│   ├── config/               # settings + config.yaml
│   ├── extractors/           # lectura de fuentes
│   ├── transformers/         # limpieza y estandarización
│   ├── loaders/              # carga full e incremental
│   ├── quality/              # validaciones
│   ├── pipelines/            # composición de los flujos
│   └── utils/                # logging y acceso a base de datos
├── orchestration/            # (a completar) implementación del orquestador
├── tests/
├── main.py                   # CLI del ETL
├── docker-compose.yml
└── Dockerfile
```

## Requisitos

- Python 3.10+
- PostgreSQL 14+ (local o vía Docker)
- Docker y Docker Compose (opcional)

## Puesta en marcha

### 1. Clonar y preparar el entorno

```bash
git clone <url-del-repo>
cd prueba-tecnica-etl

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # ajustar credenciales
```

### 2. Crear la base de datos

**Opción A — con Docker (el DDL se ejecuta automáticamente al iniciar):**

```bash
docker compose up -d postgres
docker compose logs -f postgres   # esperar "database system is ready"
```

**Opción B — PostgreSQL local:**

```bash
createdb electoral_db
psql -d electoral_db -f sql/01_ddl_electoral.sql
```

Verificar:

```bash
psql -d electoral_db -c "\dt electoral.*"
```

### 3. Ejecutar la carga histórica (una sola vez)

```bash
python main.py load-historico
```

### 4. Ejecutar la carga incremental del padrón

Un día a la vez, en orden:

```bash
python main.py load-empadronados --fecha 2026-03-02
python main.py load-empadronados --fecha 2026-03-03
python main.py load-empadronados --fecha 2026-03-04
```

### 5. Ejecutar las pruebas

```bash
pytest -q
```

### 6. Ejecutar la orquestación

> A documentar por el candidato según la herramienta elegida.

## Estado de los flujos

| Flujo | Modo | Comando | Estado |
|---|---|---|---|
| Centros de votación | Carga única | `load-historico` | ⬜ pendiente |
| Resultados históricos | Carga única | `load-historico` | ⬜ pendiente |
| Padrón (empadronados) | Incremental diaria | `load-empadronados --fecha` | ⬜ pendiente |
