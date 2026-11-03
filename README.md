# ETL electoral - prueba técnica junior

Lee CSV, limpia representaciones, valida reglas y carga PostgreSQL sin duplicar entidades al repetir una ejecución. Incluye histórico, padrón por fecha y orquestación Prefect. El DDL entregado se conserva sin cambios.

Reglas y límites: [DECISIONES.md](DECISIONES.md). Modelo propuesto: [MEJORAS_MODELO.md](docs/MEJORAS_MODELO.md).

## Ejecutar con Docker

Requisitos: Git, Docker Desktop iniciado con contenedores Linux; puertos 5432 y, para Prefect, 4200 disponibles. Comandos para PowerShell:

```powershell
git clone https://github.com/DeividArriaza/prueba_tecnica_improgress.git
cd prueba_tecnica_improgress
git switch feature/etl
Copy-Item .env.example .env
```

Editar `.env` y cambiar POSTGRES_PASSWORD. Variables: POSTGRES_HOST=localhost, POSTGRES_PORT=5432, POSTGRES_DB=electoral_db, POSTGRES_USER=etl_user, contraseña elegida y LOG_LEVEL=INFO. No versionar .env. Compose cambia host a postgres y puerto a 5432 dentro de los contenedores. POSTGRES_PORT permite cambiar el puerto publicado en el equipo.

```powershell
docker compose up -d --wait postgres
docker compose build etl
docker compose run --rm etl validate
docker compose run --rm etl load-historico
docker compose run --rm etl backfill --desde 2026-03-02 --hasta 2026-03-04
# Repetir el último día debe escribir cero filas:
docker compose run --rm etl load-empadronados --fecha 2026-03-04
```

El DDL se ejecuta automáticamente solo al crear un volumen vacío. No ejecutarlo sobre una base con información: contiene DROP SCHEMA. `docker compose down` conserva los datos. El contenedor ETL incorpora CSV y código al construir la imagen: reconstruir si cambian. El scheduler monta data en modo lectura.

## Pruebas

```powershell
docker compose run --rm --entrypoint python etl -m pytest -q
# Integración: requiere permiso CREATEDB; usa bases temporales propias:
docker compose run --rm -e RUN_DB_TESTS=1 --entrypoint python etl -m pytest -q
```

Las pruebas no aplican el DDL destructivo sobre electoral_db. El usuario creado por este Compose tiene permisos para crear bases temporales.

## Python local

Python 3.10+ para ETL básico; Prefect 3.9.1 requiere Python >=3.11,<3.16. Python 3.12 recomendado y usado en Docker. PostgreSQL 14+.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py validate
.\.venv\Scripts\python.exe main.py load-historico
.\.venv\Scripts\python.exe main.py load-empadronados --fecha 2026-03-02
.\.venv\Scripts\python.exe main.py load-empadronados --fecha 2026-03-03
.\.venv\Scripts\python.exe main.py load-empadronados --fecha 2026-03-04
.\.venv\Scripts\python.exe -m pytest -q
```

Linux/macOS: usar `.venv/bin/python`. Para PostgreSQL sin Docker, crear una base vacía y ejecutar `psql -d electoral_db -f sql/01_ddl_electoral.sql` únicamente en esa base nueva. Ajustar .env a sus credenciales.

## Orquestación

```powershell
docker compose --profile orchestration up -d --build prefect-server scheduler
```

Abrir http://localhost:4200. El scheduler registra histórico manual y padrón diario a las 02:00 America/Guatemala. Inicializar histórico antes del padrón:

```powershell
docker compose run --rm --entrypoint python scheduler -m orchestration.flows historico
docker compose run --rm --entrypoint python scheduler -m orchestration.flows daily 2026-03-04
```

Ver [ORQUESTACION.md](docs/ORQUESTACION.md). Para Prefect local instalar requirements-orchestration.txt; el ETL básico funciona sin esas dependencias.

## Consultar datos y evidencia

```powershell
docker compose exec postgres psql -U etl_user -d electoral_db
```

En psql: `\dt electoral.*`, consultas de [02_verificacion.sql](sql/02_verificacion.sql), salir con `\q`. En pgAdmin/DBeaver: localhost, puerto de .env, base electoral_db, usuario etl_user y contraseña de .env.

Cada ejecución deja output/<run_id>/metrics.json, quarantine.jsonl y warnings.jsonl cuando alcanza validación. Fallos anteriores pueden tener solo métricas. output no se versiona. Los éxitos se resumen en electoral.carga_log; watermark:empadronados identifica la última fecha confirmada. SHA-256 identifica el archivo procesado.

## Resultados esperados

| Fuente | Leídas | Válidas | Rechazadas | Copias exactas |
|---|---:|---:|---:|---:|
| Centros | 98 | 95 | 2 | 1 |
| Resultados | 20.328 | 11.564 | 8.669 | 95 |
| Padrón 02/03 | 18.025 | 17.625 | 375 | 25 |
| Padrón 03/03 | 18.156 | 17.756 | 375 | 25 |
| Padrón 04/03 | 18.302 | 17.898 | 379 | 25 |

Después de los tres días: 95 centros, 834 mesas, 11.564 resultados y 17.932 empadronados. Se conservan 34 versiones anteriores válidas cuyo último registro fue rechazado. Las 11.564 filas de resultados admitidas tienen advertencia de conciliación: no se inventaron correcciones y su carga no certifica las cifras.

Una fecha menor que el watermark se rechaza. Para corregir fechas antiguas ejecutar `docker compose run --rm etl rebuild-padron --hasta 2026-03-04` (usar el corte vigente o uno posterior). Reconstruye todos los snapshots diarios desde el inicio en tabla temporal y publica atómicamente; cualquier fallo conserva el padrón anterior. Mantiene created_at de personas existentes y exige conservar los archivos originales del intervalo. No se eliminan personas por ausencia ni se modifica el DDL para guardar historia.

## Organización

src/extractors lee; src/transformers limpia; src/quality valida; src/loaders guarda; src/pipelines coordina. src/config/config.yaml define fuentes, columnas, categorías y horario. Las credenciales solo se leen del entorno. orchestration contiene Prefect y tests contiene pruebas unitarias e integración.


## Verificación completa y recuperación

La suite final contiene 32 pruebas, aprobadas localmente y en Docker con integración. Para ejecutar también las pruebas de Prefect:

```powershell
docker compose run --rm -e RUN_DB_TESTS=1 --entrypoint python scheduler -m pytest -q
# Reprocesar archivos corregidos sin deshacer cambios posteriores:
docker compose run --rm etl rebuild-padron --hasta 2026-03-04
```

El ETL básico omite las pruebas operativas si Prefect no está instalado. La reconstrucción necesita todos los snapshots desde el inicio hasta el corte vigente o posterior; un archivo faltante o inválido revierte el intervalo entero. No se modifican los CSV ni el DDL original.
