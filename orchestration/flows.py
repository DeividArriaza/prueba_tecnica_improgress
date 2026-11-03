"""Prefect coordina; el ETL funciona también sin Prefect."""

from datetime import date, datetime
import json
import os
from pathlib import Path
import sys
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import psycopg2
from prefect import flow, task
from prefect.schedules import Cron
from main import run_historico, run_empadronados
from src.config.settings import PROJECT_ROOT, load_config
from src.config.sources import snapshot_files
from src.pipelines.rebuild_pipeline import rebuild_padron
from src.loaders.postgres_loader import watermark
from src.utils.db import get_connection

SETTINGS = load_config()["orchestration"]


def alert(flow, flow_run, state):
    message = {
        "flow": flow.name,
        "run": str(flow_run.id),
        "state": state.name,
        "message": str(state.message),
    }
    print("ALERTA " + json.dumps(message), file=sys.stderr)
    endpoint = os.getenv("ALERT_WEBHOOK_URL")
    if endpoint:
        try:
            with urlopen(
                Request(
                    endpoint,
                    data=json.dumps(message).encode(),
                    headers={"Content-Type": "application/json"},
                ),
                timeout=10,
            ) as response:
                response.read()
        except Exception as exc:
            print(f"No se pudo entregar alerta: {exc}", file=sys.stderr)


def retry_transient(task, task_run, state):
    try:
        state.result()
    except (
        psycopg2.OperationalError,
        psycopg2.InterfaceError,
        psycopg2.errors.DeadlockDetected,
        psycopg2.errors.SerializationFailure,
    ):
        return True
    except Exception:
        return False
    return False


@task(
    retries=SETTINGS["retries"],
    retry_delay_seconds=SETTINGS["retry_delay_seconds"],
    retry_condition_fn=retry_transient,
)
def historical_task():
    return run_historico()


@task(
    retries=SETTINGS["retries"],
    retry_delay_seconds=SETTINGS["retry_delay_seconds"],
    retry_condition_fn=retry_transient,
)
def daily_task(fecha):
    return run_empadronados(fecha)


@flow(name="electoral-historico", on_failure=[alert])
def historical_flow():
    return historical_task()


@flow(name="electoral-padron", on_failure=[alert])
def daily_flow(fecha=None):
    latest = prepare_daily()
    if fecha:
        return daily_task(fecha)
    today = datetime.now(ZoneInfo(SETTINGS["timezone"])).date().isoformat()
    dates = [
        value
        for value, _ in snapshot_files()
        if value <= today and (latest is None or value > latest)
    ]
    if not dates:
        raise FileNotFoundError(
            "No hay archivos nuevos de padrón; revisar llegada de la fuente"
        )
    return [daily_task(value) for value in dates]


@task(
    retries=SETTINGS["retries"],
    retry_delay_seconds=SETTINGS["retry_delay_seconds"],
    retry_condition_fn=retry_transient,
)
def prepare_daily():
    """La conexión inicial participa de la misma política de reintentos."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM electoral.centros_votacion")
            if not cur.fetchone()[0]:
                raise ValueError("Ejecutar primero electoral-historico")
        latest = watermark(conn)
    return latest


@task(
    retries=SETTINGS["retries"],
    retry_delay_seconds=SETTINGS["retry_delay_seconds"],
    retry_condition_fn=retry_transient,
)
def rebuild_task(hasta):
    return rebuild_padron(hasta)


@flow(name="electoral-reconstruccion", on_failure=[alert])
def rebuild_flow(hasta):
    return rebuild_task(hasta)


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "daily"
    if command == "serve":
        from prefect import serve

        serve(
            historical_flow.to_deployment(name="historico"),
            rebuild_flow.to_deployment(name="reconstruir"),
            daily_flow.to_deployment(
                name="diario",
                schedules=[
                    Cron(
                        f"{SETTINGS['minute']} {SETTINGS['hour']} * * *",
                        timezone=SETTINGS["timezone"],
                    )
                ],
            ),
            pause_on_shutdown=False,
        )
    elif command == "historico":
        historical_flow()
    elif command == "daily":
        daily_flow(sys.argv[2] if len(sys.argv) > 2 else None)
    elif command == "rebuild" and len(sys.argv) == 3:
        rebuild_flow(sys.argv[2])
    else:
        raise SystemExit(
            "Usar: serve | historico | daily [YYYY-MM-DD] | rebuild YYYY-MM-DD"
        )
