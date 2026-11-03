"""Persistencia de una ejecución. Mantiene PostgreSQL fuera del coordinador."""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from src.utils.db import get_connection


class PostgresRunStore:
    @contextmanager
    def transaction(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(7302026)")
            yield conn

    def catalog(self, conn):
        with conn.cursor() as cur:
            # Sin FK, mantener estable el catálogo hasta confirmar dependientes.
            cur.execute("LOCK TABLE electoral.centros_votacion IN SHARE MODE")
            cur.execute(
                "SELECT codigo_centro_votacion,codigo_departamento,codigo_municipio FROM electoral.centros_votacion"
            )
            rows = cur.fetchall()
        if len({r[0] for r in rows}) != len(rows):
            raise ValueError("Catálogo destino contiene claves duplicadas")
        if not rows:
            raise ValueError("Cargar centros antes de las fuentes dependientes")
        fields = ["codigo_centro_votacion", "codigo_departamento", "codigo_municipio"]
        return {r[0]: dict(zip(fields, r)) for r in rows}

    def record_success(self, conn, name, fecha, digest, metrics):
        compact = json.dumps(
            {
                "s": "ok",
                "d": fecha,
                "r": metrics["leidas"],
                "v": metrics["validas"],
                "x": metrics["rechazadas"],
                "dup": metrics["duplicadas"],
                "w": metrics["advertencias"],
                "i": metrics["insertadas"],
                "u": metrics["actualizadas"],
                "t": metrics["segundos"],
                "id": metrics["run_id"],
            },
            separators=(",", ":"),
        )
        if len(compact) > 255:
            raise ValueError("Resumen de carga excede el DDL")
        now = datetime.now(timezone.utc).isoformat()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO electoral.carga_log(proceso,observacion,fecha) VALUES (%s,%s,%s)",
                (name, compact, now),
            )
            if name == "empadronados":
                cur.execute(
                    "INSERT INTO electoral.carga_log(proceso,observacion,fecha) VALUES (%s,%s,%s)",
                    (
                        "watermark:empadronados",
                        json.dumps({"fecha": fecha, "sha256": digest}),
                        now,
                    ),
                )
