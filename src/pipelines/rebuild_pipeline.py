"""Reconstrucción cronológica aislada, publicada atómicamente sin retroceder el corte."""

from datetime import timedelta
from hashlib import sha256
import json
from time import perf_counter
from uuid import uuid4
from src.config.settings import PROJECT_ROOT, load_config
from src.config.sources import snapshot_files, parse_cutoff
from src.loaders.postgres_loader import FullLoader, merge, watermark
from src.pipelines.factory import build_pipeline
from src.utils.run_store import PostgresRunStore


def save_metrics(metrics):
    folder = PROJECT_ROOT / "output" / metrics["run_id"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def rebuild_padron(hasta):
    end = parse_cutoff(hasta)
    available = dict(snapshot_files())
    selected = sorted(value for value in available if value <= hasta)
    if not selected or hasta not in available:
        raise FileNotFoundError(f"No hay archivos para reconstruir hasta {hasta}")
    start = parse_cutoff(selected[0])
    dates = []
    current = start
    while current <= end:
        value = current.isoformat()
        if value not in available:
            raise FileNotFoundError(f"Falta snapshot {value}; reconstrucción cancelada")
        dates.append(value)
        current += timedelta(days=1)

    started = perf_counter()
    attempts = []
    summary = {
        "run_id": uuid4().hex,
        "pipeline": "rebuild-padron",
        "fecha": hasta,
        "desde": start.isoformat(),
        "estado": "iniciado",
    }
    store = PostgresRunStore()
    try:
        with store.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "LOCK TABLE electoral.empadronados IN SHARE ROW EXCLUSIVE MODE"
                )
                latest = watermark(conn)
                if latest and hasta < latest:
                    raise ValueError(
                        f"La reconstrucción debe llegar al watermark {latest} o superarlo"
                    )
                cur.execute(
                    "SELECT observacion FROM electoral.carga_log WHERE proceso='watermark:empadronados'"
                )
                history = [json.loads(row[0])["fecha"] for row in cur.fetchall()]
                if history and selected[0] > min(history):
                    raise ValueError(
                        "Faltan archivos del inicio del historial procesado"
                    )
                cur.execute("SELECT count(*) FROM electoral.empadronados")
                if not latest and cur.fetchone()[0]:
                    raise ValueError(
                        "Padrón existente sin watermark: revisar su procedencia antes de reconstruir"
                    )
                cur.execute(
                    "CREATE TEMP TABLE replay_empadronados (LIKE electoral.empadronados INCLUDING DEFAULTS) ON COMMIT DROP"
                )

            source = load_config()["sources"]["empadronados"]
            shadow_config = dict(source, target_table="pg_temp.replay_empadronados")
            for value in dates:
                pipeline = build_pipeline("empadronados", value)
                # La tabla temporal no es el padrón vigente y no necesita su guardia de fechas.
                pipeline.loader = FullLoader(shadow_config)
                attempts.append(
                    pipeline.run(connection=conn, audit_name="replay:empadronados")
                )

            columns = source["columns"]
            with conn.cursor() as cur:
                # Columnas de YAML validadas mediante el mismo componedor que el loader.
                from psycopg2 import sql

                cur.execute(
                    sql.SQL("SELECT {} FROM replay_empadronados").format(
                        sql.SQL(",").join(map(sql.Identifier, columns))
                    )
                )
                rows = [dict(zip(columns, row)) for row in cur.fetchall()]
                cur.execute(
                    "DELETE FROM electoral.empadronados t WHERE NOT EXISTS (SELECT 1 FROM replay_empadronados s WHERE s.id_empadronado=t.id_empadronado)"
                )
                deleted = cur.rowcount
            changed = merge(
                conn, source["target_table"], source["natural_key"], columns, rows
            )
            summary.update(
                {
                    field: sum(m[field] for m in attempts)
                    for field in (
                        "leidas",
                        "validas",
                        "rechazadas",
                        "duplicadas",
                        "advertencias",
                    )
                }
            )
            summary.update(
                changed,
                eliminadas=deleted,
                publicadas=len(rows),
                cargadas=changed["insertadas"] + changed["actualizadas"],
                ejecuciones=[m["run_id"] for m in attempts],
                sha256=attempts[-1]["sha256"],
                sha256_lote=sha256(
                    json.dumps([(m["fecha"], m["sha256"]) for m in attempts]).encode()
                ).hexdigest(),
                segundos=round(perf_counter() - started, 3),
            )
            store.record_success(
                conn, "empadronados", hasta, summary["sha256"], summary
            )
        summary["estado"] = "ok"
        for metrics in attempts:
            metrics["estado"] = "ok"
            metrics["reconstruccion"] = summary["run_id"]
            save_metrics(metrics)
        return summary
    except Exception as exc:
        summary.update(
            estado="error",
            error=str(exc),
            cargadas=0,
            insertadas=0,
            actualizadas=0,
            eliminadas=0,
        )
        for metrics in attempts:
            metrics.update(estado="revertido", cargadas=0, insertadas=0, actualizadas=0)
            save_metrics(metrics)
        raise
    finally:
        summary["segundos"] = round(perf_counter() - started, 3)
        save_metrics(summary)
