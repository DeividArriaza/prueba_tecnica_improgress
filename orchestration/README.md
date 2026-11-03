# Orquestación

Coloca aquí la implementación de tu estrategia de orquestación y documenta la
justificación en `docs/ORQUESTACION.md`.

Ejemplos de estructura según la herramienta que elijas:

- **Airflow**: `orchestration/dags/etl_electoral.py`
- **Prefect**: `orchestration/flows/etl_electoral.py` + `prefect.yaml`
- **Dagster**: `orchestration/definitions.py`
- **cron + contenedor**: `orchestration/crontab` + entrypoint
- **GitHub Actions**: `.github/workflows/etl.yml`

Requisito mínimo: dos flujos programables — carga histórica (una vez) y
actualización diaria del padrón — con dependencias, reintentos y capacidad de
reprocesar una fecha específica.
